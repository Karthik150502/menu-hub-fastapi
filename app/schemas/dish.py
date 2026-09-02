import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.price import ItemPriceCreate, ItemPriceRead


class DishCreate(BaseModel):
    restaurant_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(min_length=1)
    image_url: str | None = None
    available: bool = True
    veg: bool = True
    show_in_menu: bool = True
    tag: str | None = None
    price: ItemPriceCreate


class DishRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    restaurant_id: uuid.UUID
    name: str
    description: str | None
    category: str
    image_url: str | None
    available: bool
    veg: bool
    show_in_menu: bool
    tag: str | None
    created_at: datetime
    updated_at: datetime
    price: ItemPriceRead
