"""API-02 /api/users – GET, POST, PATCH (FR-01); system administrator only."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import SYSTEM_ADMIN, require_roles
from app.models import User
from app.schemas.users import UserCreate, UserOut, UserUpdate
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["API-02 users"])
admin_only = require_roles(SYSTEM_ADMIN)


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)) -> list[UserOut]:
    return [UserOut.of(u) for u in user_service.list_users(db)]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, db: Session = Depends(get_db), actor: User = Depends(admin_only)) -> UserOut:
    return UserOut.of(user_service.create_user(db, body, actor))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(admin_only)) -> UserOut:
    return UserOut.of(user_service.update_user(db, user_id, body, actor))
