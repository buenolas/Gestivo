from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.contact import Contact
from app.models.employee import Employee
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.models.user import UserRole
from app.schemas.cash_flow import CashFlowEntryCreate
from app.schemas.cash_flow import CashFlowEntryUpdate
from app.schemas.cash_flow import CashFlowResponse
from app.schemas.cash_flow import CashFlowSummary

CASH_FLOW_SOURCE = "cash_flow"
ZERO = Decimal("0.00")


class CashFlowValidationError(ValueError):
    pass


class CashFlowPermissionError(PermissionError):
    pass


def list_cash_flow_entries(
    db: Session,
    user: User,
    transaction_type: FinancialTransactionType | None = None,
    contact_id: UUID | None = None,
    employee_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
) -> CashFlowResponse:
    query = select(FinancialTransaction).where(
        FinancialTransaction.company_id == user.company_id,
        FinancialTransaction.source == CASH_FLOW_SOURCE,
        FinancialTransaction.status == FinancialTransactionStatus.settled,
        FinancialTransaction.deleted_at.is_(None),
    )
    if transaction_type is not None:
        query = query.where(FinancialTransaction.type == transaction_type)
    if contact_id is not None:
        query = query.where(FinancialTransaction.contact_id == contact_id)
    if employee_id is not None:
        query = query.where(FinancialTransaction.employee_id == employee_id)
    if start_date is not None:
        query = query.where(FinancialTransaction.competence_date >= start_date)
    if end_date is not None:
        query = query.where(FinancialTransaction.competence_date <= end_date)
    if search is not None and search.strip():
        query = query.where(FinancialTransaction.description.ilike(f"%{search.strip()}%"))

    query = query.options(
        selectinload(FinancialTransaction.contact),
        selectinload(FinancialTransaction.employee),
    ).order_by(
        FinancialTransaction.competence_date.desc(),
        FinancialTransaction.created_at.desc(),
    )
    items = list(db.scalars(query))
    income_total = ZERO
    expense_total = ZERO
    for item in items:
        if item.type == FinancialTransactionType.income:
            income_total += item.amount
        else:
            expense_total += item.amount

    return CashFlowResponse(
        generated_at=datetime.now(UTC),
        summary=CashFlowSummary(
            income_total=income_total,
            expense_total=expense_total,
            result=income_total - expense_total,
        ),
        items=items,
    )


def create_cash_flow_entry(
    db: Session,
    user: User,
    entry_in: CashFlowEntryCreate,
) -> FinancialTransaction:
    _validate_links(db, user, entry_in.contact_id, entry_in.employee_id)
    now = datetime.now(UTC)
    transaction = FinancialTransaction(
        company_id=user.company_id,
        contact_id=entry_in.contact_id,
        employee_id=entry_in.employee_id,
        description=entry_in.description.strip(),
        amount=entry_in.amount,
        type=entry_in.type,
        status=FinancialTransactionStatus.settled,
        competence_date=entry_in.competence_date,
        settled_at=now,
        notes=_strip_optional_text(entry_in.notes),
        source=CASH_FLOW_SOURCE,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_cash_flow_entry(
    db: Session,
    user: User,
    transaction_id: UUID,
) -> FinancialTransaction | None:
    return db.scalar(
        select(FinancialTransaction).where(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.company_id == user.company_id,
            FinancialTransaction.source == CASH_FLOW_SOURCE,
            FinancialTransaction.deleted_at.is_(None),
        )
    )


def update_cash_flow_entry(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
    entry_in: CashFlowEntryUpdate,
) -> FinancialTransaction:
    _ensure_can_update_cash_flow(user, transaction)

    next_contact_id = (
        entry_in.contact_id
        if "contact_id" in entry_in.model_fields_set
        else transaction.contact_id
    )
    next_employee_id = (
        entry_in.employee_id
        if "employee_id" in entry_in.model_fields_set
        else transaction.employee_id
    )
    _validate_links(db, user, next_contact_id, next_employee_id)

    if entry_in.description is not None:
        transaction.description = entry_in.description.strip()
    if entry_in.amount is not None:
        transaction.amount = entry_in.amount
    if entry_in.type is not None:
        transaction.type = entry_in.type
    if entry_in.competence_date is not None:
        transaction.competence_date = entry_in.competence_date
    if "contact_id" in entry_in.model_fields_set:
        transaction.contact_id = entry_in.contact_id
    if "employee_id" in entry_in.model_fields_set:
        transaction.employee_id = entry_in.employee_id
    if "notes" in entry_in.model_fields_set:
        transaction.notes = _strip_optional_text(entry_in.notes)

    transaction.updated_by = user.id
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def _ensure_can_update_cash_flow(user: User, transaction: FinancialTransaction) -> None:
    if transaction.company_id != user.company_id:
        raise CashFlowPermissionError("Movimentacao de caixa nao encontrada")
    if transaction.source != CASH_FLOW_SOURCE:
        raise CashFlowValidationError("Este lancamento nao pertence ao fluxo de caixa")
    if transaction.deleted_at is not None:
        raise CashFlowValidationError("Movimentacoes excluidas nao podem ser editadas")
    if transaction.status == FinancialTransactionStatus.canceled:
        raise CashFlowValidationError("Movimentacoes canceladas nao podem ser editadas")
    if user.role == UserRole.user and transaction.created_by != user.id:
        raise CashFlowPermissionError("Voce so pode editar movimentacoes criadas por voce")


def _validate_links(
    db: Session,
    user: User,
    contact_id: UUID | None,
    employee_id: UUID | None,
) -> None:
    if contact_id is not None:
        contact = db.scalar(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.company_id == user.company_id,
                Contact.is_active.is_(True),
            )
        )
        if contact is None:
            raise CashFlowValidationError("Cliente/fornecedor nao encontrado")

    if employee_id is not None:
        employee = db.scalar(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.company_id == user.company_id,
            )
        )
        if employee is None:
            raise CashFlowValidationError("Funcionario nao encontrado")


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
