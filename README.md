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
| Migrations | Alembic |
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
│   │   ├── security.py          # JWT helpers, password hashing
│   │   ├── logging.py           # structlog setup
│   │   └── exceptions.py        # Typed HTTP exceptions
│   ├── db/
│   │   ├── session.py           # Async SQLAlchemy engine + get_db()
│   │   ├── supabase.py          # Supabase async client (anon + service role)
│   │   └── repository.py        # Generic async repository base class
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
make migrate
# or: alembic upgrade head
```

### 3. Start dev server
```bash
make dev
# API: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

### 4. Run tests
```bash
make test
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
async def me(current_user: CurrentUser, session: DBSession):
    ...
```

### Repository pattern
Extend `BaseRepository` for new models:
```python
class PostRepository(BaseRepository[Post]):
    async def find_by_author(self, author_id: UUID) -> list[Post]:
        ...
```

### Adding a new feature
1. Add model in `app/models/`
2. Add schema in `app/schemas/`
3. Add service in `app/services/`
4. Add router in `app/api/v1/endpoints/`
5. Register router in `app/api/v1/router.py`
6. Generate migration: `make migration name=add_posts_table`

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
