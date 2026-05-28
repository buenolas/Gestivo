import hashlib
import secrets
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.user import UserRole
from app.services.email import send_email_verification

DISPOSABLE_EMAIL_DOMAINS = {
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "tempmail.com",
    "yopmail.com",
}


class EmailVerificationError(ValueError):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def ensure_email_domain_allowed(email: str) -> None:
    domain = normalize_email(email).rsplit("@", 1)[-1]
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        raise EmailVerificationError("Este dominio de e-mail nao pode ser usado no cadastro")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_email_verification_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(48)
    user.email_verification_token_hash = token_hash(token)
    user.email_verification_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.email_verification_token_expire_minutes,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return token


def verification_link(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/?email_verification_token={token}"


def send_user_email_verification(db: Session, user: User) -> None:
    if user.email_verified_at is not None:
        return

    token = create_email_verification_token(db, user)
    send_email_verification(user.email, verification_link(token))


def confirm_email(db: Session, token: str) -> bool:
    user = db.scalar(
        select(User).where(User.email_verification_token_hash == token_hash(token))
    )
    if user is None or user.email_verification_expires_at is None:
        return False

    expires_at = user.email_verification_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        return False

    user.email_verified_at = datetime.now(UTC)
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.add(user)
    db.commit()
    return True


def can_access_customer_financial_routes(user: User) -> bool:
    if user.role == UserRole.platform_admin:
        return True
    return user.email_verified_at is not None
