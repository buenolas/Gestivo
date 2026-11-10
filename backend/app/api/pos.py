from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_plan_feature
from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.inventory_product import InventoryProduct
from app.models.pos_sale import POSSale
from app.models.user import User
from app.schemas.inventory import InventoryProductResponse
from app.schemas.pos import POSCheckoutRequest
from app.schemas.pos import POSPricingRequest
from app.schemas.pos import POSPricingResponse
from app.schemas.pos import POSQuoteCreateRequest
from app.schemas.pos import POSSavedQuoteResponse
from app.schemas.pos import POSSaleResponse
from app.services.pos import POSValidationError
from app.services.pos import checkout_pos_sale
from app.services.pos import create_pos_quote
from app.services.pos import list_pos_products
from app.services.pos import list_pos_quotes
from app.services.pos import list_pos_sales
from app.services.pos import quote_pos_sale

router = APIRouter(
    prefix="/pos",
    tags=["pos"],
    dependencies=[Depends(require_plan_feature("point_of_sale"))],
)


def _raise_validation_error(error: POSValidationError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/products", response_model=list[InventoryProductResponse])
def products(
    search: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[InventoryProduct]:
    return list_pos_products(db, current_user, search)


@router.post("/quote", response_model=POSPricingResponse)
def quote(
    quote_in: POSPricingRequest,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> POSPricingResponse:
    try:
        return quote_pos_sale(
            db,
            current_user,
            quote_in.items,
            discount_type=quote_in.discount_type,
            discount_value=quote_in.discount_value,
            quote_id=quote_in.quote_id,
        )
    except POSValidationError as error:
        _raise_validation_error(error)


@router.get("/quotes", response_model=list[POSSavedQuoteResponse])
def quotes(
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
):
    return list_pos_quotes(db, current_user)


@router.post("/quotes", response_model=POSSavedQuoteResponse, status_code=status.HTTP_201_CREATED)
def create_quote(
    quote_in: POSQuoteCreateRequest,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
):
    try:
        return create_pos_quote(db, current_user, quote_in)
    except POSValidationError as error:
        _raise_validation_error(error)


@router.get("/sales", response_model=list[POSSaleResponse])
def sales(
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> list[POSSale]:
    return list_pos_sales(db, current_user)


@router.post("/sales", response_model=POSSaleResponse, status_code=status.HTTP_201_CREATED)
def checkout(
    sale_in: POSCheckoutRequest,
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> POSSale:
    try:
        return checkout_pos_sale(db, current_user, sale_in)
    except POSValidationError as error:
        _raise_validation_error(error)
