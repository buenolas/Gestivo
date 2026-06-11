import uuid
from datetime import UTC
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.models.user import UserRole
from app.schemas.company_user import CompanyUserCreate
from app.services.email_verification import EmailVerificationError
from app.services.email_verification import ensure_email_domain_allowed
from app.services.email_verification import normalize_email


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
        password_hash=hash_password(user_in.temporary_password),
        role=UserRole.user,
        is_active=True,
        must_change_password=True,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
