import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class RestaurantBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_open: bool = True
    currency: str = Field(default="₹", max_length=10)
    logo_url: str | None = None
    image_url: str | None = None
    address_line: str | None = None
    pincode: str | None = Field(default=None, max_length=20)
    city: str | None = None
    state: str | None = None
    country: str = "India"


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_open: bool | None = None
    currency: str | None = Field(default=None, max_length=10)
    logo_url: str | None = None
    image_url: str | None = None
    address_line: str | None = None
    pincode: str | None = Field(default=None, max_length=20)
    city: str | None = None
    state: str | None = None
    country: str | None = None


class RestaurantRead(RestaurantBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
