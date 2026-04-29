"""In-memory session store — manages uploaded CSV sessions for the lifetime of the process."""

from __future__ import annotations

import hmac
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

import pandas as pd

if TYPE_CHECKING:
    pass

# Sessions expire after this many hours
SESSION_TTL_HOURS = 24
_TTL_SECONDS = SESSION_TTL_HOURS * 3600

# ---------------------------------------------------------------------------
# Session dataclass
# ---------------------------------------------------------------------------


@dataclass
class Session:
    """All state associated with one uploaded CSV session."""

    session_id: str
    session_token: str  # secret companion to session_id; never in URLs
    filename: str
    created_at: datetime
    df: pd.DataFrame
    profiler: object  # DataProfiler instance — typed as object to avoid circular import
    profile: object  # DataProfile dataclass
    analysis: object | None = None  # AnalysisResult dataclass, set after /analyze
    chat_history: list[dict] = field(default_factory=list)
    # chat_history contains raw Anthropic message dicts:
    # [{"role": "user", "content": "..."}, {"role": "assistant", "content": [...]}]


# ---------------------------------------------------------------------------
# Module-level store
# ---------------------------------------------------------------------------

_sessions: dict[str, Session] = {}


# ---------------------------------------------------------------------------
# Expiry helpers
# ---------------------------------------------------------------------------


def _is_expired(session: Session) -> bool:
    """Check whether a session has exceeded the TTL."""
    age = (datetime.now(tz=timezone.utc) - session.created_at).total_seconds()
    return age > _TTL_SECONDS


def _cleanup_expired() -> None:
    """Remove all expired sessions from the store."""
    expired = [sid for sid, s in _sessions.items() if _is_expired(s)]
    for sid in expired:
        del _sessions[sid]


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def create_session(
    filename: str,
    df: pd.DataFrame,
    profiler: object,
    profile: object,
) -> Session:
    """Create a new session, store it, and return it.

    Generates a UUID4 as the public session_id and a 256-bit URL-safe
    session_token to be set as an HttpOnly cookie on the upload response.
    Also cleans up expired sessions.
    """
    _cleanup_expired()
    session_id = str(uuid.uuid4())
    session_token = secrets.token_urlsafe(32)
    session = Session(
        session_id=session_id,
        session_token=session_token,
        filename=filename,
        created_at=datetime.now(tz=timezone.utc),
        df=df,
        profiler=profiler,
        profile=profile,
    )
    _sessions[session_id] = session
    return session


def authorize(session_id: str, presented_token: Optional[str]) -> Session:
    """Return the session iff the presented token matches the stored one.

    Constant-time comparison guards against timing oracles. Returns the
    Session on success; raises ValueError on any failure mode (missing,
    expired, mismatch) — callers translate to HTTP 401/404.
    """
    session = get_session(session_id)
    if session is None:
        raise ValueError("session_not_found")
    if not presented_token:
        raise ValueError("missing_token")
    if not hmac.compare_digest(session.session_token, presented_token):
        raise ValueError("invalid_token")
    return session


def get_session(session_id: str) -> Session | None:
    """Retrieve a session by ID. Returns None if not found or expired."""
    session = _sessions.get(session_id)
    if session is None:
        return None
    if _is_expired(session):
        del _sessions[session_id]
        return None
    return session


def delete_session(session_id: str) -> bool:
    """Delete a session. Returns True if deleted, False if not found."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def list_sessions() -> list[str]:
    """Return all active session IDs."""
    return list(_sessions.keys())


def session_count() -> int:
    """Return the number of active sessions."""
    return len(_sessions)
