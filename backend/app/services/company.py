from datetime import UTC
from datetime import date
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyOnboardingComplete
from app.schemas.company import CompanyUpdate
from app.schemas.company import OpeningBalanceUpdate


def get_user_company(db: Session, user: User) -> Company | None:
    return db.get(Company, user.company_id)


def update_user_company(db: Session, user: User, company_in: CompanyUpdate) -> Company | None:
    company = get_user_company(db, user)
    if company is None:
        return None

    if company_in.name is not None:
        company.name = company_in.name.strip()
    if company_in.opening_balance is not None:
        company.opening_balance = company_in.opening_balance
    if "opening_balance_date" in company_in.model_fields_set:
        company.opening_balance_date = company_in.opening_balance_date
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def update_opening_balance(
    db: Session,
    user: User,
    balance_in: OpeningBalanceUpdate,
) -> Company | None:
    company = get_user_company(db, user)
    if company is None:
        return None

    company.opening_balance = balance_in.opening_balance
    company.opening_balance_date = balance_in.opening_balance_date
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def complete_company_onboarding(
    db: Session,
    user: User,
    onboarding_in: CompanyOnboardingComplete,
) -> Company | None:
    company = get_user_company(db, user)
    if company is None:
        return None
    if company.onboarding_completed_at is not None:
        return company

    company.name = onboarding_in.company_name.strip()
    company.opening_balance = onboarding_in.opening_balance
    company.opening_balance_date = date.today()
    company.onboarding_completed_at = datetime.now(UTC)
    user.name = onboarding_in.user_name.strip()
    db.add(company)
    db.add(user)
    db.commit()
    db.refresh(company)
    db.refresh(user)
    return company
