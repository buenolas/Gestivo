import uuid

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial_category import FinancialCategory
from app.models.user import User
from app.schemas.financial_category import FinancialCategoryCreate
from app.schemas.financial_category import FinancialCategoryUpdate


def list_financial_categories(db: Session, user: User) -> list[FinancialCategory]:
    return list(
        db.scalars(
            select(FinancialCategory)
            .where(FinancialCategory.company_id == user.company_id)
            .order_by(FinancialCategory.name)
        )
    )


def get_financial_category(
    db: Session,
    user: User,
    category_id: uuid.UUID,
) -> FinancialCategory | None:
    return db.scalar(
        select(FinancialCategory).where(
            FinancialCategory.id == category_id,
            FinancialCategory.company_id == user.company_id,
        )
    )


def financial_category_name_exists(
    db: Session,
    user: User,
    name: str,
    exclude_category_id: uuid.UUID | None = None,
) -> bool:
    normalized_name = name.strip().lower()
    query = select(FinancialCategory.id).where(
        FinancialCategory.company_id == user.company_id,
        func.lower(FinancialCategory.name) == normalized_name,
    )
    if exclude_category_id is not None:
        query = query.where(FinancialCategory.id != exclude_category_id)

    return db.scalar(query) is not None


def create_financial_category(
    db: Session,
    user: User,
    category_in: FinancialCategoryCreate,
) -> FinancialCategory:
    category = FinancialCategory(
        company_id=user.company_id,
        name=category_in.name.strip(),
        type=category_in.type,
        is_active=category_in.is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_financial_category(
    db: Session,
    category: FinancialCategory,
    category_in: FinancialCategoryUpdate,
) -> FinancialCategory:
    if category_in.name is not None:
        category.name = category_in.name.strip()
    if category_in.type is not None:
        category.type = category_in.type
    if category_in.is_active is not None:
        category.is_active = category_in.is_active

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def deactivate_financial_category(
    db: Session,
    category: FinancialCategory,
) -> FinancialCategory:
    category.is_active = False
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
