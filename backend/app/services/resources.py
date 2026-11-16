"""Resources, availability and allocation – part of CMP-03 (plan management), FR-05, NFR-01.

Access (API-08: project manager, planner):
- resources and their availability: users with role PROJECT_MANAGER or PLANNER;
- allocation of a resource to a task: the manager of the task's project, or a PLANNER who is a member of it.
A resource is linked to a user only through the pseudonymous username (NFR-01).
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Task, User
from app.models.resource import Resource, ResourceSnapshot, TaskAllocation
from app.schemas.projects import UserRef
from app.schemas.resources import (AllocationCreate, AllocationOut, AvailabilityCreate, AvailabilityOut,
                                   ResourceCreate, ResourceOut, ResourceUpdate)
from app.services import audit, plan

CAPACITY_RANGE = "السعة اليومية يجب أن تكون أكبر من 0 ولا تزيد على 24 ساعة"
AVAILABILITY_RANGE = "نسبة التوفر يجب أن تكون بين 0 و100"


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", plan.VALIDATION_MESSAGE, [{"field": field, "message": message}])


def _user_ref(u: User | None) -> UserRef | None:
    return None if u is None else UserRef(user_id=u.user_id, username=u.username, display_alias=u.display_alias)


def availability_out(s: ResourceSnapshot) -> AvailabilityOut:
    return AvailabilityOut(resource_snapshot_id=s.resource_snapshot_id, snapshot_date=s.snapshot_date,
                           capacity_hours=float(s.capacity_hours), availability_pct=float(s.availability_pct),
                           note=s.note, recorded_by=_user_ref(s.recorder), recorded_at=s.recorded_at)


def latest_availability(db: Session, resource_id: int, on_date: date) -> ResourceSnapshot | None:
    """Last recorded availability on or before a date (same rule as Queries.sql Q4)."""
    return db.scalar(select(ResourceSnapshot).where(ResourceSnapshot.resource_id == resource_id,
                                                    ResourceSnapshot.snapshot_date <= on_date)
                     .order_by(ResourceSnapshot.snapshot_date.desc()).limit(1))


def resource_out(db: Session, r: Resource) -> ResourceOut:
    latest = latest_availability(db, r.resource_id, date.today())
    return ResourceOut(resource_id=r.resource_id, resource_code=r.resource_code, resource_type=r.resource_type,
                       linked_user=_user_ref(r.linked_user), default_capacity_hours=float(r.default_capacity_hours),
                       is_active=r.is_active, latest_availability=None if latest is None else availability_out(latest))


def _snapshot(r: Resource) -> dict:
    return {"resource_code": r.resource_code, "resource_type": r.resource_type,
            "linked_username": r.linked_user.username if r.linked_user else None,
            "default_capacity_hours": float(r.default_capacity_hours), "is_active": r.is_active}


def get_resource(db: Session, resource_id: int) -> Resource:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise ApiError(404, "NOT_FOUND", "المورد غير موجود")
    return resource


def _check_capacity(value: Decimal) -> None:
    if not (Decimal(0) < value <= Decimal(24)):
        raise _invalid("default_capacity_hours", CAPACITY_RANGE)


def _linked_user(db: Session, username: str | None, resource_id: int | None = None) -> User | None:
    if username is None or not username.strip():
        return None
    user = db.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None:
        raise _invalid("linked_username", "اسم المستخدم غير موجود")
    taken = db.scalar(select(Resource.resource_id).where(Resource.linked_user_id == user.user_id))
    if taken is not None and taken != resource_id:
        raise ApiError(409, "USER_ALREADY_LINKED", "هذا المستخدم مرتبط بمورد آخر",
                       [{"field": "linked_username", "message": "هذا المستخدم مرتبط بمورد آخر"}])
    return user


# --- resources ---------------------------------------------------------------

def list_resources(db: Session) -> list[ResourceOut]:
    return [resource_out(db, r) for r in db.scalars(select(Resource).order_by(Resource.resource_code))]


def create_resource(db: Session, data: ResourceCreate, actor: User) -> ResourceOut:
    _check_capacity(data.default_capacity_hours)
    if db.scalar(select(Resource.resource_id).where(Resource.resource_code == data.resource_code)) is not None:
        raise ApiError(409, "DUPLICATE_RESOURCE_CODE", "رمز المورد مستخدم من قبل",
                       [{"field": "resource_code", "message": "رمز المورد مستخدم من قبل"}])
    linked = _linked_user(db, data.linked_username)
    resource = Resource(resource_code=data.resource_code, resource_type=data.resource_type,
                        linked_user_id=None if linked is None else linked.user_id,
                        default_capacity_hours=data.default_capacity_hours, is_active=True)
    resource.linked_user = linked
    db.add(resource)
    db.flush()
    audit.record(db, "create", actor.user_id, "resources", resource.resource_id, new_value=_snapshot(resource))
    db.commit()
    return resource_out(db, resource)


def update_resource(db: Session, resource_id: int, data: ResourceUpdate, actor: User) -> ResourceOut:
    resource = get_resource(db, resource_id)
    changes = data.model_dump(exclude_unset=True)
    old = _snapshot(resource)
    if "default_capacity_hours" in changes:
        _check_capacity(changes["default_capacity_hours"])
        resource.default_capacity_hours = changes["default_capacity_hours"]
    if "linked_username" in changes:
        linked = _linked_user(db, changes["linked_username"], resource.resource_id)
        resource.linked_user_id = None if linked is None else linked.user_id
        resource.linked_user = linked
    for key in ("resource_type", "is_active"):
        if key in changes and changes[key] is not None:
            setattr(resource, key, changes[key])
    db.flush()
    new = _snapshot(resource)
    changed = {k for k in new if new[k] != old[k]}
    if changed:
        audit.record(db, "update", actor.user_id, "resources", resource.resource_id,
                     old_value={k: old[k] for k in changed}, new_value={k: new[k] for k in changed})
    db.commit()
    return resource_out(db, resource)


# --- availability on a date (TC-09) ------------------------------------------

def list_availability(db: Session, resource_id: int) -> list[AvailabilityOut]:
    get_resource(db, resource_id)
    rows = db.scalars(select(ResourceSnapshot).where(ResourceSnapshot.resource_id == resource_id)
                      .order_by(ResourceSnapshot.snapshot_date.desc()))
    return [availability_out(s) for s in rows]


def create_availability(db: Session, resource_id: int, data: AvailabilityCreate, actor: User) -> AvailabilityOut:
    resource = get_resource(db, resource_id)
    if not (Decimal(0) <= data.availability_pct <= Decimal(100)):
        raise _invalid("availability_pct", AVAILABILITY_RANGE)
    if data.capacity_hours is not None and data.capacity_hours < 0:
        raise _invalid("capacity_hours", "ساعات السعة لا يمكن أن تكون سالبة")
    capacity = data.capacity_hours
    if capacity is None:  # default: daily capacity x availability, e.g. 8 h x 60% = 4.8 h
        capacity = (resource.default_capacity_hours * data.availability_pct / Decimal(100)).quantize(Decimal("0.01"))
    snapshot = ResourceSnapshot(resource_id=resource.resource_id, snapshot_date=data.snapshot_date,
                                capacity_hours=capacity, availability_pct=data.availability_pct, note=data.note,
                                recorded_by=actor.user_id)
    db.add(snapshot)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "DUPLICATE_AVAILABILITY_DATE", "سُجّل توفر هذا المورد في هذا التاريخ من قبل",
                       [{"field": "snapshot_date", "message": "سُجّل توفر هذا المورد في هذا التاريخ من قبل"}])
    audit.record(db, "create", actor.user_id, "resource_snapshots", snapshot.resource_snapshot_id,
                 new_value={"resource_code": resource.resource_code, "snapshot_date": data.snapshot_date.isoformat(),
                            "availability_pct": float(data.availability_pct), "capacity_hours": float(capacity)})
    db.commit()
    db.refresh(snapshot)
    return availability_out(snapshot)


# --- allocation to a task ----------------------------------------------------

def allocation_out(a: TaskAllocation, resource_code: str) -> AllocationOut:
    return AllocationOut(allocation_id=a.allocation_id, resource_id=a.resource_id, resource_code=resource_code,
                         task_id=a.task_id, task_code=a.task.task_code, project_id=a.task.project_id,
                         allocated_hours=float(a.allocated_hours))


def _ensure_allocation_editor(db: Session, task: Task, user: User) -> None:
    project = plan.get_project(db, task.project_id)
    planner_member = user.role.role_code == "PLANNER" and plan.is_member(project, user)
    if user.user_id != project.manager_user_id and not planner_member:
        raise audit.deny(db, user.user_id, "projects", project.project_id,
                         "ليست لديك صلاحية لتخصيص الموارد لمهام هذا المشروع")


def list_allocations(db: Session, resource_id: int) -> list[AllocationOut]:
    resource = get_resource(db, resource_id)
    rows = db.scalars(select(TaskAllocation).where(TaskAllocation.resource_id == resource_id)
                      .order_by(TaskAllocation.allocation_id))
    return [allocation_out(a, resource.resource_code) for a in rows]


def create_allocation(db: Session, resource_id: int, data: AllocationCreate, actor: User) -> AllocationOut:
    resource = get_resource(db, resource_id)
    task = db.get(Task, data.task_id)
    if task is None:
        raise _invalid("task_id", "المهمة غير موجودة")
    _ensure_allocation_editor(db, task, actor)
    if not resource.is_active:
        raise _invalid("resource_id", "لا يمكن تخصيص مورد غير نشط")
    if data.allocated_hours <= 0:
        raise _invalid("allocated_hours", "الساعات المخصصة يجب أن تكون أكبر من 0")
    exists = db.scalar(select(TaskAllocation.allocation_id).where(TaskAllocation.task_id == task.task_id,
                                                                  TaskAllocation.resource_id == resource_id))
    if exists is not None:
        raise ApiError(409, "DUPLICATE_ALLOCATION", "هذا المورد مخصص لهذه المهمة من قبل")
    allocation = TaskAllocation(task_id=task.task_id, resource_id=resource_id, allocated_hours=data.allocated_hours)
    db.add(allocation)
    db.flush()
    audit.record(db, "create", actor.user_id, "task_allocations", allocation.allocation_id,
                 new_value={"resource_code": resource.resource_code, "task_code": task.task_code,
                            "allocated_hours": float(data.allocated_hours)})
    db.commit()
    db.refresh(allocation)
    return allocation_out(allocation, resource.resource_code)


def delete_allocation(db: Session, resource_id: int, allocation_id: int, actor: User) -> None:
    resource = get_resource(db, resource_id)
    allocation = db.get(TaskAllocation, allocation_id)
    if allocation is None or allocation.resource_id != resource_id:
        raise ApiError(404, "NOT_FOUND", "التخصيص غير موجود لهذا المورد")
    _ensure_allocation_editor(db, allocation.task, actor)
    old = {"resource_code": resource.resource_code, "task_code": allocation.task.task_code,
           "allocated_hours": float(allocation.allocated_hours)}
    db.delete(allocation)
    audit.record(db, "delete", actor.user_id, "task_allocations", allocation_id, old_value=old)
    db.commit()
