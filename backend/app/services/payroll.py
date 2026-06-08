from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee import EmployeeStatus
from app.models.financial_category import FinancialCategory
from app.models.financial_category import FinancialCategoryType
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User

SALARY_CATEGORY_NAME = "Salarios"
SALARY_SOURCE = "employee_salary"


def generate_monthly_salary_expenses(
    db: Session,
    user: User,
    reference_month: date,
    due_date: date | None = None,
) -> tuple[list[FinancialTransaction], int]:
    month_start = reference_month.replace(day=1)
    month_end = date(
        month_start.year,
        month_start.month,
        monthrange(month_start.year, month_start.month)[1],
    )
    salary_due_date = due_date or month_end
    category = _get_or_create_salary_category(db, user)
    employees = _list_employees_for_month(db, user, month_start, month_end)
    created_transactions: list[FinancialTransaction] = []
    skipped_count = 0

    for employee in employees:
        existing = db.scalar(
            select(FinancialTransaction).where(
                FinancialTransaction.company_id == user.company_id,
                FinancialTransaction.employee_id == employee.id,
                FinancialTransaction.reference_month == month_start,
                FinancialTransaction.source == SALARY_SOURCE,
            )
        )
        if existing is not None:
            skipped_count += 1
            continue

        transaction = FinancialTransaction(
            company_id=user.company_id,
            category_id=category.id,
            employee_id=employee.id,
            description=f"Salario - {employee.name} - {month_start:%m/%Y}",
            amount=employee.salary_amount,
            type=FinancialTransactionType.expense,
            status=FinancialTransactionStatus.pending,
            competence_date=month_start,
            reference_month=month_start,
            due_date=salary_due_date,
            notes="Despesa salarial gerada manualmente a partir do cadastro de funcionario.",
            source=SALARY_SOURCE,
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(transaction)
        created_transactions.append(transaction)

    db.commit()
    for transaction in created_transactions:
        db.refresh(transaction)
    return created_transactions, skipped_count


def _list_employees_for_month(
    db: Session,
    user: User,
    month_start: date,
    month_end: date,
) -> list[Employee]:
    return list(
        db.scalars(
            select(Employee)
            .where(
                Employee.company_id == user.company_id,
                Employee.status == EmployeeStatus.active,
                Employee.contract_start_date <= month_end,
            )
            .where(
                (Employee.contract_end_date.is_(None))
                | (Employee.contract_end_date >= month_start)
            )
            .order_by(Employee.name)
        )
    )


def _get_or_create_salary_category(db: Session, user: User) -> FinancialCategory:
    category = db.scalar(
        select(FinancialCategory).where(
            FinancialCategory.company_id == user.company_id,
            FinancialCategory.name == SALARY_CATEGORY_NAME,
            FinancialCategory.type == FinancialCategoryType.expense,
            FinancialCategory.is_active.is_(True),
        )
    )
    if category is not None:
        return category

    category = FinancialCategory(
        company_id=user.company_id,
        name=SALARY_CATEGORY_NAME,
        type=FinancialCategoryType.expense,
        is_active=True,
    )
    db.add(category)
    db.flush()
    return category
