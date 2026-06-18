from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.financial_transaction import FinancialTransaction
from app.models.user import User
from app.schemas.product_output import ProductOutputCreate
from app.schemas.product_output import ProductOutputResponse
from app.schemas.product_output import ProductOutputUpdate
from app.services.product_output import ProductOutputPermissionError
from app.services.product_output import ProductOutputValidationError
from app.services.product_output import create_product_output
from app.services.product_output import get_product_output
from app.services.product_output import list_product_outputs
from app.services.product_output import update_product_output

router = APIRouter(prefix="/product-outputs", tags=["product-outputs"])


def _raise_validation_error(error: ProductOutputValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


def _raise_permission_error(error: ProductOutputPermissionError) -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=str(error),
    ) from error


def _get_product_output_or_404(
    db: Session,
    current_user: User,
    transaction_id: UUID,
) -> FinancialTransaction:
    transaction = get_product_output(db, current_user, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saida de produto nao encontrada",
        )
    return transaction


@router.get("", response_model=list[ProductOutputResponse])
def list_outputs(
    employee_id: UUID | None = None,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[FinancialTransaction]:
    return list_product_outputs(db, current_user, employee_id)


@router.post("", response_model=ProductOutputResponse, status_code=status.HTTP_201_CREATED)
def create_output(
    output_in: ProductOutputCreate,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    try:
        return create_product_output(db, current_user, output_in)
    except ProductOutputValidationError as error:
        _raise_validation_error(error)


@router.patch("/{transaction_id}", response_model=ProductOutputResponse)
def update_output(
    transaction_id: UUID,
    output_in: ProductOutputUpdate,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    transaction = _get_product_output_or_404(db, current_user, transaction_id)
    try:
        return update_product_output(db, current_user, transaction, output_in)
    except ProductOutputPermissionError as error:
        _raise_permission_error(error)
    except ProductOutputValidationError as error:
        _raise_validation_error(error)
