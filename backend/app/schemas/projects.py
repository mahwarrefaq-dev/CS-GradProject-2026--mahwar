"""API-03 and API-05 bodies (FR-02, NFR-01)."""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ProjectStatus = Literal["planned", "active", "on_hold", "closed"]
DataMode = Literal["synthetic", "real"]


class ProjectCreate(BaseModel):
    project_code: str = Field(min_length=1, max_length=20)
    project_name: str = Field(min_length=1, max_length=150)
    project_type: str | None = Field(default=None, max_length=50)
    planned_start_date: date
    planned_end_date: date
    team_size: int | None = Field(default=None, gt=0, le=32767)
    status: ProjectStatus = "planned"
    data_mode: DataMode = "synthetic"
    consent_ref: str | None = Field(default=None, max_length=255)
    consent_date: date | None = None
    # Design-review change: API-03 also carries the project members (no separate endpoint exists).
    member_ids: list[int] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=150)
    project_type: str | None = Field(default=None, max_length=50)
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    team_size: int | None = Field(default=None, gt=0, le=32767)
    status: ProjectStatus | None = None
    data_mode: DataMode | None = None
    consent_ref: str | None = Field(default=None, max_length=255)
    consent_date: date | None = None
    member_ids: list[int] | None = None


class UserRef(BaseModel):
    user_id: int
    username: str
    display_alias: str


class BaselineRef(BaseModel):
    baseline_id: int
    version_no: int
    created_at: datetime
    note: str | None


class ProjectOut(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    project_type: str | None
    planned_start_date: date
    planned_end_date: date
    team_size: int | None
    status: str
    data_mode: str
    consent_ref: str | None
    consent_date: date | None
    manager: UserRef
    members: list[UserRef]
    task_count: int
    current_baseline: BaselineRef | None
    can_edit: bool


class BaselineCreate(BaseModel):
    note: str | None = Field(default=None, max_length=255)


class BaselineOut(BaseModel):
    baseline_id: int
    version_no: int
    task_count: int
    created_at: datetime
    note: str | None
