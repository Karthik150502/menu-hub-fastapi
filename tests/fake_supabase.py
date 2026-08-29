"""
A minimal in-memory fake of the pieces of supabase.AsyncClient that
AuthService/ProfileService actually use (auth.sign_up/sign_in_with_password/
refresh_session/get_user/admin.*, and .table("profiles")...execute()).

Lets tests exercise the real service/endpoint code against realistic
Supabase response shapes without any network access or a live project —
including the same handle_new_user-trigger behavior (a profiles row is
created alongside every signed-up user).
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from supabase_auth.errors import AuthApiError


class FakeUser:
    def __init__(
        self,
        user_id: str,
        email: str,
        password: str,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> None:
        self.id = user_id
        self.email = email
        self.password = password
        self.user_metadata = {"full_name": full_name, "avatar_url": avatar_url}
        self.email_confirmed_at = datetime.now(timezone.utc)
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class FakeSession:
    def __init__(self, user: FakeUser) -> None:
        self.user = user
        self.access_token = f"access-{user.id}"
        self.refresh_token = f"refresh-{user.id}"


class FakeAuthResponse:
    def __init__(self, user: FakeUser | None = None, session: FakeSession | None = None) -> None:
        self.user = user
        self.session = session


class FakeUserResponse:
    def __init__(self, user: FakeUser | None) -> None:
        self.user = user


class FakeAdminAPI:
    def __init__(self, store: "FakeSupabaseClient") -> None:
        self.store = store

    async def get_user_by_id(self, uid: str) -> FakeUserResponse:
        return FakeUserResponse(self.store.users_by_id.get(uid))

    async def delete_user(self, uid: str) -> None:
        self.store.users_by_id.pop(uid, None)
        self.store.profiles.pop(uid, None)


class FakeAuth:
    def __init__(self, store: "FakeSupabaseClient") -> None:
        self.store = store
        self.admin = FakeAdminAPI(store)

    async def sign_up(self, credentials: dict[str, Any]) -> FakeAuthResponse:
        email = credentials["email"]
        if any(u.email == email for u in self.store.users_by_id.values()):
            raise AuthApiError("User already registered", 422, None)

        data = (credentials.get("options") or {}).get("data") or {}
        user_id = str(uuid.uuid4())
        user = FakeUser(
            user_id, email, credentials["password"], data.get("full_name"), data.get("avatar_url")
        )
        self.store.users_by_id[user_id] = user
        # simulate the handle_new_user DB trigger from migration 0004
        self.store.profiles[user_id] = {
            "id": user_id,
            "full_name": data.get("full_name"),
            "avatar_url": data.get("avatar_url"),
            "is_active": True,
            "is_superuser": False,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
        return FakeAuthResponse(user=user, session=None)

    async def sign_in_with_password(self, credentials: dict[str, Any]) -> FakeAuthResponse:
        user = next(
            (u for u in self.store.users_by_id.values() if u.email == credentials["email"]), None
        )
        if user is None or user.password != credentials["password"]:
            raise AuthApiError("Invalid login credentials", 400, None)
        return FakeAuthResponse(user=user, session=FakeSession(user))

    async def refresh_session(self, refresh_token: str | None = None) -> FakeAuthResponse:
        user_id = (refresh_token or "").removeprefix("refresh-")
        user = self.store.users_by_id.get(user_id)
        if user is None:
            raise AuthApiError("Invalid refresh token", 401, None)
        return FakeAuthResponse(user=user, session=FakeSession(user))

    async def get_user(self, token: str | None = None) -> FakeUserResponse | None:
        user_id = (token or "").removeprefix("access-")
        user = self.store.users_by_id.get(user_id)
        if user is None:
            # matches real Supabase: a still-valid token for a deleted user
            # raises rather than returning an empty response.
            raise AuthApiError("User from sub claim in JWT does not exist", 403, None)
        return FakeUserResponse(user)


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    """Supports the exact chain shapes ProfileService uses against
    .table("profiles") — select/eq/maybe_single/order/range, and update/eq."""

    def __init__(self, store: "FakeSupabaseClient") -> None:
        self.store = store
        self._filters: dict[str, str] = {}
        self._single = False
        self._order: tuple[str, bool] | None = None
        self._range: tuple[int, int] | None = None
        self._update_data: dict[str, Any] | None = None

    def select(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        return self

    def eq(self, field: str, value: Any) -> "FakeQuery":
        self._filters[field] = str(value)
        return self

    def maybe_single(self) -> "FakeQuery":
        self._single = True
        return self

    def order(self, field: str, desc: bool = False) -> "FakeQuery":
        self._order = (field, desc)
        return self

    def range(self, start: int, end: int) -> "FakeQuery":
        self._range = (start, end)
        return self

    def update(self, data: dict[str, Any]) -> "FakeQuery":
        self._update_data = data
        return self

    def _matching_rows(self) -> list[dict[str, Any]]:
        rows = list(self.store.profiles.values())
        for field, value in self._filters.items():
            rows = [r for r in rows if str(r.get(field)) == value]
        return rows

    async def execute(self) -> FakeResponse:
        rows = self._matching_rows()

        if self._update_data is not None:
            for row in rows:
                row.update(self._update_data)
            return FakeResponse(rows)

        if self._order:
            field, desc = self._order
            rows = sorted(rows, key=lambda r: r[field], reverse=desc)
        if self._range:
            start, end = self._range
            rows = rows[start : end + 1]

        if self._single:
            return FakeResponse(rows[0] if rows else None)
        return FakeResponse(rows)


class FakeSupabaseClient:
    """Stands in for both the anon and service Supabase clients in tests —
    both flavours talk to the same underlying store, matching how they'd
    both hit the same real Postgres/Auth instance in production."""

    def __init__(self) -> None:
        self.users_by_id: dict[str, FakeUser] = {}
        self.profiles: dict[str, dict[str, Any]] = {}
        self.auth = FakeAuth(self)

    def table(self, name: str) -> FakeQuery:
        assert name == "profiles", f"fake client only knows about 'profiles', got {name!r}"
        return FakeQuery(self)
