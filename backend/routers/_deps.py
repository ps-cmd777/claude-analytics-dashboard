"""Shared FastAPI dependencies — session authorization."""

from __future__ import annotations

from typing import Optional

from fastapi import Cookie, HTTPException, Path

from services.session_store import Session, authorize


def require_session(
    session_id: str = Path(...),
    session_token: Optional[str] = Cookie(default=None),
) -> Session:
    """Resolve a session by its public id + secret cookie token.

    Returns the Session on success. Raises HTTP 404 if the session is missing
    (so attackers can't probe for valid IDs by error code) — both
    "missing token" and "wrong token" collapse to the same response as
    "session not found".
    """
    try:
        return authorize(session_id, session_token)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
