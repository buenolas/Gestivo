from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.user import User
from app.models.user import UserRole

PLATFORM_COMPANY_NAME = "Plataforma"


class PlatformAdminSeedError(ValueError):
    pass


def create_platform_admin(
    db: Session,
    *,
    name: str,
    email: str,
    password: str,
) -> User:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise PlatformAdminSeedError("Informe o e-mail do administrador da plataforma")
    if len(password) < 8:
        raise PlatformAdminSeedError("A senha deve ter ao menos 8 caracteres")

    existing_user = db.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise PlatformAdminSeedError("Já existe um usuário com esse e-mail")

    company = get_or_create_platform_company(db)
    user = User(
        company=company,
        name=name.strip(),
        email=normalized_email,
        password_hash=hash_password(password),
        role=UserRole.platform_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_platform_company(db: Session) -> Company:
    company = db.scalar(
        select(Company).where(Company.is_platform_company.is_(True))
    )
    if company is not None:
        return company

    now = datetime.now(UTC)
    company = Company(
        name=PLATFORM_COMPANY_NAME,
        subscription_status=SubscriptionStatus.active,
        trial_ends_at=now + timedelta(days=3650),
        subscription_valid_until=now + timedelta(days=3650),
        is_platform_company=True,
    )
    db.add(company)
    db.flush()
    return company
