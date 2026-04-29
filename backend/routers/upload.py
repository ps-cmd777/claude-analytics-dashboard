"""Upload router — POST /api/upload handles CSV file upload and profiling."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse

from rate_limit import limiter
from models.schemas import UploadResponse, profile_to_schema
from services.profiler import profile_upload
from services.session_store import SESSION_TTL_HOURS, create_session

router = APIRouter()

_MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
_MAX_BYTES = _MAX_UPLOAD_MB * 1024 * 1024
_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("20/hour")
async def upload_csv(request: Request, file: UploadFile = File(...)) -> JSONResponse:
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

    # Quick reject if Content-Length advertises a too-large body. The
    # authoritative size enforcement happens in profile_upload via chunked
    # reads — this header may be missing or spoofed.
    if file.size is not None and file.size > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {_MAX_UPLOAD_MB} MB limit",
        )

    # Profile the upload — chunked read aborts at _MAX_BYTES.
    try:
        profiler, profile, df = await profile_upload(file, max_bytes=_MAX_BYTES)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail="Failed to parse CSV. Please ensure the file is a valid CSV with UTF-8 encoding.",
        ) from exc

    session = create_session(
        filename=filename,
        df=df,
        profiler=profiler,
        profile=profile,
    )

    payload = UploadResponse(
        session_id=session.session_id,
        filename=filename,
        profile=profile_to_schema(profile),
    )
    response = JSONResponse(content=payload.model_dump())
    # HttpOnly cookie carries the secret companion token. The session_id is
    # public (it appears in URL paths); the token is not. Without both, no
    # endpoint will return data for this session.
    response.set_cookie(
        key="session_token",
        value=session.session_token,
        max_age=SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return response
