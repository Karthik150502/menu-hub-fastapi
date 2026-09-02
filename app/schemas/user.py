import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    # Optional because a phone-only account (see PhoneOtpRequest/
    # PhoneVerifyRequest below) has no email — email/password and phone/OTP
    # are separate, equally valid signup paths onto the same profiles table.
    email: EmailStr | None = None
    phone: str | None = None
    full_name: str | None = None
    avatar_url: str | None = None


class UserCreate(UserBase):
    email: EmailStr  # required here — this schema is specifically the email/password signup
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    email_confirmed: bool
    created_at: datetime
    updated_at: datetime


# ── Auth schemas ───────────────────────────────────────────────────────────────

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Phone (OTP) auth schemas ─────────────────────────────────────────────────

# E.164: leading '+', country code (no leading 0), then the subscriber
# number — no spaces/dashes. Validated here so a malformed number fails
# fast with a clean 422 instead of a confusing error from Supabase.
_E164_PATTERN = r"^\+[1-9]\d{7,14}$"


class PhoneOtpRequest(BaseModel):
    phone: str = Field(pattern=_E164_PATTERN)


class PhoneVerifyRequest(BaseModel):
    phone: str = Field(pattern=_E164_PATTERN)
    token: str = Field(min_length=4, max_length=10)
