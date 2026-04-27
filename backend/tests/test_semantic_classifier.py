"""Tests for semantic_classifier.classify_column().

Each fixture asserts the correct SemanticRole for a column given its
statistical profile. These are the foundation — a bug here silently kills
entire chart categories for every dataset.
"""

from __future__ import annotations

import pytest

from services.semantic_classifier import classify_column, detect_measure_pairs
from services.semantic_types import SemanticRole


# ---------------------------------------------------------------------------
# Fixtures: (col_name, dtype, is_temporal, n_unique, missing_pct,
#            total_rows, mean, std, min_val, max_val, expected_role)
# ---------------------------------------------------------------------------

FIXTURES = [
    # Identifiers — very high cardinality relative to row count
    ("employee_id",   "int64",   False, 865,  0.0,  870,  None,   None,  None,   None,   SemanticRole.IDENTIFIER),
    ("product_id",    "object",  False, 1000, 0.0,  1001, None,   None,  None,   None,   SemanticRole.IDENTIFIER),

    # MEASURE_AVERAGE_ONLY — CV < 1.0 (low spread relative to mean)
    ("salary_usd",    "float64", False, 400,  0.0,  870,  85000,  15000, 30000,  200000, SemanticRole.MEASURE_AVERAGE_ONLY),  # CV=0.18
    ("age",           "float64", False, 45,   2.0,  870,  38.0,   8.5,   22.0,   65.0,   SemanticRole.MEASURE_AVERAGE_ONLY),  # CV=0.22
    ("satisfaction",  "float64", False, 5,    0.0,  870,  3.8,    0.9,   1.0,    5.0,    SemanticRole.MEASURE_AVERAGE_ONLY),  # CV=0.24 — but n_unique=5 → boolean check fails, numeric branch

    # MEASURE_ADDITIVE — CV >= 1.0 (high spread, summing is meaningful)
    ("total_revenue", "float64", False, 500,  0.0,  870,  50000,  80000, 0.0,    900000, SemanticRole.MEASURE_ADDITIVE),     # CV=1.6
    ("quantity",      "int64",   False, 50,   2.0,  870,  12.0,   25.0,  1.0,    200.0,  SemanticRole.MEASURE_ADDITIVE),     # CV=2.1
    ("order_count",   "int64",   False, 300,  0.0,  870,  5.0,    18.0,  0.0,    120.0,  SemanticRole.MEASURE_ADDITIVE),     # CV=3.6

    # MEASURE_RATIO — only strict [0, 1] bounded values qualify
    ("completion_rt", "float64", False, 200,  0.0,  870,  0.72,   0.18,  0.0,    1.0,    SemanticRole.MEASURE_RATIO),        # [0,1] ✓

    # 0–100 percentage columns — max > 1 so _is_ratio returns False
    # variance_pct can be negative, so even the max>1 guard isn't needed — CV>1 → ADDITIVE
    ("variance_pct",  "float64", False, 400,  0.0,  870,  3.2,    8.5,   -18.0,  22.0,   SemanticRole.MEASURE_ADDITIVE),    # CV=2.7, can go negative → additive
    # discount_pct is 0–60, CV=0.64 < 1 → AVERAGE_ONLY (correct: you avg discounts, never sum)
    ("discount_pct",  "float64", False, 400,  0.0,  870,  12.5,   8.0,   0.0,    60.0,   SemanticRole.MEASURE_AVERAGE_ONLY), # max=60 > 1 → not ratio; CV=0.64 → avg-only
    # satisfaction 1–5: max=5 > 1 → not ratio; CV=0.24 < 1 → AVERAGE_ONLY (correct)
    ("satisfaction_score", "float64", False, 5, 0.0, 870, 3.8, 0.9, 1.0, 5.0,   SemanticRole.MEASURE_AVERAGE_ONLY), # score, not ratio

    # BOOLEAN — exactly 2 unique values
    ("attrition",     "bool",    False, 2,    0.0,  870,  0.15,   None,  0.0,    1.0,    SemanticRole.BOOLEAN),
    ("is_returned",   "object",  False, 2,    0.0,  870,  None,   None,  None,   None,   SemanticRole.BOOLEAN),

    # TEMPORAL — date columns
    ("hire_date",     "datetime64[ns]", True, 300, 0.0, 870, None, None, None, None, SemanticRole.TEMPORAL),

    # DIMENSION_LOW — 2 < unique <= 15
    ("department",    "object",  False, 8,    0.0,  870,  None,   None,  None,   None,   SemanticRole.DIMENSION_LOW),
    ("region",        "object",  False, 4,    0.0,  870,  None,   None,  None,   None,   SemanticRole.DIMENSION_LOW),
    ("status",        "object",  False, 3,    0.0,  870,  None,   None,  None,   None,   SemanticRole.DIMENSION_LOW),

    # DIMENSION_MEDIUM — 16 < unique <= 50
    ("job_title",     "object",  False, 32,   0.0,  870,  None,   None,  None,   None,   SemanticRole.DIMENSION_MEDIUM),

    # DIMENSION_HIGH — high unique count, not identifier ratio
    ("postal_code",   "object",  False, 180,  0.0,  870,  None,   None,  None,   None,   SemanticRole.DIMENSION_HIGH),

    # TEXT_FREE — unique_ratio 0.7–0.95: string column, not quite an identifier
    ("notes",         "object",  False, 800,  0.0,  870,  None,   None,  None,   None,   SemanticRole.TEXT_FREE),   # ratio=0.92 → TEXT_FREE
    # IDENTIFIER — unique_ratio > 0.95: classifier can't distinguish free text
    # from ID codes without avg string length; both are safe to skip as metrics.
    ("description",   "object",  False, 850,  0.0,  870,  None,   None,  None,   None,   SemanticRole.IDENTIFIER),  # ratio=0.977 → IDENTIFIER

    # CONSTANT — only 1 unique value
    ("country",       "object",  False, 1,    0.0,  870,  None,   None,  None,   None,   SemanticRole.CONSTANT),

    # EMPTY — >95% missing
    ("legacy_flag",   "float64", False, 2,    97.0, 870,  None,   None,  None,   None,   SemanticRole.EMPTY),
]


@pytest.mark.parametrize(
    "col_name,dtype,is_temporal,n_unique,missing_pct,total_rows,mean,std,min_val,max_val,expected",
    FIXTURES,
    ids=[f[0] for f in FIXTURES],
)
def test_classify_column(
    col_name, dtype, is_temporal, n_unique, missing_pct,
    total_rows, mean, std, min_val, max_val, expected,
):
    result = classify_column(
        col_name=col_name,
        dtype=dtype,
        is_temporal=is_temporal,
        n_unique=n_unique,
        missing_pct=missing_pct,
        total_rows=total_rows,
        mean=mean,
        std=std,
        min_val=min_val,
        max_val=max_val,
    )
    assert result == expected, (
        f"{col_name!r}: expected {expected.value!r}, got {result.value!r}"
    )


# ---------------------------------------------------------------------------
# Cascade priority checks
# ---------------------------------------------------------------------------

def test_empty_wins_over_boolean():
    """EMPTY must fire before the n_unique==2 boolean check."""
    result = classify_column(
        col_name="sparse_flag", dtype="float64", is_temporal=False,
        n_unique=2, missing_pct=96.0, total_rows=500,
        mean=None, std=None, min_val=None, max_val=None,
    )
    assert result == SemanticRole.EMPTY


def test_constant_wins_over_numeric():
    """CONSTANT (n_unique=1) must fire before numeric branch."""
    result = classify_column(
        col_name="fixed_fee", dtype="float64", is_temporal=False,
        n_unique=1, missing_pct=0.0, total_rows=500,
        mean=100.0, std=0.0, min_val=100.0, max_val=100.0,
    )
    assert result == SemanticRole.CONSTANT


def test_temporal_wins_over_high_cardinality():
    """TEMPORAL must fire before identifier check."""
    result = classify_column(
        col_name="created_at", dtype="datetime64[ns]", is_temporal=True,
        n_unique=490, missing_pct=0.0, total_rows=500,
        mean=None, std=None, min_val=None, max_val=None,
    )
    assert result == SemanticRole.TEMPORAL


def test_identifier_high_cardinality_string():
    """High-cardinality string with unique_ratio > 0.95 → IDENTIFIER."""
    result = classify_column(
        col_name="order_ref", dtype="object", is_temporal=False,
        n_unique=980, missing_pct=0.0, total_rows=1000,
        mean=None, std=None, min_val=None, max_val=None,
    )
    assert result == SemanticRole.IDENTIFIER


def test_ratio_detected_by_bounds():
    """Values strictly in [0, 1] → MEASURE_RATIO regardless of CV."""
    result = classify_column(
        col_name="win_rate", dtype="float64", is_temporal=False,
        n_unique=100, missing_pct=0.0, total_rows=200,
        mean=0.55, std=0.2, min_val=0.0, max_val=1.0,
    )
    assert result == SemanticRole.MEASURE_RATIO


def test_salary_never_additive():
    """Low-CV numeric → MEASURE_AVERAGE_ONLY, never ADDITIVE."""
    result = classify_column(
        col_name="base_salary", dtype="float64", is_temporal=False,
        n_unique=300, missing_pct=0.0, total_rows=600,
        mean=92000, std=14000, min_val=40000, max_val=180000,
    )
    assert result == SemanticRole.MEASURE_AVERAGE_ONLY
    assert result != SemanticRole.MEASURE_ADDITIVE


# ---------------------------------------------------------------------------
# detect_measure_pairs
# ---------------------------------------------------------------------------

def test_detect_budget_actual_pair():
    cols = ["department", "budget_usd", "actual_usd", "variance_usd"]
    pairs = detect_measure_pairs(cols)
    assert any(
        p["base"] == "budget_usd" and p["comparison"] == "actual_usd"
        for p in pairs
    ), f"Expected budget↔actual pair, got: {pairs}"


def test_detect_no_pairs_when_absent():
    cols = ["employee_id", "salary_usd", "department", "hire_date"]
    pairs = detect_measure_pairs(cols)
    assert pairs == []


def test_forecast_actual_pair():
    cols = ["month", "forecast_revenue", "actual_revenue"]
    pairs = detect_measure_pairs(cols)
    assert len(pairs) >= 1
