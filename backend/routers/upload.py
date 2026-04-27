"""Upload router — POST /api/upload handles CSV file upload and profiling."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from rate_limit import limiter
from models.schemas import UploadResponse, profile_to_schema
from services.profiler import profile_upload
from services.session_store import create_session

router = APIRouter()

_MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
_MAX_BYTES = _MAX_UPLOAD_MB * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("20/hour")
async def upload_csv(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    """Accept a CSV file, profile it, create a session, and return the profile.

    Validates:
    - File must have .csv extension or text/csv content type
    - File must not exceed MAX_UPLOAD_MB (default 50 MB)
    """
    # Validate content type / extension
    filename = file.filename or ""
    content_type = file.content_type or ""
    if not (
        filename.lower().endswith(".csv")
        or "csv" in content_type
        or content_type in ("text/plain", "application/octet-stream")
    ):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    # Check file size before reading (peek at Content-Length if available)
    if file.size is not None and file.size > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {_MAX_UPLOAD_MB} MB limit",
        )

    # Profile the upload (reads file, writes temp, profiles, cleans up)
    try:
        profiler, profile, df = await profile_upload(file)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Failed to parse CSV. Please ensure the file is a valid CSV with UTF-8 encoding.",
        ) from exc

    # Double-check size after reading
    if df.memory_usage(deep=True).sum() > _MAX_BYTES * 10:
        raise HTTPException(
            status_code=413,
            detail=f"Parsed data exceeds {_MAX_UPLOAD_MB * 10} MB in memory",
        )

    session = create_session(
        filename=filename,
        df=df,
        profiler=profiler,
        profile=profile,
    )

    return UploadResponse(
        session_id=session.session_id,
        filename=filename,
        profile=profile_to_schema(profile),
    )
