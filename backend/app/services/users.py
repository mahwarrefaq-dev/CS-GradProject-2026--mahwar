"""User administration service (CMP-02, FR-01, API-02)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Role, User
from app.schemas.users import UserCreate, UserUpdate
from app.security import hash_password
from app.services import audit


def _role(db: Session, role_code: str) -> Role:
    role = db.scalar(select(Role).where(Role.role_code == role_code))
    if role is None:
        raise ApiError(422, "VALIDATION_ERROR", "تحقق من الحقول المظللة",
                       [{"field": "role_code", "message": "الدور غير موجود"}])
    return role


def _snapshot(user: User) -> dict:
    return {"username": user.username, "display_alias": user.display_alias,
            "role_code": user.role.role_code, "is_active": user.is_active}


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.user_id)))


def create_user(db: Session, data: UserCreate, actor: User) -> User:
    if db.scalar(select(User.user_id).where(User.username == data.username)) is not None:
        raise ApiError(409, "DUPLICATE_USERNAME", "اسم المستخدم مستخدم من قبل",
                       [{"field": "username", "message": "اسم المستخدم مستخدم من قبل"}])
    role = _role(db, data.role_code)
    user = User(username=data.username, display_alias=data.display_alias,
                password_hash=hash_password(data.password), role_id=role.role_id, is_active=True)
    user.role = role
    db.add(user)
    db.flush()
    audit.record(db, "create", actor.user_id, "users", user.user_id, new_value=_snapshot(user))
    db.commit()
    return user


def update_user(db: Session, user_id: int, data: UserUpdate, actor: User) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "NOT_FOUND", "المستخدم غير موجود")
    old = _snapshot(user)
    changes = data.model_dump(exclude_unset=True)

    if "display_alias" in changes:
        user.display_alias = changes["display_alias"]
    if "is_active" in changes:
        user.is_active = changes["is_active"]
    if "password" in changes:
        user.password_hash = hash_password(changes["password"])
        user.failed_login_count = 0
        user.locked_until = None
    role_changed = "role_code" in changes and changes["role_code"] != user.role.role_code
    if role_changed:
        role = _role(db, changes["role_code"])
        user.role_id = role.role_id
        user.role = role

    db.flush()
    new = _snapshot(user)
    if role_changed:
        audit.record(db, "role_change", actor.user_id, "users", user.user_id,
                     old_value={"role_code": old["role_code"]}, new_value={"role_code": new["role_code"]})
    other_changes = {k for k in changes if k != "role_code"}
    if other_changes:
        audit.record(db, "update", actor.user_id, "users", user.user_id,
                     old_value={k: v for k, v in old.items() if k in other_changes},
                     new_value={k: ("***" if k == "password" else new.get(k)) for k in other_changes})
    db.commit()
    return user
