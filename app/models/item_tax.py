from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, DateTime, Identity, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ItemTax(Base):
    """A single, reusable tax rule — e.g. "GST" 18%, "CGST" 2.5%.
    Global catalogue, not restaurant-scoped."""

    __tablename__ = "item_taxes"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    rate: Mapped[float] = mapped_column(Numeric, nullable=False)
    inclusive: Mapped[bool | None] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ItemTax id={self.id} name={self.name!r} rate={self.rate}>"
