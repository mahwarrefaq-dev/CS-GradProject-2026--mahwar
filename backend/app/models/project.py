"""TBL-03 projects, TBL-04 project_members, TBL-05 baselines, TBL-06 tasks,
TBL-07 baseline_tasks, TBL-08 task_snapshots (read-only here) – FR-02, NFR-01."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (BigInteger, Column, Computed, Date, DateTime, ForeignKey, Integer, Numeric,
                        SmallInteger, String, Table, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import User

project_members = Table(
    "project_members", Base.metadata,
    Column("project_id", BigInteger, ForeignKey("projects.project_id"), primary_key=True),
    Column("user_id", BigInteger, ForeignKey("users.user_id"), primary_key=True),
    Column("joined_at", Date, server_default=func.current_date()),
)


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_code: Mapped[str] = mapped_column(String(20), unique=True)
    project_name: Mapped[str] = mapped_column(String(150))
    project_type: Mapped[str | None] = mapped_column(String(50))
    manager_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    planned_start_date: Mapped[date] = mapped_column(Date)
    planned_end_date: Mapped[date] = mapped_column(Date)
    team_size: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    data_mode: Mapped[str] = mapped_column(String(10), default="synthetic")
    consent_ref: Mapped[str | None] = mapped_column(String(255))
    consent_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    manager: Mapped[User] = relationship(lazy="joined")
    members: Mapped[list[User]] = relationship(secondary=project_members, lazy="selectin",
                                               order_by=User.user_id)


class Baseline(Base):
    __tablename__ = "baselines"

    baseline_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.project_id"))
    version_no: Mapped[int] = mapped_column(SmallInteger)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(String(255))


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.project_id"))
    task_code: Mapped[str] = mapped_column(String(20))
    task_name: Mapped[str] = mapped_column(String(200))
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    assignee_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    planned_start_date: Mapped[date] = mapped_column(Date)
    planned_due_date: Mapped[date] = mapped_column(Date)
    planned_duration_days: Mapped[int] = mapped_column(
        Integer, Computed("planned_due_date - planned_start_date + 1", persisted=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assignee: Mapped[User | None] = relationship(lazy="joined")


class BaselineTask(Base):
    __tablename__ = "baseline_tasks"

    baseline_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("baselines.baseline_id"), primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.task_id"), primary_key=True)
    planned_start_date: Mapped[date] = mapped_column(Date)
    planned_due_date: Mapped[date] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(String(10))


class Dependency(Base):
    """TBL-11 dependencies (FR-04, FR-08): finish-to-start only, lag in calendar days."""
    __tablename__ = "dependencies"

    dependency_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    predecessor_task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.task_id"))
    successor_task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.task_id"))
    dependency_type: Mapped[str] = mapped_column(String(2), default="FS")
    lag_days: Mapped[int] = mapped_column(SmallInteger, default=0)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    predecessor: Mapped[Task] = relationship(foreign_keys=[predecessor_task_id], lazy="joined")
    successor: Mapped[Task] = relationship(foreign_keys=[successor_task_id], lazy="joined")


class TaskSnapshot(Base):
    """Dated progress snapshot. Append-only (ARC-03, SEC-08): the API never updates or deletes it."""
    __tablename__ = "task_snapshots"

    snapshot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("tasks.task_id"))
    baseline_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("baselines.baseline_id"))
    snapshot_date: Mapped[date] = mapped_column(Date)
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    update_source: Mapped[str] = mapped_column(String(20))
    progress_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    status_at_snapshot: Mapped[str] = mapped_column(String(20))
    remaining_estimate_days: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    blocker_note: Mapped[str | None] = mapped_column(String(500))
    recorded_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"))

    baseline: Mapped[Baseline] = relationship(lazy="joined")
    recorder: Mapped[User] = relationship(lazy="joined")
