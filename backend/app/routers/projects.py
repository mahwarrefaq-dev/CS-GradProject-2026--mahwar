"""API-03 /api/projects, API-04 /api/projects/{id}/tasks, API-05 /api/projects/{id}/baselines (FR-02),
API-07 /api/projects/{id}/dependencies (FR-04)."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import PROJECT_MANAGER, get_current_user, require_roles
from app.models import User
from app.schemas.dependencies import DependencyCreate, DependencyOut
from app.schemas.projects import (BaselineCreate, BaselineOut, MemberAdd, ProjectCreate, ProjectOut,
                                  ProjectUpdate, UserRef)
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


# API-03: project members (supervisor's review) ------------------------------
@router.get("/{project_id}/members", response_model=list[UserRef], tags=["API-03 projects"])
def list_members(project_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)) -> list[UserRef]:
    return plan.list_members(db, plan.get_project(db, project_id), user)


@router.post("/{project_id}/members", response_model=UserRef, status_code=status.HTTP_201_CREATED,
             tags=["API-03 projects"])
def add_member(project_id: int, body: MemberAdd, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)) -> UserRef:
    return plan.add_member(db, plan.get_project(db, project_id), body.username, user)


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               tags=["API-03 projects"])
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)) -> Response:
    plan.remove_member(db, plan.get_project(db, project_id), user_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


# API-07 ---------------------------------------------------------------------
@router.get("/{project_id}/dependencies", response_model=list[DependencyOut], tags=["API-07 dependencies"])
def list_dependencies(project_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)) -> list[DependencyOut]:
    return plan.list_dependencies(db, plan.get_project(db, project_id), user)


@router.post("/{project_id}/dependencies", response_model=DependencyOut, status_code=status.HTTP_201_CREATED,
             tags=["API-07 dependencies"])
def create_dependency(project_id: int, body: DependencyCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)) -> DependencyOut:
    return plan.create_dependency(db, plan.get_project(db, project_id), body, user)


@router.delete("/{project_id}/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT,
               tags=["API-07 dependencies"])
def delete_dependency(project_id: int, dependency_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)) -> Response:
    plan.delete_dependency(db, plan.get_project(db, project_id), dependency_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# API-05 ---------------------------------------------------------------------
@router.post("/{project_id}/baselines", response_model=BaselineOut, status_code=status.HTTP_201_CREATED,
             tags=["API-05 baselines"])
def create_baseline(project_id: int, body: BaselineCreate | None = None, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)) -> BaselineOut:
    return plan.create_baseline(db, plan.get_project(db, project_id), body or BaselineCreate(), user)
