.PHONY: install dev lint test migrate migration db-pull db-push db-new

install:
	poetry install

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check . && mypy app/

test:
	pytest --cov=app --cov-report=term-missing -v

# ── Schema (Supabase CLI — see README's Migrations section) ────────────────
db-pull:
	supabase db pull

db-push:
	supabase db push

db-new:
	supabase migration new $(name)

# ── Legacy (Alembic) — frozen as of 2026-08-29, kept for history only ──────
migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(name)"
