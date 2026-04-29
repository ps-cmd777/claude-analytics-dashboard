"""Export router — GET /api/export/{session_id} returns a Markdown report download."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from rate_limit import limiter
from routers._deps import require_session
from services.report_generator import generate_report, report_filename
from services.session_store import Session

router = APIRouter()


@router.get("/export/{session_id}")
@limiter.limit("30/hour")
async def export_report(
    request: Request,
    session_id: str,
    session: Session = Depends(require_session),
) -> Response:
    """Generate and return a Markdown report for the given session.

    The report is generated on-the-fly from the stored profile and analysis.
    If analysis has not been run yet, returns a profile-only report.
    """
    if session.analysis is None:
        raise HTTPException(
            status_code=400,
            detail="Analysis has not been run for this session. "
            "Call GET /api/analyze/{session_id} first.",
        )

    report_content = generate_report(
        filename=session.filename,
        profile=session.profile,
        analysis=session.analysis,
    )

    filename = report_filename(session.filename)

    return Response(
        content=report_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/session/{session_id}")
@limiter.limit("60/hour")
async def session_info(
    request: Request,
    session_id: str,
    session: Session = Depends(require_session),
) -> dict:
    """Return lightweight session metadata for the health-check endpoint."""
    return {
        "session_id": session.session_id,
        "filename": session.filename,
        "created_at": session.created_at.isoformat(),
        "has_analysis": session.analysis is not None,
        "chat_turns": len(session.chat_history) // 2,
    }
