"""Plan service (CMP-03): projects, tasks and baselines – FR-02, NFR-01, NFR-02, NFR-04.

Access (SEC-02), checked on every request:
- read: the project manager or a project member;
- write: the project manager only.
Denied access is recorded as access_denied (SEC-07).
"""
from datetime import date

from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Baseline, BaselineTask, Project, Task, TaskSnapshot, User, project_members
from app.schemas.projects import (BaselineCreate, BaselineOut, BaselineRef, ProjectCreate, ProjectOut,
                                  ProjectUpdate, UserRef)
from app.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.services import audit

VALIDATION_MESSAGE = "تحقق من الحقول المظللة"
DUE_BEFORE_START = "تاريخ الاستحقاق يجب ألا يسبق تاريخ البدء"
END_BEFORE_START = "تاريخ الانتهاء المخطط يجب ألا يسبق تاريخ البدء المخطط"
CONSENT_REQUIRED = "سجّل مرجع موافقة مالك البيانات وتاريخها قبل اعتماد البيانات الفعلية"


def _invalid(fields: list[dict]) -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", VALIDATION_MESSAGE, fields)


def _json(values: dict) -> dict:
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in values.items()}


def _user_ref(user: User) -> UserRef:
    return UserRef(user_id=user.user_id, username=user.username, display_alias=user.display_alias)


# --- access ------------------------------------------------------------------

def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise ApiError(404, "NOT_FOUND", "المشروع غير موجود")
    return project


def is_member(project: Project, user: User) -> bool:
    return user.user_id == project.manager_user_id or any(m.user_id == user.user_id for m in project.members)


def ensure_read(db: Session, project: Project, user: User) -> None:
    if not is_member(project, user):
        raise audit.deny(db, user.user_id, "projects", project.project_id,
                         "ليست لديك صلاحية لعرض هذا المشروع")


def ensure_write(db: Session, project: Project, user: User) -> None:
    if user.user_id != project.manager_user_id:
        raise audit.deny(db, user.user_id, "projects", project.project_id,
                         "ليست لديك صلاحية لتعديل خطة هذا المشروع")


# --- projects (API-03) -------------------------------------------------------

def _project_snapshot(p: Project) -> dict:
    return _json({"project_code": p.project_code, "project_name": p.project_name, "project_type": p.project_type,
                  "planned_start_date": p.planned_start_date, "planned_end_date": p.planned_end_date,
                  "team_size": p.team_size, "status": p.status, "data_mode": p.data_mode,
                  "consent_ref": p.consent_ref, "consent_date": p.consent_date,
                  "members": sorted(m.username for m in p.members)})


def _check_project_rules(start: date, end: date, data_mode: str, consent_ref: str | None,
                         consent_date: date | None) -> None:
    fields = []
    if end < start:
        fields.append({"field": "planned_end_date", "message": END_BEFORE_START})
    if data_mode == "real":  # NFR-01, TC-24
        if not consent_ref:
            fields.append({"field": "consent_ref", "message": CONSENT_REQUIRED})
        if consent_date is None:
            fields.append({"field": "consent_date", "message": CONSENT_REQUIRED})
    if fields:
        raise _invalid(fields)


def _resolve_members(db: Session, member_usernames: list[str], manager: User) -> list[User]:
    names = {n.strip().lower() for n in member_usernames if n and n.strip()} | {manager.username}
    users = list(db.scalars(select(User).where(User.username.in_(names))))
    missing = names - {u.username for u in users}
    inactive = {u.username for u in users if not u.is_active}
    if missing or inactive:
        bad = "، ".join(sorted(missing | inactive))
        raise _invalid([{"field": "member_usernames",
                         "message": f"أسماء مستخدمين غير موجودة أو غير نشطة: {bad}"}])
    return sorted(users, key=lambda u: u.user_id)


def project_out(db: Session, project: Project, user: User) -> ProjectOut:
    task_count = db.scalar(select(func.count()).select_from(Task).where(Task.project_id == project.project_id))
    baseline = db.scalar(select(Baseline).where(Baseline.project_id == project.project_id)
                         .order_by(Baseline.version_no.desc()).limit(1))
    return ProjectOut(
        project_id=project.project_id, project_code=project.project_code, project_name=project.project_name,
        project_type=project.project_type, planned_start_date=project.planned_start_date,
        planned_end_date=project.planned_end_date, team_size=project.team_size, status=project.status,
        data_mode=project.data_mode, consent_ref=project.consent_ref, consent_date=project.consent_date,
        manager=_user_ref(project.manager), members=[_user_ref(m) for m in project.members],
        task_count=task_count,
        current_baseline=None if baseline is None else BaselineRef(
            baseline_id=baseline.baseline_id, version_no=baseline.version_no,
            created_at=baseline.created_at, note=baseline.note),
        can_edit=user.user_id == project.manager_user_id,
    )


def list_projects(db: Session, user: User) -> list[Project]:
    member_of = exists().where(project_members.c.project_id == Project.project_id,
                               project_members.c.user_id == user.user_id)
    return list(db.scalars(select(Project).where(or_(Project.manager_user_id == user.user_id, member_of))
                           .order_by(Project.project_code)))


def create_project(db: Session, data: ProjectCreate, actor: User) -> Project:
    _check_project_rules(data.planned_start_date, data.planned_end_date, data.data_mode,
                         data.consent_ref, data.consent_date)
    if db.scalar(select(Project.project_id).where(Project.project_code == data.project_code)) is not None:
        raise ApiError(409, "DUPLICATE_PROJECT_CODE", "رمز المشروع مستخدم من قبل",
                       [{"field": "project_code", "message": "رمز المشروع مستخدم من قبل"}])
    project = Project(**data.model_dump(exclude={"member_usernames"}), manager_user_id=actor.user_id)
    project.manager = actor
    project.members = _resolve_members(db, data.member_usernames, actor)
    db.add(project)
    db.flush()
    audit.record(db, "create", actor.user_id, "projects", project.project_id, new_value=_project_snapshot(project))
    db.commit()
    return project


def update_project(db: Session, project: Project, data: ProjectUpdate, actor: User) -> Project:
    ensure_write(db, project, actor)
    changes = data.model_dump(exclude_unset=True)
    old = _project_snapshot(project)
    merged = {k: changes.get(k, getattr(project, k)) for k in
              ("planned_start_date", "planned_end_date", "data_mode", "consent_ref", "consent_date")}
    _check_project_rules(merged["planned_start_date"], merged["planned_end_date"], merged["data_mode"],
                         merged["consent_ref"], merged["consent_date"])
    if "member_usernames" in changes:
        project.members = _resolve_members(db, changes.pop("member_usernames") or [], project.manager)
    for key, value in changes.items():
        setattr(project, key, value)
    project.updated_at = func.now()
    db.flush()
    new = _project_snapshot(project)
    changed = {k for k in new if new[k] != old[k]}
    if changed:
        audit.record(db, "update", actor.user_id, "projects", project.project_id,
                     old_value={k: old[k] for k in changed}, new_value={k: new[k] for k in changed})
    db.commit()
    db.refresh(project)
    return project


# --- tasks (API-04) ----------------------------------------------------------

def _task_snapshot(t: Task) -> dict:
    return _json({"task_code": t.task_code, "task_name": t.task_name, "priority": t.priority,
                  "assignee_user_id": t.assignee_user_id, "planned_start_date": t.planned_start_date,
                  "planned_due_date": t.planned_due_date})


def _tasks_with_snapshots(db: Session, task_ids: list[int]) -> set[int]:
    if not task_ids:
        return set()
    return set(db.scalars(select(TaskSnapshot.task_id).where(TaskSnapshot.task_id.in_(task_ids)).distinct()))


def task_out(task: Task, has_snapshots: bool) -> TaskOut:
    return TaskOut(task_id=task.task_id, project_id=task.project_id, task_code=task.task_code,
                   task_name=task.task_name, priority=task.priority,
                   assignee=None if task.assignee is None else _user_ref(task.assignee),
                   planned_start_date=task.planned_start_date, planned_due_date=task.planned_due_date,
                   planned_duration_days=task.planned_duration_days, has_snapshots=has_snapshots)


def list_tasks(db: Session, project: Project, user: User) -> list[TaskOut]:
    ensure_read(db, project, user)
    tasks = list(db.scalars(select(Task).where(Task.project_id == project.project_id).order_by(Task.task_code)))
    with_snapshots = _tasks_with_snapshots(db, [t.task_id for t in tasks])
    return [task_out(t, t.task_id in with_snapshots) for t in tasks]


def _check_task_rules(db: Session, project: Project, start: date, due: date, assignee_user_id: int | None,
                      task_code: str, exclude_task_id: int | None = None) -> None:
    fields = []
    if due < start:  # TC-05
        fields.append({"field": "planned_due_date", "message": DUE_BEFORE_START})
    if assignee_user_id is not None and not any(m.user_id == assignee_user_id for m in project.members) \
            and assignee_user_id != project.manager_user_id:
        fields.append({"field": "assignee_user_id", "message": "المسند إليه يجب أن يكون عضوًا في المشروع"})
    if fields:
        raise _invalid(fields)
    query = select(Task.task_id).where(Task.project_id == project.project_id, Task.task_code == task_code)
    if exclude_task_id is not None:
        query = query.where(Task.task_id != exclude_task_id)
    if db.scalar(query) is not None:
        raise ApiError(409, "DUPLICATE_TASK_CODE", "رمز المهمة مستخدم في هذا المشروع",
                       [{"field": "task_code", "message": "رمز المهمة مستخدم في هذا المشروع"}])


def get_task(db: Session, project: Project, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.project_id != project.project_id:
        raise ApiError(404, "NOT_FOUND", "المهمة غير موجودة في هذا المشروع")
    return task


def create_task(db: Session, project: Project, data: TaskCreate, actor: User) -> TaskOut:
    ensure_write(db, project, actor)
    _check_task_rules(db, project, data.planned_start_date, data.planned_due_date, data.assignee_user_id,
                      data.task_code)
    task = Task(project_id=project.project_id, **data.model_dump())
    db.add(task)
    db.flush()
    audit.record(db, "create", actor.user_id, "tasks", task.task_id, new_value=_task_snapshot(task))
    db.commit()
    db.refresh(task)
    return task_out(task, False)


def update_task(db: Session, project: Project, task_id: int, data: TaskUpdate, actor: User) -> TaskOut:
    ensure_write(db, project, actor)  # TC-02: checked before anything is read or changed
    task = get_task(db, project, task_id)
    changes = data.model_dump(exclude_unset=True)
    _check_task_rules(db, project, changes.get("planned_start_date", task.planned_start_date),
                      changes.get("planned_due_date", task.planned_due_date),
                      changes.get("assignee_user_id", task.assignee_user_id),
                      changes.get("task_code", task.task_code), exclude_task_id=task.task_id)
    old = _task_snapshot(task)
    for key, value in changes.items():
        setattr(task, key, value)
    task.updated_at = func.now()
    db.flush()
    db.refresh(task)
    new = _task_snapshot(task)
    changed = {k for k in new if new[k] != old[k]}
    if changed:
        audit.record(db, "update", actor.user_id, "tasks", task.task_id,
                     old_value={k: old[k] for k in changed}, new_value={k: new[k] for k in changed})
    db.commit()
    return task_out(task, bool(_tasks_with_snapshots(db, [task.task_id])))


def delete_task(db: Session, project: Project, task_id: int, actor: User) -> None:
    ensure_write(db, project, actor)
    task = get_task(db, project, task_id)
    if _tasks_with_snapshots(db, [task.task_id]):
        raise ApiError(409, "TASK_HAS_SNAPSHOTS",
                       "لا يمكن حذف مهمة لها لقطات تقدم مسجلة؛ سجل التقدم لا يُحذف (ARC-03)")
    old = _task_snapshot(task)
    try:
        db.delete(task)
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "TASK_IN_USE", "لا يمكن حذف المهمة لأنها مستخدمة في سيناريو محفوظ")
    audit.record(db, "delete", actor.user_id, "tasks", task_id, old_value=old)
    db.commit()


# --- baselines (API-05) ------------------------------------------------------

def create_baseline(db: Session, project: Project, data: BaselineCreate, actor: User) -> BaselineOut:
    ensure_write(db, project, actor)
    tasks = list(db.scalars(select(Task).where(Task.project_id == project.project_id)))
    if not tasks:
        raise ApiError(409, "NO_TASKS", "لا يمكن حفظ خط أساس لمشروع بلا مهام")
    last_version = db.scalar(select(func.max(Baseline.version_no)).where(Baseline.project_id == project.project_id))
    baseline = Baseline(project_id=project.project_id, version_no=(last_version or 0) + 1,
                        created_by=actor.user_id, note=data.note)
    db.add(baseline)
    db.flush()
    db.add_all(BaselineTask(baseline_id=baseline.baseline_id, task_id=t.task_id,
                            planned_start_date=t.planned_start_date, planned_due_date=t.planned_due_date,
                            priority=t.priority) for t in tasks)
    audit.record(db, "create", actor.user_id, "baselines", baseline.baseline_id,
                 new_value={"project_id": project.project_id, "version_no": baseline.version_no,
                            "task_count": len(tasks)})
    db.commit()
    db.refresh(baseline)
    return BaselineOut(baseline_id=baseline.baseline_id, version_no=baseline.version_no, task_count=len(tasks),
                       created_at=baseline.created_at, note=baseline.note)
