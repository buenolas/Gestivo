from datetime import date
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.db.session import get_db
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.schemas.cash_flow import CashFlowEntryCreate
from app.schemas.cash_flow import CashFlowResponse
from app.schemas.financial_transaction import FinancialTransactionResponse
from app.services.cash_flow import CashFlowValidationError
from app.services.cash_flow import create_cash_flow_entry
from app.services.cash_flow import list_cash_flow_entries

router = APIRouter(prefix="/cash-flow", tags=["cash-flow"])


def _raise_validation_error(error: CashFlowValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


@router.get("", response_model=CashFlowResponse)
def list_cash_flow(
    type: FinancialTransactionType | None = None,
    contact_id: UUID | None = None,
    employee_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> CashFlowResponse:
    return list_cash_flow_entries(
        db=db,
        user=current_user,
        transaction_type=type,
        contact_id=contact_id,
        employee_id=employee_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )


@router.post("", response_model=FinancialTransactionResponse, status_code=status.HTTP_201_CREATED)
def create_cash_flow(
    entry_in: CashFlowEntryCreate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    try:
        return create_cash_flow_entry(db, current_user, entry_in)
    except CashFlowValidationError as error:
        _raise_validation_error(error)
