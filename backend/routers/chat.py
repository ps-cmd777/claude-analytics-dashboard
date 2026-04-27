"""Chat router — POST /api/chat/{session_id} streams Claude Q&A replies via SSE."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from rate_limit import limiter
from models.schemas import ChatRequest
from services.claude_client import stream_chat, _sse
from services.session_store import get_session

router = APIRouter()


@router.post("/chat/{session_id}")
@limiter.limit("30/hour")
async def chat(request: Request, session_id: str, body: ChatRequest) -> StreamingResponse:
    """Stream Claude's reply to a follow-up question about the uploaded data.

    SSE event types:
    - token: one chunk of the reply text
    - done: stream complete
    - error: something went wrong
    """
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        _chat_generator(session_id, body.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _chat_generator(session_id: str, user_message: str):
    """Sync generator that streams the chat reply and persists history."""
    session = get_session(session_id)
    if session is None:
        yield _sse({"type": "error", "message": "Session not found"})
        return

    try:
        analysis_context = None
        if session.analysis is not None:
            a = session.analysis
            findings = "\n".join(f"- {f}" for f in a.key_findings)
            recs = "\n".join(f"- {r}" for r in a.recommendations[:5])
            anomaly_count = len(a.anomalies)
            domain_line = ""
            if a.domain or a.grain:
                parts = []
                if a.domain:
                    parts.append(f"Domain: {a.domain}")
                if a.grain:
                    parts.append(f"Grain: {a.grain}")
                if a.practitioner_persona:
                    parts.append(f"Practitioner: {a.practitioner_persona}")
                domain_line = " | ".join(parts) + "\n\n"
            analysis_context = (
                domain_line
                + f"Executive Summary: {a.executive_summary[:1200]}\n\n"
                f"Key Findings ({len(a.key_findings)}):\n{findings}\n\n"
                f"Recommendations:\n{recs}\n\n"
                f"Anomalies detected: {anomaly_count}"
            )

        gen = stream_chat(
            profiler=session.profiler,
            chat_history=session.chat_history,
            user_message=user_message,
            analysis_context=analysis_context,
        )

        full_reply = ""
        while True:
            try:
                chunk = next(gen)
                yield chunk
            except StopIteration as exc:
                full_reply = exc.value or ""
                break

        # Persist the conversation turn
        session.chat_history.append({"role": "user", "content": user_message})
        session.chat_history.append({"role": "assistant", "content": full_reply})

        yield _sse({"type": "done"})

    except Exception as exc:
        yield _sse({"type": "error", "message": "Chat request failed. Please try again."})
