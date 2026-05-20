import uuid
from datetime import datetime
from typing import Any

from app.db.supabase import AsyncClient

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate 


class UserService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    def _to_user(self, data: Any) -> User:
        def _parse_dt(value: str | datetime | None) -> datetime | None:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(value)

        return User(
            id=uuid.UUID(data["id"]),
            email=data["email"],
            full_name=data.get("full_name"),
            avatar_url=data.get("avatar_url"),
            hashed_password=data.get("hashed_password", ""),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            is_superuser=data.get("is_superuser", False),
            created_at=_parse_dt(data.get("created_at")),
            updated_at=_parse_dt(data.get("updated_at")),
        )

    async def _get_by_email(self, email: str) -> User | None:
        response = await (
            self.client.table("users")
            .select("*")
            .eq("email", email.lower())
            .maybe_single()
            .execute()
        )
        return self._to_user(response.data) if response and response.data else None

    async def _get_or_404(self, user_id: uuid.UUID) -> User:
        response = await (
            self.client.table("users")
            .select("*")
            .eq("id", str(user_id))
            .maybe_single()
            .execute()
        )
        if response and response.data:
            return self._to_user(response.data)
        raise NotFoundError("User")

    async def create(self, payload: UserCreate) -> User:
        if await self._get_by_email(payload.email):
            raise ConflictError("A user with that email already exists")

        response = await (
            self.client.table("users")
            .insert({
                "id": str(uuid.uuid4()),
                "email": payload.email.lower(),
                "full_name": payload.full_name,
                "hashed_password": hash_password(payload.password),
            })
            .execute()
        )
        return self._to_user(response.data[0])

    async def get(self, user_id: uuid.UUID) -> User:
        return await self._get_or_404(user_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        response = await (
            self.client.table("users")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return [self._to_user(row) for row in (response.data or [])]

    async def update(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        await self._get_or_404(user_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        response = await (
            self.client.table("users")
            .update(update_data)
            .eq("id", str(user_id))
            .execute()
        )
        return self._to_user(response.data[0])

    async def delete(self, user_id: uuid.UUID) -> None:
        await self._get_or_404(user_id)
        await self.client.table("users").delete().eq("id", str(user_id)).execute()

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")
        return user
