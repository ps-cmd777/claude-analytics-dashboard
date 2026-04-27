"""Pydantic schemas for request/response models and SSE event payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ── Column / Profile schemas ───────────────────────────────────────────────────


class ColumnProfileSchema(BaseModel):
    """Statistics for a single column in the dataset."""

    name: str
    dtype: str
    missing_count: int
    missing_pct: float
    unique_count: int
    semantic_role: str = "dimension_high"
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    outlier_count: int = 0
    top_values: Dict[str, int] = Field(default_factory=dict)
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    date_range_days: Optional[int] = None


class DataProfileSchema(BaseModel):
    """Complete profile of a CSV dataset, serialised for JSON transport."""

    shape: Tuple[int, int]
    columns: List[str]
    column_profiles: Dict[str, ColumnProfileSchema]
    numeric_columns: List[str]
    categorical_columns: List[str]
    date_columns: List[str]
    total_missing: int
    total_missing_pct: float
    correlation_matrix: Dict[str, Dict[str, float]]
    duplicate_rows: int
    memory_usage_mb: float
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


# ── Upload response ────────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    """Response returned after a successful CSV upload."""

    session_id: str
    filename: str
    profile: DataProfileSchema


# ── Analysis result schemas ────────────────────────────────────────────────────


class ColumnAnalysisSchema(BaseModel):
    """Claude's analysis of a single column."""

    column_name: str
    summary: str
    quality: str
    patterns: str


class ChartSpecSchema(BaseModel):
    """A single AI-specified chart for the dynamic chart grid."""
    type: str = "bar"
    title: str
    description: str = ""
    x_col: str
    y_col: str
    agg: str = "sum"
    sort: str = "desc"
    limit: Optional[int] = 10
    time_unit: Optional[str] = None
    format: str = "number"


class AnalysisResultSchema(BaseModel):
    """Structured analysis result produced by the Claude tool-use loop."""

    executive_summary: str
    key_findings: List[str] = Field(default_factory=list)
    column_analyses: List[ColumnAnalysisSchema] = Field(default_factory=list)
    anomalies: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    methodology_notes: str = ""
    chart_specs: List[ChartSpecSchema] = Field(default_factory=list)
    skip_distributions: List[str] = Field(default_factory=list)
    domain: str = ""
    grain: str = ""
    practitioner_persona: str = ""
    insight_cards: List[Dict[str, Any]] = Field(default_factory=list)


# ── Chat ──────────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Body for the POST /api/chat/{session_id} endpoint."""

    message: str = Field(..., min_length=1, max_length=2000)


# ── SSE event envelopes ────────────────────────────────────────────────────────


class SSEStatusEvent(BaseModel):
    """Emitted when the server wants to report progress to the client."""

    type: str = "status"
    message: str


class SSETokenEvent(BaseModel):
    """Emitted once per text chunk streamed from Claude."""

    type: str = "token"
    text: str


class SSEDoneEvent(BaseModel):
    """Emitted when the stream is complete."""

    type: str = "done"
    result: Optional[AnalysisResultSchema] = None  # present on /analyze, absent on /chat


class SSEErrorEvent(BaseModel):
    """Emitted when an error occurs during streaming."""

    type: str = "error"
    message: str


# ── Session info ───────────────────────────────────────────────────────────────


class SessionInfo(BaseModel):
    """Lightweight session metadata for the health-check endpoint."""

    session_id: str
    filename: str
    created_at: str  # ISO-8601 UTC string


# ── Helpers ───────────────────────────────────────────────────────────────────


def profile_to_schema(profile: Any) -> DataProfileSchema:
    """Convert a DataProfile dataclass to a DataProfileSchema Pydantic model.

    Maps ColumnProfile dataclass fields to ColumnProfileSchema, excluding
    the outlier_indices field which is not needed by the frontend.
    """
    column_profiles: Dict[str, ColumnProfileSchema] = {}
    for name, cp in profile.column_profiles.items():
        column_profiles[name] = ColumnProfileSchema(
            name=cp.name,
            dtype=cp.dtype,
            missing_count=cp.missing_count,
            missing_pct=cp.missing_pct,
            unique_count=cp.unique_count,
            semantic_role=str(getattr(cp, "semantic_role", "dimension_high")),
            mean=cp.mean,
            median=cp.median,
            std=cp.std,
            min_val=cp.min_val,
            max_val=cp.max_val,
            q25=cp.q25,
            q75=cp.q75,
            outlier_count=cp.outlier_count,
            top_values=cp.top_values,
            date_min=cp.date_min,
            date_max=cp.date_max,
            date_range_days=cp.date_range_days,
        )

    return DataProfileSchema(
        shape=profile.shape,
        columns=profile.columns,
        column_profiles=column_profiles,
        numeric_columns=profile.numeric_columns,
        categorical_columns=profile.categorical_columns,
        date_columns=profile.date_columns,
        total_missing=profile.total_missing,
        total_missing_pct=profile.total_missing_pct,
        correlation_matrix=profile.correlation_matrix,
        duplicate_rows=profile.duplicate_rows,
        memory_usage_mb=profile.memory_usage_mb,
        relationships=getattr(profile, "relationships", []),
    )


def analysis_to_schema(analysis: Any) -> AnalysisResultSchema:
    """Convert an AnalysisResult dataclass to an AnalysisResultSchema Pydantic model."""
    column_analyses = [
        ColumnAnalysisSchema(
            column_name=ca.column_name,
            summary=ca.summary,
            quality=ca.quality,
            patterns=ca.patterns,
        )
        for ca in analysis.column_analyses
    ]
    chart_specs = []
    for spec in getattr(analysis, "chart_specs", []):
        try:
            chart_specs.append(ChartSpecSchema(**spec))
        except Exception:
            pass

    return AnalysisResultSchema(
        executive_summary=analysis.executive_summary,
        key_findings=analysis.key_findings,
        column_analyses=column_analyses,
        anomalies=analysis.anomalies,
        recommendations=analysis.recommendations,
        methodology_notes=analysis.methodology_notes,
        chart_specs=chart_specs,
        skip_distributions=getattr(analysis, "skip_distributions", []),
        domain=getattr(analysis, "domain", ""),
        grain=getattr(analysis, "grain", ""),
        practitioner_persona=getattr(analysis, "practitioner_persona", ""),
        insight_cards=getattr(analysis, "insight_cards", []),
    )
