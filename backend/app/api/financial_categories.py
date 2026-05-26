from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.financial_category import FinancialCategory
from app.models.user import User
from app.schemas.financial_category import FinancialCategoryCreate
from app.schemas.financial_category import FinancialCategoryResponse
from app.schemas.financial_category import FinancialCategoryUpdate
from app.services.financial_category import create_financial_category
from app.services.financial_category import deactivate_financial_category
from app.services.financial_category import financial_category_name_exists
from app.services.financial_category import get_financial_category
from app.services.financial_category import list_financial_categories
from app.services.financial_category import update_financial_category

router = APIRouter(prefix="/financial-categories", tags=["financial-categories"])


def _get_user_category_or_404(
    db: Session,
    current_user: User,
    category_id: UUID,
) -> FinancialCategory:
    category = get_financial_category(db, current_user, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria financeira não encontrada",
        )
    return category


def _raise_duplicate_name() -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Já existe uma categoria financeira com esse nome",
    )


@router.get("", response_model=list[FinancialCategoryResponse])
def list_categories(
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[FinancialCategory]:
    return list_financial_categories(db, current_user)


@router.post(
    "",
    response_model=FinancialCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category_in: FinancialCategoryCreate,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialCategory:
    if financial_category_name_exists(db, current_user, category_in.name):
        _raise_duplicate_name()

    return create_financial_category(db, current_user, category_in)


@router.get("/{category_id}", response_model=FinancialCategoryResponse)
def get_category(
    category_id: UUID,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialCategory:
    return _get_user_category_or_404(db, current_user, category_id)


@router.patch("/{category_id}", response_model=FinancialCategoryResponse)
def update_category(
    category_id: UUID,
    category_in: FinancialCategoryUpdate,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialCategory:
    category = _get_user_category_or_404(db, current_user, category_id)
    if category_in.name is not None and financial_category_name_exists(
        db,
        current_user,
        category_in.name,
        exclude_category_id=category.id,
    ):
        _raise_duplicate_name()

    return update_financial_category(db, category, category_in)


@router.delete("/{category_id}", response_model=FinancialCategoryResponse)
def delete_category(
    category_id: UUID,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> FinancialCategory:
    category = _get_user_category_or_404(db, current_user, category_id)
    return deactivate_financial_category(db, category)
