"""
Token verification for Supabase Auth.

Password hashing and token *issuance* are Supabase's job now (sign_up /
sign_in_with_password / refresh_session in app/services/auth_service.py) —
this module only verifies bearer tokens the client already got from
Supabase.

Supabase projects on the legacy shared JWT secret sign access tokens with
HS256 using SUPABASE_JWT_SECRET, which we can verify locally with no
network round-trip. Projects that have switched to the newer asymmetric
JWT signing keys (JWKS) won't validate against that secret — for those,
verify_supabase_token falls back to asking Supabase's Auth server directly
via client.auth.get_user(token). The fallback keeps this working either
way without needing to know in advance which mode a given project is in.
"""
from typing import Any

from jose import JWTError, jwt
from supabase import AsyncClient
from supabase_auth.errors import AuthApiError

from app.core.config import settings

ALGORITHM = "HS256"
AUDIENCE = "authenticated"


def _decode_local(token: str) -> dict[str, Any]:
    return jwt.decode(
        token, settings.SUPABASE_JWT_SECRET, algorithms=[ALGORITHM], audience=AUDIENCE
    )


async def verify_supabase_token(token: str, client: AsyncClient) -> dict[str, Any]:
    """Return the token's claims (sub, email, ...), raising ValueError if invalid/expired."""
    try:
        return _decode_local(token)
    except JWTError:
        pass  # not a locally-verifiable HS256 token — fall back to asking Supabase

    try:
        response = await client.auth.get_user(token)
    except AuthApiError as exc:
        # e.g. "User from sub claim in JWT does not exist" — a still-valid
        # token for a user that's since been deleted.
        raise ValueError("Invalid or expired token") from exc

    if response is None or response.user is None:
        raise ValueError("Invalid or expired token")
    user = response.user
    return {"sub": str(user.id), "email": user.email, "phone": user.phone}
