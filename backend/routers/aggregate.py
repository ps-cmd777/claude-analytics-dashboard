"""Aggregate router — POST /api/aggregate/{session_id}

Computes group-by aggregations on the stored DataFrame for dynamic charts.
Used by DynamicChartGrid in the frontend to render Claude-specified charts.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rate_limit import limiter
from services.session_store import get_session

router = APIRouter()


class AggregateRequest(BaseModel):
    group_col: str
    metric_col: str
    agg: str = Field(default="sum", pattern="^(sum|mean|median|count)$")
    limit: int = Field(default=15, ge=1, le=50)
    time_unit: Optional[str] = Field(default=None)


@router.post("/aggregate/{session_id}")
@limiter.limit("120/hour")
async def aggregate(request: Request, session_id: str, req: AggregateRequest) -> dict:
    """Return aggregated data for a dynamic chart spec."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Headline question: no group_col → return a single total aggregate value
    if not req.group_col:
        df = session.profiler.df
        col = req.metric_col
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{col}' not found")
        agg = req.agg
        series = df[col].dropna()
        if agg == "sum":
            value = float(series.sum())
        elif agg == "median":
            value = float(series.median())
        elif agg == "count_distinct":
            value = float(series.nunique())
        elif agg == "count":
            value = float(len(df))
        else:  # mean and fallback
            value = float(series.mean())
        return {"data": [{"label": "All", "value": value}]}

    data = session.profiler.aggregate(
        group_col=req.group_col,
        metric_col=req.metric_col,
        agg=req.agg,
        limit=req.limit,
        time_unit=req.time_unit,
    )
    return {"data": data}
