"""API-07 bodies (FR-04): finish-to-start dependencies only."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DependencyCreate(BaseModel):
    predecessor_task_id: int
    successor_task_id: int
    dependency_type: Literal["FS"] = "FS"
    lag_days: int = Field(default=0, ge=-32768, le=32767)  # SMALLINT range; the design sets no other limit


class TaskRef(BaseModel):
    task_id: int
    task_code: str
    task_name: str


class DependencyOut(BaseModel):
    dependency_id: int
    predecessor: TaskRef
    successor: TaskRef
    dependency_type: str
    lag_days: int
    created_at: datetime
