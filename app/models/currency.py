from datetime import datetime, timezone
from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Currency(Base):
    """Global currency lookup — e.g. code='INR', symbol='₹'. Referenced by
    dishes.currency_code and item_prices.currency_code."""

    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(Text, primary_key=True, server_default="INR")
    symbol: Mapped[str] = mapped_column(Text, nullable=False, server_default="₹")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Currency code={self.code!r} symbol={self.symbol!r}>"
