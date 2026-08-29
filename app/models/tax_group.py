from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaxGroup(Base):
    """A named, reusable bundle of ItemTaxes — e.g. "Restaurant Standard" =
    [CGST 2.5% + SGST 2.5%]. Global catalogue, not restaurant-scoped
    (matches item_taxes). combined_rate is kept in sync with its members by
    a DB trigger (refresh_tax_group_combined_rate) — never set it directly."""

    __tablename__ = "tax_groups"

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    combined_rate: Mapped[float] = mapped_column(Numeric(6, 3), default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<TaxGroup id={self.id} name={self.name!r} combined_rate={self.combined_rate}>"


class TaxGroupMember(Base):
    """Join table: which item_taxes belong to a tax_group."""

    __tablename__ = "tax_group_members"

    tax_group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tax_groups.id", ondelete="CASCADE"), primary_key=True
    )
    item_tax_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("item_taxes.id", ondelete="CASCADE"), primary_key=True
    )

    def __repr__(self) -> str:
        return f"<TaxGroupMember tax_group_id={self.tax_group_id} item_tax_id={self.item_tax_id}>"
