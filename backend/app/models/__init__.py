"""SQLAlchemy models of TBL-01..TBL-20 (CMP-07).

The tables are created by database/Schema_Script.sql (source of truth); the models only map them.
Models are added release by release.
"""
from app.models.audit import AuditLog
from app.models.user import Role, User

__all__ = ["AuditLog", "Role", "User"]
