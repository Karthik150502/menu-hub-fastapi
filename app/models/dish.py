import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dish(Base):
    """A menu item belonging to a restaurant.

    Note: base_price/currency_code here mirror the same fields on
    ItemPrice (see app/models/price.py) — that duplication comes straight
    from the DishItem TS type on the client (types/dish.ts). item_prices is
    the source of truth for pricing; these columns exist only for parity
    with the client type. base_price is kept in sync with
    item_prices.base_price by a DB trigger (sync_dish_base_price) — never
    set it directly once an item_prices row exists for the dish.
    """

    __tablename__ = "dishes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(
        Text, ForeignKey("currencies.code"), default="INR", nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    veg: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    show_in_menu: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tag: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Dish id={self.id} name={self.name!r}>"
