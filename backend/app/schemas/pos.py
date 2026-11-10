from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from app.models.financial_transaction import FinancialTransactionPaymentMethod
from app.models.pos_sale import POSQuoteStatus

ZERO = Decimal("0.00")
DiscountType = Literal["none", "percentage", "amount"]


class POSCartItem(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=14, decimal_places=3)


class POSPricingRequest(BaseModel):
    items: list[POSCartItem] = Field(min_length=1, max_length=100)
    discount_type: DiscountType = "none"
    discount_value: Decimal = Field(default=ZERO, ge=ZERO, max_digits=14, decimal_places=2)
    quote_id: UUID | None = None


class POSCheckoutRequest(POSPricingRequest):
    payment_method: FinancialTransactionPaymentMethod
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class POSQuoteCreateRequest(BaseModel):
    items: list[POSCartItem] = Field(min_length=1, max_length=100)
    customer_name: str = Field(min_length=2, max_length=160)
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class POSQuoteLine(BaseModel):
    product_id: UUID
    product_name: str
    sku: str | None
    barcode: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    line_total: Decimal
    stock_quantity: Decimal

    @field_serializer("quantity", "unit_price", "line_total", "stock_quantity")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)


class POSPricingResponse(BaseModel):
    items: list[POSQuoteLine]
    subtotal: Decimal
    discount_type: DiscountType
    discount_value: Decimal
    discount_amount: Decimal
    total: Decimal

    @field_serializer("subtotal", "discount_value", "discount_amount", "total")
    def serialize_amount(self, value: Decimal) -> str:
        return str(value)


class POSQuoteItemResponse(BaseModel):
    product_id: UUID
    product_name: str
    sku: str | None
    barcode: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    line_total: Decimal
    stock_quantity: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("quantity", "unit_price", "line_total", "stock_quantity")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)


class POSSavedQuoteResponse(BaseModel):
    id: UUID
    contact_id: UUID | None
    customer_name: str
    status: POSQuoteStatus
    total: Decimal
    notes: str | None
    created_at: datetime
    items: list[POSQuoteItemResponse]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("total")
    def serialize_total(self, value: Decimal) -> str:
        return str(value)


class POSSaleItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    sku: str | None
    barcode: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("quantity", "unit_price", "line_total")
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)


class POSSaleResponse(BaseModel):
    id: UUID
    financial_transaction_id: UUID
    quote_id: UUID | None
    contact_id: UUID | None
    payment_method: FinancialTransactionPaymentMethod
    subtotal: Decimal
    discount_type: DiscountType
    discount_value: Decimal
    discount_amount: Decimal
    total: Decimal
    notes: str | None
    sold_at: datetime
    items: list[POSSaleItemResponse]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("subtotal", "discount_value", "discount_amount", "total")
    def serialize_amount(self, value: Decimal) -> str:
        return str(value)
