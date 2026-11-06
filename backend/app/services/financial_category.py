import uuid

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.financial_category import FinancialCategory
from app.models.financial_category import FinancialCategoryType
from app.models.user import User
from app.schemas.financial_category import FinancialCategoryCreate
from app.schemas.financial_category import FinancialCategoryUpdate


class FinancialCategoryValidationError(ValueError):
    pass


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
    if category_in.parent_id is not None:
        parent = db.scalar(
            select(FinancialCategory).where(
                FinancialCategory.id == category_in.parent_id,
                FinancialCategory.company_id == user.company_id,
                FinancialCategory.is_active.is_(True),
            )
        )
        if parent is None:
            raise FinancialCategoryValidationError("A categoria principal não foi encontrada ou está inativa.")
        if parent.parent_id is not None:
            raise FinancialCategoryValidationError("Subcategorias só podem ficar um nível abaixo da categoria principal.")

    category = FinancialCategory(
        company_id=user.company_id,
        name=category_in.name.strip(),
        parent_id=category_in.parent_id,
        type=FinancialCategoryType.both,
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
    if category_in.is_active is True and category.parent_id is not None:
        parent = db.scalar(
            select(FinancialCategory).where(
                FinancialCategory.id == category.parent_id,
                FinancialCategory.company_id == category.company_id,
                FinancialCategory.parent_id.is_(None),
                FinancialCategory.is_active.is_(True),
            )
        )
        if parent is None:
            raise FinancialCategoryValidationError("Ative a categoria principal antes de reativar esta subcategoria.")

    if category_in.name is not None:
        category.name = category_in.name.strip()
    if category_in.is_active is not None:
        if category_in.is_active:
            category.is_active = True
        else:
            _deactivate_category_tree(db, category)

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def deactivate_financial_category(
    db: Session,
    category: FinancialCategory,
) -> FinancialCategory:
    _deactivate_category_tree(db, category)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _deactivate_category_tree(db: Session, category: FinancialCategory) -> None:
    category.is_active = False
    if category.parent_id is None:
        db.execute(
            update(FinancialCategory)
            .where(
                FinancialCategory.company_id == category.company_id,
                FinancialCategory.parent_id == category.id,
            )
            .values(is_active=False)
        )
