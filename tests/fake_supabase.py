"""
A minimal in-memory fake of the pieces of supabase.AsyncClient that
AuthService/ProfileService/RestaurantService/DishService actually use
(auth.sign_up/sign_in_with_password/refresh_session/get_user/
sign_in_with_otp/verify_otp/admin.*, and .table(...)...execute()).

Lets tests exercise the real service/endpoint code against realistic
Supabase response shapes without any network access or a live project —
including the same handle_new_user-trigger behavior (a profiles row is
created alongside every signed-up user).
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from postgrest.exceptions import APIError
from supabase_auth.errors import AuthApiError


class FakeUser:
    def __init__(
        self,
        user_id: str,
        email: str | None = None,
        password: str | None = None,
        full_name: str | None = None,
        avatar_url: str | None = None,
        phone: str | None = None,
    ) -> None:
        self.id = user_id
        self.email = email
        self.password = password
        self.phone = phone
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

    async def sign_in_with_otp(self, credentials: dict[str, Any]) -> FakeAuthResponse:
        phone = credentials["phone"]
        should_create_user = (credentials.get("options") or {}).get("should_create_user", True)
        user = next((u for u in self.store.users_by_id.values() if u.phone == phone), None)
        if user is None:
            if not should_create_user:
                raise AuthApiError("Signups not allowed for otp", 422, None)
            user_id = str(uuid.uuid4())
            user = FakeUser(user_id, phone=phone)
            self.store.users_by_id[user_id] = user
            # simulate the handle_new_user DB trigger from migration 0004 —
            # fires on any auth.users insert, phone signups included
            self.store.profiles[user_id] = {
                "id": user_id,
                "full_name": None,
                "avatar_url": None,
                "is_active": True,
                "is_superuser": False,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }
        self.store.pending_otps[phone] = "123456"  # fixed test code, no real SMS involved
        return FakeAuthResponse(user=user, session=None)

    async def verify_otp(self, params: dict[str, Any]) -> FakeAuthResponse:
        phone = params["phone"]
        if self.store.pending_otps.get(phone) != params["token"]:
            raise AuthApiError("Token has expired or is invalid", 401, None)
        self.store.pending_otps.pop(phone, None)  # single-use
        user = next((u for u in self.store.users_by_id.values() if u.phone == phone), None)
        if user is None:
            raise AuthApiError("Token has expired or is invalid", 401, None)
        return FakeAuthResponse(user=user, session=FakeSession(user))


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    """Supports the chain shapes ProfileService/RestaurantService use
    against .table(...) — select/eq/maybe_single/order/range/insert/
    update/delete. Operates on one table's row dict (keyed by id)."""

    def __init__(
        self, table: dict[str, dict[str, Any]], table_name: str, fail_inserts: set[str]
    ) -> None:
        self._table = table
        self._table_name = table_name
        self._fail_inserts = fail_inserts
        self._filters: dict[str, str] = {}
        self._single = False
        self._order: tuple[str, bool] | None = None
        self._range: tuple[int, int] | None = None
        self._insert_data: dict[str, Any] | None = None
        self._update_data: dict[str, Any] | None = None
        self._delete = False

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

    def insert(self, data: dict[str, Any]) -> "FakeQuery":
        self._insert_data = data
        return self

    def update(self, data: dict[str, Any]) -> "FakeQuery":
        self._update_data = data
        return self

    def delete(self) -> "FakeQuery":
        self._delete = True
        return self

    def _matching_rows(self) -> list[dict[str, Any]]:
        rows = list(self._table.values())
        for field, value in self._filters.items():
            rows = [r for r in rows if str(r.get(field)) == value]
        return rows

    async def execute(self) -> FakeResponse:
        if self._insert_data is not None and self._table_name in self._fail_inserts:
            self._fail_inserts.discard(self._table_name)  # single-shot
            raise APIError({"message": f"simulated constraint violation on {self._table_name}"})

        if self._insert_data is not None:
            row = dict(self._insert_data)
            row.setdefault("id", str(uuid.uuid4()))
            now = datetime.now(timezone.utc).isoformat()
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
            self._table[row["id"]] = row
            return FakeResponse([row])

        rows = self._matching_rows()

        if self._delete:
            for row in rows:
                self._table.pop(row["id"], None)
            return FakeResponse(rows)

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
        self.pending_otps: dict[str, str] = {}  # phone -> code, set by sign_in_with_otp
        self.tables: dict[str, dict[str, dict[str, Any]]] = {
            "profiles": {},
            "restaurants": {},
            "dishes": {},
            "item_prices": {},
        }
        self.auth = FakeAuth(self)
        # table names in here raise APIError on their next insert (single-shot) —
        # lets tests simulate a DB constraint violation without modelling
        # every real constraint.
        self.fail_inserts: set[str] = set()

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        return self.tables["profiles"]

    def table(self, name: str) -> FakeQuery:
        if name not in self.tables:
            raise AssertionError(f"fake client doesn't know about table {name!r}")
        return FakeQuery(self.tables[name], name, self.fail_inserts)
