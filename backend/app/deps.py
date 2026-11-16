"""Request dependencies: current user from the JWT and role checks (SEC-02, SEC-03)."""
from collections.abc import Callable

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.security import decode_access_token
from app.services import audit

PROJECT_MANAGER = "PROJECT_MANAGER"
TEAM_MEMBER = "TEAM_MEMBER"
SYSTEM_ADMIN = "SYSTEM_ADMIN"
PLANNER = "PLANNER"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise ApiError(401, "NOT_AUTHENTICATED", "يجب تسجيل الدخول أولًا")
    try:
        payload = decode_access_token(header.removeprefix("Bearer ").strip())
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise ApiError(401, "INVALID_TOKEN", "انتهت الجلسة أو رمز الدخول غير صالح؛ سجّل الدخول مجددًا")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "INVALID_TOKEN", "انتهت الجلسة أو رمز الدخول غير صالح؛ سجّل الدخول مجددًا")
    return user


def require_roles(*role_codes: str) -> Callable[..., User]:
    """The role is read from the database on every request, not trusted from the token."""

    def checker(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if user.role.role_code not in role_codes:
            raise audit.deny(db, user.user_id, "endpoint", f"{request.method} {request.url.path}"[:40])
        return user

    return checker
