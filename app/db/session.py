"""
SQLAlchemy declarative base + column-type re-exports.

Runtime session/engine machinery (engine, AsyncSessionLocal, get_db) was
removed here once RestaurantService — the last consumer — moved to the
Supabase SDK on 2026-08-29; the app no longer opens its own Postgres
connections. Base and the column-type re-exports below stay because
app/models/*.py (frozen alongside Alembic, see migrations/env.py) still
import them.
"""
from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass
