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
from app.schemas.product_output import ProductOutputCreate

PRODUCT_OUTPUT_SOURCE = "product_output"


class ProductOutputValidationError(ValueError):
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
