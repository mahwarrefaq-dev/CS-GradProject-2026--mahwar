"""API-08 /api/resources (FR-05) with sub-paths for availability and allocation
(design-review detail of API-08: one path in the API table covers three things)."""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import PLANNER, PROJECT_MANAGER, get_current_user, require_roles
from app.models import User
from app.schemas.resources import (AllocationCreate, AllocationOut, AvailabilityCreate, AvailabilityOut,
                                   ResourceCreate, ResourceOut, ResourceUpdate)
from app.services import resources as service

router = APIRouter(prefix="/resources", tags=["API-08 resources"])
planners = require_roles(PROJECT_MANAGER, PLANNER)


@router.get("", response_model=list[ResourceOut])
def list_resources(db: Session = Depends(get_db), _: User = Depends(planners)) -> list[ResourceOut]:
    return service.list_resources(db)


@router.post("", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
def create_resource(body: ResourceCreate, db: Session = Depends(get_db),
                    user: User = Depends(planners)) -> ResourceOut:
    return service.create_resource(db, body, user)


@router.patch("/{resource_id}", response_model=ResourceOut)
def update_resource(resource_id: int, body: ResourceUpdate, db: Session = Depends(get_db),
                    user: User = Depends(planners)) -> ResourceOut:
    return service.update_resource(db, resource_id, body, user)


@router.get("/{resource_id}/availability", response_model=list[AvailabilityOut])
def list_availability(resource_id: int, db: Session = Depends(get_db),
                      _: User = Depends(planners)) -> list[AvailabilityOut]:
    return service.list_availability(db, resource_id)


@router.post("/{resource_id}/availability", response_model=AvailabilityOut, status_code=status.HTTP_201_CREATED)
def create_availability(resource_id: int, body: AvailabilityCreate, db: Session = Depends(get_db),
                        user: User = Depends(planners)) -> AvailabilityOut:
    return service.create_availability(db, resource_id, body, user)


@router.get("/{resource_id}/allocations", response_model=list[AllocationOut])
def list_allocations(resource_id: int, db: Session = Depends(get_db),
                     _: User = Depends(planners)) -> list[AllocationOut]:
    return service.list_allocations(db, resource_id)


@router.post("/{resource_id}/allocations", response_model=AllocationOut, status_code=status.HTTP_201_CREATED)
def create_allocation(resource_id: int, body: AllocationCreate, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)) -> AllocationOut:
    return service.create_allocation(db, resource_id, body, user)


@router.delete("/{resource_id}/allocations/{allocation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allocation(resource_id: int, allocation_id: int, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)) -> Response:
    service.delete_allocation(db, resource_id, allocation_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
