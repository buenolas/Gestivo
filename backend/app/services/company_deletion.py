from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.contact import Contact
from app.models.employee import Employee
from app.models.financial_category import FinancialCategory
from app.models.financial_transaction import FinancialTransaction
from app.models.import_batch import ImportBatch
from app.models.manual_payment import ManualPayment
from app.models.stripe_webhook_event import StripeWebhookEvent
from app.models.usage_event import UsageEvent
from app.models.user import User, UserRole

DELETION_RETENTION_DAYS = 30


class CompanyDeletionNotFoundError(ValueError):
    pass


class CompanyDeletionConflictError(ValueError):
    pass


def schedule_company_deletion(db: Session, company_id: UUID) -> Company:
    company = db.scalar(
        select(Company)
        .where(Company.id == company_id)
        .with_for_update()
    )
    if company is None or company.is_platform_company:
        raise CompanyDeletionNotFoundError("Empresa não encontrada.")

    has_platform_admin = db.scalar(
        select(User.id)
        .where(User.company_id == company.id, User.role == UserRole.platform_admin)
        .limit(1)
    )
    if has_platform_admin is not None:
        raise CompanyDeletionConflictError(
            "Esta empresa está vinculada a um administrador da plataforma e não pode ser excluída."
        )

    if company.deletion_requested_at is None:
        now = datetime.now(UTC)
        company.deletion_requested_at = now
        db.execute(
            update(User)
            .where(User.company_id == company.id)
            .values(is_active=False, updated_at=now)
        )
        db.add(company)
        db.commit()
        db.refresh(company)
    return company


def purge_due_company_deletions(
    db: Session,
    reference_at: datetime | None = None,
) -> int:
    now = reference_at or datetime.now(UTC)
    now = now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)
    cutoff = now - timedelta(days=DELETION_RETENTION_DAYS)
    company_ids = list(
        db.scalars(
            select(Company.id)
            .where(
                Company.is_platform_company.is_(False),
                Company.deletion_requested_at.is_not(None),
                Company.deletion_requested_at <= cutoff,
                ~exists().where(
                    User.company_id == Company.id,
                    User.role == UserRole.platform_admin,
                ),
            )
            .order_by(Company.deletion_requested_at, Company.id)
            .with_for_update(skip_locked=True)
        ).all()
    )

    for company_id in company_ids:
        db.execute(delete(FinancialTransaction).where(FinancialTransaction.company_id == company_id))
        db.execute(delete(ManualPayment).where(ManualPayment.company_id == company_id))
        db.execute(delete(ImportBatch).where(ImportBatch.company_id == company_id))
        db.execute(delete(UsageEvent).where(UsageEvent.company_id == company_id))
        db.execute(delete(StripeWebhookEvent).where(StripeWebhookEvent.company_id == company_id))
        db.execute(delete(FinancialCategory).where(FinancialCategory.company_id == company_id))
        db.execute(delete(Contact).where(Contact.company_id == company_id))
        db.execute(delete(Employee).where(Employee.company_id == company_id))
        db.execute(delete(User).where(User.company_id == company_id))
        db.execute(delete(Company).where(Company.id == company_id))

    if company_ids:
        db.commit()
    return len(company_ids)
