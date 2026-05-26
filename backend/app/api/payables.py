from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_valid_subscription
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

router = APIRouter(prefix="/payables", tags=["payables"])


def _get_user_payable_or_404(
    db: Session,
    current_user: User,
    payable_id: UUID,
) -> FinancialTransaction:
    payable = get_account_view_transaction(
        db=db,
        user=current_user,
        transaction_id=payable_id,
        transaction_type=FinancialTransactionType.expense,
    )
    if payable is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta a pagar não encontrada",
        )
    return payable


def _raise_validation_error(error: FinancialTransactionValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


@router.get("", response_model=list[FinancialTransactionResponse])
def list_payables(
    due: DueDateFilter | None = None,
    status: FinancialTransactionStatus | None = None,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[FinancialTransaction]:
    return list_account_view_transactions(
        db=db,
        user=current_user,
        transaction_type=FinancialTransactionType.expense,
        status=status,
        due=due,
    )


@router.post("/{payable_id}/pay", response_model=FinancialTransactionResponse)
def pay_payable(
    payable_id: UUID,
    settle_in: FinancialTransactionSettle | None = None,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    payable = _get_user_payable_or_404(db, current_user, payable_id)
    try:
        return settle_account_view_transaction(
            db=db,
            user=current_user,
            transaction=payable,
            settle_in=settle_in or FinancialTransactionSettle(),
        )
    except FinancialTransactionValidationError as error:
        _raise_validation_error(error)
