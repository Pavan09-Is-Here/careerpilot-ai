from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthStatusResponse(BaseModel):
    # Whether at least one account exists. Registration is always open.
    configured: bool
    registration_open: bool = True


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=255)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: datetime
    username: str


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    authenticated: bool = True
    username: str
    email: str | None = None
    email_verified: bool = False
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, max_length=200)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class MessageResponse(BaseModel):
    message: str


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool = False
