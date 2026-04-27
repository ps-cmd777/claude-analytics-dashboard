"""FastAPI application entry point — mounts all routers and configures CORS."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Load environment variables before anything else
load_dotenv()

from routers import upload, analyze, chat, export, filter, aggregate  # noqa: E402

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

from rate_limit import limiter  # noqa: E402

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="claude-analytics-dashboard",
    description="AI-powered CSV analytics dashboard backend",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
_allowed_origins = [o.strip() for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(filter.router, prefix="/api", tags=["filter"])
app.include_router(aggregate.router, prefix="/api", tags=["aggregate"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict:
    """Basic health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
