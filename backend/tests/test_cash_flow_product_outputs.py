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
from app.schemas.cash_flow import CashFlowEntryUpdate
from app.schemas.employee import EmployeeOptionResponse
from app.schemas.product_output import ProductOutputCreate
from app.schemas.product_output import ProductOutputUpdate
from app.services.cash_flow import CASH_FLOW_SOURCE
from app.services.cash_flow import CashFlowPermissionError
from app.services.cash_flow import CashFlowValidationError
from app.services.cash_flow import create_cash_flow_entry
from app.services.cash_flow import list_cash_flow_entries
from app.services.cash_flow import update_cash_flow_entry
from app.services.product_output import PRODUCT_OUTPUT_SOURCE
from app.services.product_output import ProductOutputPermissionError
from app.services.product_output import ProductOutputValidationError
from app.services.product_output import create_product_output
from app.services.product_output import list_product_outputs
from app.services.product_output import update_product_output


class FakeDb:
    def __init__(self, scalar_result=None, scalars_result=None) -> None:
        self.scalar_result = scalar_result
        self.scalars_result = scalars_result or []
        self.added = []
        self.commits = 0
        self.statements = []

    def scalar(self, statement):
        self.statements.append(statement)
        return self.scalar_result

    def scalars(self, statement):
        self.statements.append(statement)
        return self.scalars_result

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


def make_user(company: Company, role: UserRole = UserRole.company_admin) -> User:
    return User(
        id=uuid4(),
        company_id=company.id,
        name="Usuario Teste",
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        role=role,
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


def make_cash_flow_transaction(company: Company, user: User):
    transaction = create_cash_flow_entry(
        FakeDb(),
        user,
        CashFlowEntryCreate(
            description="Caixa teste",
            amount=Decimal("80.00"),
            type=FinancialTransactionType.income,
            competence_date=date(2026, 6, 17),
        ),
    )
    transaction.id = transaction.id or uuid4()
    transaction.created_at = transaction.created_at or datetime.now(UTC)
    transaction.updated_at = transaction.updated_at or datetime.now(UTC)
    return transaction


def make_product_output_transaction(company: Company, user: User, employee: Employee):
    transaction = create_product_output(
        FakeDb(scalar_result=employee),
        user,
        ProductOutputCreate(
            employee_id=employee.id,
            product_name="Produto",
            unit_price=Decimal("20.00"),
            quantity=Decimal("2"),
            unit="un",
            competence_date=date(2026, 6, 17),
        ),
    )
    transaction.id = transaction.id or uuid4()
    transaction.created_at = transaction.created_at or datetime.now(UTC)
    transaction.updated_at = transaction.updated_at or datetime.now(UTC)
    return transaction


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


def test_employee_user_lists_all_company_cash_flow_entries() -> None:
    company = make_company()
    user = make_user(company, role=UserRole.user)
    other_user = make_user(company, role=UserRole.user)
    own = make_cash_flow_transaction(company, user)
    other = make_cash_flow_transaction(company, other_user)
    db = FakeDb(scalars_result=[own, other])

    response = list_cash_flow_entries(db, user)

    assert [item.id for item in response.items] == [own.id, other.id]
    sql = str(db.statements[0])
    assert "financial_transactions.company_id" in sql
    assert "AND financial_transactions.created_by" not in sql


def test_employee_user_lists_all_company_product_outputs() -> None:
    company = make_company()
    employee = make_employee(company)
    user = make_user(company, role=UserRole.user)
    other_user = make_user(company, role=UserRole.user)
    own = make_product_output_transaction(company, user, employee)
    other = make_product_output_transaction(company, other_user, employee)
    db = FakeDb(scalars_result=[own, other])

    outputs = list_product_outputs(db, user)

    assert outputs == [own, other]
    sql = str(db.statements[0])
    assert "financial_transactions.company_id" in sql
    assert "AND financial_transactions.created_by" not in sql


def test_employee_user_updates_own_cash_flow_entry() -> None:
    company = make_company()
    user = make_user(company, role=UserRole.user)
    transaction = make_cash_flow_transaction(company, user)
    db = FakeDb()

    updated = update_cash_flow_entry(
        db,
        user,
        transaction,
        CashFlowEntryUpdate(description="Caixa corrigido", amount=Decimal("90.00")),
    )

    assert updated.description == "Caixa corrigido"
    assert updated.amount == Decimal("90.00")
    assert updated.updated_by == user.id
    assert db.commits == 1


def test_employee_user_cannot_update_other_user_cash_flow_entry() -> None:
    company = make_company()
    user = make_user(company, role=UserRole.user)
    other_user = make_user(company, role=UserRole.user)
    transaction = make_cash_flow_transaction(company, other_user)

    try:
        update_cash_flow_entry(FakeDb(), user, transaction, CashFlowEntryUpdate(description="Ok"))
    except CashFlowPermissionError:
        pass
    else:
        raise AssertionError("Expected CashFlowPermissionError")


def test_company_admin_updates_any_cash_flow_entry() -> None:
    company = make_company()
    admin = make_user(company)
    other_user = make_user(company, role=UserRole.user)
    transaction = make_cash_flow_transaction(company, other_user)
    db = FakeDb()

    updated = update_cash_flow_entry(
        db,
        admin,
        transaction,
        CashFlowEntryUpdate(description="Ajuste admin"),
    )

    assert updated.description == "Ajuste admin"
    assert updated.updated_by == admin.id


def test_cash_flow_update_rejects_wrong_source_canceled_or_deleted() -> None:
    company = make_company()
    user = make_user(company)
    transaction = make_cash_flow_transaction(company, user)
    transaction.source = PRODUCT_OUTPUT_SOURCE

    try:
        update_cash_flow_entry(FakeDb(), user, transaction, CashFlowEntryUpdate(description="Ok"))
    except CashFlowValidationError:
        pass
    else:
        raise AssertionError("Expected CashFlowValidationError")

    transaction.source = CASH_FLOW_SOURCE
    transaction.status = FinancialTransactionStatus.canceled
    try:
        update_cash_flow_entry(FakeDb(), user, transaction, CashFlowEntryUpdate(description="Ok"))
    except CashFlowValidationError:
        pass
    else:
        raise AssertionError("Expected CashFlowValidationError")

    transaction.status = FinancialTransactionStatus.settled
    transaction.deleted_at = datetime.now(UTC)
    try:
        update_cash_flow_entry(FakeDb(), user, transaction, CashFlowEntryUpdate(description="Ok"))
    except CashFlowValidationError:
        pass
    else:
        raise AssertionError("Expected CashFlowValidationError")


def test_employee_user_updates_own_product_output_and_recalculates_amount() -> None:
    company = make_company()
    employee = make_employee(company)
    user = make_user(company, role=UserRole.user)
    transaction = make_product_output_transaction(company, user, employee)
    db = FakeDb(scalar_result=employee)

    updated = update_product_output(
        db,
        user,
        transaction,
        ProductOutputUpdate(unit_price=Decimal("30.00"), quantity=Decimal("3")),
    )

    assert updated.amount == Decimal("90.00")
    assert updated.product_unit_price == Decimal("30.00")
    assert updated.product_quantity == Decimal("3")
    assert updated.updated_by == user.id


def test_employee_user_cannot_update_other_user_product_output() -> None:
    company = make_company()
    employee = make_employee(company)
    user = make_user(company, role=UserRole.user)
    other_user = make_user(company, role=UserRole.user)
    transaction = make_product_output_transaction(company, other_user, employee)

    try:
        update_product_output(
            FakeDb(scalar_result=employee),
            user,
            transaction,
            ProductOutputUpdate(product_name="Outro"),
        )
    except ProductOutputPermissionError:
        pass
    else:
        raise AssertionError("Expected ProductOutputPermissionError")


def test_company_admin_updates_any_product_output() -> None:
    company = make_company()
    employee = make_employee(company)
    admin = make_user(company)
    other_user = make_user(company, role=UserRole.user)
    transaction = make_product_output_transaction(company, other_user, employee)

    updated = update_product_output(
        FakeDb(scalar_result=employee),
        admin,
        transaction,
        ProductOutputUpdate(product_name="Produto ajustado"),
    )

    assert updated.product_name == "Produto ajustado"
    assert updated.description == "Saida de produto: Produto ajustado"
    assert updated.updated_by == admin.id


def test_product_output_update_rejects_wrong_source_canceled_or_deleted() -> None:
    company = make_company()
    employee = make_employee(company)
    user = make_user(company)
    transaction = make_product_output_transaction(company, user, employee)
    transaction.source = CASH_FLOW_SOURCE

    try:
        update_product_output(FakeDb(scalar_result=employee), user, transaction, ProductOutputUpdate(product_name="Ok"))
    except ProductOutputValidationError:
        pass
    else:
        raise AssertionError("Expected ProductOutputValidationError")

    transaction.source = PRODUCT_OUTPUT_SOURCE
    transaction.status = FinancialTransactionStatus.canceled
    try:
        update_product_output(FakeDb(scalar_result=employee), user, transaction, ProductOutputUpdate(product_name="Ok"))
    except ProductOutputValidationError:
        pass
    else:
        raise AssertionError("Expected ProductOutputValidationError")

    transaction.status = FinancialTransactionStatus.pending
    transaction.deleted_at = datetime.now(UTC)
    try:
        update_product_output(FakeDb(scalar_result=employee), user, transaction, ProductOutputUpdate(product_name="Ok"))
    except ProductOutputValidationError:
        pass
    else:
        raise AssertionError("Expected ProductOutputValidationError")


def test_employee_option_response_does_not_expose_salary() -> None:
    company = make_company()
    employee = make_employee(company)

    payload = EmployeeOptionResponse.model_validate(employee).model_dump()

    assert payload == {
        "id": employee.id,
        "name": employee.name,
        "status": EmployeeStatus.active,
    }
    assert "salary_amount" not in payload
