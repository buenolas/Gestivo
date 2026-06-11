from datetime import datetime
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.db.session import get_db
from app.models.company import SubscriptionStatus
from app.models.user import User
from app.schemas.admin_financial import AdminFinancialDashboardResponse
from app.schemas.admin_financial import AdminFinancialTableResponse
from app.services.admin_financial import get_admin_financial_dashboard
from app.services.admin_financial import list_admin_financial_rows

router = APIRouter(prefix="/admin/financial", tags=["admin-financial"])


@router.get("/dashboard", response_model=AdminFinancialDashboardResponse)
def financial_dashboard(
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminFinancialDashboardResponse:
    return get_admin_financial_dashboard(
        db,
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/payments", response_model=AdminFinancialTableResponse)
def financial_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
    subscription_status: SubscriptionStatus | None = None,
    payment_status: str | None = Query(default=None, max_length=20),
    plan_id: UUID | None = None,
    payment_method: str | None = Query(default=None, max_length=40),
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminFinancialTableResponse:
    return list_admin_financial_rows(
        db,
        page=page,
        page_size=page_size,
        search=search,
        subscription_status=subscription_status,
        payment_status=payment_status,
        plan_id=plan_id,
        payment_method=payment_method,
    )
