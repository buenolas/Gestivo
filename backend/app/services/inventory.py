import uuid
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.inventory_product import InventoryMovement
from app.models.inventory_product import InventoryMovementType
from app.models.inventory_product import InventoryProduct
from app.models.user import User
from app.models.user import UserRole
from app.schemas.inventory import InventoryProductCreate
from app.schemas.inventory import InventoryProductUpdate
from app.schemas.inventory import InventoryStockAdjustment

ZERO = Decimal("0.000")


class InventoryValidationError(ValueError):
    pass


class InventoryProductNotFoundError(InventoryValidationError):
    pass


def list_products(
    db: Session,
    user: User,
    *,
    include_inactive: bool = False,
    search: str | None = None,
) -> list[InventoryProduct]:
    query = select(InventoryProduct).where(InventoryProduct.company_id == user.company_id)
    if not include_inactive or user.role != UserRole.company_admin:
        query = query.where(InventoryProduct.is_active.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            InventoryProduct.name.ilike(term)
            | InventoryProduct.sku.ilike(term)
            | InventoryProduct.barcode.ilike(term)
        )
    return list(db.scalars(query.order_by(InventoryProduct.name.asc())))


def get_product(db: Session, user: User, product_id: UUID) -> InventoryProduct | None:
    return db.scalar(
        select(InventoryProduct).where(
            InventoryProduct.id == product_id,
            InventoryProduct.company_id == user.company_id,
        )
    )


def create_product(
    db: Session,
    user: User,
    product_in: InventoryProductCreate,
) -> InventoryProduct:
    product = InventoryProduct(
        id=uuid.uuid4(),
        company_id=user.company_id,
        name=product_in.name.strip(),
        sku=_normalize_sku(product_in.sku),
        barcode=_normalize_barcode(product_in.barcode),
        sale_price=product_in.sale_price,
        stock_quantity=product_in.initial_stock,
        unit=product_in.unit.strip() or "un",
        is_active=True,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(product)
    if product_in.initial_stock > ZERO:
        db.add(
            InventoryMovement(
                id=uuid.uuid4(),
                company_id=user.company_id,
                product_id=product.id,
                movement_type=InventoryMovementType.inbound,
                quantity_change=product_in.initial_stock,
                stock_after=product_in.initial_stock,
                notes="Estoque inicial",
                created_by=user.id,
            )
        )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise InventoryValidationError("Já existe um produto com esse SKU ou código de barras nesta empresa.") from error
    db.refresh(product)
    return product


def update_product(
    db: Session,
    user: User,
    product: InventoryProduct,
    product_in: InventoryProductUpdate,
) -> InventoryProduct:
    update_data = product_in.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is not None:
        product.name = update_data["name"].strip()
    if "sku" in update_data:
        product.sku = _normalize_sku(update_data["sku"])
    if "barcode" in update_data:
        product.barcode = _normalize_barcode(update_data["barcode"])
    if "sale_price" in update_data and update_data["sale_price"] is not None:
        product.sale_price = update_data["sale_price"]
    if "unit" in update_data and update_data["unit"] is not None:
        product.unit = update_data["unit"].strip() or "un"
    if "is_active" in update_data and update_data["is_active"] is not None:
        product.is_active = update_data["is_active"]
    product.updated_by = user.id
    db.add(product)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise InventoryValidationError("Já existe um produto com esse SKU ou código de barras nesta empresa.") from error
    db.refresh(product)
    return product


def set_product_stock(
    db: Session,
    user: User,
    product_id: UUID,
    adjustment: InventoryStockAdjustment,
) -> InventoryProduct:
    product = db.scalar(
        select(InventoryProduct)
        .where(
            InventoryProduct.id == product_id,
            InventoryProduct.company_id == user.company_id,
        )
        .with_for_update()
    )
    if product is None:
        raise InventoryProductNotFoundError("Produto não encontrado para a empresa autenticada.")
    before = product.stock_quantity
    change = adjustment.quantity - before
    if change == ZERO:
        raise InventoryValidationError("A quantidade informada já corresponde ao estoque atual.")

    product.stock_quantity = adjustment.quantity
    product.updated_by = user.id
    db.add(product)
    db.add(
        InventoryMovement(
            id=uuid.uuid4(),
            company_id=user.company_id,
            product_id=product.id,
            movement_type=(
                InventoryMovementType.inbound
                if change > ZERO
                else InventoryMovementType.adjustment
            ),
            quantity_change=change,
            stock_after=adjustment.quantity,
            notes=_strip_optional_text(adjustment.notes),
            created_by=user.id,
        )
    )
    db.commit()
    db.refresh(product)
    return product


def list_movements(
    db: Session,
    user: User,
    *,
    product_id: UUID | None = None,
) -> list[InventoryMovement]:
    query = select(InventoryMovement).where(InventoryMovement.company_id == user.company_id)
    if product_id is not None:
        query = query.where(InventoryMovement.product_id == product_id)
    return list(
        db.scalars(
            query.options(joinedload(InventoryMovement.product))
            .order_by(InventoryMovement.created_at.desc())
            .limit(100)
        )
    )


def _normalize_sku(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().upper()
    return cleaned or None


def _normalize_barcode(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
