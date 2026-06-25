import uuid
from datetime import UTC
from datetime import date
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.contact import ContactType
from app.models.employee import Employee
from app.models.financial_category import FinancialCategory
from app.models.financial_category import FinancialCategoryType
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionPaymentMethod
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.models.user import UserRole
from app.models.usage_event import UsageEventType
from app.schemas.financial_transaction import FinancialTransactionCreate
from app.schemas.financial_transaction import FinancialTransactionSettle
from app.schemas.financial_transaction import FinancialTransactionUpdate
from app.services.usage_event import record_usage_event


class FinancialTransactionValidationError(ValueError):
    pass


def list_financial_transactions(
    db: Session,
    user: User,
    transaction_type: FinancialTransactionType | None = None,
    status: FinancialTransactionStatus | None = None,
    category_id: uuid.UUID | None = None,
    contact_id: uuid.UUID | None = None,
    employee_id: uuid.UUID | None = None,
    payment_method: FinancialTransactionPaymentMethod | None = None,
    source: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
) -> list[FinancialTransaction]:
    query = select(FinancialTransaction).where(
        FinancialTransaction.company_id == user.company_id,
        FinancialTransaction.deleted_at.is_(None),
    )
    if user.role == UserRole.user:
        query = query.where(FinancialTransaction.created_by == user.id)

    if transaction_type is not None:
        query = query.where(FinancialTransaction.type == transaction_type)
    if status is not None:
        query = query.where(FinancialTransaction.status == status)
    if category_id is not None:
        query = query.where(FinancialTransaction.category_id == category_id)
    if contact_id is not None:
        query = query.where(FinancialTransaction.contact_id == contact_id)
    if employee_id is not None:
        query = query.where(FinancialTransaction.employee_id == employee_id)
    if payment_method is not None:
        query = query.where(FinancialTransaction.payment_method == payment_method)
    if source is not None:
        query = query.where(FinancialTransaction.source == source)
    if start_date is not None:
        query = query.where(FinancialTransaction.competence_date >= start_date)
    if end_date is not None:
        query = query.where(FinancialTransaction.competence_date <= end_date)
    if search is not None and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.where(
            or_(
                FinancialTransaction.description.ilike(search_term),
                FinancialTransaction.notes.ilike(search_term),
            )
        )

    query = query.order_by(
        FinancialTransaction.competence_date.desc(),
        FinancialTransaction.created_at.desc(),
    )
    return [transaction for transaction in db.scalars(query) if transaction.deleted_at is None]


def get_financial_transaction(
    db: Session,
    user: User,
    transaction_id: uuid.UUID,
) -> FinancialTransaction | None:
    query = select(FinancialTransaction).where(
        FinancialTransaction.id == transaction_id,
        FinancialTransaction.company_id == user.company_id,
        FinancialTransaction.deleted_at.is_(None),
    )
    if user.role == UserRole.user:
        query = query.where(FinancialTransaction.created_by == user.id)
    return db.scalar(query)


def create_financial_transaction(
    db: Session,
    user: User,
    transaction_in: FinancialTransactionCreate,
) -> FinancialTransaction:
    _validate_transaction_links(
        db=db,
        user=user,
        transaction_type=transaction_in.type,
        category_id=transaction_in.category_id,
        contact_id=transaction_in.contact_id,
        employee_id=transaction_in.employee_id,
    )
    transaction = FinancialTransaction(
        company_id=user.company_id,
        category_id=transaction_in.category_id,
        contact_id=transaction_in.contact_id,
        employee_id=transaction_in.employee_id,
        description=transaction_in.description.strip(),
        amount=transaction_in.amount,
        type=transaction_in.type,
        payment_method=transaction_in.payment_method,
        status=FinancialTransactionStatus.pending,
        competence_date=transaction_in.competence_date,
        due_date=transaction_in.due_date,
        notes=_strip_optional_text(transaction_in.notes),
        product_name=_strip_optional_text(transaction_in.product_name),
        product_unit_price=transaction_in.product_unit_price,
        product_quantity=transaction_in.product_quantity,
        product_unit=_strip_optional_text(transaction_in.product_unit),
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(transaction)
    record_usage_event(
        db,
        company_id=user.company_id,
        user_id=user.id,
        event_type=UsageEventType.financial_entry_created,
    )
    db.commit()
    db.refresh(transaction)
    return transaction


def update_financial_transaction(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
    transaction_in: FinancialTransactionUpdate,
) -> FinancialTransaction:
    if transaction.deleted_at is not None:
        raise FinancialTransactionValidationError("Lancamentos excluidos nao podem ser editados")
    if transaction.status == FinancialTransactionStatus.canceled:
        raise FinancialTransactionValidationError("Lançamentos cancelados não podem ser editados")

    next_type = transaction_in.type if transaction_in.type is not None else transaction.type
    next_category_id = (
        transaction_in.category_id
        if "category_id" in transaction_in.model_fields_set
        else transaction.category_id
    )
    next_contact_id = (
        transaction_in.contact_id
        if "contact_id" in transaction_in.model_fields_set
        else transaction.contact_id
    )
    next_employee_id = (
        transaction_in.employee_id
        if "employee_id" in transaction_in.model_fields_set
        else transaction.employee_id
    )
    _validate_transaction_links(
        db=db,
        user=user,
        transaction_type=next_type,
        category_id=next_category_id,
        contact_id=next_contact_id,
        employee_id=next_employee_id,
    )

    if transaction_in.description is not None:
        transaction.description = transaction_in.description.strip()
    if transaction_in.amount is not None:
        transaction.amount = transaction_in.amount
    if transaction_in.type is not None:
        transaction.type = transaction_in.type
    if "payment_method" in transaction_in.model_fields_set:
        transaction.payment_method = transaction_in.payment_method
    if transaction_in.competence_date is not None:
        transaction.competence_date = transaction_in.competence_date
    if "due_date" in transaction_in.model_fields_set:
        transaction.due_date = transaction_in.due_date
    if "category_id" in transaction_in.model_fields_set:
        transaction.category_id = transaction_in.category_id
    if "contact_id" in transaction_in.model_fields_set:
        transaction.contact_id = transaction_in.contact_id
    if "employee_id" in transaction_in.model_fields_set:
        transaction.employee_id = transaction_in.employee_id
    if "product_name" in transaction_in.model_fields_set:
        transaction.product_name = _strip_optional_text(transaction_in.product_name)
    if "product_unit_price" in transaction_in.model_fields_set:
        transaction.product_unit_price = transaction_in.product_unit_price
    if "product_quantity" in transaction_in.model_fields_set:
        transaction.product_quantity = transaction_in.product_quantity
    if "product_unit" in transaction_in.model_fields_set:
        transaction.product_unit = _strip_optional_text(transaction_in.product_unit)
    if "notes" in transaction_in.model_fields_set:
        transaction.notes = _strip_optional_text(transaction_in.notes)

    transaction.updated_by = user.id
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def settle_financial_transaction(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
    settle_in: FinancialTransactionSettle,
) -> FinancialTransaction:
    if transaction.deleted_at is not None:
        raise FinancialTransactionValidationError("Lancamentos excluidos nao podem ser liquidados")
    if transaction.status == FinancialTransactionStatus.canceled:
        raise FinancialTransactionValidationError("Lançamentos cancelados não podem ser liquidados")

    transaction.status = FinancialTransactionStatus.settled
    transaction.settled_at = settle_in.settled_at or datetime.now(UTC)
    if "payment_method" in settle_in.model_fields_set:
        transaction.payment_method = settle_in.payment_method
    transaction.canceled_at = None
    transaction.updated_by = user.id
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def cancel_financial_transaction(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
) -> FinancialTransaction:
    if transaction.deleted_at is not None:
        raise FinancialTransactionValidationError("Lancamentos excluidos nao podem ser cancelados")
    transaction.status = FinancialTransactionStatus.canceled
    transaction.canceled_at = datetime.now(UTC)
    transaction.updated_by = user.id
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def soft_delete_financial_transaction(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
) -> FinancialTransaction:
    if transaction.deleted_at is None:
        transaction.deleted_at = datetime.now(UTC)
        transaction.updated_by = user.id
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
    return transaction


def _validate_transaction_links(
    db: Session,
    user: User,
    transaction_type: FinancialTransactionType,
    category_id: uuid.UUID | None,
    contact_id: uuid.UUID | None,
    employee_id: uuid.UUID | None,
) -> None:
    if category_id is not None:
        category = db.scalar(
            select(FinancialCategory).where(
                FinancialCategory.id == category_id,
                FinancialCategory.company_id == user.company_id,
                FinancialCategory.is_active.is_(True),
            )
        )
        if category is None:
            raise FinancialTransactionValidationError(
                "Categoria não encontrada para a empresa autenticada"
            )
        if not _is_category_type_compatible(category.type, transaction_type):
            raise FinancialTransactionValidationError(
                "O tipo da categoria não é compatível com o tipo do lançamento"
            )

    if contact_id is not None:
        contact = db.scalar(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.company_id == user.company_id,
                Contact.is_active.is_(True),
            )
        )
        if contact is None:
            raise FinancialTransactionValidationError(
                "Contato não encontrado para a empresa autenticada"
            )
        if not _is_contact_type_compatible(contact.type, transaction_type):
            raise FinancialTransactionValidationError(
                "O tipo do contato não é compatível com o tipo do lançamento"
            )

    if employee_id is not None:
        employee = db.scalar(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.company_id == user.company_id,
            )
        )
        if employee is None:
            raise FinancialTransactionValidationError(
                "Funcionario nao encontrado para a empresa autenticada"
            )


def _is_category_type_compatible(
    category_type: FinancialCategoryType,
    transaction_type: FinancialTransactionType,
) -> bool:
    return category_type == FinancialCategoryType.both or category_type.value == transaction_type.value


def _is_contact_type_compatible(
    contact_type: ContactType,
    transaction_type: FinancialTransactionType,
) -> bool:
    if contact_type == ContactType.both:
        return True
    if transaction_type == FinancialTransactionType.income:
        return contact_type == ContactType.customer
    return contact_type == ContactType.supplier


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
