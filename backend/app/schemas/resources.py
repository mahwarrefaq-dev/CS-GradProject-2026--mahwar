"""API-08 bodies (FR-05, NFR-01): resource, availability on a date, allocation to a task."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.projects import UserRef

ResourceType = Literal["human", "equipment", "facility", "other"]


class ResourceCreate(BaseModel):
    resource_code: str = Field(min_length=1, max_length=20)
    resource_type: ResourceType
    linked_username: str | None = Field(default=None, max_length=50)  # pseudonymous username, never a real name
    default_capacity_hours: Decimal = Field(max_digits=7, decimal_places=2)


class ResourceUpdate(BaseModel):
    resource_type: ResourceType | None = None
    linked_username: str | None = Field(default=None, max_length=50)
    default_capacity_hours: Decimal | None = Field(default=None, max_digits=7, decimal_places=2)
    is_active: bool | None = None


class AvailabilityCreate(BaseModel):
    snapshot_date: date
    availability_pct: Decimal = Field(max_digits=6, decimal_places=2)
    capacity_hours: Decimal | None = Field(default=None, max_digits=8, decimal_places=2)
    note: str | None = Field(default=None, max_length=255)


class AvailabilityOut(BaseModel):
    resource_snapshot_id: int
    snapshot_date: date
    capacity_hours: float
    availability_pct: float
    note: str | None
    recorded_by: UserRef
    recorded_at: datetime


class ResourceOut(BaseModel):
    resource_id: int
    resource_code: str
    resource_type: str
    linked_user: UserRef | None
    default_capacity_hours: float
    is_active: bool
    latest_availability: AvailabilityOut | None


class AllocationCreate(BaseModel):
    task_id: int
    allocated_hours: Decimal = Field(max_digits=9, decimal_places=2)


class AllocationOut(BaseModel):
    allocation_id: int
    resource_id: int
    resource_code: str
    task_id: int
    task_code: str
    project_id: int
    allocated_hours: float
