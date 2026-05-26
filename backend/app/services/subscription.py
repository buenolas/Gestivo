from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.manual_payment import ManualPayment
from app.models.user import User
from app.models.user import UserRole
from app.schemas.subscription import AdminCompanySubscriptionResponse
from app.schemas.subscription import ManualRenewalCreate
from app.schemas.subscription import SubscriptionStatusResponse

TRIAL_DAYS = 30
RENEWAL_DAYS = 30


class SubscriptionPermissionError(PermissionError):
    pass


class SubscriptionValidationError(ValueError):
    pass


def now_utc() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def trial_end_date(from_date: datetime | None = None) -> datetime:
    return (as_utc(from_date) or now_utc()) + timedelta(days=TRIAL_DAYS)


def get_access_until(company: Company) -> datetime | None:
    if company.subscription_status == SubscriptionStatus.trialing:
        return as_utc(company.trial_ends_at)
    if company.subscription_status == SubscriptionStatus.active:
        return as_utc(company.subscription_valid_until)
    return None


def refresh_subscription_status(db: Session, company: Company) -> Company:
    if company.subscription_status not in {
        SubscriptionStatus.trialing,
        SubscriptionStatus.active,
    }:
        return company

    access_until = get_access_until(company)
    if access_until is not None and access_until < now_utc():
        company.subscription_status = SubscriptionStatus.pending_payment
        db.add(company)
        db.commit()
        db.refresh(company)
    return company


def is_subscription_valid(company: Company) -> bool:
    access_until = get_access_until(company)
    return (
        company.subscription_status in {SubscriptionStatus.trialing, SubscriptionStatus.active}
        and access_until is not None
        and access_until >= now_utc()
    )


def get_subscription_status(db: Session, company: Company) -> SubscriptionStatusResponse:
    company = refresh_subscription_status(db, company)
    return SubscriptionStatusResponse(
        company_id=company.id,
        status=company.subscription_status,
        is_valid=is_subscription_valid(company),
        trial_ends_at=company.trial_ends_at,
        subscription_valid_until=company.subscription_valid_until,
        access_until=get_access_until(company),
    )


def list_admin_company_subscriptions(db: Session) -> list[AdminCompanySubscriptionResponse]:
    companies = db.scalars(
        select(Company)
        .where(Company.is_platform_company.is_(False))
        .order_by(Company.created_at.desc())
    )
    return [
        AdminCompanySubscriptionResponse(
            **get_subscription_status(db, company).model_dump(),
            company_name=company.name,
        )
        for company in companies
    ]


def create_manual_renewal(
    db: Session,
    admin_user: User,
    renewal_in: ManualRenewalCreate,
) -> ManualPayment:
    if admin_user.role != UserRole.platform_admin:
        raise SubscriptionPermissionError("Apenas platform_admin pode renovar assinaturas")

    company = db.get(Company, renewal_in.company_id)
    if company is None:
        raise SubscriptionValidationError("Empresa não encontrada")
    if company.is_platform_company:
        raise SubscriptionValidationError("Empresa da plataforma não pode ser renovada manualmente")

    company = refresh_subscription_status(db, company)
    paid_at = as_utc(renewal_in.paid_at) or now_utc()
    current_access_until = get_access_until(company)
    period_start = (
        current_access_until
        if current_access_until is not None and current_access_until >= paid_at
        else paid_at
    )
    period_end = period_start + timedelta(days=RENEWAL_DAYS)

    company.subscription_status = SubscriptionStatus.active
    company.subscription_valid_until = period_end

    payment = ManualPayment(
        company_id=company.id,
        amount=renewal_in.amount,
        paid_at=paid_at,
        period_start=period_start,
        period_end=period_end,
        notes=_strip_optional_text(renewal_in.notes),
        created_by=admin_user.id,
    )
    db.add(company)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
