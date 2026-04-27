"""Validates ANALYTICAL_PLAN questions from Claude against the structural profile.

Every question that reaches the frontend has been checked:
  - All column names exist in the dataset
  - Aggregation is valid for the column's semantic role
  - Quality gates pass (not too many missing values, not a constant column)

If fewer than 2 questions pass, _universal_fallback() generates baseline charts
so the dashboard always has something to show.
"""

from __future__ import annotations

import logging
from typing import Any

from .semantic_types import SemanticRole

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Aggregation rules per semantic role
# ---------------------------------------------------------------------------

VALID_AGGS_BY_ROLE: dict[str, set[str]] = {
    SemanticRole.MEASURE_ADDITIVE:     {"sum", "mean", "count", "count_distinct"},
    SemanticRole.MEASURE_AVERAGE_ONLY: {"mean", "median"},   # NEVER sum
    SemanticRole.MEASURE_RATIO:        {"mean", "median"},
    SemanticRole.MEASURE_DERIVED:      set(),                # never use as a KPI metric
    SemanticRole.IDENTIFIER:           {"count", "count_distinct"},
    SemanticRole.BOOLEAN:              {"mean", "count"},    # mean of 0/1 = rate
    SemanticRole.DIMENSION_LOW:        {"count"},
    SemanticRole.DIMENSION_MEDIUM:     {"count"},
    SemanticRole.DIMENSION_HIGH:       {"count"},
    SemanticRole.TEMPORAL:             {"count"},            # only as dimension/time_col
    SemanticRole.TEXT_FREE:            set(),
    SemanticRole.CONSTANT:             set(),
    SemanticRole.EMPTY:                set(),
}

# Map ANALYTICAL_PLAN question types to frontend chart types
_TYPE_MAP: dict[str, str] = {
    "headline":    "headline",
    "ranking":     "bar",
    "composition": "bar",
    "comparison":  "bar",
    "trend":       "line",
}

MAX_RETRIES = 1  # explicit cap — never a loop


class CompilationError(Exception):
    pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compile_questions(
    questions: list[dict],
    profile: Any,  # DataProfile — Any to avoid circular import
) -> list[dict]:
    """Validate questions and return chart specs ready for the frontend.

    Drops invalid questions silently. Falls back to universal template if
    fewer than 2 valid specs result.
    """
    valid: list[dict] = []
    rejected: list[str] = []

    for q in questions:
        try:
            _validate_columns_exist(q, profile)
            _validate_agg_matches_role(q, profile)
            _validate_quality_gates(q, profile)
            valid.append(_to_chart_spec(q))
        except CompilationError as e:
            rejected.append(f"  {q.get('id','?')}: {e}")

    if rejected:
        logger.debug("Rejected questions:\n" + "\n".join(rejected))

    # Enforce max 1 headline — keep the highest-priority one
    headlines = [s for s in valid if s.get("question_type") == "headline"]
    others    = [s for s in valid if s.get("question_type") != "headline"]
    if len(headlines) > 1:
        headlines = sorted(headlines, key=lambda s: s.get("priority", 5))[:1]
    valid = headlines + others

    if len(valid) < 2:
        logger.info("Fewer than 2 valid specs — using universal fallback")
        valid = _universal_fallback(profile)

    return valid


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _validate_columns_exist(q: dict, profile: Any) -> None:
    metric_col = q.get("metric", {}).get("column")
    dimension = q.get("dimension")
    time_col = q.get("time_column")

    if metric_col and metric_col not in profile.columns:
        raise CompilationError(f"metric column '{metric_col}' not in dataset")
    if dimension and dimension not in profile.columns:
        raise CompilationError(f"dimension column '{dimension}' not in dataset")
    if time_col and time_col not in profile.columns:
        raise CompilationError(f"time_column '{time_col}' not in dataset")


def _validate_agg_matches_role(q: dict, profile: Any) -> None:
    metric = q.get("metric", {})
    col = metric.get("column")
    agg = metric.get("agg", "sum")

    if not col:
        return  # headline with no metric column is ok (count of rows)

    cp = profile.column_profiles.get(col)
    if cp is None:
        return

    role = getattr(cp, "semantic_role", SemanticRole.DIMENSION_HIGH)
    valid_aggs = VALID_AGGS_BY_ROLE.get(role, set())

    if not valid_aggs:
        raise CompilationError(
            f"column '{col}' has role '{role}' which cannot be used as a metric"
        )
    if agg not in valid_aggs:
        raise CompilationError(
            f"agg='{agg}' is invalid for '{col}' (role={role}, allowed={valid_aggs})"
        )


def _validate_quality_gates(q: dict, profile: Any) -> None:
    metric_col = q.get("metric", {}).get("column")
    dimension = q.get("dimension")

    if metric_col:
        cp = profile.column_profiles.get(metric_col)
        if cp and cp.missing_pct > 50:
            raise CompilationError(f"metric column '{metric_col}' is {cp.missing_pct}% missing")

    if dimension:
        cp = profile.column_profiles.get(dimension)
        if cp and cp.unique_count <= 1:
            raise CompilationError(f"dimension '{dimension}' has only 1 unique value")


# ---------------------------------------------------------------------------
# Chart spec builder
# ---------------------------------------------------------------------------

def _to_chart_spec(q: dict) -> dict:
    """Convert a validated ANALYTICAL_PLAN question to a legacy chart spec dict."""
    q_type = q.get("type", "ranking")
    chart_type = _TYPE_MAP.get(q_type, "bar")

    metric = q.get("metric", {})
    metric_col = metric.get("column", "")
    agg = metric.get("agg", "count")

    dimension = q.get("dimension") or ""
    time_col = q.get("time_column") or ""

    # For trend charts the x-axis is the time column
    x_col = time_col if q_type == "trend" else dimension
    y_col = metric_col

    if not x_col and not y_col:
        raise CompilationError("question has neither dimension nor metric column")

    # headline → still use bar layout but flagged for KPI card rendering
    return {
        "type": chart_type,
        "question_type": q_type,
        "title": q.get("title", ""),
        "description": q.get("narrative", ""),
        "x_col": x_col,
        "y_col": y_col,
        "agg": agg,
        "sort": "none" if q_type == "trend" else "desc",
        "limit": q.get("top_n", 10),
        "time_unit": q.get("granularity") if q_type == "trend" else None,
        "format": q.get("format", "number"),
        "priority": q.get("priority", 5),
    }


# ---------------------------------------------------------------------------
# Universal fallback
# ---------------------------------------------------------------------------

def _universal_fallback(profile: Any) -> list[dict]:
    """Always produces ≥1 chart even when Claude's plan is fully rejected.

    Strategy (in order):
    1. One bar chart per DIMENSION_LOW column (count by category)
    2. One mean chart per MEASURE_ADDITIVE or MEASURE_AVERAGE_ONLY column
    3. Time series if any TEMPORAL column exists
    If zero numeric columns: count by top 2-3 DIMENSION_LOW columns only.
    """
    specs: list[dict] = []

    dimensions = [
        c for c in profile.columns
        if getattr(profile.column_profiles.get(c), "semantic_role", "") == SemanticRole.DIMENSION_LOW
        and profile.column_profiles[c].unique_count > 1
    ]

    additive = [
        c for c in profile.numeric_columns
        if getattr(profile.column_profiles.get(c), "semantic_role", "") in (
            SemanticRole.MEASURE_ADDITIVE, SemanticRole.MEASURE_AVERAGE_ONLY
        )
    ]

    temporal = [
        c for c in profile.columns
        if getattr(profile.column_profiles.get(c), "semantic_role", "") == SemanticRole.TEMPORAL
    ]

    # Bar charts: metric × dimension
    for dim in dimensions[:3]:
        if additive:
            metric_col = additive[0]
            role = getattr(profile.column_profiles[metric_col], "semantic_role", "")
            agg = "mean" if role == SemanticRole.MEASURE_AVERAGE_ONLY else "sum"
            specs.append({
                "type": "bar", "question_type": "composition",
                "title": f"{metric_col.replace('_',' ').title()} by {dim.replace('_',' ').title()}",
                "description": "", "x_col": dim, "y_col": metric_col,
                "agg": agg, "sort": "desc", "limit": 10,
                "time_unit": None, "format": "number", "priority": 5,
            })
        else:
            # Zero numeric columns — count by dimension
            specs.append({
                "type": "bar", "question_type": "composition",
                "title": f"Count by {dim.replace('_',' ').title()}",
                "description": "", "x_col": dim, "y_col": dim,
                "agg": "count", "sort": "desc", "limit": 10,
                "time_unit": None, "format": "integer", "priority": 5,
            })
        if len(specs) >= 3:
            break

    # Time series
    if temporal and additive and len(specs) < 4:
        metric_col = additive[0]
        role = getattr(profile.column_profiles[metric_col], "semantic_role", "")
        agg = "mean" if role == SemanticRole.MEASURE_AVERAGE_ONLY else "sum"
        specs.append({
            "type": "line", "question_type": "trend",
            "title": f"{metric_col.replace('_',' ').title()} Over Time",
            "description": "", "x_col": temporal[0], "y_col": metric_col,
            "agg": agg, "sort": "none", "limit": 50,
            "time_unit": "month", "format": "number", "priority": 5,
        })

    return specs or [{
        "type": "bar", "question_type": "composition",
        "title": "Row Count by Category",
        "description": "",
        "x_col": profile.categorical_columns[0] if profile.categorical_columns else profile.columns[0],
        "y_col": profile.columns[0],
        "agg": "count", "sort": "desc", "limit": 10,
        "time_unit": None, "format": "integer", "priority": 5,
    }]
