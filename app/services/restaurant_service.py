import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate


class RestaurantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _get_or_404(self, restaurant_id: uuid.UUID) -> Restaurant:
        restaurant = await self.session.get(Restaurant, restaurant_id)
        if not restaurant:
            raise NotFoundError("Restaurant")
        return restaurant

    async def create(self, owner_id: uuid.UUID, payload: RestaurantCreate) -> Restaurant:
        restaurant = Restaurant(owner_id=owner_id, **payload.model_dump())
        self.session.add(restaurant)
        await self.session.flush()
        await self.session.refresh(restaurant)
        return restaurant

    async def get(self, restaurant_id: uuid.UUID) -> Restaurant:
        return await self._get_or_404(restaurant_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Restaurant]:
        result = await self.session.execute(
            select(Restaurant).order_by(Restaurant.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_owner(self, owner_id: uuid.UUID, *, limit: int = 50, offset: int = 0) -> list[Restaurant]:
        result = await self.session.execute(
            select(Restaurant)
            .where(Restaurant.owner_id == owner_id)
            .order_by(Restaurant.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, restaurant_id: uuid.UUID, owner_id: uuid.UUID, payload: RestaurantUpdate) -> Restaurant:
        restaurant = await self._get_or_404(restaurant_id)
        if restaurant.owner_id != owner_id:
            raise ForbiddenError("You do not own this restaurant")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(restaurant, field, value)

        await self.session.flush()
        await self.session.refresh(restaurant)
        return restaurant

    async def delete(self, restaurant_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        restaurant = await self._get_or_404(restaurant_id)
        if restaurant.owner_id != owner_id:
            raise ForbiddenError("You do not own this restaurant")
        await self.session.delete(restaurant)
