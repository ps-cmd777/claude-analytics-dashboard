"""Profiler adapter — bridges FastAPI's UploadFile to the DataProfiler class.

The core profiling logic lives in DataProfiler (copied from Project 1).
This module provides:
  - A standalone DataProfiler + supporting dataclasses (ColumnProfile, DataProfile)
  - profile_upload() — the async adapter used by the upload router
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException, UploadFile

from .semantic_types import SemanticRole
from .semantic_classifier import classify_column, detect_derived_columns, detect_measure_pairs

# Hard caps for CSV parsing to prevent memory-exhaustion DoS.
_MAX_CSV_ROWS = 5_000_000
_MAX_CSV_COLS = 500


# ---------------------------------------------------------------------------
# Dataclasses (mirror of Project 1's profiler.py)
# ---------------------------------------------------------------------------


@dataclass
class ColumnProfile:
    """Statistics for a single column in the dataset."""

    name: str
    dtype: str
    missing_count: int
    missing_pct: float
    unique_count: int
    semantic_role: str = SemanticRole.DIMENSION_HIGH  # set after classification
    # Numeric columns only
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    q25: float | None = None
    q75: float | None = None
    outlier_count: int = 0
    outlier_indices: list[int] = field(default_factory=list)
    # Categorical columns only
    top_values: dict[str, int] = field(default_factory=dict)
    # Date columns only
    date_min: str | None = None
    date_max: str | None = None
    date_range_days: int | None = None


@dataclass
class DataProfile:
    """Complete profile of a CSV dataset."""

    shape: tuple[int, int]
    columns: list[str]
    column_profiles: dict[str, ColumnProfile]
    numeric_columns: list[str]
    categorical_columns: list[str]
    date_columns: list[str]
    total_missing: int
    total_missing_pct: float
    correlation_matrix: dict[str, dict[str, float]]
    duplicate_rows: int
    memory_usage_mb: float
    relationships: list[dict] = field(default_factory=list)  # pairs + derived cols


# ---------------------------------------------------------------------------
# DataProfiler class
# ---------------------------------------------------------------------------


class DataProfiler:
    """Loads a CSV and computes a comprehensive DataProfile.

    Also exposes four tool-handler methods used by the Claude client when
    Claude invokes tools during its analysis loop.
    """

    def __init__(self) -> None:
        """Initialize with empty state."""
        self._df: pd.DataFrame | None = None
        self._profile: DataProfile | None = None

    # ── Public pipeline methods ────────────────────────────────────────────

    def load_csv(self, path: Path) -> pd.DataFrame:
        """Load a CSV file into a DataFrame, attempting date column parsing.

        Bounded by _MAX_CSV_ROWS and _MAX_CSV_COLS to prevent memory-exhaustion
        DoS from pathological CSV inputs.

        Returns the loaded DataFrame and stores it internally.
        """
        df = pd.read_csv(
            path,
            low_memory=False,
            encoding="utf-8",
            encoding_errors="replace",
            nrows=_MAX_CSV_ROWS,
        )
        if df.shape[1] > _MAX_CSV_COLS:
            raise HTTPException(
                status_code=413,
                detail=f"CSV exceeds {_MAX_CSV_COLS}-column limit",
            )
        detected_dates = self._detect_date_columns(df)
        for col in detected_dates:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        self._df = df
        return df

    def profile(self) -> DataProfile:
        """Compute a full DataProfile for the loaded DataFrame.

        Must call load_csv() first.
        """
        if self._df is None:
            raise RuntimeError("Call load_csv() before profile().")

        df = self._df
        rows, cols = df.shape

        date_cols = [
            c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])
        ]
        numeric_cols = [
            c
            for c in df.select_dtypes(include="number").columns
            if c not in date_cols
        ]
        categorical_cols = [
            c for c in df.columns if c not in numeric_cols and c not in date_cols
        ]

        column_profiles: dict[str, ColumnProfile] = {}
        for col in df.columns:
            column_profiles[col] = self._profile_column(
                df, col, numeric_cols, date_cols
            )

        total_missing = int(df.isnull().sum().sum())
        total_cells = rows * cols
        total_missing_pct = (
            round(total_missing / total_cells * 100, 2) if total_cells else 0.0
        )

        corr = self.compute_correlations()
        dup_rows = int(df.duplicated().sum())
        mem_mb = round(df.memory_usage(deep=True).sum() / 1024 / 1024, 3)

        # Detect derived columns (C ≈ A - B or A / B) and mark them
        derived_cols = detect_derived_columns(column_profiles, df)
        for col in derived_cols:
            if col in column_profiles:
                column_profiles[col].semantic_role = SemanticRole.MEASURE_DERIVED

        # Detect budget/actual-style pairs
        pairs = detect_measure_pairs(list(df.columns))
        relationships: list[dict] = (
            [{"type": "derived", "column": c} for c in derived_cols]
            + [{"type": "pair", **p} for p in pairs]
        )

        self._profile = DataProfile(
            shape=(rows, cols),
            columns=list(df.columns),
            column_profiles=column_profiles,
            numeric_columns=list(numeric_cols),
            categorical_columns=list(categorical_cols),
            date_columns=list(date_cols),
            total_missing=total_missing,
            total_missing_pct=total_missing_pct,
            correlation_matrix=corr,
            duplicate_rows=dup_rows,
            memory_usage_mb=mem_mb,
            relationships=relationships,
        )
        return self._profile

    def detect_outliers(self, column: str) -> tuple[int, list[int]]:
        """Detect outliers in a numeric column using the IQR method.

        Returns (outlier_count, list_of_row_indices).
        """
        if self._df is None:
            return 0, []
        series = self._df[column].dropna()
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = (self._df[column] < lower) | (self._df[column] > upper)
        indices = list(self._df.index[mask].tolist())
        return int(mask.sum()), indices

    def compute_correlations(self) -> dict[str, dict[str, float]]:
        """Compute Pearson correlation matrix for numeric columns.

        Returns a JSON-serializable nested dict rounded to 4 decimal places.
        """
        if self._df is None:
            return {}
        num_df = self._df.select_dtypes(include="number")
        if num_df.shape[1] < 2:
            return {}
        corr_df = num_df.corr(numeric_only=True).round(4)
        return {
            col: {
                other: float(val)
                for other, val in corr_df[col].items()
                if not np.isnan(val)
            }
            for col in corr_df.columns
        }

    # ── Tool handler methods (called by Claude during the loop) ────────────

    def get_column_stats(self, column: str) -> dict[str, Any]:
        """Return full statistics for a single column as a JSON-ready dict.

        This is the handler for Claude's get_column_stats tool.
        """
        if self._profile is None:
            raise RuntimeError("Call profile() before using tool handlers.")
        if column not in self._profile.column_profiles:
            return {"error": f"Column '{column}' not found in dataset."}
        cp = self._profile.column_profiles[column]
        return {
            "name": cp.name,
            "dtype": cp.dtype,
            "missing_count": cp.missing_count,
            "missing_pct": cp.missing_pct,
            "unique_count": cp.unique_count,
            "mean": cp.mean,
            "median": cp.median,
            "std": cp.std,
            "min": cp.min_val,
            "max": cp.max_val,
            "q25": cp.q25,
            "q75": cp.q75,
            "outlier_count": cp.outlier_count,
            "top_values": cp.top_values,
            "date_min": cp.date_min,
            "date_max": cp.date_max,
            "date_range_days": cp.date_range_days,
        }

    def get_correlations(self) -> dict[str, Any]:
        """Return significant correlation pairs (|r| > 0.5) sorted by strength.

        This is the handler for Claude's get_correlations tool.
        """
        if self._profile is None:
            raise RuntimeError("Call profile() before using tool handlers.")
        pairs: list[dict[str, Any]] = []
        seen: set[frozenset[str]] = set()
        for col_a, row in self._profile.correlation_matrix.items():
            for col_b, r in row.items():
                if col_a == col_b:
                    continue
                pair_key = frozenset({col_a, col_b})
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                if abs(r) > 0.5:
                    pairs.append(
                        {"column_a": col_a, "column_b": col_b, "correlation": r}
                    )
        pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)
        return {
            "significant_pairs": pairs,
            "total_numeric_columns": len(self._profile.numeric_columns),
        }

    def get_outliers(self) -> dict[str, Any]:
        """Return outlier summary across all numeric columns.

        This is the handler for Claude's get_outliers tool.
        """
        if self._profile is None:
            raise RuntimeError("Call profile() before using tool handlers.")
        summary = []
        for col in self._profile.numeric_columns:
            cp = self._profile.column_profiles[col]
            if cp.outlier_count > 0:
                summary.append(
                    {
                        "column": col,
                        "outlier_count": cp.outlier_count,
                        "outlier_pct": round(
                            cp.outlier_count / self._profile.shape[0] * 100, 2
                        ),
                        "min": cp.min_val,
                        "max": cp.max_val,
                        "q25": cp.q25,
                        "q75": cp.q75,
                    }
                )
        summary.sort(key=lambda x: x["outlier_count"], reverse=True)
        return {
            "columns_with_outliers": summary,
            "total_columns_affected": len(summary),
        }

    def get_missing_values(self) -> dict[str, Any]:
        """Return missing value counts and percentages, sorted descending.

        This is the handler for Claude's get_missing_values tool.
        """
        if self._profile is None:
            raise RuntimeError("Call profile() before using tool handlers.")
        missing = [
            {
                "column": cp.name,
                "missing_count": cp.missing_count,
                "missing_pct": cp.missing_pct,
                "dtype": cp.dtype,
            }
            for cp in self._profile.column_profiles.values()
            if cp.missing_count > 0
        ]
        missing.sort(key=lambda x: x["missing_count"], reverse=True)
        return {
            "columns_with_missing": missing,
            "total_missing": self._profile.total_missing,
            "total_missing_pct": self._profile.total_missing_pct,
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _profile_column(
        self,
        df: pd.DataFrame,
        col: str,
        numeric_cols: list[str],
        date_cols: list[str],
    ) -> ColumnProfile:
        """Build a ColumnProfile for a single column."""
        series = df[col]
        missing_count = int(series.isnull().sum())
        missing_pct = (
            round(missing_count / len(series) * 100, 2) if len(series) else 0.0
        )
        unique_count = int(series.nunique(dropna=True))
        dtype_str = str(series.dtype)

        cp = ColumnProfile(
            name=col,
            dtype=dtype_str,
            missing_count=missing_count,
            missing_pct=missing_pct,
            unique_count=unique_count,
        )

        # Classify semantic role before filling numeric stats (mean/std not yet set)
        # Will be updated after numeric stats are filled for numeric columns.
        cp.semantic_role = classify_column(
            col_name=col,
            dtype=dtype_str,
            is_temporal=col in date_cols,
            n_unique=unique_count,
            missing_pct=missing_pct,
            total_rows=len(series),
            mean=None,
            std=None,
            min_val=None,
            max_val=None,
        )

        if col in numeric_cols:
            desc = series.describe()
            cp.mean = _safe_float(desc.get("mean"))
            cp.median = _safe_float(series.median())
            cp.std = _safe_float(desc.get("std"))
            cp.min_val = _safe_float(desc.get("min"))
            cp.max_val = _safe_float(desc.get("max"))
            cp.q25 = _safe_float(desc.get("25%"))
            cp.q75 = _safe_float(desc.get("75%"))
            outlier_count, outlier_indices = self.detect_outliers(col)
            cp.outlier_count = outlier_count
            cp.outlier_indices = outlier_indices[:50]
            # Re-classify with actual numeric stats now available
            cp.semantic_role = classify_column(
                col_name=col,
                dtype=dtype_str,
                is_temporal=False,
                n_unique=unique_count,
                missing_pct=missing_pct,
                total_rows=len(series),
                mean=cp.mean,
                std=cp.std,
                min_val=cp.min_val,
                max_val=cp.max_val,
            )

        elif col in date_cols:
            non_null = series.dropna()
            if len(non_null) > 0:
                date_min = non_null.min()
                date_max = non_null.max()
                cp.date_min = str(date_min)
                cp.date_max = str(date_max)
                cp.date_range_days = (date_max - date_min).days

        else:
            top = series.value_counts(dropna=True).head(10).to_dict()
            cp.top_values = {str(k): int(v) for k, v in top.items()}

        return cp

    def _detect_date_columns(self, df: pd.DataFrame) -> list[str]:
        """Heuristically detect date columns in a raw DataFrame."""
        date_name_hints = {"date", "time", "dt", "day", "month", "year", "timestamp"}
        detected: list[str] = []

        for col in df.columns:
            series = df[col]
            if pd.api.types.is_datetime64_any_dtype(series):
                detected.append(col)
                continue
            if series.dtype not in (object, "string"):
                continue
            col_lower = col.lower()
            has_date_hint = any(hint in col_lower for hint in date_name_hints)
            non_null = series.dropna()
            if len(non_null) == 0:
                continue
            sample = non_null.iloc[: min(100, len(non_null))]
            try:
                parsed = pd.to_datetime(sample, errors="coerce")
                parse_rate = parsed.notna().sum() / len(sample)
                if parse_rate >= 0.8 and (has_date_hint or parse_rate >= 0.95):
                    detected.append(col)
            except Exception:
                continue

        return detected


# ---------------------------------------------------------------------------
# Aggregate — used by the /aggregate endpoint for dynamic chart data
# ---------------------------------------------------------------------------

    def aggregate(
        self,
        group_col: str,
        metric_col: str,
        agg: str = "sum",
        limit: int = 15,
        time_unit: str | None = None,
    ) -> list[dict]:
        """Group metric_col by group_col and return [{label, value}] sorted desc.

        Supports time bucketing (month/quarter/week) for date columns.
        """
        if self._df is None:
            return []
        df = self._df.copy()

        # Time bucketing for date columns
        effective_group = group_col
        if time_unit and group_col in df.columns:
            try:
                series = pd.to_datetime(df[group_col], errors="coerce")
                period_map = {"month": "M", "quarter": "Q", "week": "W"}
                freq = period_map.get(time_unit, "M")
                df["_period"] = series.dt.to_period(freq).astype(str)
                effective_group = "_period"
            except Exception:
                pass

        if effective_group not in df.columns or metric_col not in df.columns:
            return []

        try:
            grp = df.groupby(effective_group)
            if agg == "sum":
                result = grp[metric_col].sum()
            elif agg == "mean":
                result = grp[metric_col].mean()
            elif agg == "median":
                result = grp[metric_col].median()
            elif agg == "count":
                result = grp.size()
            else:
                result = grp[metric_col].sum()

            # For time series keep chronological; for others sort desc
            if time_unit:
                result = result.dropna()
            else:
                result = result.dropna().sort_values(ascending=False).head(limit)

            return [
                {"label": str(k), "value": round(float(v), 2)}
                for k, v in result.items()
            ]
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Upload adapter
# ---------------------------------------------------------------------------


async def profile_upload(
    upload_file: UploadFile,
    max_bytes: int,
) -> tuple[DataProfiler, DataProfile, pd.DataFrame]:
    """Read an UploadFile in bounded chunks, profile it, and return results.

    Streams the upload to a temp file in 1 MiB chunks. Aborts with HTTP 413
    if the running total exceeds `max_bytes` — preventing OOM DoS from
    unbounded multipart bodies.

    Returns (profiler, profile, dataframe). The profiler instance is retained
    in the session so that tool handlers remain available during the Claude
    loop.
    """
    chunk_size = 1024 * 1024  # 1 MiB
    total = 0
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="File exceeds size limit",
                    )
                tmp.write(chunk)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    profiler = DataProfiler()
    try:
        df = profiler.load_csv(tmp_path)
        profile = profiler.profile()
    finally:
        tmp_path.unlink(missing_ok=True)

    return profiler, profile, df


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------


def _safe_float(val: Any) -> float | None:
    """Convert a value to float, returning None if conversion fails or is NaN."""
    try:
        f = float(val)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None
