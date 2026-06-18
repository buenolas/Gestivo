from calendar import monthrange
from decimal import Decimal
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.models.user import UserRole
from app.schemas.product_output import ProductOutputCreate
from app.schemas.product_output import ProductOutputUpdate

PRODUCT_OUTPUT_SOURCE = "product_output"


class ProductOutputValidationError(ValueError):
    pass


class ProductOutputPermissionError(PermissionError):
    pass


def list_product_outputs(
    db: Session,
    user: User,
    employee_id: UUID | None = None,
) -> list[FinancialTransaction]:
    query = (
        select(FinancialTransaction)
        .where(
            FinancialTransaction.company_id == user.company_id,
            FinancialTransaction.source == PRODUCT_OUTPUT_SOURCE,
            FinancialTransaction.deleted_at.is_(None),
        )
        .options(selectinload(FinancialTransaction.employee))
        .order_by(
            FinancialTransaction.competence_date.desc(),
            FinancialTransaction.created_at.desc(),
        )
    )
    if employee_id is not None:
        query = query.where(FinancialTransaction.employee_id == employee_id)
    return list(db.scalars(query))


def create_product_output(
    db: Session,
    user: User,
    output_in: ProductOutputCreate,
) -> FinancialTransaction:
    employee = db.scalar(
        select(Employee).where(
            Employee.id == output_in.employee_id,
            Employee.company_id == user.company_id,
        )
    )
    if employee is None:
        raise ProductOutputValidationError("Funcionario nao encontrado")

    quantity = output_in.quantity
    unit_price = output_in.unit_price
    amount = _money(unit_price * quantity)
    unit = output_in.unit.strip() or "un"
    product_name = output_in.product_name.strip()
    transaction = FinancialTransaction(
        company_id=user.company_id,
        employee_id=employee.id,
        description=f"Saida de produto: {product_name}",
        amount=amount,
        type=FinancialTransactionType.income,
        status=FinancialTransactionStatus.pending,
        competence_date=output_in.competence_date,
        due_date=_month_end(output_in.competence_date),
        notes=_strip_optional_text(output_in.notes),
        product_name=product_name,
        product_unit_price=unit_price,
        product_quantity=quantity,
        product_unit=unit,
        source=PRODUCT_OUTPUT_SOURCE,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_product_output(
    db: Session,
    user: User,
    transaction_id: UUID,
) -> FinancialTransaction | None:
    return db.scalar(
        select(FinancialTransaction).where(
            FinancialTransaction.id == transaction_id,
            FinancialTransaction.company_id == user.company_id,
            FinancialTransaction.source == PRODUCT_OUTPUT_SOURCE,
            FinancialTransaction.deleted_at.is_(None),
        )
    )


def update_product_output(
    db: Session,
    user: User,
    transaction: FinancialTransaction,
    output_in: ProductOutputUpdate,
) -> FinancialTransaction:
    _ensure_can_update_product_output(user, transaction)

    next_employee_id = (
        output_in.employee_id
        if "employee_id" in output_in.model_fields_set
        else transaction.employee_id
    )
    if next_employee_id is None:
        raise ProductOutputValidationError("Funcionario e obrigatorio")
    employee = _get_employee_or_raise(db, user, next_employee_id)

    next_unit_price = (
        output_in.unit_price
        if output_in.unit_price is not None
        else transaction.product_unit_price
    )
    next_quantity = (
        output_in.quantity
        if output_in.quantity is not None
        else transaction.product_quantity
    )
    if next_unit_price is None or next_quantity is None:
        raise ProductOutputValidationError("Valor unitario e quantidade sao obrigatorios")

    if output_in.product_name is not None:
        product_name = output_in.product_name.strip()
        transaction.product_name = product_name
        transaction.description = f"Saida de produto: {product_name}"
    if "employee_id" in output_in.model_fields_set:
        transaction.employee_id = employee.id
    if output_in.unit_price is not None:
        transaction.product_unit_price = output_in.unit_price
    if output_in.quantity is not None:
        transaction.product_quantity = output_in.quantity
    if "unit" in output_in.model_fields_set:
        transaction.product_unit = _strip_optional_text(output_in.unit) or "un"
    if output_in.competence_date is not None:
        transaction.competence_date = output_in.competence_date
        transaction.due_date = _month_end(output_in.competence_date)
    if "notes" in output_in.model_fields_set:
        transaction.notes = _strip_optional_text(output_in.notes)

    transaction.amount = _money(next_unit_price * next_quantity)
    transaction.updated_by = user.id
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def _get_employee_or_raise(db: Session, user: User, employee_id: UUID) -> Employee:
    employee = db.scalar(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.company_id == user.company_id,
        )
    )
    if employee is None:
        raise ProductOutputValidationError("Funcionario nao encontrado")
    return employee


def _ensure_can_update_product_output(user: User, transaction: FinancialTransaction) -> None:
    if transaction.company_id != user.company_id:
        raise ProductOutputPermissionError("Saida de produto nao encontrada")
    if transaction.source != PRODUCT_OUTPUT_SOURCE:
        raise ProductOutputValidationError("Este lancamento nao pertence a saida de produtos")
    if transaction.deleted_at is not None:
        raise ProductOutputValidationError("Saidas excluidas nao podem ser editadas")
    if transaction.status == FinancialTransactionStatus.canceled:
        raise ProductOutputValidationError("Saidas canceladas nao podem ser editadas")
    if user.role == UserRole.user and transaction.created_by != user.id:
        raise ProductOutputPermissionError("Voce so pode editar saidas criadas por voce")


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"))


def _month_end(value: date) -> date:
    last_day = monthrange(value.year, value.month)[1]
    return date(value.year, value.month, last_day)


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
