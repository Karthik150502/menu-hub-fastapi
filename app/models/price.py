import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ItemPrice(Base):
    """The full priced state of one dish — mirrors the ItemPrice TS type
    (types/price.ts) 1:1 with Dish via dish_id. Discount is a value object
    (null = no discount) flattened into nullable columns rather than its
    own table, since it never exists independently of an ItemPrice.
    """

    __tablename__ = "item_prices"
    __table_args__ = (
        CheckConstraint(
            "(discount_type is null and discount_on is null and discount_value is null)"
            " or (discount_type is not null and discount_on is not null and discount_value is not null)",
            name="chk_discount_consistent",
        ),
        CheckConstraint("discount_type in ('percentage', 'fixed')"),
        CheckConstraint("discount_on in ('basePrice', 'priceIncludingTaxes')"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dishes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(Text, ForeignKey("currencies.code"), nullable=False)

    total_tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    final_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    mrp: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Discount | null
    discount_type: Mapped[str | None] = mapped_column(Text)
    discount_on: Mapped[str | None] = mapped_column(Text)
    discount_value: Mapped[float | None] = mapped_column(Numeric(10, 2))
    discount_label: Mapped[str | None] = mapped_column(Text)
    discount_valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    discount_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ItemPrice id={self.id} dish_id={self.dish_id} final_price={self.final_price}>"


class TaxLineItem(Base):
    """The single tax configuration attached to one ItemPrice — 1:1 via
    item_price_id. Holds all groups + individually applied taxes."""

    __tablename__ = "tax_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_price_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("item_prices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<TaxLineItem id={self.id} item_price_id={self.item_price_id}>"


class TaxLineItemGroup(Base):
    """Join table: TaxLineItem.groups — which tax_groups apply to a
    tax_line_item, with the pre-computed amount for that group
    (replaces TaxLineItem.computedAmounts[group.id] from the TS type)."""

    __tablename__ = "tax_line_item_groups"

    tax_line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_line_items.id", ondelete="CASCADE"), primary_key=True
    )
    tax_group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tax_groups.id", ondelete="RESTRICT"), primary_key=True
    )
    computed_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<TaxLineItemGroup tax_line_item_id={self.tax_line_item_id} tax_group_id={self.tax_group_id}>"


class TaxLineItemTax(Base):
    """Join table: TaxLineItem.taxes — which individual item_taxes apply to
    a tax_line_item, with the pre-computed amount for that tax
    (replaces TaxLineItem.computedAmounts[tax.id] from the TS type)."""

    __tablename__ = "tax_line_item_taxes"

    tax_line_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_line_items.id", ondelete="CASCADE"), primary_key=True
    )
    item_tax_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("item_taxes.id", ondelete="RESTRICT"), primary_key=True
    )
    computed_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<TaxLineItemTax tax_line_item_id={self.tax_line_item_id} item_tax_id={self.item_tax_id}>"
