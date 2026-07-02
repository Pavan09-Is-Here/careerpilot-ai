from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuthStatusResponse(BaseModel):
    configured: bool


class SetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: datetime


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    authenticated: bool = True
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime


class MessageResponse(BaseModel):
    message: str


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool = False
