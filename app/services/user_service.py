"""
UserService encapsulates all business logic for user management.
It sits between the API layer and the repository / Supabase client.
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────
    async def _get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def _get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.session.get(User, user_id)
        if not user:
            raise NotFoundError("User")
        return user

    # ── Public API ────────────────────────────────────────────────────────
    async def create(self, payload: UserCreate) -> User:
        if await self._get_by_email(payload.email):
            raise ConflictError("A user with that email already exists")

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get(self, user_id: uuid.UUID) -> User:
        return await self._get_or_404(user_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[User]:
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = await self._get_or_404(user_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete(self, user_id: uuid.UUID) -> None:
        user = await self._get_or_404(user_id)
        await self.session.delete(user)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")
        return user
