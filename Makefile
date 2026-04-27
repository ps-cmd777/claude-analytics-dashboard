.PHONY: install install-backend install-frontend dev dev-backend dev-frontend \
        test test-backend test-frontend lint lint-backend lint-frontend \
        format format-backend format-frontend build clean

# ── Installation ───────────────────────────────────────────────────────────────

install: install-backend install-frontend

install-backend:
	cd backend && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

# ── Development servers ────────────────────────────────────────────────────────

dev:
	make -j 2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# ── Testing ────────────────────────────────────────────────────────────────────

test: test-backend test-frontend

test-backend:
	cd backend && pytest tests/ -v --tb=short

test-backend-cov:
	cd backend && pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

test-frontend:
	cd frontend && npm run test

# ── Linting & formatting ───────────────────────────────────────────────────────

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check .

lint-frontend:
	cd frontend && npm run lint

format: format-backend format-frontend

format-backend:
	cd backend && ruff format .

format-frontend:
	cd frontend && npm run format

# ── Build (production) ─────────────────────────────────────────────────────────

build:
	cd frontend && npm run build

# ── Clean ──────────────────────────────────────────────────────────────────────

clean:
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find backend -name "*.pyc" -delete 2>/dev/null; true
	rm -rf frontend/dist 2>/dev/null; true
	rm -rf frontend/node_modules/.cache 2>/dev/null; true
	@echo "Clean complete."
