"""Filter router — POST /api/filter/{session_id} returns a filtered DataProfile."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict

from rate_limit import limiter
from models.schemas import DataProfileSchema, profile_to_schema
from services.profiler import DataProfiler
from services.session_store import get_session

router = APIRouter()


class FilterRequest(BaseModel):
    """Body for the POST /api/filter/{session_id} endpoint.

    filters is a dict mapping column names to selected values.
    Example: {"department": "Engineering", "gender": "Female"}
    """

    filters: Dict[str, str] = Field(
        default_factory=dict,
        description="Column name → selected value pairs to filter by",
    )


@router.post("/filter/{session_id}", response_model=DataProfileSchema)
@limiter.limit("60/hour")
async def filter_data(
    request: Request, session_id: str, body: FilterRequest
) -> DataProfileSchema:
    """Apply filters to the session's DataFrame, re-profile, and return the new profile.

    Filters are applied as exact match on categorical columns.
    Pass an empty filters dict to get the unfiltered profile.
    """
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    df = session.df

    # Apply each filter
    for col, value in body.filters.items():
        if col not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Column '{col}' not found in dataset",
            )
        df = df[df[col].astype(str) == value]

    if len(df) == 0:
        raise HTTPException(
            status_code=400,
            detail="No rows match the selected filters",
        )

    # Re-profile the filtered DataFrame
    profiler = DataProfiler()
    profiler._df = df
    profile = profiler.profile()

    return profile_to_schema(profile)
