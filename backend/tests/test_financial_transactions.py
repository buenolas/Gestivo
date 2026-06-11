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
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.models.user import UserRole
from app.services.financial_transaction import list_financial_transactions
from app.services.financial_transaction import soft_delete_financial_transaction


class FakeDb:
    def __init__(self, transactions: list[FinancialTransaction] | None = None) -> None:
        self.transactions = transactions or []
        self.added = []
        self.commits = 0
        self.statements = []

    def scalars(self, statement):
        self.statements.append(statement)
        return self.transactions

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


def make_employee_user(company: Company) -> User:
    user = make_user(company)
    user.role = UserRole.user
    return user


def make_transaction(
    company: Company,
    deleted_at: datetime | None = None,
) -> FinancialTransaction:
    user_id = uuid4()
    return FinancialTransaction(
        id=uuid4(),
        company_id=company.id,
        description="Lancamento teste",
        amount=Decimal("100.00"),
        type=FinancialTransactionType.income,
        status=FinancialTransactionStatus.pending,
        competence_date=date(2026, 5, 10),
        deleted_at=deleted_at,
        created_by=user_id,
        updated_by=user_id,
    )


def test_list_financial_transactions_ignores_soft_deleted_items() -> None:
    company = make_company()
    user = make_user(company)
    visible = make_transaction(company)
    deleted = make_transaction(company, deleted_at=datetime.now(UTC))
    db = FakeDb([visible, deleted])

    transactions = list_financial_transactions(db, user)

    assert transactions == [visible]


def test_employee_transaction_list_is_filtered_by_creator() -> None:
    company = make_company()
    user = make_employee_user(company)
    db = FakeDb()

    list_financial_transactions(db, user)

    sql = str(db.statements[0])
    assert "financial_transactions.company_id" in sql
    assert "financial_transactions.created_by" in sql


def test_soft_delete_marks_deleted_at_and_preserves_record() -> None:
    company = make_company()
    user = make_user(company)
    transaction = make_transaction(company)
    db = FakeDb()

    deleted = soft_delete_financial_transaction(db, user, transaction)

    assert deleted is transaction
    assert deleted.deleted_at is not None
    assert deleted.updated_by == user.id
    assert db.added == [transaction]
    assert db.commits == 1
