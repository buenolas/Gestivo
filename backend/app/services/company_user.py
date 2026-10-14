import secrets
import uuid
from datetime import UTC
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.models.user import UserRole
from app.schemas.company_user import CompanyUserCreate
from app.services.email_verification import send_company_user_invitation
from app.services.email_verification import EmailVerificationError
from app.services.email_verification import ensure_email_domain_allowed
from app.services.email_verification import normalize_email
from app.services.email_verification import token_hash


class CompanyUserError(ValueError):
    pass


def list_company_users(db: Session, admin: User) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.company_id == admin.company_id)
            .order_by(User.created_at, User.name)
        )
    )


def get_company_user(
    db: Session,
    admin: User,
    user_id: uuid.UUID,
) -> User | None:
    return db.scalar(
        select(User).where(
            User.id == user_id,
            User.company_id == admin.company_id,
        )
    )


def create_company_user(
    db: Session,
    admin: User,
    user_in: CompanyUserCreate,
) -> User:
    email = normalize_email(user_in.email)
    try:
        ensure_email_domain_allowed(email)
    except EmailVerificationError as error:
        raise CompanyUserError(str(error)) from error
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise CompanyUserError("Ja existe um usuario com este e-mail.")

    user = User(
        company_id=admin.company_id,
        name=user_in.name.strip(),
        email=email,
        password_hash=hash_password(secrets.token_urlsafe(48)),
        role=UserRole.user,
        is_active=False,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    send_company_user_invitation(db, user)
    return user


def resend_company_user_invitation(db: Session, user: User) -> None:
    if user.role != UserRole.user or user.is_active or user.email_verified_at is not None:
        raise CompanyUserError("Este usuário não tem um convite pendente.")
    send_company_user_invitation(db, user)


def accept_company_user_invitation(
    db: Session,
    token: str,
    new_password: str,
) -> None:
    user = db.scalar(
        select(User)
        .where(User.email_verification_token_hash == token_hash(token))
        .with_for_update()
    )
    if (
        user is None
        or user.role != UserRole.user
        or user.is_active
        or user.email_verified_at is not None
        or user.email_verification_expires_at is None
    ):
        raise CompanyUserError("Este convite é inválido, expirou ou já foi utilizado.")

    expires_at = user.email_verification_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise CompanyUserError("Este convite é inválido, expirou ou já foi utilizado.")

    user.password_hash = hash_password(new_password)
    user.email_verified_at = datetime.now(UTC)
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    user.is_active = True
    user.must_change_password = False
    db.add(user)
    db.commit()


def set_company_user_status(
    db: Session,
    admin: User,
    user: User,
    is_active: bool,
) -> User:
    if user.id == admin.id and not is_active:
        raise CompanyUserError("O administrador nao pode bloquear o proprio acesso.")
    if user.role != UserRole.user:
        raise CompanyUserError("Apenas usuarios funcionarios podem ter o status alterado.")
    if is_active and user.email_verified_at is None:
        raise CompanyUserError("O e-mail precisa ser confirmado antes de ativar este usuário.")

    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_company_user_password(
    db: Session,
    user: User,
    temporary_password: str,
) -> User:
    if user.role != UserRole.user:
        raise CompanyUserError("A senha de outro administrador nao pode ser redefinida.")

    user.password_hash = hash_password(temporary_password)
    user.must_change_password = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
