"""API-06 bodies (FR-03, NFR-04) and the "my tasks" list (SCR-05)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.projects import UserRef

SnapshotStatus = Literal["not_started", "in_progress", "blocked", "completed", "cancelled"]


class SnapshotCreate(BaseModel):
    # Ranges are checked in services/progress.py so the messages match the design (Security_Design, Errors).
    snapshot_date: date
    progress_pct: Decimal = Field(max_digits=6, decimal_places=2)
    status_at_snapshot: SnapshotStatus
    remaining_estimate_days: Decimal | None = Field(default=None, max_digits=6, decimal_places=1)
    blocker_note: str | None = Field(default=None, max_length=500)


class SnapshotOut(BaseModel):
    snapshot_id: int
    task_id: int
    baseline_version: int
    snapshot_date: date
    snapshot_timestamp: datetime
    update_source: str
    progress_pct: float
    status_at_snapshot: str
    remaining_estimate_days: float | None
    blocker_note: str | None
    recorded_by: UserRef


class ProjectRef(BaseModel):
    project_id: int
    project_code: str
    project_name: str


class MyTaskOut(BaseModel):
    task_id: int
    task_code: str
    task_name: str
    priority: str
    planned_start_date: date
    planned_due_date: date
    planned_duration_days: int
    project: ProjectRef
    latest_snapshot: SnapshotOut | None
