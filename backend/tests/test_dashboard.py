from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
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
from app.services.dashboard import get_financial_dashboard

DEFAULT_DUE_DATE = object()


class FakeDb:
    def __init__(self, company: Company, transactions: list[FinancialTransaction]) -> None:
        self.company = company
        self.transactions = transactions

    def get(self, model, object_id):
        if model is Company and self.company.id == object_id:
            return self.company
        return None

    def scalars(self, statement):
        return self.transactions


def make_company(
    opening_balance: Decimal = Decimal("0.00"),
    opening_balance_date: date | None = None,
) -> Company:
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=SubscriptionStatus.active,
        trial_ends_at=datetime.now(UTC),
        subscription_valid_until=datetime.now(UTC),
        opening_balance=opening_balance,
        opening_balance_date=opening_balance_date,
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


def make_transaction(
    company: Company,
    amount: Decimal,
    transaction_type: FinancialTransactionType,
    status: FinancialTransactionStatus,
    settled_at: datetime | None,
    due_date: date | None | object = DEFAULT_DUE_DATE,
    deleted_at: datetime | None = None,
) -> FinancialTransaction:
    user_id = uuid4()
    return FinancialTransaction(
        id=uuid4(),
        company_id=company.id,
        description="Lancamento teste",
        amount=amount,
        type=transaction_type,
        status=status,
        competence_date=date.today(),
        due_date=date.today() if due_date is DEFAULT_DUE_DATE else due_date,
        settled_at=settled_at,
        deleted_at=deleted_at,
        created_by=user_id,
        updated_by=user_id,
    )


def test_current_balance_uses_opening_balance_and_only_settled_transactions() -> None:
    company = make_company(opening_balance=Decimal("1000.00"))
    user = make_user(company)
    db = FakeDb(
        company,
        [
            make_transaction(
                company,
                Decimal("300.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.settled,
                datetime(2026, 5, 10, tzinfo=UTC),
            ),
            make_transaction(
                company,
                Decimal("120.00"),
                FinancialTransactionType.expense,
                FinancialTransactionStatus.settled,
                datetime(2026, 5, 11, tzinfo=UTC),
            ),
            make_transaction(
                company,
                Decimal("999.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.pending,
                None,
            ),
            make_transaction(
                company,
                Decimal("999.00"),
                FinancialTransactionType.expense,
                FinancialTransactionStatus.canceled,
                datetime(2026, 5, 12, tzinfo=UTC),
            ),
            make_transaction(
                company,
                Decimal("999.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.settled,
                datetime(2026, 5, 12, tzinfo=UTC),
                deleted_at=datetime(2026, 5, 13, tzinfo=UTC),
            ),
        ],
    )

    dashboard = get_financial_dashboard(db, user)

    assert dashboard.current_balance == Decimal("1180.00")


def test_current_balance_ignores_settled_transactions_before_opening_balance_date() -> None:
    company = make_company(
        opening_balance=Decimal("500.00"),
        opening_balance_date=date(2026, 5, 10),
    )
    user = make_user(company)
    db = FakeDb(
        company,
        [
            make_transaction(
                company,
                Decimal("200.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.settled,
                datetime(2026, 5, 9, 23, 59, tzinfo=UTC),
            ),
            make_transaction(
                company,
                Decimal("100.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.settled,
                datetime(2026, 5, 10, tzinfo=UTC),
            ),
            make_transaction(
                company,
                Decimal("40.00"),
                FinancialTransactionType.expense,
                FinancialTransactionStatus.settled,
                datetime(2026, 5, 11, tzinfo=UTC),
            ),
        ],
    )

    dashboard = get_financial_dashboard(db, user)

    assert dashboard.current_balance == Decimal("560.00")


def test_dashboard_due_alerts_include_pending_transactions_due_within_five_days() -> None:
    today = date.today()
    company = make_company()
    user = make_user(company)
    db = FakeDb(
        company,
        [
            make_transaction(
                company,
                Decimal("100.00"),
                FinancialTransactionType.expense,
                FinancialTransactionStatus.pending,
                None,
                due_date=today,
            ),
            make_transaction(
                company,
                Decimal("200.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.pending,
                None,
                due_date=today + timedelta(days=2),
            ),
            make_transaction(
                company,
                Decimal("300.00"),
                FinancialTransactionType.expense,
                FinancialTransactionStatus.pending,
                None,
                due_date=today + timedelta(days=5),
            ),
            make_transaction(
                company,
                Decimal("400.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.pending,
                None,
                due_date=today + timedelta(days=6),
            ),
        ],
    )

    dashboard = get_financial_dashboard(db, user)

    assert [alert.amount for alert in dashboard.due_alerts] == [
        Decimal("100.00"),
        Decimal("200.00"),
        Decimal("300.00"),
    ]
    assert [alert.severity for alert in dashboard.due_alerts] == ["red", "orange", "yellow"]
    assert dashboard.due_alerts[0].kind == FinancialTransactionType.expense
    assert dashboard.due_alerts[1].kind == FinancialTransactionType.income


def test_dashboard_due_alerts_ignore_settled_canceled_deleted_and_without_due_date() -> None:
    today = date.today()
    company = make_company()
    user = make_user(company)
    db = FakeDb(
        company,
        [
            make_transaction(
                company,
                Decimal("100.00"),
                FinancialTransactionType.expense,
                FinancialTransactionStatus.settled,
                datetime.now(UTC),
                due_date=today,
            ),
            make_transaction(
                company,
                Decimal("200.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.canceled,
                None,
                due_date=today,
            ),
            make_transaction(
                company,
                Decimal("300.00"),
                FinancialTransactionType.expense,
                FinancialTransactionStatus.pending,
                None,
                due_date=today,
                deleted_at=datetime.now(UTC),
            ),
            make_transaction(
                company,
                Decimal("400.00"),
                FinancialTransactionType.income,
                FinancialTransactionStatus.pending,
                None,
                due_date=None,
            ),
        ],
    )

    dashboard = get_financial_dashboard(db, user)

    assert dashboard.due_alerts == []
