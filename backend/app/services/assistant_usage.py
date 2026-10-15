from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.plan import Plan
from app.models.usage_event import UsageEvent
from app.models.usage_event import UsageEventType
from app.models.user import User
from app.services.plan import ensure_fixed_plans

BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


class AssistantPlanUnavailableError(PermissionError):
    pass


class AssistantDailyLimitError(ValueError):
    def __init__(self, limit: int, used: int) -> None:
        self.limit = limit
        self.used = used
        super().__init__(
            f"O limite de {limit} interações com a IA por dia foi atingido. Tente novamente amanhã."
        )


def assistant_interactions_today(
    db: Session,
    company_id,
    reference_at: datetime | None = None,
) -> int:
    start_at, end_at = _today_window(reference_at)
    count = db.scalar(
        select(func.count(UsageEvent.id)).where(
            UsageEvent.company_id == company_id,
            UsageEvent.event_type == UsageEventType.assistant_interaction,
            UsageEvent.created_at >= start_at,
            UsageEvent.created_at < end_at,
        )
    )
    return int(count or 0)


def ensure_assistant_interaction_available(
    db: Session,
    user: User,
) -> tuple[int, int | None]:
    company, plan = _assistant_company_and_plan(db, user)
    used = assistant_interactions_today(db, company.id)
    _ensure_daily_limit(plan.ai_daily_limit, used)
    return used, plan.ai_daily_limit


def consume_assistant_interaction(db: Session, user: User) -> tuple[int, int | None]:
    # Seed before taking the company lock so concurrent requests remain serialized
    # while counting and recording the interaction.
    company, plan = _assistant_company_and_plan(db, user, lock_company=True)
    used = assistant_interactions_today(db, company.id)
    _ensure_daily_limit(plan.ai_daily_limit, used)

    db.add(
        UsageEvent(
            company_id=company.id,
            user_id=user.id,
            event_type=UsageEventType.assistant_interaction,
        )
    )
    db.commit()
    return used + 1, plan.ai_daily_limit


def _assistant_company_and_plan(
    db: Session,
    user: User,
    *,
    lock_company: bool = False,
) -> tuple[Company, Plan]:
    # Seed fixed plans before taking the company lock. The lock then serializes
    # simultaneous successful interactions for the same company.
    ensure_fixed_plans(db)
    company_query = select(Company).where(Company.id == user.company_id)
    if lock_company:
        company_query = company_query.with_for_update()
    company = db.scalar(company_query)
    if company is None:
        raise AssistantPlanUnavailableError("Empresa não encontrada.")

    plan = (
        db.get(Plan, company.current_plan_id)
        if company.current_plan_id is not None
        else db.scalar(select(Plan).where(Plan.slug == "basic"))
    )
    if plan is None or "assistant" not in (plan.feature_codes or []):
        raise AssistantPlanUnavailableError(
            "O plano atual não inclui o assistente financeiro."
        )

    return company, plan


def _ensure_daily_limit(limit: int | None, used: int) -> None:
    if limit is not None and used >= limit:
        raise AssistantDailyLimitError(limit, used)


def _today_window(reference_at: datetime | None) -> tuple[datetime, datetime]:
    current = reference_at or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    local_date: date = current.astimezone(BUSINESS_TIMEZONE).date()
    local_start = datetime.combine(local_date, time.min, tzinfo=BUSINESS_TIMEZONE)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)
