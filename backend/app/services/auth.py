from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.security import verify_password
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.services.subscription import trial_end_date
from app.models.user import User
from app.models.user import UserRole
from app.schemas.auth import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    normalized_email = email.strip().lower()
    return db.scalar(select(User).where(User.email == normalized_email))


def create_user(db: Session, user_in: UserCreate) -> User:
    company = Company(
        name=user_in.company_name.strip(),
        subscription_status=SubscriptionStatus.trialing,
        trial_ends_at=trial_end_date(),
    )
    user = User(
        company=company,
        name=user_in.name.strip(),
        email=user_in.email.lower(),
        password_hash=hash_password(user_in.password),
        role=UserRole.company_admin,
    )
    db.add(company)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
