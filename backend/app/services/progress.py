"""Progress service (CMP-04): dated task snapshots – FR-03, NFR-04, ARC-03, SEC-08.

- A snapshot is only ever added; there is no update or delete (ARC-03, SEC-08).
- POST: the task's assignee or the project manager (SEQ-01); others get 403 + access_denied.
  Status `cancelled` is accepted from the project manager only (403 + access_denied otherwise).
- GET: any reader of the project (manager or member).
- Each snapshot points to the project's current (latest) baseline; without one -> 409.
- "Latest" = most recent snapshot_timestamp, as in Queries.sql Q1 and v_latest_task_snapshot.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Baseline, Project, Task, TaskSnapshot, User
from app.schemas.projects import UserRef
from app.schemas.snapshots import MyTaskOut, ProjectRef, SnapshotCreate, SnapshotOut
from app.services import audit, plan

PCT_RANGE = "نسبة الإنجاز يجب أن تكون بين 0 و100"
COMPLETED_NEEDS_100 = "الحالة «مكتملة» تتطلب نسبة إنجاز 100"
FUTURE_DATE = "تاريخ اللقطة لا يمكن أن يكون بعد تاريخ اليوم"
NEGATIVE_REMAINING = "المتبقي بالأيام لا يمكن أن يكون سالبًا"


def snapshot_out(s: TaskSnapshot) -> SnapshotOut:
    return SnapshotOut(
        snapshot_id=s.snapshot_id, task_id=s.task_id, baseline_version=s.baseline.version_no,
        snapshot_date=s.snapshot_date, snapshot_timestamp=s.snapshot_timestamp, update_source=s.update_source,
        progress_pct=float(s.progress_pct), status_at_snapshot=s.status_at_snapshot,
        remaining_estimate_days=None if s.remaining_estimate_days is None else float(s.remaining_estimate_days),
        blocker_note=s.blocker_note,
        recorded_by=UserRef(user_id=s.recorder.user_id, username=s.recorder.username,
                            display_alias=s.recorder.display_alias),
    )


def _task_and_project(db: Session, task_id: int) -> tuple[Task, Project]:
    task = db.get(Task, task_id)
    if task is None:
        raise ApiError(404, "NOT_FOUND", "المهمة غير موجودة")
    return task, plan.get_project(db, task.project_id)


def list_snapshots(db: Session, task_id: int, user: User) -> list[SnapshotOut]:
    task, project = _task_and_project(db, task_id)
    plan.ensure_read(db, project, user)
    rows = db.scalars(select(TaskSnapshot).where(TaskSnapshot.task_id == task.task_id)
                      .order_by(TaskSnapshot.snapshot_timestamp.desc(), TaskSnapshot.snapshot_id.desc()))
    return [snapshot_out(s) for s in rows]


def _validate(data: SnapshotCreate) -> None:
    fields = []
    if not (Decimal(0) <= data.progress_pct <= Decimal(100)):
        fields.append({"field": "progress_pct", "message": PCT_RANGE})
    elif data.status_at_snapshot == "completed" and data.progress_pct != Decimal(100):
        fields.append({"field": "progress_pct", "message": COMPLETED_NEEDS_100})
    if data.snapshot_date > date.today():
        fields.append({"field": "snapshot_date", "message": FUTURE_DATE})
    if data.remaining_estimate_days is not None and data.remaining_estimate_days < 0:
        fields.append({"field": "remaining_estimate_days", "message": NEGATIVE_REMAINING})
    if fields:
        raise ApiError(422, "VALIDATION_ERROR", plan.VALIDATION_MESSAGE, fields)


def create_snapshot(db: Session, task_id: int, data: SnapshotCreate, actor: User) -> SnapshotOut:
    task, project = _task_and_project(db, task_id)
    if actor.user_id not in (task.assignee_user_id, project.manager_user_id):
        raise audit.deny(db, actor.user_id, "tasks", task.task_id,
                         "ليست لديك صلاحية لتسجيل تقدم هذه المهمة؛ التسجيل للمسند إليه أو مدير المشروع")
    if data.status_at_snapshot == "cancelled" and actor.user_id != project.manager_user_id:
        # Supervisor review 2026-11-17 (API-06, SEQ-01): only the project manager cancels a task.
        raise audit.deny(db, actor.user_id, "tasks", task.task_id,
                         "إلغاء المهمة (الحالة «ملغاة») يسجله مدير المشروع فقط")
    _validate(data)
    baseline = db.scalar(select(Baseline).where(Baseline.project_id == project.project_id)
                         .order_by(Baseline.version_no.desc()).limit(1))
    if baseline is None:
        raise ApiError(409, "NO_BASELINE", "احفظ خط الأساس أولًا قبل تسجيل التقدم")

    snapshot = TaskSnapshot(task_id=task.task_id, baseline_id=baseline.baseline_id, update_source="manual",
                            recorded_by=actor.user_id, **data.model_dump())
    db.add(snapshot)
    db.flush()
    audit.record(db, "create", actor.user_id, "task_snapshots", snapshot.snapshot_id,
                 new_value={"task_id": task.task_id, "snapshot_date": data.snapshot_date.isoformat(),
                            "progress_pct": float(data.progress_pct), "status": data.status_at_snapshot,
                            "baseline_version": baseline.version_no})
    db.commit()
    db.refresh(snapshot)
    return snapshot_out(snapshot)


def my_tasks(db: Session, user: User) -> list[MyTaskOut]:
    """Tasks assigned to the current user in all projects, with their latest snapshot (SCR-05)."""
    tasks = list(db.scalars(select(Task).where(Task.assignee_user_id == user.user_id)
                            .order_by(Task.planned_due_date, Task.task_code)))
    if not tasks:
        return []
    latest: dict[int, TaskSnapshot] = {}
    rows = db.scalars(select(TaskSnapshot).where(TaskSnapshot.task_id.in_([t.task_id for t in tasks]))
                      .ext(distinct_on(TaskSnapshot.task_id))
                      .order_by(TaskSnapshot.task_id, TaskSnapshot.snapshot_timestamp.desc(),
                                TaskSnapshot.snapshot_id.desc()))
    for s in rows:
        latest[s.task_id] = s
    projects = {p.project_id: p for p in db.scalars(
        select(Project).where(Project.project_id.in_({t.project_id for t in tasks})))}
    return [
        MyTaskOut(
            task_id=t.task_id, task_code=t.task_code, task_name=t.task_name, priority=t.priority,
            planned_start_date=t.planned_start_date, planned_due_date=t.planned_due_date,
            planned_duration_days=t.planned_duration_days,
            project=ProjectRef(project_id=t.project_id, project_code=projects[t.project_id].project_code,
                               project_name=projects[t.project_id].project_name),
            latest_snapshot=snapshot_out(latest[t.task_id]) if t.task_id in latest else None,
        )
        for t in tasks
    ]
