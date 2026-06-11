from datetime import UTC
from datetime import datetime
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.google import GoogleUserInfo
from app.core.security import hash_password
from app.core.security import verify_password
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.user import User
from app.models.user import UserRole
from app.schemas.auth import UserCreate
from app.services.email_verification import ensure_email_domain_allowed
from app.services.email_verification import normalize_email
from app.services.email_verification import send_user_email_verification
from app.services.subscription import trial_end_date


class GoogleLoginError(Exception):
    pass


class PasswordChangeError(ValueError):
    pass


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = normalize_email(email)
    return db.scalar(select(User).where(User.email == normalized_email))


def get_user_by_google_sub(db: Session, google_sub: str) -> User | None:
    return db.scalar(select(User).where(User.google_sub == google_sub))


def create_user(db: Session, user_in: UserCreate) -> User:
    normalized_email = normalize_email(user_in.email)
    ensure_email_domain_allowed(normalized_email)

    display_name = normalized_email.split("@", 1)[0]
    company = Company(
        name="Configurar empresa",
        subscription_status=SubscriptionStatus.trialing,
        trial_ends_at=trial_end_date(),
    )
    user = User(
        company=company,
        name=display_name[:120],
        email=normalized_email,
        password_hash=hash_password(user_in.password),
        role=UserRole.company_admin,
    )
    db.add(company)
    db.add(user)
    db.commit()
    db.refresh(user)
    send_user_email_verification(db, user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def change_user_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    if not verify_password(current_password, user.password_hash):
        raise PasswordChangeError("A senha atual esta incorreta.")
    if verify_password(new_password, user.password_hash):
        raise PasswordChangeError("A nova senha deve ser diferente da senha atual.")

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_google_user(db: Session, google_user: GoogleUserInfo) -> User:
    normalized_email = normalize_email(google_user.email)
    ensure_email_domain_allowed(normalized_email)

    user = get_user_by_google_sub(db, google_user.sub)
    if user is not None:
        if not user.is_active:
            raise GoogleLoginError("Nao foi possivel concluir o login com Google.")
        return user

    user = get_user_by_email(db, normalized_email)
    if user is not None:
        if not user.is_active:
            raise GoogleLoginError("Nao foi possivel concluir o login com Google.")
        if user.google_sub is not None and user.google_sub != google_user.sub:
            raise GoogleLoginError("Nao foi possivel concluir o login com Google.")

        user.google_sub = google_user.sub
        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)
        user.email_verification_token_hash = None
        user.email_verification_expires_at = None
        db.commit()
        db.refresh(user)
        return user

    display_name = google_user.name.strip() or normalized_email.split("@", 1)[0]
    company = Company(
        name="Configurar empresa",
        subscription_status=SubscriptionStatus.trialing,
        trial_ends_at=trial_end_date(),
    )
    user = User(
        company=company,
        name=display_name[:120],
        email=normalized_email,
        password_hash=hash_password(secrets.token_urlsafe(48)),
        google_sub=google_user.sub,
        role=UserRole.company_admin,
        email_verified_at=datetime.now(UTC),
    )
    db.add(company)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
