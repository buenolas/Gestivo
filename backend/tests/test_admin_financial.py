from datetime import UTC
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import os
from uuid import uuid4

TEST_DATABASE_URL = "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

import pytest
from fastapi import HTTPException

from app.api.deps import require_platform_admin
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.manual_payment import ManualPayment
from app.models.manual_payment import PaymentStatus
from app.models.plan import BillingCycle
from app.models.plan import Plan
from app.models.usage_event import UsageEvent
from app.models.usage_event import UsageEventType
from app.models.user import User
from app.models.user import UserRole
from app.services.admin_financial import get_admin_financial_dashboard
from app.services.admin_financial import _mrr_at
from app.services.admin_financial import list_admin_financial_rows
from app.services.admin_financial import monthly_equivalent


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeDb:
    def __init__(self, companies, payments, events):
        self.results = [companies, payments, events]

    def scalars(self, statement):
        return ScalarResult(self.results.pop(0))


def make_plan(slug: str, price: Decimal, duration: int) -> Plan:
    return Plan(
        id=uuid4(),
        name={"monthly": "Mensal", "semiannual": "Semestral", "annual": "Anual"}[slug],
        slug=slug,
        billing_cycle=BillingCycle(slug),
        duration_months=duration,
        price=price,
        is_active=True,
    )


def make_company(
    plan: Plan,
    *,
    status: SubscriptionStatus = SubscriptionStatus.active,
    valid_until: datetime | None = None,
) -> Company:
    company = Company(
        id=uuid4(),
        name=f"Empresa {uuid4()}",
        subscription_status=status,
        trial_ends_at=datetime.now(UTC) + timedelta(days=30),
        subscription_valid_until=valid_until or datetime.now(UTC) + timedelta(days=10),
        current_plan_id=plan.id,
        subscription_price=plan.price,
        subscription_duration_months=plan.duration_months,
        is_platform_company=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    company.current_plan = plan
    return company


def make_admin(company: Company, role: UserRole = UserRole.platform_admin) -> User:
    return User(
        id=uuid4(),
        company_id=company.id,
        name="Admin",
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        role=role,
        is_active=True,
    )


def make_payment(company: Company, plan: Plan, amount: Decimal, paid_at: datetime) -> ManualPayment:
    admin = make_admin(company)
    payment = ManualPayment(
        id=uuid4(),
        company_id=company.id,
        plan_id=plan.id,
        plan_slug=plan.slug,
        billing_cycle=plan.billing_cycle,
        duration_months=plan.duration_months,
        price_at_payment=amount,
        amount=amount,
        status=PaymentStatus.paid,
        payment_method="manual",
        paid_at=paid_at,
        due_date=paid_at,
        period_start=paid_at,
        period_end=paid_at + timedelta(days=365),
        created_by=admin.id,
        created_at=paid_at,
        updated_at=paid_at,
    )
    payment.company = company
    payment.plan = plan
    payment.creator = admin
    return payment


def test_monthly_equivalent_converts_semiannual_and_annual_plans() -> None:
    assert monthly_equivalent(Decimal("300.00"), 6) == Decimal("50.00")
    assert monthly_equivalent(Decimal("600.00"), 12) == Decimal("50.00")


def test_dashboard_calculates_mrr_arr_ticket_and_received_revenue() -> None:
    now = datetime.now(UTC)
    monthly = make_plan("monthly", Decimal("50.00"), 1)
    annual = make_plan("annual", Decimal("600.00"), 12)
    companies = [make_company(monthly), make_company(annual)]
    payments = [
        make_payment(companies[0], monthly, Decimal("50.00"), now),
        make_payment(companies[1], annual, Decimal("600.00"), now),
    ]

    result = get_admin_financial_dashboard(FakeDb(companies, payments, []))

    assert result.metrics.mrr == Decimal("100.00")
    assert result.metrics.arr == Decimal("1200.00")
    assert result.metrics.average_ticket == Decimal("50.00")
    assert result.metrics.received_current_month == Decimal("650.00")
    assert result.metrics.paying_customers == 2


def test_dashboard_calculates_pending_overdue_churn_and_delinquency() -> None:
    now = datetime.now(UTC)
    plan = make_plan("monthly", Decimal("100.00"), 1)
    active = make_company(plan, valid_until=now + timedelta(days=5))
    overdue = make_company(
        plan,
        status=SubscriptionStatus.pending_payment,
        valid_until=now - timedelta(days=2),
    )
    canceled = make_company(plan, status=SubscriptionStatus.canceled)
    cancel_event = UsageEvent(
        company_id=canceled.id,
        event_type=UsageEventType.subscription_canceled,
        event_metadata={"monthly_revenue": "100.00"},
        created_at=now,
    )
    payments = [make_payment(active, plan, Decimal("100.00"), now - timedelta(days=25))]

    result = get_admin_financial_dashboard(
        FakeDb([active, overdue, canceled], payments, [cancel_event])
    )

    assert result.metrics.pending_revenue == Decimal("100.00")
    assert result.metrics.overdue_revenue == Decimal("100.00")
    assert result.metrics.lost_cancellations == Decimal("100.00")
    assert result.metrics.monthly_financial_churn_rate == Decimal("100.00")
    assert result.metrics.delinquency_rate == Decimal("100.00")


def test_historical_mrr_restores_reactivated_subscription() -> None:
    now = datetime.now(UTC)
    plan = make_plan("monthly", Decimal("100.00"), 1)
    company = make_company(plan)
    payment = make_payment(company, plan, Decimal("100.00"), now - timedelta(days=10))
    canceled = UsageEvent(
        company_id=company.id,
        event_type=UsageEventType.subscription_canceled,
        event_metadata={"monthly_revenue": "100.00"},
        created_at=now - timedelta(days=5),
    )
    reactivated = UsageEvent(
        company_id=company.id,
        event_type=UsageEventType.subscription_reactivated,
        created_at=now - timedelta(days=2),
    )

    assert _mrr_at([payment], [canceled, reactivated], now) == Decimal("100.00")


def test_financial_table_filters_and_paginates() -> None:
    plan = make_plan("monthly", Decimal("80.00"), 1)
    companies = [
        make_company(plan),
        make_company(plan, status=SubscriptionStatus.pending_payment, valid_until=datetime.now(UTC) - timedelta(days=1)),
    ]
    companies[0].name = "Alfa"
    companies[1].name = "Beta"
    payment = make_payment(companies[0], plan, Decimal("80.00"), datetime.now(UTC))

    result = list_admin_financial_rows(
        FakeDb(companies, [payment], []),
        search="beta",
        payment_status="overdue",
        page=1,
        page_size=1,
    )

    assert result.total == 1
    assert result.pages == 1
    assert result.items[0].company_name == "Beta"
    assert result.items[0].pending_amount == Decimal("80.00")


def test_common_user_cannot_access_platform_financial_dashboard() -> None:
    plan = make_plan("monthly", Decimal("50.00"), 1)
    company = make_company(plan)
    user = make_admin(company, role=UserRole.company_admin)

    with pytest.raises(HTTPException) as exc_info:
        require_platform_admin(current_user=user)

    assert exc_info.value.status_code == 403
