from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.api.deps import require_plan_feature
from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.inventory_product import InventoryProduct
from app.models.user import User
from app.schemas.inventory import InventoryMovementResponse
from app.schemas.inventory import InventoryProductCreate
from app.schemas.inventory import InventoryProductResponse
from app.schemas.inventory import InventoryProductUpdate
from app.schemas.inventory import InventoryStockAdjustment
from app.services.inventory import InventoryValidationError
from app.services.inventory import InventoryProductNotFoundError
from app.services.inventory import create_product
from app.services.inventory import get_product
from app.services.inventory import list_movements
from app.services.inventory import list_products
from app.services.inventory import set_product_stock
from app.services.inventory import update_product

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(require_plan_feature("inventory"))],
)


def _raise_validation_error(error: InventoryValidationError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


def _get_product_or_404(db: Session, user: User, product_id: UUID) -> InventoryProduct:
    product = get_product(db, user, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado para a empresa autenticada.",
        )
    return product


@router.get("/products", response_model=list[InventoryProductResponse])
def products(
    include_inactive: bool = False,
    search: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[InventoryProduct]:
    return list_products(db, current_user, include_inactive=include_inactive, search=search)


@router.post(
    "/products",
    response_model=InventoryProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(
    product_in: InventoryProductCreate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> InventoryProduct:
    try:
        return create_product(db, current_user, product_in)
    except InventoryValidationError as error:
        _raise_validation_error(error)


@router.patch("/products/{product_id}", response_model=InventoryProductResponse)
def update(
    product_id: UUID,
    product_in: InventoryProductUpdate,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> InventoryProduct:
    product = _get_product_or_404(db, current_user, product_id)
    try:
        return update_product(db, current_user, product, product_in)
    except InventoryValidationError as error:
        _raise_validation_error(error)


@router.post("/products/{product_id}/stock", response_model=InventoryProductResponse)
def adjust_stock(
    product_id: UUID,
    adjustment: InventoryStockAdjustment,
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> InventoryProduct:
    try:
        return set_product_stock(db, current_user, product_id, adjustment)
    except InventoryProductNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InventoryValidationError as error:
        _raise_validation_error(error)


@router.get("/movements", response_model=list[InventoryMovementResponse])
def movements(
    product_id: UUID | None = None,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
):
    if product_id is not None and get_product(db, current_user, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado para a empresa autenticada.",
        )
    return list_movements(db, current_user, product_id=product_id)
