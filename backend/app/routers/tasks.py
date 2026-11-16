"""API-06 /api/tasks/{id}/snapshots (FR-03, NFR-04) and GET /api/tasks?assignee=me (SCR-05).

There is deliberately no PUT/PATCH/DELETE for snapshots (ARC-03, SEC-08)."""
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas.snapshots import MyTaskOut, SnapshotCreate, SnapshotOut
from app.services import progress

router = APIRouter(prefix="/tasks")


@router.get("", response_model=list[MyTaskOut], tags=["SCR-05 my tasks"])
def my_tasks(assignee: Literal["me"] = Query(...), db: Session = Depends(get_db),
             user: User = Depends(get_current_user)) -> list[MyTaskOut]:
    """Design-review addition: list of the current user's tasks with their latest snapshot."""
    return progress.my_tasks(db, user)


@router.get("/{task_id}/snapshots", response_model=list[SnapshotOut], tags=["API-06 snapshots"])
def list_snapshots(task_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)) -> list[SnapshotOut]:
    return progress.list_snapshots(db, task_id, user)


@router.post("/{task_id}/snapshots", response_model=SnapshotOut, status_code=status.HTTP_201_CREATED,
             tags=["API-06 snapshots"])
def create_snapshot(task_id: int, body: SnapshotCreate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)) -> SnapshotOut:
    return progress.create_snapshot(db, task_id, body, user)
