import secrets
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.services.email import send_password_reset_code
from app.services.email_verification import normalize_email
from app.services.email_verification import token_hash


PASSWORD_RESET_GENERIC_MESSAGE = "Se existir uma conta para este e-mail, enviaremos um codigo."


class PasswordResetError(ValueError):
    pass


def request_password_reset(db: Session, email: str) -> None:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return

    now = datetime.now(UTC)
    requested_at = _as_utc(user.password_reset_requested_at)
    if requested_at is not None:
        resend_at = requested_at + timedelta(
            seconds=settings.password_reset_resend_interval_seconds,
        )
        if resend_at > now:
            return

    code = f"{secrets.randbelow(1_000_000):06d}"
    user.password_reset_code_hash = token_hash(code)
    user.password_reset_expires_at = now + timedelta(
        minutes=settings.password_reset_code_expire_minutes,
    )
    user.password_reset_requested_at = now
    db.add(user)
    db.commit()
    db.refresh(user)
    send_password_reset_code(user.email, code)


def confirm_password_reset(
    db: Session,
    email: str,
    code: str,
    new_password: str,
) -> User:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise PasswordResetError("Codigo invalido ou expirado.")

    expires_at = _as_utc(user.password_reset_expires_at)
    if (
        user.password_reset_code_hash is None
        or expires_at is None
        or expires_at < datetime.now(UTC)
        or user.password_reset_code_hash != token_hash(code)
    ):
        raise PasswordResetError("Codigo invalido ou expirado.")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    clear_password_reset(user)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def clear_password_reset(user: User) -> None:
    user.password_reset_code_hash = None
    user.password_reset_expires_at = None
    user.password_reset_requested_at = None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = normalize_email(email)
    return db.scalar(select(User).where(User.email == normalized_email))
