import uuid
from datetime import UTC
from datetime import date
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.contact import ContactType
from app.models.financial_category import FinancialCategory
from app.models.financial_category import FinancialCategoryType
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.schemas.financial_transaction import FinancialTransactionCreate
from app.schemas.financial_transaction import FinancialTransactionSettle
from app.schemas.financial_transaction import FinancialTransactionUpdate


class FinancialTransactionValidationError(ValueError):
    pass


def list_financial_transactions(
    db: Session,
    user: User,
    transaction_type: FinancialTransactionType | None = None,
    status: FinancialTransactionStatus | None = None,
    category_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
) -> list[FinancialTransaction]:
    query = select(FinancialTransaction).where(
        FinancialTransaction.company_id == user.company_id
    )

    if transaction_type is not None:
        query = query.where(FinancialTransaction.type == transaction_type)
    if status is not None:
        query = query.where(FinancialTransaction.status == status)
    if category_id is not None:
        query = query.where(FinancialTransaction.category_id == category_id)
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
    return list(db.scalars(query))


def get_financial_transaction(
    db: Session,
    user: User,
    transaction_id: uuid.UUID,
) -> FinancialTransaction | None:
    return db.scalar(
        select(FinancialTransaction).where(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.company_id == user.company_id,
        )
    )


def create_financial_transaction(
    db: Session,
    user: User,
    transaction_in: FinancialTransactionCreate,
) -> FinancialTransaction:
    _validate_category_and_contact(
        db=db,
        user=user,
        transaction_type=transaction_in.type,
        category_id=transaction_in.category_id,
        contact_id=transaction_in.contact_id,
    )
    transaction = FinancialTransaction(
        company_id=user.company_id,
        category_id=transaction_in.category_id,
        contact_id=transaction_in.contact_id,
        description=transaction_in.description.strip(),
        amount=transaction_in.amount,
        type=transaction_in.type,
        status=FinancialTransactionStatus.pending,
        competence_date=transaction_in.competence_date,
        due_date=transaction_in.due_date,
        notes=_strip_optional_text(transaction_in.notes),
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def update_financial_transaction(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
    transaction_in: FinancialTransactionUpdate,
) -> FinancialTransaction:
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
    _validate_category_and_contact(
        db=db,
        user=user,
        transaction_type=next_type,
        category_id=next_category_id,
        contact_id=next_contact_id,
    )

    if transaction_in.description is not None:
        transaction.description = transaction_in.description.strip()
    if transaction_in.amount is not None:
        transaction.amount = transaction_in.amount
    if transaction_in.type is not None:
        transaction.type = transaction_in.type
    if transaction_in.competence_date is not None:
        transaction.competence_date = transaction_in.competence_date
    if "due_date" in transaction_in.model_fields_set:
        transaction.due_date = transaction_in.due_date
    if "category_id" in transaction_in.model_fields_set:
        transaction.category_id = transaction_in.category_id
    if "contact_id" in transaction_in.model_fields_set:
        transaction.contact_id = transaction_in.contact_id
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
    if transaction.status == FinancialTransactionStatus.canceled:
        raise FinancialTransactionValidationError("Lançamentos cancelados não podem ser liquidados")

    transaction.status = FinancialTransactionStatus.settled
    transaction.settled_at = settle_in.settled_at or datetime.now(UTC)
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
    transaction.status = FinancialTransactionStatus.canceled
    transaction.canceled_at = datetime.now(UTC)
    transaction.updated_by = user.id
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def _validate_category_and_contact(
    db: Session,
    user: User,
    transaction_type: FinancialTransactionType,
    category_id: uuid.UUID | None,
    contact_id: uuid.UUID | None,
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
