from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.deps import require_platform_admin
from app.db.session import get_db
from app.models.company import Company
from app.models.manual_payment import ManualPayment
from app.models.user import User
from app.schemas.subscription import AdminCompanySubscriptionResponse
from app.schemas.subscription import ManualPaymentResponse
from app.schemas.subscription import ManualRenewalCreate
from app.schemas.subscription import SubscriptionStatusResponse
from app.services.subscription import SubscriptionPermissionError
from app.services.subscription import SubscriptionValidationError
from app.services.subscription import create_manual_renewal
from app.services.subscription import get_subscription_status
from app.services.subscription import list_admin_company_subscriptions

router = APIRouter(prefix="/subscription", tags=["subscription"])
admin_router = APIRouter(prefix="/admin/subscriptions", tags=["admin-subscriptions"])


@router.get("/status", response_model=SubscriptionStatusResponse)
def get_my_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionStatusResponse:
    company = db.get(Company, current_user.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )
    return get_subscription_status(db, company)


@admin_router.get("/companies", response_model=list[AdminCompanySubscriptionResponse])
def list_companies_for_subscription_admin(
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[AdminCompanySubscriptionResponse]:
    return list_admin_company_subscriptions(db)


@admin_router.post(
    "/manual-renewals",
    response_model=ManualPaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def renew_subscription_manually(
    renewal_in: ManualRenewalCreate,
    current_user: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> ManualPayment:
    try:
        return create_manual_renewal(db, current_user, renewal_in)
    except SubscriptionPermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except SubscriptionValidationError as error:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "nÃ£o encontrada" in str(error) or "nao encontrado" in str(error)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(
            status_code=status_code,
            detail=str(error),
        ) from error
