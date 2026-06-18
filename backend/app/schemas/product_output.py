from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from app.schemas.financial_transaction import FinancialTransactionResponse

MONEY_GT_ZERO = Decimal("0")


class ProductOutputCreate(BaseModel):
    employee_id: UUID
    product_name: str = Field(min_length=2, max_length=160)
    unit_price: Decimal = Field(gt=MONEY_GT_ZERO, max_digits=14, decimal_places=2)
    quantity: Decimal = Field(gt=MONEY_GT_ZERO, max_digits=14, decimal_places=3)
    unit: str = Field(default="un", max_length=20)
    competence_date: date
    notes: str | None = Field(default=None, max_length=1000)


class ProductOutputUpdate(BaseModel):
    employee_id: UUID | None = None
    product_name: str | None = Field(default=None, min_length=2, max_length=160)
    unit_price: Decimal | None = Field(
        default=None,
        gt=MONEY_GT_ZERO,
        max_digits=14,
        decimal_places=2,
    )
    quantity: Decimal | None = Field(
        default=None,
        gt=MONEY_GT_ZERO,
        max_digits=14,
        decimal_places=3,
    )
    unit: str | None = Field(default=None, max_length=20)
    competence_date: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ProductOutputResponse(FinancialTransactionResponse):
    pass
