from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.plan import PlanResponse
from app.schemas.plan import PlanUpdate
from app.services.plan import PlanNotFoundError
from app.services.plan import get_plan
from app.services.plan import list_plans
from app.services.plan import update_plan

router = APIRouter(prefix="/admin/plans", tags=["admin-plans"])


@router.get("", response_model=list[PlanResponse])
def list_admin_plans(
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[PlanResponse]:
    return list_plans(db)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_admin_plan(
    plan_id: UUID,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> PlanResponse:
    try:
        return get_plan(db, plan_id)
    except PlanNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/{plan_id}", response_model=PlanResponse)
def update_admin_plan(
    plan_id: UUID,
    plan_in: PlanUpdate,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> PlanResponse:
    try:
        return update_plan(db, plan_id, plan_in)
    except PlanNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
