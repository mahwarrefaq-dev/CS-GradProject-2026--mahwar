"""TBL-12 resources, TBL-13 resource_snapshots, TBL-14 task_allocations (FR-05, NFR-01)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.project import Task
from app.models.user import User


class Resource(Base):
    __tablename__ = "resources"

    resource_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    resource_code: Mapped[str] = mapped_column(String(20), unique=True)
    resource_type: Mapped[str] = mapped_column(String(20))
    linked_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"), unique=True)
    default_capacity_hours: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    linked_user: Mapped[User | None] = relationship(lazy="joined")


class ResourceSnapshot(Base):
    """Availability of a resource on a date; one row per resource and date."""
    __tablename__ = "resource_snapshots"

    resource_snapshot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.resource_id"))
    snapshot_date: Mapped[date] = mapped_column(Date)
    capacity_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    availability_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    note: Mapped[str | None] = mapped_column(String(255))
    recorded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    recorder: Mapped[User] = relationship(lazy="joined")


class TaskAllocation(Base):
    __tablename__ = "task_allocations"

    allocation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.task_id"))
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resources.resource_id"))
    allocated_hours: Mapped[Decimal] = mapped_column(Numeric(7, 2))

    task: Mapped[Task] = relationship(lazy="joined")
