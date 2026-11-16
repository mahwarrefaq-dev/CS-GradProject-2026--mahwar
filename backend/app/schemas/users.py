"""API-02 request/response bodies (FR-01, NFR-01: pseudonymous display alias only)."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RoleCode = Literal["PROJECT_MANAGER", "TEAM_MEMBER", "SYSTEM_ADMIN", "PLANNER"]
USERNAME_PATTERN = r"^[a-z0-9._-]{3,50}$"   # same rule as the CHECK on users.username


class UserCreate(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN, max_length=50)
    display_alias: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=8, max_length=128)
    role_code: RoleCode


class UserUpdate(BaseModel):
    display_alias: str | None = Field(default=None, min_length=1, max_length=60)
    role_code: RoleCode | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(BaseModel):
    user_id: int
    username: str
    display_alias: str
    role_code: str
    is_active: bool
    locked_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime

    @classmethod
    def of(cls, user) -> "UserOut":
        return cls(user_id=user.user_id, username=user.username, display_alias=user.display_alias,
                   role_code=user.role.role_code, is_active=user.is_active, locked_until=user.locked_until,
                   last_login_at=user.last_login_at, created_at=user.created_at)
