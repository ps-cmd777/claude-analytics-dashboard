"""Shared rate limiter instance — imported by routers and mounted in main.py.

NOTE on storage: by default slowapi uses in-memory storage which is per-process.
For production with multiple workers, set RATE_LIMIT_STORAGE_URI to a Redis URL
(e.g. ``redis://localhost:6379``) so counters are shared across workers.
"""

from __future__ import annotations

import os

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

_STORAGE_URI = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

limiter = Limiter(key_func=get_remote_address, storage_uri=_STORAGE_URI)


def session_key(request: Request) -> str:
    """Rate-limit key derived from the session_id (path or cookie).

    Falls back to the client IP if no session is present so the decorator never
    crashes. Using session_id prevents an attacker behind one IP from spinning
    up many sessions to multiply spend on /analyze.
    """
    sid = request.path_params.get("session_id") if request.path_params else None
    if not sid:
        sid = request.cookies.get("session_id")
    if not sid:
        return get_remote_address(request)
    return f"sid:{sid}"
