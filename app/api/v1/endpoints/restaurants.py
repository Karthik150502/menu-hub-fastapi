"""
Restaurant endpoints.
  • POST   /restaurants          — create (authenticated)
  • GET    /restaurants          — list all (public)
  • GET    /restaurants/me       — list own restaurants (authenticated)
  • GET    /restaurants/{id}     — get by id (public)
  • PATCH  /restaurants/{id}     — update (owner only)
  • DELETE /restaurants/{id}     — delete (owner only)
"""
import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import PaginatedResponse, Response
from app.schemas.restaurant import RestaurantCreate, RestaurantRead, RestaurantUpdate
from app.services.restaurant_service import RestaurantService

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.post("", response_model=Response[RestaurantRead], status_code=201)
async def create_restaurant(
    payload: RestaurantCreate,
    current_user: CurrentUser,
    session: DBSession,
) -> Response[RestaurantRead]:
    service = RestaurantService(session)
    restaurant = await service.create(current_user.id, payload)
    return Response(message="Restaurant created", data=RestaurantRead.model_validate(restaurant))


@router.get("", response_model=PaginatedResponse[RestaurantRead])
async def list_restaurants(
    session: DBSession,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[RestaurantRead]:
    service = RestaurantService(session)
    offset = (page - 1) * page_size
    restaurants = await service.list(limit=page_size + 1, offset=offset)
    has_next = len(restaurants) > page_size
    return PaginatedResponse(
        data=[RestaurantRead.model_validate(r) for r in restaurants[:page_size]],
        total=-1,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.get("/me", response_model=PaginatedResponse[RestaurantRead])
async def list_my_restaurants(
    current_user: CurrentUser,
    session: DBSession,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[RestaurantRead]:
    service = RestaurantService(session)
    offset = (page - 1) * page_size
    restaurants = await service.list_by_owner(current_user.id, limit=page_size + 1, offset=offset)
    has_next = len(restaurants) > page_size
    return PaginatedResponse(
        data=[RestaurantRead.model_validate(r) for r in restaurants[:page_size]],
        total=-1,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.get("/{restaurant_id}", response_model=Response[RestaurantRead])
async def get_restaurant(
    restaurant_id: uuid.UUID,
    session: DBSession,
) -> Response[RestaurantRead]:
    service = RestaurantService(session)
    restaurant = await service.get(restaurant_id)
    return Response(data=RestaurantRead.model_validate(restaurant))


@router.patch("/{restaurant_id}", response_model=Response[RestaurantRead])
async def update_restaurant(
    restaurant_id: uuid.UUID,
    payload: RestaurantUpdate,
    current_user: CurrentUser,
    session: DBSession,
) -> Response[RestaurantRead]:
    service = RestaurantService(session)
    restaurant = await service.update(restaurant_id, current_user.id, payload)
    return Response(message="Restaurant updated", data=RestaurantRead.model_validate(restaurant))


@router.delete("/{restaurant_id}", status_code=204)
async def delete_restaurant(
    restaurant_id: uuid.UUID,
    current_user: CurrentUser,
    session: DBSession,
) -> None:
    service = RestaurantService(session)
    await service.delete(restaurant_id, current_user.id)
