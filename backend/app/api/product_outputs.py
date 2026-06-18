from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.db.session import get_db
from app.models.financial_transaction import FinancialTransaction
from app.models.user import User
from app.schemas.product_output import ProductOutputCreate
from app.schemas.product_output import ProductOutputResponse
from app.services.product_output import ProductOutputValidationError
from app.services.product_output import create_product_output
from app.services.product_output import list_product_outputs

router = APIRouter(prefix="/product-outputs", tags=["product-outputs"])


def _raise_validation_error(error: ProductOutputValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


@router.get("", response_model=list[ProductOutputResponse])
def list_outputs(
    employee_id: UUID | None = None,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> list[FinancialTransaction]:
    return list_product_outputs(db, current_user, employee_id)


@router.post("", response_model=ProductOutputResponse, status_code=status.HTTP_201_CREATED)
def create_output(
    output_in: ProductOutputCreate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    try:
        return create_product_output(db, current_user, output_in)
    except ProductOutputValidationError as error:
        _raise_validation_error(error)
