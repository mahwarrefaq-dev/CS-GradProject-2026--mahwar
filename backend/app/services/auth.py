"""Authentication service (CMP-02, FR-01, SEC-01, SEC-03).

- bcrypt password check.
- Temporary lock: after `max_failed_logins` consecutive failures the account is locked for
  `lockout_minutes`; while locked every attempt is rejected with 423 (TC-03).
- login_success / login_failed are recorded in audit_log.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import ApiError
from app.models import User
from app.security import create_access_token, verify_password
from app.services import audit

INVALID_CREDENTIALS = "اسم المستخدم أو كلمة المرور غير صحيحة"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def login(db: Session, username: str, password: str) -> tuple[str, User]:
    user = db.scalar(select(User).where(User.username == username))

    if user is None:
        audit.record(db, "login_failed", None, "users", None, new_value={"username": username})
        db.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", INVALID_CREDENTIALS)

    if user.locked_until is not None and user.locked_until > _now():
        audit.record(db, "login_failed", user.user_id, "users", user.user_id, new_value={"reason": "locked"})
        db.commit()
        minutes = max(1, int((user.locked_until - _now()).total_seconds() // 60) + 1)
        raise ApiError(423, "ACCOUNT_LOCKED",
                       f"الحساب مقفل مؤقتًا بسبب محاولات دخول فاشلة متكررة؛ أعد المحاولة بعد {minutes} دقيقة")

    if not user.is_active or not verify_password(password, user.password_hash):
        reason = "inactive" if not user.is_active else "wrong_password"
        if user.is_active:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.max_failed_logins:
                user.locked_until = _now() + timedelta(minutes=settings.lockout_minutes)
                user.failed_login_count = 0
                reason = "locked_now"
        audit.record(db, "login_failed", user.user_id, "users", user.user_id, new_value={"reason": reason})
        db.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", INVALID_CREDENTIALS)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = _now()
    audit.record(db, "login_success", user.user_id, "users", user.user_id)
    db.commit()
    return create_access_token(user.user_id, user.role.role_code), user
