"""Pure statistical column classification — no domain knowledge, only math.

classify_column() is called for every column during profiling. The result
(SemanticRole) tells chart_compiler.py what aggregations are valid for that
column, enforced before any chart spec reaches the frontend.

Key invariant: column *names* are never the primary signal. Only statistics.
Column name hints are only used as a tiebreaker inside the numeric cascade.
"""

from __future__ import annotations

import re
from typing import Any

from .semantic_types import SemanticRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_ratio(min_val: float | None, max_val: float | None, mean: float | None) -> bool:
    """Return True if values are strictly bounded in [0, 1].

    Only [0, 1] is treated as a ratio/rate. The broader [0, 100] check was
    removed because it falsely matched ages (22–65), satisfaction scores (1–5),
    and other bounded-but-not-percentage columns.
    """
    if min_val is None or max_val is None or mean is None:
        return False
    return min_val >= 0 and max_val <= 1.0


# ---------------------------------------------------------------------------
# Primary classifier
# ---------------------------------------------------------------------------

def classify_column(
    col_name: str,  # noqa: ARG001 — not used as primary signal; kept for logging/future use
    dtype: str,
    is_temporal: bool,
    n_unique: int,
    missing_pct: float,
    total_rows: int,
    mean: float | None,
    std: float | None,
    min_val: float | None,
    max_val: float | None,
) -> SemanticRole:
    """Classify a single column into a SemanticRole.

    Cascade order: unusable → temporal → boolean → identifier → numeric → string.
    All checks are statistical; domain keywords only used as a last tiebreaker
    inside the numeric branch.
    """
    unique_ratio = n_unique / total_rows if total_rows > 0 else 0

    # ── Unusable ──────────────────────────────────────────────────────────
    if missing_pct > 95:
        return SemanticRole.EMPTY
    if n_unique <= 1:
        return SemanticRole.CONSTANT

    # ── Temporal ──────────────────────────────────────────────────────────
    if is_temporal:
        return SemanticRole.TEMPORAL

    # ── Boolean ───────────────────────────────────────────────────────────
    if n_unique == 2:
        return SemanticRole.BOOLEAN

    # ── Identifier ────────────────────────────────────────────────────────
    # Very high cardinality relative to row count → most likely a key column
    if unique_ratio > 0.95 and n_unique > 20:
        return SemanticRole.IDENTIFIER

    # ── Numeric branch ────────────────────────────────────────────────────
    is_numeric = dtype.startswith(("int", "float", "Int", "Float"))
    if is_numeric:
        if mean is None:
            return SemanticRole.MEASURE_ADDITIVE  # fallback

        # Ratio detection: values bounded in [0, 1] or [0, 100]
        if _is_ratio(min_val, max_val, mean):
            return SemanticRole.MEASURE_RATIO

        # Coefficient of variation: CV < 1.0 means low spread relative to mean
        # → per-entity measure (salary, age, score) → only mean/median meaningful
        if std is not None and abs(mean) > 0:
            cv = std / abs(mean)
            if cv < 1.0:
                return SemanticRole.MEASURE_AVERAGE_ONLY

        return SemanticRole.MEASURE_ADDITIVE

    # ── String / categorical branch ───────────────────────────────────────
    if n_unique <= 15:
        return SemanticRole.DIMENSION_LOW
    if n_unique <= 50:
        return SemanticRole.DIMENSION_MEDIUM

    # High cardinality strings: check average token length for free-text
    # (We can't compute avg_len here without the series, so use unique_ratio as proxy)
    if unique_ratio > 0.7:
        return SemanticRole.TEXT_FREE

    return SemanticRole.DIMENSION_HIGH


# ---------------------------------------------------------------------------
# Derived column detection
# ---------------------------------------------------------------------------

def detect_derived_columns(
    profiles: dict[str, Any],
    df_sample: Any,  # pd.DataFrame — kept as Any to avoid import cycle
) -> set[str]:
    """Return column names that are approximately A - B or A / B of two others.

    Uses a 200-row sample to keep this fast. Only numeric columns are checked.
    A column is marked MEASURE_DERIVED if the residual |C - (A op B)| / std(C)
    is < 0.05 for at least 90% of sample rows.
    """
    import numpy as np

    derived: set[str] = set()
    numeric_cols = [
        c for c, p in profiles.items()
        if p.mean is not None and p.std is not None and p.std > 0
    ]
    if len(numeric_cols) < 3:
        return derived

    sample = df_sample[numeric_cols].dropna().head(200)
    if len(sample) < 20:
        return derived

    col_list = list(sample.columns)
    for i, c in enumerate(col_list):
        c_vals = sample[c].values
        c_std = c_vals.std()
        if c_std == 0:
            continue
        for j, a in enumerate(col_list):
            if j == i:
                continue
            for k, b in enumerate(col_list):
                if k == i or k == j:
                    continue
                a_vals = sample[a].values
                b_vals = sample[b].values
                # Test C ≈ A - B
                residual = np.abs(c_vals - (a_vals - b_vals))
                if (residual / c_std < 0.05).mean() >= 0.90:
                    derived.add(c)
                    break
                # Test C ≈ A / B  (avoid division by zero)
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio = np.where(b_vals != 0, a_vals / b_vals, np.nan)
                ratio_resid = np.abs(c_vals - ratio)
                valid = ~np.isnan(ratio_resid)
                if valid.sum() >= 10 and (ratio_resid[valid] / c_std < 0.05).mean() >= 0.90:
                    derived.add(c)
                    break
            if c in derived:
                break

    return derived


# ---------------------------------------------------------------------------
# Measure-pair detection (budget/actual, before/after, plan/realized)
# ---------------------------------------------------------------------------

_PAIR_PATTERNS = [
    (r"budget", r"actual"),
    (r"plan(ned)?", r"actual"),
    (r"target", r"achieved?"),
    (r"before", r"after"),
    (r"prior", r"current"),
    (r"last.?(year|month|quarter)", r"(this|current).?(year|month|quarter)"),
    (r"forecast", r"actual"),
]


def detect_measure_pairs(col_names: list[str]) -> list[dict[str, str]]:
    """Find budget/actual-style pairs by name pattern.

    Returns list of {"base": col_a, "comparison": col_b, "relationship": "actual_vs_budget"}.
    """
    pairs = []
    lower_names = [(c, c.lower().replace("_", " ")) for c in col_names]

    for base_pat, comp_pat in _PAIR_PATTERNS:
        base_re = re.compile(base_pat)
        comp_re = re.compile(comp_pat)
        bases = [c for c, lc in lower_names if base_re.search(lc)]
        comps = [c for c, lc in lower_names if comp_re.search(lc)]
        for b in bases:
            for cp in comps:
                if b != cp:
                    pairs.append({
                        "base": b,
                        "comparison": cp,
                        "relationship": f"{comp_pat}_vs_{base_pat}",
                    })

    return pairs
