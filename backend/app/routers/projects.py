"""API-03 /api/projects, API-04 /api/projects/{id}/tasks, API-05 /api/projects/{id}/baselines (FR-02)."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import PROJECT_MANAGER, get_current_user, require_roles
from app.models import User
from app.schemas.projects import BaselineCreate, BaselineOut, ProjectCreate, ProjectOut, ProjectUpdate
from app.schemas.tasks import TaskCreate, TaskOut, TaskUpdate
from app.services import plan

router = APIRouter(prefix="/projects")


# API-03 ---------------------------------------------------------------------
@router.get("", response_model=list[ProjectOut], tags=["API-03 projects"])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[ProjectOut]:
    return [plan.project_out(db, p, user) for p in plan.list_projects(db, user)]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, tags=["API-03 projects"])
def create_project(body: ProjectCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_roles(PROJECT_MANAGER))) -> ProjectOut:
    return plan.project_out(db, plan.create_project(db, body, user), user)


@router.get("/{project_id}", response_model=ProjectOut, tags=["API-03 projects"])
def get_project(project_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> ProjectOut:
    project = plan.get_project(db, project_id)
    plan.ensure_read(db, project, user)
    return plan.project_out(db, project, user)


@router.patch("/{project_id}", response_model=ProjectOut, tags=["API-03 projects"])
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)) -> ProjectOut:
    project = plan.update_project(db, plan.get_project(db, project_id), body, user)
    return plan.project_out(db, project, user)


# API-04 ---------------------------------------------------------------------
@router.get("/{project_id}/tasks", response_model=list[TaskOut], tags=["API-04 tasks"])
def list_tasks(project_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)) -> list[TaskOut]:
    return plan.list_tasks(db, plan.get_project(db, project_id), user)


@router.post("/{project_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED,
             tags=["API-04 tasks"])
def create_task(project_id: int, body: TaskCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> TaskOut:
    return plan.create_task(db, plan.get_project(db, project_id), body, user)


@router.patch("/{project_id}/tasks/{task_id}", response_model=TaskOut, tags=["API-04 tasks"])
def update_task(project_id: int, task_id: int, body: TaskUpdate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> TaskOut:
    return plan.update_task(db, plan.get_project(db, project_id), task_id, body, user)


@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["API-04 tasks"])
def delete_task(project_id: int, task_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> Response:
    plan.delete_task(db, plan.get_project(db, project_id), task_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# API-05 ---------------------------------------------------------------------
@router.post("/{project_id}/baselines", response_model=BaselineOut, status_code=status.HTTP_201_CREATED,
             tags=["API-05 baselines"])
def create_baseline(project_id: int, body: BaselineCreate | None = None, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)) -> BaselineOut:
    return plan.create_baseline(db, plan.get_project(db, project_id), body or BaselineCreate(), user)
