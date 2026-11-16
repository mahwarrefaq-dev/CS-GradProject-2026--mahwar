"""Audit service (CMP-02, NFR-02, SEC-07): records create/update/delete, logins,
role changes and denied access in audit_log."""
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import AuditLog


def record(db: Session, action: str, user_id: int | None = None, entity_type: str | None = None,
           entity_id: object = None, old_value: dict | None = None, new_value: dict | None = None) -> None:
    """Adds an audit row to the current transaction (committed with the change it describes)."""
    db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type,
                    entity_id=None if entity_id is None else str(entity_id),
                    old_value=old_value, new_value=new_value))


def deny(db: Session, user_id: int | None, entity_type: str | None = None, entity_id: object = None,
         message: str = "ليست لديك صلاحية لتنفيذ هذه العملية") -> ApiError:
    """Records access_denied in its own commit and returns the 403 error to raise."""
    db.rollback()
    record(db, "access_denied", user_id, entity_type, entity_id)
    db.commit()
    return ApiError(403, "FORBIDDEN", message)
