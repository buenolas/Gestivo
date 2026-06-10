from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_platform_admin
from app.db.session import get_db
from app.models.company import SubscriptionStatus
from app.models.manual_payment import ManualPayment
from app.models.user import User
from app.schemas.admin_client import AdminClientActionResponse
from app.schemas.admin_client import AdminClientDashboardResponse
from app.schemas.admin_client import AdminClientDetailResponse
from app.schemas.admin_client import AdminClientListResponse
from app.schemas.admin_client import AdminClientPlanUpdate
from app.schemas.admin_client import AdminClientRenewRequest
from app.schemas.subscription import ManualPaymentResponse
from app.services.admin_client import AdminClientNotFoundError
from app.services.admin_client import AdminClientValidationError
from app.services.admin_client import block_admin_client
from app.services.admin_client import cancel_admin_client
from app.services.admin_client import change_admin_client_plan
from app.services.admin_client import get_admin_client_dashboard
from app.services.admin_client import get_admin_client_detail
from app.services.admin_client import list_admin_clients
from app.services.admin_client import reactivate_admin_client
from app.services.admin_client import renew_admin_client
from app.services.admin_client import unblock_admin_client
from app.services.subscription import SubscriptionValidationError

router = APIRouter(prefix="/admin", tags=["admin-clients"])


@router.get("/dashboard/clients", response_model=AdminClientDashboardResponse)
def get_clients_dashboard(
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientDashboardResponse:
    return get_admin_client_dashboard(db)


@router.get("/clients", response_model=AdminClientListResponse)
def list_clients(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=120),
    subscription_status: SubscriptionStatus | None = None,
    plan_id: UUID | None = None,
    filter_key: str | None = Query(default=None, max_length=60),
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientListResponse:
    return list_admin_clients(
        db,
        page=page,
        page_size=page_size,
        search=search,
        subscription_status=subscription_status,
        plan_id=plan_id,
        filter_key=filter_key,
    )


@router.get("/clients/{company_id}", response_model=AdminClientDetailResponse)
def get_client(
    company_id: UUID,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientDetailResponse:
    try:
        return get_admin_client_detail(db, company_id)
    except AdminClientNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/clients/{company_id}/usage")
def get_client_usage(
    company_id: UUID,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str | None]]:
    return get_admin_client_detail(db, company_id).usage_events


@router.get("/clients/{company_id}/payments")
def get_client_payments(
    company_id: UUID,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str | None]]:
    return get_admin_client_detail(db, company_id).payment_history


@router.get("/clients/{company_id}/renewals")
def get_client_renewals(
    company_id: UUID,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, str | None]]:
    return get_admin_client_detail(db, company_id).renewal_history


@router.post("/clients/{company_id}/renew", response_model=ManualPaymentResponse)
def renew_client(
    company_id: UUID,
    renewal_in: AdminClientRenewRequest,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> ManualPayment:
    try:
        return renew_admin_client(db, current_user, company_id, renewal_in)
    except (AdminClientNotFoundError, SubscriptionValidationError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/clients/{company_id}/block", response_model=AdminClientActionResponse)
def block_client(
    company_id: UUID,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientActionResponse:
    return _run_action(block_admin_client, db, current_user, company_id)


@router.post("/clients/{company_id}/unblock", response_model=AdminClientActionResponse)
def unblock_client(
    company_id: UUID,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientActionResponse:
    return _run_action(unblock_admin_client, db, current_user, company_id)


@router.post("/clients/{company_id}/cancel", response_model=AdminClientActionResponse)
def cancel_client(
    company_id: UUID,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientActionResponse:
    return _run_action(cancel_admin_client, db, current_user, company_id)


@router.post("/clients/{company_id}/reactivate", response_model=AdminClientActionResponse)
def reactivate_client(
    company_id: UUID,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientActionResponse:
    return _run_action(reactivate_admin_client, db, current_user, company_id)


@router.patch("/clients/{company_id}/plan", response_model=AdminClientActionResponse)
def change_client_plan(
    company_id: UUID,
    plan_in: AdminClientPlanUpdate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientActionResponse:
    try:
        return change_admin_client_plan(db, current_user, company_id, plan_in.plan_id)
    except (AdminClientNotFoundError, AdminClientValidationError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


def _run_action(action, db: Session, current_user: User, company_id: UUID) -> AdminClientActionResponse:
    try:
        return action(db, current_user, company_id)
    except AdminClientNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
