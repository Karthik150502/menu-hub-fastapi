# FastAPI + Supabase — Production Starter

A production-ready FastAPI project with Supabase (auth + Postgres) as the backend, async SQLAlchemy for ORM/migrations, structured logging, JWT auth, and a full test suite.

---

## Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| Auth | JWT (python-jose) + Supabase Auth |
| Database | Supabase Postgres (via asyncpg) |
| ORM | SQLAlchemy 2 (async) |
| Migrations | Supabase CLI (`supabase/migrations/`) — Alembic (`migrations/`) is frozen, kept only as pre-2026-08-29 history |
| Validation | Pydantic v2 |
| Logging | structlog |
| Testing | pytest-asyncio + HTTPX |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
fastapi-supabase/
├── app/
│   ├── main.py                  # App factory (lifespan, middleware, routers)
│   ├── api/
│   │   ├── deps.py              # Reusable FastAPI dependencies
│   │   └── v1/
│   │       ├── router.py        # Aggregates all v1 routers
│   │       └── endpoints/
│   │           ├── auth.py      # /auth — register, login, refresh, me
│   │           ├── users.py     # /users — CRUD (admin-gated)
│   │           └── health.py    # /health — liveness + readiness
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings + .env)
│   │   ├── security.py          # Supabase-token verification
│   │   ├── logging.py           # structlog setup
│   │   └── exceptions.py        # Typed HTTP exceptions
│   ├── db/
│   │   ├── session.py           # SQLAlchemy Base + column re-exports (frozen models only — no runtime engine)
│   │   └── supabase.py          # Supabase async client (anon + service role) — how the app actually talks to the DB
│   ├── models/
│   │   └── user.py              # SQLAlchemy User model
│   ├── schemas/
│   │   ├── user.py              # Pydantic schemas (request / response)
│   │   └── common.py            # Response[T] + PaginatedResponse[T]
│   ├── services/
│   │   └── user_service.py      # Business logic layer
│   └── middleware/
│       ├── logging.py           # Request/response logging
│       └── errors.py            # Global exception → JSON handler
├── migrations/
│   ├── env.py                   # Async Alembic environment
│   └── versions/                # Generated migration scripts
├── tests/
│   ├── conftest.py              # Shared fixtures (in-memory DB, test client)
│   ├── unit/
│   │   └── test_user_service.py
│   └── integration/
│       └── test_auth.py
├── .env.example
├── alembic.ini
├── pyproject.toml
├── Makefile
├── Dockerfile
└── docker-compose.yml
```

---

## Quick Start

### 1. Clone & install
```bash
git clone <repo>
cd fastapi-supabase
cp .env.example .env          # Fill in your Supabase credentials
poetry install
```

### 2. Run database migrations
```bash
make db-push
# or: supabase db push
```
Schema is managed through the Supabase CLI now, not Alembic — see
[Migrations](#migrations) below.

### 3. Start dev server
```bash
make dev
# or, without make:
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

### 4. Run tests
```bash
make test
```

---

## Development Environment

### Prerequisites
- Python 3.11+ and [Poetry](https://python-poetry.org/)
- [Supabase CLI](https://supabase.com/docs/guides/cli) — for local Postgres/Studio and schema migrations
- Docker Desktop — required by `supabase start` (and for the optional container workflow below)

### Option A — run natively (recommended for day-to-day dev)
```bash
poetry install                          # 1. install deps
cp .env.example .env                    # 2. fill in Supabase creds (see Environment Variables)
make db-start                           # 3. start local Supabase (Postgres + Studio), needs Docker running
make db-push                            # 4. apply migrations to the local DB
make dev                                # 5. start the API with autoreload
# or, without make:
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API: http://localhost:8000
- Swagger/OpenAPI docs: http://localhost:8000/docs
- Supabase Studio: http://127.0.0.1:54323 (`make db-studio` prints this)

Set `APP_ENV=development` in `.env`. `make dev` runs `uvicorn app.main:app --reload`, so code changes hot-reload automatically. Stop the local Supabase stack with `supabase stop` when you're done.

### Option B — run via Docker Compose
```bash
cp .env.example .env                    # fill in Supabase creds first
docker compose up --build
```
This builds the API image and runs it with `--reload` (bind-mounted source, so edits on the host still hot-reload), plus a `redis` service. You still need `make db-start` / `make db-push` (via the Supabase CLI on the host) to have a database to point `DATABASE_URL` at, unless you're pointing at a hosted Supabase project instead.

### Running tests during dev
```bash
make test        # pytest --cov=app --cov-report=term-missing -v
make lint         # ruff check . && mypy app/
```

---

## Supabase Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Copy your project URL, anon key, service role key, and JWT secret into `.env`
3. The `DATABASE_URL` should use the **direct connection** string (not the pooler) from:
   - Supabase Dashboard → Settings → Database → Connection string → URI

---

## Key Patterns

### Response envelope
All endpoints return a consistent JSON shape:
```json
{ "success": true, "message": "OK", "data": { ... } }
```

### Typed exceptions
Throw domain exceptions anywhere — the global handler maps them to JSON:
```python
raise NotFoundError("User")        # → 404
raise ConflictError("Email taken") # → 409
raise UnauthorizedError()          # → 401
```

### Dependency injection
```python
@router.get("/me")
async def me(current_user: CurrentUser, client: ServiceSupabase):
    ...
```

### Service pattern
Services are thin wrappers over `client.table("...")` calls — see
`app/services/profile_service.py` or `app/services/restaurant_service.py`
for the shape to copy (`_get_or_404`, dict-based rows, ownership checked
in Python). There's no repository/ORM layer to extend anymore.

### Adding a new feature
1. Add schema in `app/schemas/`
2. Add service in `app/services/`, following the pattern above
3. Add router in `app/api/v1/endpoints/`
4. Register router in `app/api/v1/router.py`
5. Edit the table's file in `supabase/schemas/` (add a new file for a new domain), then `make db-diff name=add_posts_table` and `make db-push` — see [Migrations](#migrations)

---

## Migrations

Schema changes go through the **Supabase CLI**, using **declarative schemas** — not Alembic.

`supabase/schemas/*.sql` is the schema, split one file per domain (`02_currencies.sql`, `04_restaurants.sql`, `05_dishes.sql`, …), listed in dependency order in `supabase/config.toml`'s `db.migrations.schema_paths`. This is the thing to edit — it's always the current end-state definition (think `schema.prisma`), not a diff. `supabase/migrations/*.sql` stays a generated, append-only history; don't hand-edit past files in it.

```bash
make db-start                          # supabase start — local Postgres + Studio (needs Docker Desktop running)
# edit supabase/schemas/*.sql to the shape you want
make db-diff name=add_posts_table      # supabase db diff -f add_posts_table — diffs schemas/ against local DB, writes the migration
make db-push                           # supabase db push — applies pending migrations to the linked project
make db-pull                           # supabase db pull — pulls the linked project's schema as a migration (needs Docker)
```

**Visualizing the schema:** with `make db-start` running, open Studio at `http://127.0.0.1:54323` → **Database → Schema Visualizer** for an interactive ERD of the live local DB. `make db-studio` prints that URL.

`migrations/` (Alembic) is **frozen** as of 2026-08-29 — kept in the repo as historical record of how the schema got to that point, but no longer used to author new changes. Don't run `alembic revision --autogenerate` — `make migrate`/`make migration` are kept working for reference but are not how schema changes happen anymore. `app/models/*.py` are similarly frozen ORM definitions, kept only so Alembic's autogenerate metadata still resolves — the app itself has no SQLAlchemy runtime left (as of 2026-08-29, when `RestaurantService`, the last holdout, moved to the Supabase SDK); every service talks to Supabase directly via `app/db/supabase.py`. Neither is read by `db diff`/`db push` anymore, so they can't drift out of sync with `supabase/schemas/` in a way that breaks anything — they just won't reflect new columns you add there.

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret — keep this long and random |
| `SUPABASE_URL` | Your project URL (`https://xxx.supabase.co`) |
| `SUPABASE_ANON_KEY` | Public anon key (safe for client apps) |
| `SUPABASE_SERVICE_ROLE_KEY` | Bypasses RLS — never expose to clients |
| `SUPABASE_JWT_SECRET` | Used to verify Supabase-issued JWTs |
| `DATABASE_URL` | Direct `postgresql+asyncpg://` connection string |
| `APP_ENV` | `development` / `staging` / `production` |
| `ALLOWED_ORIGINS` | JSON array of frontend origins allowed by CORS, e.g. `["http://localhost:3000","http://localhost:8081"]`. Defaults to those two (web + Expo/Metro) if unset — add your app's origin(s) if it runs elsewhere |
