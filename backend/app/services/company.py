from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyUpdate


def get_user_company(db: Session, user: User) -> Company | None:
    return db.get(Company, user.company_id)


def update_user_company(db: Session, user: User, company_in: CompanyUpdate) -> Company | None:
    company = get_user_company(db, user)
    if company is None:
        return None

    company.name = company_in.name.strip()
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
