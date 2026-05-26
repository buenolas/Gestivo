from datetime import date
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.schemas.financial_transaction import FinancialTransactionCreate
from app.schemas.financial_transaction import FinancialTransactionListResponse
from app.schemas.financial_transaction import FinancialTransactionResponse
from app.schemas.financial_transaction import FinancialTransactionSettle
from app.schemas.financial_transaction import FinancialTransactionUpdate
from app.services.financial_transaction import FinancialTransactionValidationError
from app.services.financial_transaction import cancel_financial_transaction
from app.services.financial_transaction import create_financial_transaction
from app.services.financial_transaction import get_financial_transaction
from app.services.financial_transaction import list_financial_transactions
from app.services.financial_transaction import settle_financial_transaction
from app.services.financial_transaction import update_financial_transaction

router = APIRouter(prefix="/financial-transactions", tags=["financial-transactions"])


def _get_user_transaction_or_404(
    db: Session,
    current_user: User,
    transaction_id: UUID,
) -> FinancialTransaction:
    transaction = get_financial_transaction(db, current_user, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lançamento financeiro não encontrado",
        )
    return transaction


def _raise_validation_error(error: FinancialTransactionValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


@router.get("", response_model=list[FinancialTransactionListResponse])
def list_transactions(
    type: FinancialTransactionType | None = None,
    status: FinancialTransactionStatus | None = None,
    category_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[FinancialTransaction]:
    return list_financial_transactions(
        db=db,
        user=current_user,
        transaction_type=type,
        status=status,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )


@router.post(
    "",
    response_model=FinancialTransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    transaction_in: FinancialTransactionCreate,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    try:
        return create_financial_transaction(db, current_user, transaction_in)
    except FinancialTransactionValidationError as error:
        _raise_validation_error(error)


@router.get("/{transaction_id}", response_model=FinancialTransactionResponse)
def get_transaction(
    transaction_id: UUID,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    return _get_user_transaction_or_404(db, current_user, transaction_id)


@router.patch("/{transaction_id}", response_model=FinancialTransactionResponse)
def update_transaction(
    transaction_id: UUID,
    transaction_in: FinancialTransactionUpdate,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    transaction = _get_user_transaction_or_404(db, current_user, transaction_id)
    try:
        return update_financial_transaction(db, current_user, transaction, transaction_in)
    except FinancialTransactionValidationError as error:
        _raise_validation_error(error)


@router.post("/{transaction_id}/settle", response_model=FinancialTransactionResponse)
def settle_transaction(
    transaction_id: UUID,
    settle_in: FinancialTransactionSettle | None = None,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    transaction = _get_user_transaction_or_404(db, current_user, transaction_id)
    try:
        return settle_financial_transaction(
            db,
            current_user,
            transaction,
            settle_in or FinancialTransactionSettle(),
        )
    except FinancialTransactionValidationError as error:
        _raise_validation_error(error)


@router.post("/{transaction_id}/cancel", response_model=FinancialTransactionResponse)
def cancel_transaction(
    transaction_id: UUID,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialTransaction:
    transaction = _get_user_transaction_or_404(db, current_user, transaction_id)
    return cancel_financial_transaction(db, current_user, transaction)
