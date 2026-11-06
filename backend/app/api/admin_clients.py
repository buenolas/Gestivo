from datetime import timedelta
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
from app.schemas.admin_client import AdminClientDeletionResponse
from app.schemas.admin_client import AdminClientDetailResponse
from app.schemas.admin_client import AdminClientListResponse
from app.schemas.admin_client import AdminClientRenewRequest
from app.schemas.subscription import ManualPaymentResponse
from app.services.admin_client import AdminClientNotFoundError
from app.services.admin_client import AdminClientValidationError
from app.services.admin_client import block_admin_client
from app.services.admin_client import get_admin_client_dashboard
from app.services.admin_client import get_admin_client_detail
from app.services.admin_client import list_admin_clients
from app.services.admin_client import renew_admin_client
from app.services.admin_client import unblock_admin_client
from app.services.subscription import SubscriptionValidationError
from app.services.company_deletion import CompanyDeletionConflictError
from app.services.company_deletion import CompanyDeletionNotFoundError
from app.services.company_deletion import DELETION_RETENTION_DAYS
from app.services.company_deletion import schedule_company_deletion

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
    except AdminClientNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AdminClientValidationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except SubscriptionValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.delete(
    "/clients/{company_id}",
    response_model=AdminClientDeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def delete_client_profile(
    company_id: UUID,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> AdminClientDeletionResponse:
    try:
        company = schedule_company_deletion(db, company_id)
    except CompanyDeletionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except CompanyDeletionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    assert company.deletion_requested_at is not None
    return AdminClientDeletionResponse(
        company_id=company.id,
        deletion_requested_at=company.deletion_requested_at,
        deletion_due_at=company.deletion_requested_at + timedelta(days=DELETION_RETENTION_DAYS),
        message=f"Acesso revogado. Os dados serão removidos automaticamente após {DELETION_RETENTION_DAYS} dias.",
    )


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


def _run_action(action, db: Session, current_user: User, company_id: UUID) -> AdminClientActionResponse:
    try:
        return action(db, current_user, company_id)
    except AdminClientNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except AdminClientValidationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
