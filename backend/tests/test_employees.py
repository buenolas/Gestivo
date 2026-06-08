from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
import os
from uuid import uuid4

TEST_DATABASE_URL = "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

import pytest

from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.employee import Employee
from app.models.employee import EmployeeStatus
from app.models.financial_category import FinancialCategory
from app.models.financial_category import FinancialCategoryType
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.models.user import UserRole
from app.schemas.employee import EmployeeCreate
from app.schemas.employee import EmployeeUpdate
from app.services.employees import EmployeeValidationError
from app.services.employees import create_employee
from app.services.employees import update_employee
from app.services.payroll import SALARY_SOURCE
from app.services.payroll import generate_monthly_salary_expenses


class FakeDb:
    def __init__(
        self,
        scalar_values: list[object] | None = None,
        scalars_values: list[list[object]] | None = None,
    ) -> None:
        self.scalar_values = scalar_values or []
        self.scalars_values = scalars_values or []
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.refreshed = []

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1

    def refresh(self, instance):
        self.refreshed.append(instance)

    def scalar(self, statement):
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None

    def scalars(self, statement):
        if self.scalars_values:
            return self.scalars_values.pop(0)
        return []


def make_company() -> Company:
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=SubscriptionStatus.active,
        trial_ends_at=datetime.now(UTC),
        subscription_valid_until=datetime.now(UTC),
        is_platform_company=False,
    )


def make_user(company: Company) -> User:
    return User(
        id=uuid4(),
        company_id=company.id,
        name="Usuario Teste",
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        role=UserRole.company_admin,
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )


def make_employee(company: Company) -> Employee:
    return Employee(
        id=uuid4(),
        company_id=company.id,
        name="Maria Silva",
        position="Atendimento",
        salary_amount=Decimal("2500.00"),
        contract_start_date=date(2026, 1, 10),
        contract_end_date=None,
        status=EmployeeStatus.active,
    )


def test_create_employee_uses_authenticated_user_company() -> None:
    company = make_company()
    user = make_user(company)
    db = FakeDb()

    employee = create_employee(
        db,
        user,
        EmployeeCreate(
            name=" Maria Silva ",
            position=" Atendimento ",
            salary_amount=Decimal("2500.00"),
            contract_start_date=date(2026, 1, 10),
        ),
    )

    assert employee.company_id == user.company_id
    assert employee.name == "Maria Silva"
    assert employee.position == "Atendimento"
    assert employee.salary_amount == Decimal("2500.00")
    assert db.commits == 1


def test_update_employee_rejects_contract_end_before_start() -> None:
    company = make_company()
    employee = make_employee(company)
    db = FakeDb()

    with pytest.raises(EmployeeValidationError):
        update_employee(
            db,
            employee,
            EmployeeUpdate(contract_end_date=date(2025, 12, 31)),
        )


def test_generate_salary_expense_creates_pending_payable_transaction() -> None:
    company = make_company()
    user = make_user(company)
    employee = make_employee(company)
    category = FinancialCategory(
        id=uuid4(),
        company_id=company.id,
        name="Salarios",
        type=FinancialCategoryType.expense,
        is_active=True,
    )
    db = FakeDb(
        scalar_values=[category, None],
        scalars_values=[[employee]],
    )

    transactions, skipped_count = generate_monthly_salary_expenses(
        db,
        user,
        reference_month=date(2026, 5, 15),
    )

    assert skipped_count == 0
    assert len(transactions) == 1
    assert transactions[0].company_id == user.company_id
    assert transactions[0].employee_id == employee.id
    assert transactions[0].category_id == category.id
    assert transactions[0].amount == Decimal("2500.00")
    assert transactions[0].type == FinancialTransactionType.expense
    assert transactions[0].status == FinancialTransactionStatus.pending
    assert transactions[0].source == SALARY_SOURCE
    assert transactions[0].reference_month == date(2026, 5, 1)
    assert transactions[0].due_date == date(2026, 5, 31)
    assert db.commits == 1


def test_generate_salary_expense_skips_duplicate_employee_month() -> None:
    company = make_company()
    user = make_user(company)
    employee = make_employee(company)
    category = FinancialCategory(
        id=uuid4(),
        company_id=company.id,
        name="Salarios",
        type=FinancialCategoryType.expense,
        is_active=True,
    )
    existing = FinancialTransaction(
        id=uuid4(),
        company_id=company.id,
        employee_id=employee.id,
        description="Salario existente",
        amount=Decimal("2500.00"),
        type=FinancialTransactionType.expense,
        status=FinancialTransactionStatus.pending,
        competence_date=date(2026, 5, 1),
        reference_month=date(2026, 5, 1),
        due_date=date(2026, 5, 31),
        source=SALARY_SOURCE,
        created_by=user.id,
        updated_by=user.id,
    )
    db = FakeDb(
        scalar_values=[category, existing],
        scalars_values=[[employee]],
    )

    transactions, skipped_count = generate_monthly_salary_expenses(
        db,
        user,
        reference_month=date(2026, 5, 1),
    )

    assert transactions == []
    assert skipped_count == 1
    assert db.commits == 1
