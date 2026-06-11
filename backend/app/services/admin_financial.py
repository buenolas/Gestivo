from __future__ import annotations

from calendar import monthrange
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from math import ceil
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.manual_payment import ManualPayment
from app.models.manual_payment import PaymentStatus
from app.models.plan import Plan
from app.models.usage_event import UsageEvent
from app.models.usage_event import UsageEventType
from app.schemas.admin_financial import AdminFinancialBreakdown
from app.schemas.admin_financial import AdminFinancialDashboardResponse
from app.schemas.admin_financial import AdminFinancialMetrics
from app.schemas.admin_financial import AdminFinancialSeriesPoint
from app.schemas.admin_financial import AdminFinancialTableItem
from app.schemas.admin_financial import AdminFinancialTableResponse

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def monthly_equivalent(amount: Decimal | None, duration_months: int | None) -> Decimal:
    if amount is None:
        return ZERO
    return (amount / Decimal(duration_months or 1)).quantize(CENT)


def get_admin_financial_dashboard(
    db: Session,
    *,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> AdminFinancialDashboardResponse:
    now = datetime.now(UTC)
    month_start = _month_start(now)
    selected_start = _as_utc(period_start) if period_start else month_start
    selected_end = _as_utc(period_end) if period_end else _month_end(now)
    companies = _load_companies(db)
    payments = _load_payments(db)
    events = _load_financial_events(db)

    active_companies = [
        company
        for company in companies
        if company.subscription_status == SubscriptionStatus.active
        and company.subscription_valid_until is not None
        and _as_utc(company.subscription_valid_until) >= now
        and _company_price(company) > ZERO
    ]
    mrr = _money(sum((_company_mrr(company) for company in active_companies), ZERO))
    paying_customers = len(active_companies)

    received_month = _received_between(payments, month_start, now)
    received_30d = _received_between(payments, now - timedelta(days=30), now)
    forecast_month, renewals_month = _forecast_between(companies, month_start, _month_end(now))
    forecast_30d, renewals_30d = _forecast_between(companies, now, now + timedelta(days=30))
    _, renewals_7d = _forecast_between(companies, now, now + timedelta(days=7))
    pending = _status_revenue(companies, {SubscriptionStatus.pending_payment})
    overdue = _overdue_revenue(companies, now)
    lost_cancel = _lost_revenue(
        events,
        companies,
        UsageEventType.subscription_canceled,
        selected_start,
        selected_end,
    )
    lost_block = _lost_revenue(
        events,
        companies,
        UsageEventType.subscription_blocked,
        selected_start,
        selected_end,
    )
    mrr_at_start = _mrr_at(payments, events, selected_start)
    churn_rate = _percentage(lost_cancel, mrr_at_start)
    delinquency_rate = _percentage(overdue, forecast_month)

    metrics = AdminFinancialMetrics(
        mrr=mrr,
        arr=_money(mrr * Decimal(12)),
        received_current_month=received_month,
        received_last_30_days=received_30d,
        forecast_current_month=forecast_month,
        forecast_next_30_days=forecast_30d,
        pending_revenue=pending,
        overdue_revenue=overdue,
        lost_cancellations=lost_cancel,
        lost_delinquency=lost_block,
        average_ticket=_money(mrr / Decimal(paying_customers)) if paying_customers else ZERO,
        paying_customers=paying_customers,
        valid_subscriptions=len(active_companies),
        received_today=_received_between(payments, _day_start(now), now),
        received_current_week=_received_between(payments, _week_start(now), now),
        received_current_month_total=received_month,
        renewals_current_month=renewals_month,
        renewals_next_7_days=renewals_7d,
        renewals_next_30_days=renewals_30d,
        monthly_financial_churn_rate=churn_rate,
        delinquency_rate=delinquency_rate,
    )

    return AdminFinancialDashboardResponse(
        generated_at=now,
        period_start=selected_start,
        period_end=selected_end,
        metrics=metrics,
        monthly_series=_build_monthly_series(companies, payments, events, now),
        revenue_by_plan=_revenue_by_plan(payments, selected_start, selected_end),
        revenue_by_subscription_status=_revenue_by_status(companies),
    )


def list_admin_financial_rows(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    subscription_status: SubscriptionStatus | None = None,
    payment_status: str | None = None,
    plan_id: UUID | None = None,
    payment_method: str | None = None,
) -> AdminFinancialTableResponse:
    now = datetime.now(UTC)
    companies = _load_companies(db)
    payments = _load_payments(db)
    latest_by_company: dict[UUID, ManualPayment] = {}
    for payment in payments:
        latest_by_company.setdefault(payment.company_id, payment)

    items = [
        _table_item(company, latest_by_company.get(company.id), now)
        for company in companies
    ]
    if search and search.strip():
        term = search.strip().lower()
        items = [item for item in items if term in item.company_name.lower()]
    if subscription_status is not None:
        items = [item for item in items if item.subscription_status == subscription_status]
    if payment_status:
        items = [item for item in items if item.payment_status == payment_status]
    if plan_id is not None:
        items = [item for item in items if item.plan_id == plan_id]
    if payment_method:
        items = [item for item in items if item.payment_method == payment_method]

    total = len(items)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    start = (page - 1) * page_size
    return AdminFinancialTableResponse(
        items=items[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(ceil(total / page_size), 1),
    )


def _load_companies(db: Session) -> list[Company]:
    return list(
        db.scalars(
            select(Company)
            .options(selectinload(Company.current_plan))
            .where(Company.is_platform_company.is_(False))
            .order_by(Company.name.asc())
        ).all()
    )


def _load_payments(db: Session) -> list[ManualPayment]:
    return list(
        db.scalars(
            select(ManualPayment)
            .options(
                selectinload(ManualPayment.company),
                selectinload(ManualPayment.plan),
                selectinload(ManualPayment.creator),
            )
            .order_by(ManualPayment.paid_at.desc().nullslast(), ManualPayment.created_at.desc())
        ).all()
    )


def _load_financial_events(db: Session) -> list[UsageEvent]:
    return list(
        db.scalars(
            select(UsageEvent).where(
                UsageEvent.event_type.in_(
                    [
                        UsageEventType.subscription_canceled,
                        UsageEventType.subscription_blocked,
                        UsageEventType.subscription_unblocked,
                        UsageEventType.subscription_reactivated,
                    ]
                )
            )
        ).all()
    )


def _build_monthly_series(
    companies: list[Company],
    payments: list[ManualPayment],
    events: list[UsageEvent],
    now: datetime,
) -> list[AdminFinancialSeriesPoint]:
    points: list[AdminFinancialSeriesPoint] = []
    for month in _last_month_starts(now, 12):
        end = _month_end(month)
        month_payments = [
            payment
            for payment in payments
            if payment.status == PaymentStatus.paid
            and payment.paid_at is not None
            and month <= _as_utc(payment.paid_at) <= end
        ]
        received = _money(sum((payment.amount for payment in month_payments), ZERO))
        forecast = _money(
            sum(
                (
                    payment.price_at_payment or payment.amount
                    for payment in payments
                    if month <= _as_utc(payment.period_start) <= end
                ),
                ZERO,
            )
        )
        month_mrr, customers = _mrr_and_customers_at(payments, events, end)
        churn = _lost_revenue(
            events,
            companies,
            UsageEventType.subscription_canceled,
            month,
            end,
        )
        pending = (
            _status_revenue(companies, {SubscriptionStatus.pending_payment})
            if month.year == now.year and month.month == now.month
            else ZERO
        )
        points.append(
            AdminFinancialSeriesPoint(
                month=month.strftime("%Y-%m"),
                received=received,
                forecast=forecast,
                mrr=month_mrr,
                arr=_money(month_mrr * Decimal(12)),
                pending=pending,
                churn=churn,
                average_ticket=_money(month_mrr / Decimal(customers)) if customers else ZERO,
                payments_received=len(month_payments),
            )
        )
    return points


def _mrr_and_customers_at(
    payments: list[ManualPayment],
    events: list[UsageEvent],
    at: datetime,
) -> tuple[Decimal, int]:
    latest: dict[UUID, ManualPayment] = {}
    for payment in payments:
        if (
            payment.status == PaymentStatus.paid
            and _as_utc(payment.period_start) <= at <= _as_utc(payment.period_end)
        ):
            current = latest.get(payment.company_id)
            if current is None or _as_utc(payment.period_start) > _as_utc(current.period_start):
                latest[payment.company_id] = payment
    latest_event_by_company: dict[UUID, UsageEvent] = {}
    for event in events:
        if _as_utc(event.created_at) > at:
            continue
        current = latest_event_by_company.get(event.company_id)
        if current is None or _as_utc(event.created_at) > _as_utc(current.created_at):
            latest_event_by_company[event.company_id] = event
    inactive = {
        company_id
        for company_id, event in latest_event_by_company.items()
        if event.event_type in {
            UsageEventType.subscription_canceled,
            UsageEventType.subscription_blocked,
        }
    }
    values = [
        monthly_equivalent(payment.price_at_payment or payment.amount, payment.duration_months)
        for company_id, payment in latest.items()
        if company_id not in inactive
    ]
    return _money(sum(values, ZERO)), len(values)


def _mrr_at(
    payments: list[ManualPayment],
    events: list[UsageEvent],
    at: datetime,
) -> Decimal:
    return _mrr_and_customers_at(payments, events, at)[0]


def _received_between(
    payments: list[ManualPayment],
    start: datetime,
    end: datetime,
) -> Decimal:
    return _money(
        sum(
            (
                payment.amount
                for payment in payments
                if payment.status == PaymentStatus.paid
                and payment.paid_at is not None
                and start <= _as_utc(payment.paid_at) <= end
            ),
            ZERO,
        )
    )


def _forecast_between(
    companies: list[Company],
    start: datetime,
    end: datetime,
) -> tuple[Decimal, int]:
    due = [
        company
        for company in companies
        if company.subscription_status == SubscriptionStatus.active
        and company.subscription_valid_until is not None
        and start <= _as_utc(company.subscription_valid_until) <= end
    ]
    return _money(sum((_company_price(company) for company in due), ZERO)), len(due)


def _status_revenue(
    companies: list[Company],
    statuses: set[SubscriptionStatus],
) -> Decimal:
    return _money(
        sum(
            (_company_price(company) for company in companies if company.subscription_status in statuses),
            ZERO,
        )
    )


def _overdue_revenue(companies: list[Company], now: datetime) -> Decimal:
    return _money(
        sum(
            (
                _company_price(company)
                for company in companies
                if company.subscription_status == SubscriptionStatus.pending_payment
                and company.subscription_valid_until is not None
                and _as_utc(company.subscription_valid_until) < now
            ),
            ZERO,
        )
    )


def _lost_revenue(
    events: list[UsageEvent],
    companies: list[Company],
    event_type: UsageEventType,
    start: datetime,
    end: datetime,
) -> Decimal:
    companies_by_id = {company.id: company for company in companies}
    total = ZERO
    for event in events:
        if event.event_type != event_type or not start <= _as_utc(event.created_at) <= end:
            continue
        raw_value = (event.event_metadata or {}).get("monthly_revenue")
        if raw_value is not None:
            total += Decimal(str(raw_value))
        elif event.company_id in companies_by_id:
            total += _company_mrr(companies_by_id[event.company_id])
    return _money(total)


def _revenue_by_plan(
    payments: list[ManualPayment],
    start: datetime,
    end: datetime,
) -> list[AdminFinancialBreakdown]:
    totals: dict[str, Decimal] = {}
    for payment in payments:
        if (
            payment.status == PaymentStatus.paid
            and payment.paid_at is not None
            and start <= _as_utc(payment.paid_at) <= end
        ):
            label = payment.plan.name if payment.plan else payment.plan_slug or "Sem plano"
            totals[label] = totals.get(label, ZERO) + payment.amount
    return [
        AdminFinancialBreakdown(label=label, value=_money(value))
        for label, value in sorted(totals.items())
    ]


def _revenue_by_status(companies: list[Company]) -> list[AdminFinancialBreakdown]:
    totals = {
        status.value: _money(
            sum(
                (
                    _company_mrr(company)
                    for company in companies
                    if company.subscription_status == status
                ),
                ZERO,
            )
        )
        for status in SubscriptionStatus
    }
    return [
        AdminFinancialBreakdown(label=label, value=value)
        for label, value in totals.items()
    ]


def _table_item(
    company: Company,
    payment: ManualPayment | None,
    now: datetime,
) -> AdminFinancialTableItem:
    due_at = _as_utc(company.subscription_valid_until) if company.subscription_valid_until else None
    is_overdue = (
        company.subscription_status == SubscriptionStatus.pending_payment
        and due_at is not None
        and due_at < now
    )
    if is_overdue:
        payment_status = "overdue"
    elif company.subscription_status == SubscriptionStatus.pending_payment:
        payment_status = "pending"
    elif payment is not None:
        payment_status = payment.status.value
    else:
        payment_status = "pending" if company.subscription_status == SubscriptionStatus.active else "-"
    plan_value = _company_price(company)
    return AdminFinancialTableItem(
        company_id=company.id,
        company_name=company.name,
        plan_id=company.current_plan_id,
        plan_name=company.current_plan.name if company.current_plan else None,
        plan_value=plan_value,
        subscription_status=company.subscription_status,
        payment_status=payment_status,
        payment_date=payment.paid_at if payment else None,
        next_due_date=due_at,
        days_overdue=max((now.date() - due_at.date()).days, 0) if is_overdue and due_at else 0,
        payment_method=payment.payment_method if payment else None,
        received_amount=payment.amount if payment and payment.status == PaymentStatus.paid else ZERO,
        pending_amount=plan_value if payment_status in {"pending", "overdue"} else ZERO,
        renewed_by_admin=payment.creator.name if payment and payment.creator else None,
        notes=payment.notes if payment else None,
        created_at=payment.created_at if payment else company.created_at,
        updated_at=payment.updated_at if payment else company.updated_at,
    )


def _company_price(company: Company) -> Decimal:
    if company.subscription_price is not None:
        return _money(company.subscription_price)
    if company.current_plan is not None:
        return _money(company.current_plan.price)
    return ZERO


def _company_mrr(company: Company) -> Decimal:
    duration = company.subscription_duration_months
    if duration is None and company.current_plan is not None:
        duration = company.current_plan.duration_months
    return monthly_equivalent(_company_price(company), duration)


def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= ZERO:
        return ZERO
    return _money(numerator / denominator * Decimal(100))


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _day_start(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _week_start(value: datetime) -> datetime:
    return _day_start(value) - timedelta(days=value.weekday())


def _month_start(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _month_end(value: datetime) -> datetime:
    return value.replace(
        day=monthrange(value.year, value.month)[1],
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )


def _last_month_starts(value: datetime, count: int) -> list[datetime]:
    current = _month_start(value)
    result = []
    for offset in range(count - 1, -1, -1):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        result.append(current.replace(year=year, month=month))
    return result
