import uuid
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class DiscountCreate(BaseModel):
    type: Literal["percentage", "fixed"]
    on: Literal["basePrice", "priceIncludingTaxes"]
    value: float = Field(gt=0)
    label: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class ItemPriceCreate(BaseModel):
    base_price: float = Field(gt=0)
    currency_code: str = "INR"
    mrp: float | None = Field(default=None, gt=0)
    discount: DiscountCreate | None = None


class DiscountRead(BaseModel):
    type: str
    on: str
    value: float
    label: str | None
    valid_from: datetime | None
    valid_until: datetime | None


class ItemPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dish_id: uuid.UUID
    base_price: float
    currency_code: str
    total_tax_amount: float
    final_price: float
    mrp: float | None
    discount: DiscountRead | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "ItemPriceRead":
        """Supabase returns item_prices rows flat (discount_type/_on/_value/
        _label/_valid_from/_valid_until columns) — re-nest them into a
        single optional `discount` object for the API response, mirroring
        the nested shape ItemPriceCreate accepts on the way in."""
        discount = None
        if row.get("discount_type") is not None:
            discount = DiscountRead(
                type=row["discount_type"],
                on=row["discount_on"],
                value=row["discount_value"],
                label=row.get("discount_label"),
                valid_from=row.get("discount_valid_from"),
                valid_until=row.get("discount_valid_until"),
            )
        return cls(
            id=row["id"],
            dish_id=row["dish_id"],
            base_price=row["base_price"],
            currency_code=row["currency_code"],
            total_tax_amount=row["total_tax_amount"],
            final_price=row["final_price"],
            mrp=row.get("mrp"),
            discount=discount,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
