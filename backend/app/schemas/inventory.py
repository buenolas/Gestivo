from decimal import Decimal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

ZERO = Decimal("0")
MONEY_GT_ZERO = Decimal("0")


class InventoryProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=80)
    sale_price: Decimal = Field(gt=MONEY_GT_ZERO, max_digits=14, decimal_places=2)
    initial_stock: Decimal = Field(default=ZERO, ge=ZERO, max_digits=14, decimal_places=3)
    unit: str = Field(default="un", min_length=1, max_length=20)


class InventoryProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    sku: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, max_length=80)
    sale_price: Decimal | None = Field(default=None, gt=MONEY_GT_ZERO, max_digits=14, decimal_places=2)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    is_active: bool | None = None


class InventoryStockAdjustment(BaseModel):
    quantity: Decimal = Field(ge=ZERO, max_digits=14, decimal_places=3)
    notes: str | None = Field(default=None, max_length=1000)


class InventoryProductResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    sku: str | None
    barcode: str | None
    sale_price: Decimal
    stock_quantity: Decimal
    unit: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("sale_price", "stock_quantity")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)


class InventoryMovementResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_unit: str
    sale_id: UUID | None
    movement_type: str
    quantity_change: Decimal
    stock_after: Decimal
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("quantity_change", "stock_after")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)
