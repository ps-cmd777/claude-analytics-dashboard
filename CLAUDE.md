# claude-analytics-dashboard — AI Context File

## Project Overview

Portfolio Project 2 — a full-stack web application that lets users upload a CSV and
get an AI-powered analytics dashboard with interactive charts, streaming Claude insights,
and a chat interface for follow-up questions.

Builds on Project 1 (`claude-data-reporter`) by adding a React frontend and FastAPI
backend. The core pandas profiling logic and Claude tool-use loop are reused from
Project 1 and adapted for an HTTP/SSE context.

## Tech Stack

| Layer | Library |
|-------|---------|
| Backend | FastAPI, uvicorn, python-multipart |
| Data profiling | pandas, numpy (same DataProfiler as Project 1) |
| AI | anthropic SDK — tool-use loop + `.stream()` for SSE |
| Config | python-dotenv, Pydantic v2 |
| Frontend | React 19, Vite, TypeScript |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
| Testing (BE) | pytest, httpx, pytest-asyncio |
| Testing (FE) | Vitest, React Testing Library |
| Linting | ruff (Python), ESLint + TypeScript (frontend) |

## Directory Structure

```
claude-analytics-dashboard/
├── Makefile
├── CLAUDE.md
├── README.md
├── .gitignore
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── main.py               — FastAPI app + CORS
│   ├── models/schemas.py     — Pydantic models
│   ├── services/
│   │   ├── session_store.py  — In-memory session management
│   │   ├── profiler.py       — UploadFile → DataProfile adapter
│   │   ├── claude_client.py  — Tool-use loop + SSE generator
│   │   └── report_generator.py
│   ├── routers/
│   │   ├── upload.py         — POST /api/upload
│   │   ├── analyze.py        — GET /api/analyze/{id} (SSE)
│   │   ├── chat.py           — POST /api/chat/{id} (SSE)
│   │   └── export.py         — GET /api/export/{id}
│   └── tests/
└── frontend/
    └── src/
        ├── types/index.ts
        ├── utils/api.ts
        ├── hooks/            — useFileUpload, useAnalysis, useChat
        └── components/       — Dashboard, ChartGrid, DynamicChartGrid,
                                InsightCards, InsightsPanel, ChatInterface,
                                FilterBar, ExportButton, DomainBadge,
                                layout/LandingLayout
```

## Common Commands

```bash
# Install everything
make install

# Start both servers (backend :8000, frontend :5173)
make dev

# Tests
make test

# Lint
make lint

# Format
make format

# Build frontend for production
make build
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/upload | Upload CSV → profile + session_id |
| GET | /api/analyze/{id} | Stream AI insights (SSE) |
| POST | /api/chat/{id} | Stream chat reply (SSE) |
| GET | /api/export/{id} | Download Markdown report |
| GET | /api/session/{id} | Session health check |

## SSE Event Format

```json
{"type": "status", "message": "Running data profiling tools..."}
{"type": "token", "text": "This dataset..."}
{"type": "done", "result": {...}}
{"type": "error", "message": "Session not found"}
```

## Streaming Architecture

**Analyze endpoint** — two-phase:
1. Tool-use loop runs silently (no streaming); `status` SSE events keep UI alive
2. Final Claude response re-requested with `.stream()` to emit `token` events

**Chat endpoint** — single-phase:
1. POST with `ReadableStream` fetch; Claude responds with streaming; tool calls handled server-side

## Coding Standards

### Python (backend)
- **Type hints** on all function signatures
- **Docstrings** on every public method/function
- `ruff format` + `ruff check` before commits
- No hardcoded API keys — read from `ANTHROPIC_API_KEY` env var only
- `client = anthropic.Anthropic()` (reads key automatically from env)

### TypeScript (frontend)
- All components typed with explicit props interfaces
- No `any` — use proper union types or `unknown`
- Hooks in `src/hooks/`, utilities in `src/utils/`

## Environment Variables

### backend/.env
```
ANTHROPIC_API_KEY=<your-key-from-console.anthropic.com>
DEFAULT_MODEL=claude-sonnet-4-6
MAX_UPLOAD_MB=50
CORS_ORIGINS=http://localhost:5173
```

### frontend/.env
```
VITE_API_BASE_URL=http://localhost:8000
```

## Session Management

Sessions are stored in a module-level dict (`dict[str, Session]`) keyed by UUID4.
No database — single-session, in-memory. Each session stores:
- `df` — the loaded DataFrame (needed for tool dispatch)
- `profiler` — `DataProfiler` instance after `profile()` is called
- `profile` — the `DataProfile` result
- `analysis` — `AnalysisResult` (set after `/analyze` completes)
- `chat_history` — list of Anthropic message dicts for multi-turn chat

## Built With Claude Code

This project was scaffolded and developed using Claude Code CLI.
See the plan at `.claude/plans/` for the architectural decisions.

## Related Projects

- [claude-data-reporter](https://github.com/shushan/claude-data-reporter) — Project 1 (Python CLI)
