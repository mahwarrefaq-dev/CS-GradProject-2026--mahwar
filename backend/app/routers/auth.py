"""API-01 POST /api/auth/login (FR-01)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import CurrentUser, LoginRequest, LoginResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["API-01 auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    token, user = auth_service.login(db, body.username, body.password)
    return LoginResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_expire_minutes,
        user=CurrentUser(user_id=user.user_id, username=user.username, display_alias=user.display_alias,
                         role_code=user.role.role_code, role_name_ar=user.role.role_name_ar),
    )
