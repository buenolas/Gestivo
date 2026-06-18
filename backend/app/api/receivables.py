from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.db.session import get_db
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.schemas.account_view import DueDateFilter
from app.schemas.financial_transaction import FinancialTransactionResponse
from app.schemas.financial_transaction import FinancialTransactionSettle
from app.services.account_view import get_account_view_transaction
from app.services.account_view import list_account_view_transactions
from app.services.account_view import settle_account_view_transaction
from app.services.financial_transaction import FinancialTransactionValidationError

router = APIRouter(prefix="/receivables", tags=["receivables"])


def _get_user_receivable_or_404(
    db: Session,
    current_user: User,
    receivable_id: UUID,
) -> FinancialTransaction:
    receivable = get_account_view_transaction(
        db=db,
        user=current_user,
        transaction_id=receivable_id,
        transaction_type=FinancialTransactionType.income,
    )
    if receivable is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta a receber não encontrada",
        )
    return receivable


def _raise_validation_error(error: FinancialTransactionValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


@router.get("", response_model=list[FinancialTransactionResponse])
def list_receivables(
    due: DueDateFilter | None = None,
    status: FinancialTransactionStatus | None = None,
    contact_id: UUID | None = None,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> list[FinancialTransaction]:
    return list_account_view_transactions(
        db=db,
        user=current_user,
        transaction_type=FinancialTransactionType.income,
        status=status,
        due=due,
        contact_id=contact_id,
    )


@router.post("/{receivable_id}/receive", response_model=FinancialTransactionResponse)
def receive_receivable(
    receivable_id: UUID,
    settle_in: FinancialTransactionSettle | None = None,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    receivable = _get_user_receivable_or_404(db, current_user, receivable_id)
    try:
        return settle_account_view_transaction(
            db=db,
            user=current_user,
            transaction=receivable,
            settle_in=settle_in or FinancialTransactionSettle(),
        )
    except FinancialTransactionValidationError as error:
        _raise_validation_error(error)
