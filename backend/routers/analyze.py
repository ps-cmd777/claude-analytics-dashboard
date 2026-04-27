"""Analyze router — GET /api/analyze/{session_id} streams Claude analysis via SSE."""

from __future__ import annotations

import os

from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from rate_limit import limiter
from models.schemas import analysis_to_schema
from services.claude_client import stream_analysis, _sse
from services.session_store import get_session

router = APIRouter()

_DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")


@router.get("/analyze/{session_id}")
@limiter.limit("10/hour")
async def analyze(
    request: Request,
    session_id: str,
    domain_hint: Optional[str] = Query(default=None, max_length=200),
) -> StreamingResponse:
    """Stream Claude's AI analysis of the uploaded dataset as Server-Sent Events.

    SSE event types:
    - status: progress message while tool-use loop runs
    - token: one chunk of the final streamed text
    - done: analysis complete, includes structured AnalysisResult JSON
    - error: something went wrong

    Optional query param:
    - domain_hint: user-supplied domain correction (e.g. "Hospital patient records")
      Clears prior analysis and chat history so everything re-runs fresh.
    """
    return StreamingResponse(
        _analysis_generator(session_id, domain_hint=domain_hint),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _analysis_generator(session_id: str, domain_hint: str | None = None):
    """Sync generator wrapping the Claude stream_analysis generator."""
    session = get_session(session_id)
    if session is None:
        yield _sse({"type": "error", "message": "Session not found"})
        return

    # On domain correction, clear stale analysis + chat so nothing is mixed
    if domain_hint:
        session.analysis = None
        session.chat_history = []

    try:
        gen = stream_analysis(session.profiler, session.profile, domain_hint=domain_hint)
        result = None

        # Exhaust the generator, collecting the return value
        while True:
            try:
                chunk = next(gen)
                yield chunk
            except StopIteration as exc:
                result = exc.value  # The AnalysisResult returned by the generator
                break

        # Store result in session
        if result is not None:
            session.analysis = result

        # Emit done event with structured result
        result_payload = None
        if result is not None:
            try:
                schema = analysis_to_schema(result)
                result_payload = schema.model_dump()
            except Exception:
                result_payload = None

        yield _sse({"type": "done", "result": result_payload})

    except Exception:
        import logging
        logging.getLogger(__name__).exception("Analysis failed")
        yield _sse({"type": "error", "message": "Analysis failed. Please try again or upload a different file."})
