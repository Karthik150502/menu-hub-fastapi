"""
Profile model — app-specific fields for a Supabase Auth user.

Identity (email, password) lives entirely in Supabase's own auth.users
table; this model only carries what the app adds on top. 1:1 with
auth.users.id via a DB trigger (handle_new_user, see migration 0004) that
creates the row on signup — never insert a profile from application code.

id has no mapped ForeignKey here, matching Restaurant.owner_id's existing
pattern: the actual auth.users FK is added via a raw cross-schema
op.create_foreign_key in the migration, not through SQLAlchemy's metadata,
since auth.users isn't a table this app owns or maps.
"""
import uuid
from datetime import datetime, timezone
from app.db.session import Base, Boolean, DateTime, Mapped, Text, UUID, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    full_name: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Profile id={self.id}>"
