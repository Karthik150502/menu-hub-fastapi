"""
Restaurant endpoints.
  • POST   /restaurants                — create (authenticated)
  • GET    /restaurants                — list all (public)
  • GET    /restaurants/me             — list own restaurants (authenticated)
  • GET    /restaurants/{id}           — get by id (public)
  • GET    /restaurants/{id}/dishes    — list a restaurant's dishes, paginated, optionally
                                          filtered by category_id (public)
  • GET    /restaurants/{id}/categories — list categories used by a restaurant's dishes,
                                          paginated (public)
  • PATCH  /restaurants/{id}           — update (owner only)
  • DELETE /restaurants/{id}           — delete (owner only)
"""
import uuid

from fastapi import APIRouter

from app.api.deps import AnonSupabase, CurrentUser, ServiceSupabase
from app.schemas.category import CategoryRead
from app.schemas.common import PaginatedResponse, Response
from app.schemas.dish import DishRead
from app.schemas.restaurant import RestaurantCreate, RestaurantRead, RestaurantUpdate
from app.services.category_service import CategoryService
from app.services.dish_service import DishService
from app.services.restaurant_service import RestaurantService

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


@router.post("", response_model=Response[RestaurantRead], status_code=201)
async def create_restaurant(
    payload: RestaurantCreate,
    current_user: CurrentUser,
    client: ServiceSupabase,
) -> Response[RestaurantRead]:
    service = RestaurantService(client)
    restaurant = await service.create(current_user.id, payload)
    return Response(message="Restaurant created", data=RestaurantRead.model_validate(restaurant))


@router.get("", response_model=PaginatedResponse[RestaurantRead])
async def list_restaurants(
    client: AnonSupabase,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[RestaurantRead]:
    service = RestaurantService(client)
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
    client: ServiceSupabase,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[RestaurantRead]:
    service = RestaurantService(client)
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
    client: AnonSupabase,
) -> Response[RestaurantRead]:
    service = RestaurantService(client)
    restaurant = await service.get(restaurant_id)
    return Response(data=RestaurantRead.model_validate(restaurant))


@router.get("/{restaurant_id}/dishes", response_model=PaginatedResponse[DishRead])
async def list_restaurant_dishes(
    restaurant_id: uuid.UUID,
    client: AnonSupabase,
    category_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[DishRead]:
    await RestaurantService(client).get(restaurant_id)  # 404s if the restaurant doesn't exist
    service = DishService(client)
    offset = (page - 1) * page_size
    dishes = await service.list_by_restaurant(
        restaurant_id, category_id=category_id, limit=page_size + 1, offset=offset
    )
    has_next = len(dishes) > page_size
    return PaginatedResponse(
        data=dishes[:page_size],
        total=-1,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.get("/{restaurant_id}/categories", response_model=PaginatedResponse[CategoryRead])
async def list_restaurant_categories(
    restaurant_id: uuid.UUID,
    client: AnonSupabase,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[CategoryRead]:
    await RestaurantService(client).get(restaurant_id)  # 404s if the restaurant doesn't exist
    service = CategoryService(client)
    offset = (page - 1) * page_size
    categories = await service.list_by_restaurant(restaurant_id, limit=page_size + 1, offset=offset)
    has_next = len(categories) > page_size
    return PaginatedResponse(
        data=[CategoryRead.model_validate(c) for c in categories[:page_size]],
        total=-1,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.patch("/{restaurant_id}", response_model=Response[RestaurantRead])
async def update_restaurant(
    restaurant_id: uuid.UUID,
    payload: RestaurantUpdate,
    current_user: CurrentUser,
    client: ServiceSupabase,
) -> Response[RestaurantRead]:
    service = RestaurantService(client)
    restaurant = await service.update(restaurant_id, current_user.id, payload)
    return Response(message="Restaurant updated", data=RestaurantRead.model_validate(restaurant))


@router.delete("/{restaurant_id}", status_code=204)
async def delete_restaurant(
    restaurant_id: uuid.UUID,
    current_user: CurrentUser,
    client: ServiceSupabase,
) -> None:
    service = RestaurantService(client)
    await service.delete(restaurant_id, current_user.id)
