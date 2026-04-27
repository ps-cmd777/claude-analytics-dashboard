"""Export router — GET /api/export/{session_id} returns a Markdown report download."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from services.report_generator import generate_report, report_filename
from services.session_store import get_session

router = APIRouter()


@router.get("/export/{session_id}")
async def export_report(session_id: str) -> Response:
    """Generate and return a Markdown report for the given session.

    The report is generated on-the-fly from the stored profile and analysis.
    If analysis has not been run yet, returns a profile-only report.
    """
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

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
async def session_info(session_id: str) -> dict:
    """Return lightweight session metadata for the health-check endpoint."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "filename": session.filename,
        "created_at": session.created_at.isoformat(),
        "has_analysis": session.analysis is not None,
        "chat_turns": len(session.chat_history) // 2,
    }
