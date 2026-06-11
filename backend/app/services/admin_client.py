from datetime import UTC
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from math import ceil
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import case
from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.financial_transaction import FinancialTransaction
from app.models.import_batch import ImportBatch
from app.models.manual_payment import ManualPayment
from app.models.plan import Plan
from app.models.usage_event import UsageEvent
from app.models.usage_event import UsageEventType
from app.models.user import User
from app.models.user import UserRole
from app.schemas.admin_client import AdminChartPoint
from app.schemas.admin_client import AdminClientActionResponse
from app.schemas.admin_client import AdminClientDashboardResponse
from app.schemas.admin_client import AdminClientDetailResponse
from app.schemas.admin_client import AdminClientListItem
from app.schemas.admin_client import AdminClientListResponse
from app.schemas.admin_client import AdminMetricCard
from app.schemas.subscription import ManualRenewalCreate
from app.services.subscription import create_manual_renewal
from app.services.subscription import get_access_until
from app.services.subscription import refresh_subscription_status
from app.services.subscription import now_utc
from app.services.usage_event import record_usage_event


class AdminClientNotFoundError(ValueError):
    pass


class AdminClientValidationError(ValueError):
    pass


def get_admin_client_dashboard(db: Session) -> AdminClientDashboardResponse:
    reference_at = now_utc()
    companies = _all_customer_companies(db)
    rows = _client_rows(db, companies)
    total = len(rows)
    active = sum(1 for row in rows if row.subscription_status == SubscriptionStatus.active)
    trialing = sum(1 for row in rows if row.subscription_status == SubscriptionStatus.trialing)
    pending = sum(1 for row in rows if row.subscription_status == SubscriptionStatus.pending_payment)
    blocked = sum(1 for row in rows if row.subscription_status == SubscriptionStatus.blocked)
    canceled = sum(1 for row in rows if row.subscription_status == SubscriptionStatus.canceled)
    risk = sum(1 for row in rows if row.is_at_risk)
    current_month_start = reference_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    conversion_month = _count_events_since(
        db,
        UsageEventType.subscription_renewed,
        current_month_start,
    )
    trial_started_month = sum(1 for row in rows if row.created_at >= current_month_start)
    conversion_rate = (
        Decimal(conversion_month) / Decimal(trial_started_month) * Decimal("100")
        if trial_started_month
        else Decimal("0")
    ).quantize(Decimal("0.01"))
    churn_month = _count_events_since(
        db,
        UsageEventType.subscription_canceled,
        current_month_start,
    )
    churn_rate = (
        Decimal(churn_month) / Decimal(max(active + canceled, 1)) * Decimal("100")
    ).quantize(Decimal("0.01"))

    cards = [
        AdminMetricCard(key="total_companies", label="Total de empresas cadastradas", value=total),
        AdminMetricCard(key="active_clients", label="Clientes ativos", value=active),
        AdminMetricCard(key="trialing_clients", label="Clientes em trial", value=trialing),
        AdminMetricCard(key="trials_ending_7d", label="Trials vencendo em 7 dias", value=_ending_soon(rows, "trial")),
        AdminMetricCard(key="subscriptions_ending_7d", label="Assinaturas vencendo em 7 dias", value=_ending_soon(rows, "subscription")),
        AdminMetricCard(key="overdue_clients", label="Clientes vencidos", value=pending),
        AdminMetricCard(key="pending_payment_clients", label="Pendentes de pagamento", value=pending),
        AdminMetricCard(key="blocked_clients", label="Bloqueados", value=blocked),
        AdminMetricCard(key="canceled_clients", label="Cancelados", value=canceled),
        AdminMetricCard(key="new_clients_month", label="Novos clientes no mês", value=trial_started_month),
        AdminMetricCard(key="new_clients_30d", label="Novos clientes em 30 dias", value=sum(1 for row in rows if row.created_at >= reference_at - timedelta(days=30))),
        AdminMetricCard(key="trial_conversions_month", label="Conversões no mês", value=conversion_month),
        AdminMetricCard(key="trial_conversion_rate", label="Taxa de conversão trial", value=conversion_rate),
        AdminMetricCard(key="monthly_churn", label="Churn mensal", value=churn_rate),
        AdminMetricCard(key="no_login_7d", label="Sem login há 7 dias", value=_without_recent_login(rows, 7)),
        AdminMetricCard(key="no_login_15d", label="Sem login há 15 dias", value=_without_recent_login(rows, 15)),
        AdminMetricCard(key="no_login_30d", label="Sem login há 30 dias", value=_without_recent_login(rows, 30)),
        AdminMetricCard(key="never_logged_in", label="Nunca fizeram login", value=sum(1 for row in rows if row.last_login_at is None)),
        AdminMetricCard(key="never_imported", label="Nunca importaram planilha", value=sum(1 for row in rows if row.imports_count == 0)),
        AdminMetricCard(key="no_transactions_month", label="Sem lançamentos no mês", value=sum(1 for row in rows if row.financial_transactions_count == 0)),
    ]

    return AdminClientDashboardResponse(
        cards=cards,
        subscription_status=_points_from_counts({status.value: sum(1 for row in rows if row.subscription_status == status) for status in SubscriptionStatus}),
        new_clients_by_month=_monthly_company_points(companies, "created"),
        trial_conversions_by_month=_monthly_event_points(db, UsageEventType.subscription_renewed),
        cancellations_by_month=_monthly_event_points(db, UsageEventType.subscription_canceled),
        active_base_by_month=_active_base_points(companies),
        active_vs_risk=[AdminChartPoint(label="Ativos", value=active), AdminChartPoint(label="Em risco", value=risk)],
        plan_distribution=_plan_distribution(rows),
        most_active_by_transactions=[AdminChartPoint(label=row.company_name, value=row.financial_transactions_count) for row in sorted(rows, key=lambda row: row.financial_transactions_count, reverse=True)[:5]],
        highest_financial_volume=_highest_financial_volume(db),
    )


def list_admin_clients(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    subscription_status: SubscriptionStatus | None = None,
    plan_id: UUID | None = None,
    filter_key: str | None = None,
) -> AdminClientListResponse:
    companies = _all_customer_companies(db)
    rows = _client_rows(db, companies)
    rows = _apply_filters(rows, search, subscription_status, plan_id, filter_key)
    total = len(rows)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    start = (page - 1) * page_size
    return AdminClientListResponse(
        items=rows[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(ceil(total / page_size), 1),
    )


def get_admin_client_detail(db: Session, company_id: UUID) -> AdminClientDetailResponse:
    company = _get_customer_company(db, company_id)
    base = _client_rows(db, [company])[0]
    users = db.scalars(select(User).where(User.company_id == company.id).order_by(User.created_at.asc())).all()
    payments = db.scalars(
        select(ManualPayment)
        .where(ManualPayment.company_id == company.id)
        .order_by(ManualPayment.paid_at.desc().nullslast(), ManualPayment.created_at.desc())
    ).all()
    events = db.scalars(select(UsageEvent).where(UsageEvent.company_id == company.id).order_by(UsageEvent.created_at.desc()).limit(30)).all()
    last_import_at = db.scalar(
        select(func.max(ImportBatch.confirmed_at)).where(ImportBatch.company_id == company.id)
    )

    payment_history = [
        {
            "id": str(payment.id),
            "amount": str(payment.amount),
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            "period_start": payment.period_start.isoformat(),
            "period_end": payment.period_end.isoformat(),
            "plan_slug": payment.plan_slug,
            "notes": payment.notes,
        }
        for payment in payments
    ]
    return AdminClientDetailResponse(
        **base.model_dump(),
        blocked_at=company.blocked_at,
        canceled_at=company.canceled_at,
        users=[
            {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active,
            }
            for user in users
        ],
        renewal_history=payment_history,
        payment_history=payment_history,
        usage_events=[
            {
                "id": str(event.id),
                "event_type": event.event_type.value,
                "created_at": event.created_at.isoformat(),
                "user_id": str(event.user_id) if event.user_id else None,
            }
            for event in events
        ],
        last_import_at=last_import_at,
    )


def renew_admin_client(db: Session, admin_user: User, company_id: UUID, renewal_in) -> ManualPayment:
    _get_customer_company(db, company_id)
    return create_manual_renewal(
        db,
        admin_user,
        ManualRenewalCreate(
            company_id=company_id,
            plan_id=renewal_in.plan_id,
            amount=renewal_in.amount,
            paid_at=renewal_in.paid_at,
            notes=renewal_in.notes,
        ),
    )


def block_admin_client(db: Session, admin_user: User, company_id: UUID) -> AdminClientActionResponse:
    company = _get_customer_company(db, company_id)
    lost_mrr = _company_monthly_revenue(company)
    company.subscription_status = SubscriptionStatus.blocked
    company.blocked_at = now_utc()
    db.add(company)
    record_usage_event(
        db,
        company_id=company.id,
        user_id=admin_user.id,
        event_type=UsageEventType.subscription_blocked,
        metadata={"monthly_revenue": str(lost_mrr)},
    )
    db.commit()
    return _action_response(company, "Empresa bloqueada.")


def unblock_admin_client(db: Session, admin_user: User, company_id: UUID) -> AdminClientActionResponse:
    company = _get_customer_company(db, company_id)
    company.blocked_at = None
    access_until = get_access_until(company)
    company.subscription_status = (
        SubscriptionStatus.active
        if access_until is not None and access_until >= now_utc()
        else SubscriptionStatus.pending_payment
    )
    db.add(company)
    record_usage_event(db, company_id=company.id, user_id=admin_user.id, event_type=UsageEventType.subscription_unblocked)
    db.commit()
    return _action_response(company, "Empresa desbloqueada.")


def cancel_admin_client(db: Session, admin_user: User, company_id: UUID) -> AdminClientActionResponse:
    company = _get_customer_company(db, company_id)
    lost_mrr = _company_monthly_revenue(company)
    company.subscription_status = SubscriptionStatus.canceled
    company.canceled_at = now_utc()
    db.add(company)
    record_usage_event(
        db,
        company_id=company.id,
        user_id=admin_user.id,
        event_type=UsageEventType.subscription_canceled,
        metadata={"monthly_revenue": str(lost_mrr)},
    )
    db.commit()
    return _action_response(company, "Assinatura cancelada.")


def reactivate_admin_client(db: Session, admin_user: User, company_id: UUID) -> AdminClientActionResponse:
    company = _get_customer_company(db, company_id)
    company.canceled_at = None
    company.blocked_at = None
    access_until = get_access_until(company)
    company.subscription_status = (
        SubscriptionStatus.active
        if access_until is not None and access_until >= now_utc()
        else SubscriptionStatus.pending_payment
    )
    db.add(company)
    record_usage_event(db, company_id=company.id, user_id=admin_user.id, event_type=UsageEventType.subscription_reactivated)
    db.commit()
    return _action_response(company, "Assinatura reativada.")


def change_admin_client_plan(
    db: Session,
    admin_user: User,
    company_id: UUID,
    plan_id: UUID,
) -> AdminClientActionResponse:
    company = _get_customer_company(db, company_id)
    plan = db.get(Plan, plan_id)
    if plan is None or not plan.is_active:
        raise AdminClientValidationError("Plano nao encontrado ou inativo.")
    company.current_plan_id = plan.id
    company.subscription_price = plan.price
    company.subscription_duration_months = plan.duration_months
    db.add(company)
    record_usage_event(
        db,
        company_id=company.id,
        user_id=admin_user.id,
        event_type=UsageEventType.plan_changed,
        metadata={"plan_id": str(plan.id)},
    )
    db.commit()
    return _action_response(company, "Plano alterado.")


def _client_rows(db: Session, companies: list[Company]) -> list[AdminClientListItem]:
    company_ids = [company.id for company in companies]
    users_count = _count_by_company(db, User.company_id, User.company_id.in_(company_ids))
    tx_counts = _count_by_company(
        db,
        FinancialTransaction.company_id,
        and_(FinancialTransaction.company_id.in_(company_ids), FinancialTransaction.deleted_at.is_(None)),
    )
    import_counts = _count_by_company(
        db,
        ImportBatch.company_id,
        and_(ImportBatch.company_id.in_(company_ids), ImportBatch.confirmed_at.is_not(None)),
    )
    last_login = _max_by_company(
        db,
        UsageEvent.company_id,
        UsageEvent.created_at,
        and_(UsageEvent.company_id.in_(company_ids), UsageEvent.event_type == UsageEventType.login),
    )
    last_activity = _max_by_company(db, UsageEvent.company_id, UsageEvent.created_at, UsageEvent.company_id.in_(company_ids))
    admin_users = _admin_users(db, company_ids)
    first_payment = _min_by_company(db, ManualPayment.company_id, ManualPayment.period_start, ManualPayment.company_id.in_(company_ids))

    rows: list[AdminClientListItem] = []
    for company in companies:
        refresh_subscription_status(db, company)
        access_until = get_access_until(company)
        days_remaining = None
        if access_until is not None:
            days_remaining = (access_until.date() - now_utc().date()).days
        plan = company.current_plan
        rows.append(
            AdminClientListItem(
                company_id=company.id,
                company_name=company.name,
                admin_name=admin_users.get(company.id).name if admin_users.get(company.id) else None,
                admin_email=admin_users.get(company.id).email if admin_users.get(company.id) else None,
                subscription_status=company.subscription_status,
                plan_id=company.current_plan_id,
                plan_name=plan.name if plan else None,
                plan_price=plan.price if plan else None,
                created_at=company.created_at,
                trial_started_at=company.created_at,
                trial_ends_at=company.trial_ends_at,
                subscription_started_at=first_payment.get(company.id),
                subscription_valid_until=company.subscription_valid_until,
                days_remaining=days_remaining,
                last_login_at=last_login.get(company.id),
                users_count=users_count.get(company.id, 0),
                financial_transactions_count=tx_counts.get(company.id, 0),
                imports_count=import_counts.get(company.id, 0),
                usage_status=_usage_status(last_activity.get(company.id)),
                is_at_risk=_is_at_risk(company, last_login.get(company.id), tx_counts.get(company.id, 0)),
            )
        )
    return rows


def _all_customer_companies(db: Session) -> list[Company]:
    return db.scalars(
        select(Company)
        .options(selectinload(Company.current_plan))
        .where(Company.is_platform_company.is_(False))
        .order_by(Company.created_at.desc())
    ).all()


def _get_customer_company(db: Session, company_id: UUID) -> Company:
    company = db.get(Company, company_id)
    if company is None or company.is_platform_company:
        raise AdminClientNotFoundError("Empresa nao encontrada.")
    return company


def _count_by_company(db: Session, company_column, where_clause) -> dict[UUID, int]:
    rows = db.execute(select(company_column, func.count()).where(where_clause).group_by(company_column)).all()
    return {company_id: count for company_id, count in rows}


def _max_by_company(db: Session, company_column, value_column, where_clause) -> dict[UUID, datetime]:
    rows = db.execute(select(company_column, func.max(value_column)).where(where_clause).group_by(company_column)).all()
    return {company_id: value for company_id, value in rows if value is not None}


def _min_by_company(db: Session, company_column, value_column, where_clause) -> dict[UUID, datetime]:
    rows = db.execute(select(company_column, func.min(value_column)).where(where_clause).group_by(company_column)).all()
    return {company_id: value for company_id, value in rows if value is not None}


def _admin_users(db: Session, company_ids: list[UUID]) -> dict[UUID, User]:
    users = db.scalars(
        select(User)
        .where(User.company_id.in_(company_ids), User.role == UserRole.company_admin)
        .order_by(User.created_at.asc())
    ).all()
    result: dict[UUID, User] = {}
    for user in users:
        result.setdefault(user.company_id, user)
    return result


def _usage_status(last_activity_at: datetime | None) -> str:
    if last_activity_at is None:
        return "nunca usou"
    delta = now_utc() - _as_utc(last_activity_at)
    if delta.days <= 7:
        return "ativo"
    if delta.days <= 30:
        return "pouco uso"
    return "sem uso recente"


def _is_at_risk(company: Company, last_login_at: datetime | None, transactions_count: int) -> bool:
    access_until = get_access_until(company)
    if company.subscription_status in {SubscriptionStatus.pending_payment, SubscriptionStatus.blocked}:
        return True
    if access_until is not None and access_until <= now_utc() + timedelta(days=7):
        return True
    if last_login_at is None or now_utc() - _as_utc(last_login_at) > timedelta(days=15):
        return True
    return transactions_count == 0


def _apply_filters(
    rows: list[AdminClientListItem],
    search: str | None,
    subscription_status: SubscriptionStatus | None,
    plan_id: UUID | None,
    filter_key: str | None,
) -> list[AdminClientListItem]:
    filtered = rows
    if search and search.strip():
        term = search.strip().lower()
        filtered = [
            row for row in filtered
            if term in row.company_name.lower()
            or term in (row.admin_name or "").lower()
            or term in (row.admin_email or "").lower()
        ]
    if subscription_status is not None:
        filtered = [row for row in filtered if row.subscription_status == subscription_status]
    if plan_id is not None:
        filtered = [row for row in filtered if row.plan_id == plan_id]
    if filter_key:
        filtered = [row for row in filtered if _matches_filter(row, filter_key)]
    return filtered


def _matches_filter(row: AdminClientListItem, filter_key: str) -> bool:
    if filter_key == "active":
        return row.subscription_status == SubscriptionStatus.active
    if filter_key == "trialing":
        return row.subscription_status == SubscriptionStatus.trialing
    if filter_key == "overdue":
        return row.subscription_status == SubscriptionStatus.pending_payment
    if filter_key == "blocked":
        return row.subscription_status == SubscriptionStatus.blocked
    if filter_key == "canceled":
        return row.subscription_status == SubscriptionStatus.canceled
    if filter_key == "trial_ending":
        return row.subscription_status == SubscriptionStatus.trialing and row.days_remaining is not None and 0 <= row.days_remaining <= 7
    if filter_key == "subscription_ending":
        return row.subscription_status == SubscriptionStatus.active and row.days_remaining is not None and 0 <= row.days_remaining <= 7
    if filter_key == "no_recent_login":
        return row.last_login_at is None or now_utc() - _as_utc(row.last_login_at) > timedelta(days=15)
    if filter_key == "no_month_usage":
        return row.financial_transactions_count == 0
    return True


def _points_from_counts(values: dict[str, int]) -> list[AdminChartPoint]:
    return [AdminChartPoint(label=label, value=value) for label, value in values.items()]


def _monthly_company_points(companies: list[Company], mode: str) -> list[AdminChartPoint]:
    del mode
    months = _last_month_labels()
    counts = {label: 0 for label in months}
    for company in companies:
        label = company.created_at.strftime("%Y-%m")
        if label in counts:
            counts[label] += 1
    return _points_from_counts(counts)


def _monthly_event_points(db: Session, event_type: UsageEventType) -> list[AdminChartPoint]:
    months = _last_month_labels()
    counts = {label: 0 for label in months}
    since = _month_start_months_ago(11)
    month_label = func.to_char(UsageEvent.created_at, "YYYY-MM")
    rows = db.execute(
        select(month_label, func.count())
        .where(UsageEvent.event_type == event_type, UsageEvent.created_at >= since)
        .group_by(month_label)
    ).all()
    for label, count in rows:
        counts[label] = count
    return _points_from_counts(counts)


def _active_base_points(companies: list[Company]) -> list[AdminChartPoint]:
    months = _last_month_labels()
    points: list[AdminChartPoint] = []
    for label in months:
        year, month = [int(part) for part in label.split("-")]
        month_end = datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=UTC) - timedelta(seconds=1)
        points.append(
            AdminChartPoint(
                label=label,
                value=sum(
                    1
                    for company in companies
                    if _as_utc(company.created_at) <= month_end
                    and (company.canceled_at is None or _as_utc(company.canceled_at) > month_end)
                    and company.subscription_status != SubscriptionStatus.blocked
                ),
            )
        )
    return points


def _plan_distribution(rows: list[AdminClientListItem]) -> list[AdminChartPoint]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.plan_name or "Sem plano"] = counts.get(row.plan_name or "Sem plano", 0) + 1
    return _points_from_counts(counts)


def _highest_financial_volume(db: Session) -> list[AdminChartPoint]:
    amount_sum = func.coalesce(func.sum(FinancialTransaction.amount), Decimal("0.00"))
    rows = db.execute(
        select(Company.name, amount_sum)
        .join(FinancialTransaction, FinancialTransaction.company_id == Company.id)
        .where(Company.is_platform_company.is_(False), FinancialTransaction.deleted_at.is_(None))
        .group_by(Company.name)
        .order_by(desc(amount_sum))
        .limit(5)
    ).all()
    return [AdminChartPoint(label=name, value=value or Decimal("0.00")) for name, value in rows]


def _count_events_since(db: Session, event_type: UsageEventType, since: datetime) -> int:
    return db.scalar(select(func.count()).where(UsageEvent.event_type == event_type, UsageEvent.created_at >= since)) or 0


def _ending_soon(rows: list[AdminClientListItem], kind: str) -> int:
    status = SubscriptionStatus.trialing if kind == "trial" else SubscriptionStatus.active
    return sum(1 for row in rows if row.subscription_status == status and row.days_remaining is not None and 0 <= row.days_remaining <= 7)


def _without_recent_login(rows: list[AdminClientListItem], days: int) -> int:
    return sum(1 for row in rows if row.last_login_at is None or now_utc() - _as_utc(row.last_login_at) > timedelta(days=days))


def _last_month_labels() -> list[str]:
    current = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    labels = []
    for index in range(11, -1, -1):
        year = current.year
        month = current.month - index
        while month <= 0:
            month += 12
            year -= 1
        labels.append(f"{year:04d}-{month:02d}")
    return labels


def _month_start_months_ago(months: int) -> datetime:
    current = now_utc().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year = current.year
    month = current.month - months
    while month <= 0:
        month += 12
        year -= 1
    return current.replace(year=year, month=month)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _action_response(company: Company, message: str) -> AdminClientActionResponse:
    return AdminClientActionResponse(company_id=company.id, status=company.subscription_status, message=message)


def _company_monthly_revenue(company: Company) -> Decimal:
    price = company.subscription_price
    duration = company.subscription_duration_months
    if price is None and company.current_plan is not None:
        price = company.current_plan.price
        duration = company.current_plan.duration_months
    if price is None:
        return Decimal("0.00")
    return (price / Decimal(duration or 1)).quantize(Decimal("0.01"))
