.PHONY: install dev lint test migrate migration db-pull db-push db-new db-diff db-start db-studio

install:
	poetry install

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check . && mypy app/

test:
	pytest --cov=app --cov-report=term-missing -v

# ── Schema (Supabase CLI declarative schemas — see README's Migrations section) ─
# Edit supabase/schemas/*.sql (the current-state schema, like schema.prisma),
# then `make db-diff name=...` to generate the migration that gets you there.
db-start:
	supabase start

db-studio:
	@echo "Studio: http://127.0.0.1:54323  (Database > Schema Visualizer for the ERD)"

db-diff:
	supabase db diff -f $(name)

db-pull:
	supabase db pull

db-push:
	supabase db push

# Rarely needed once using declarative schemas (db-diff generates migrations
# for you) — kept for one-off data/DML migrations that shouldn't live in
# supabase/schemas/ (which is structure-only).
db-new:
	supabase migration new $(name)

# ── Legacy (Alembic) — frozen as of 2026-08-29, kept for history only ──────
migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(name)"
