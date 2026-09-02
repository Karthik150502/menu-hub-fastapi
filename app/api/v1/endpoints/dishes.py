"""
Dish endpoints.
  • POST /dishes — create a dish together with its one ItemPrice (owner only)
"""
from fastapi import APIRouter

from app.api.deps import CurrentUser, ServiceSupabase
from app.schemas.common import Response
from app.schemas.dish import DishCreate, DishRead
from app.services.dish_service import DishService

router = APIRouter(prefix="/dishes", tags=["dishes"])


@router.post("", response_model=Response[DishRead], status_code=201)
async def create_dish(
    payload: DishCreate,
    current_user: CurrentUser,
    client: ServiceSupabase,
) -> Response[DishRead]:
    service = DishService(client)
    dish = await service.create(current_user.id, payload)
    return Response(message="Dish created", data=dish)
