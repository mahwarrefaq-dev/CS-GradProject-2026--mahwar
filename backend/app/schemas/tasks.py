"""API-04 bodies (FR-02, NFR-04)."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.projects import UserRef

Priority = Literal["high", "medium", "low"]


class TaskCreate(BaseModel):
    task_code: str = Field(min_length=1, max_length=20)
    task_name: str = Field(min_length=1, max_length=200)
    priority: Priority = "medium"
    assignee_user_id: int | None = None
    planned_start_date: date
    planned_due_date: date


class TaskUpdate(BaseModel):
    task_code: str | None = Field(default=None, min_length=1, max_length=20)
    task_name: str | None = Field(default=None, min_length=1, max_length=200)
    priority: Priority | None = None
    assignee_user_id: int | None = None
    planned_start_date: date | None = None
    planned_due_date: date | None = None


class TaskOut(BaseModel):
    task_id: int
    project_id: int
    task_code: str
    task_name: str
    priority: str
    assignee: UserRef | None
    planned_start_date: date
    planned_due_date: date
    planned_duration_days: int
    has_snapshots: bool
