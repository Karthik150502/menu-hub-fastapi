"""
Category endpoints.
  • GET /categories — list all categories (public)
"""
from fastapi import APIRouter

from app.api.deps import AnonSupabase
from app.schemas.category import CategoryRead
from app.schemas.common import Response
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=Response[list[CategoryRead]])
async def list_categories(client: AnonSupabase) -> Response[list[CategoryRead]]:
    service = CategoryService(client)
    categories = await service.list()
    return Response(data=[CategoryRead.model_validate(c) for c in categories])
