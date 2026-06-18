from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
import os
from uuid import uuid4

TEST_DATABASE_URL = "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.employee import Employee
from app.models.employee import EmployeeStatus
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.models.user import UserRole
from app.schemas.cash_flow import CashFlowEntryCreate
from app.schemas.product_output import ProductOutputCreate
from app.services.cash_flow import CASH_FLOW_SOURCE
from app.services.cash_flow import create_cash_flow_entry
from app.services.product_output import PRODUCT_OUTPUT_SOURCE
from app.services.product_output import create_product_output


class FakeDb:
    def __init__(self, scalar_result=None) -> None:
        self.scalar_result = scalar_result
        self.added = []
        self.commits = 0

    def scalar(self, statement):
        return self.scalar_result

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def refresh(self, instance):
        pass


def make_company() -> Company:
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=SubscriptionStatus.active,
        trial_ends_at=datetime.now(UTC),
        subscription_valid_until=datetime.now(UTC),
        opening_balance=Decimal("0.00"),
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
        name="Funcionario Teste",
        salary_amount=Decimal("2000.00"),
        contract_start_date=date(2026, 1, 1),
        status=EmployeeStatus.active,
    )


def test_cash_flow_entry_is_settled_and_impacts_cash_immediately() -> None:
    company = make_company()
    user = make_user(company)
    employee = make_employee(company)
    db = FakeDb(scalar_result=employee)

    transaction = create_cash_flow_entry(
        db,
        user,
        CashFlowEntryCreate(
            description="Retirada para compra",
            amount=Decimal("50.00"),
            type=FinancialTransactionType.expense,
            competence_date=date(2026, 6, 17),
            employee_id=employee.id,
        ),
    )

    assert transaction.source == CASH_FLOW_SOURCE
    assert transaction.status == FinancialTransactionStatus.settled
    assert transaction.settled_at is not None
    assert transaction.due_date is None
    assert transaction.amount == Decimal("50.00")
    assert db.commits == 1


def test_product_output_creates_pending_receivable_with_calculated_total() -> None:
    company = make_company()
    user = make_user(company)
    employee = make_employee(company)
    db = FakeDb(scalar_result=employee)

    transaction = create_product_output(
        db,
        user,
        ProductOutputCreate(
            employee_id=employee.id,
            product_name="Carne",
            unit_price=Decimal("100.00"),
            quantity=Decimal("1.5"),
            unit="kg",
            competence_date=date(2026, 6, 17),
        ),
    )

    assert transaction.source == PRODUCT_OUTPUT_SOURCE
    assert transaction.type == FinancialTransactionType.income
    assert transaction.status == FinancialTransactionStatus.pending
    assert transaction.amount == Decimal("150.00")
    assert transaction.product_unit_price == Decimal("100.00")
    assert transaction.product_quantity == Decimal("1.5")
    assert transaction.product_unit == "kg"
    assert transaction.competence_date == date(2026, 6, 17)
    assert transaction.due_date == date(2026, 6, 30)


def test_product_output_due_date_uses_month_end_for_short_and_long_months() -> None:
    company = make_company()
    user = make_user(company)
    employee = make_employee(company)
    db = FakeDb(scalar_result=employee)

    cases = [
        (date(2026, 4, 10), date(2026, 4, 30)),
        (date(2026, 5, 10), date(2026, 5, 31)),
        (date(2026, 2, 10), date(2026, 2, 28)),
        (date(2028, 2, 10), date(2028, 2, 29)),
    ]

    for competence_date, expected_due_date in cases:
        transaction = create_product_output(
            db,
            user,
            ProductOutputCreate(
                employee_id=employee.id,
                product_name="Produto",
                unit_price=Decimal("10.00"),
                quantity=Decimal("1"),
                unit="un",
                competence_date=competence_date,
            ),
        )

        assert transaction.competence_date == competence_date
        assert transaction.due_date == expected_due_date
