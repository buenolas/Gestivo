import uuid
from datetime import date
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.schemas.account_view import DueDateFilter
from app.schemas.financial_transaction import FinancialTransactionSettle
from app.services.financial_transaction import settle_financial_transaction


def list_account_view_transactions(
    db: Session,
    user: User,
    transaction_type: FinancialTransactionType,
    status: FinancialTransactionStatus | None = None,
    due: DueDateFilter | None = None,
) -> list[FinancialTransaction]:
    query = select(FinancialTransaction).where(
        FinancialTransaction.company_id == user.company_id,
        FinancialTransaction.type == transaction_type,
        FinancialTransaction.deleted_at.is_(None),
    )

    if status is not None:
        query = query.where(FinancialTransaction.status == status)

    if due is not None:
        query = _apply_due_date_filter(query, due)

    query = query.order_by(
        FinancialTransaction.due_date.asc().nullslast(),
        FinancialTransaction.created_at.desc(),
    )
    return [transaction for transaction in db.scalars(query) if transaction.deleted_at is None]


def get_account_view_transaction(
    db: Session,
    user: User,
    transaction_id: uuid.UUID,
    transaction_type: FinancialTransactionType,
) -> FinancialTransaction | None:
    return db.scalar(
        select(FinancialTransaction).where(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.company_id == user.company_id,
            FinancialTransaction.type == transaction_type,
            FinancialTransaction.deleted_at.is_(None),
        )
    )


def settle_account_view_transaction(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
    settle_in: FinancialTransactionSettle,
) -> FinancialTransaction:
    return settle_financial_transaction(db, user, transaction, settle_in)


def _apply_due_date_filter(query, due: DueDateFilter):
    today = date.today()

    if due == DueDateFilter.overdue:
        return query.where(
            FinancialTransaction.due_date < today,
            FinancialTransaction.status == FinancialTransactionStatus.pending,
        )
    if due == DueDateFilter.today:
        return query.where(FinancialTransaction.due_date == today)
    if due == DueDateFilter.next_7_days:
        return query.where(
            FinancialTransaction.due_date >= today,
            FinancialTransaction.due_date <= today + timedelta(days=7),
        )

    return query.where(
        FinancialTransaction.due_date >= today,
        FinancialTransaction.due_date <= today + timedelta(days=30),
    )
