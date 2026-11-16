"""API-01 request/response bodies."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class CurrentUser(BaseModel):
    user_id: int
    username: str
    display_alias: str
    role_code: str
    role_name_ar: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: CurrentUser
