from datetime import date
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.api.deps import require_plan_feature
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_financial_dashboard

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_plan_feature("dashboard"))],
)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    period: Literal["month", "3m", "6m", "12m", "all"] = Query(default="month"),
    month: date | None = Query(default=None),
    comparison_start: date | None = Query(default=None),
    comparison_end: date | None = Query(default=None),
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    if (comparison_start is None) != (comparison_end is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe as datas inicial e final do período de comparação.",
        )
    if comparison_start and comparison_end and comparison_start > comparison_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A data inicial da comparação precisa ser anterior à data final.",
        )

    try:
        return get_financial_dashboard(
            db,
            current_user,
            period=period,
            month=month,
            comparison_start=comparison_start,
            comparison_end=comparison_end,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
