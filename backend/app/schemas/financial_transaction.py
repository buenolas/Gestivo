from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType

MONEY_GT_ZERO = Decimal("0")


class FinancialTransactionCreate(BaseModel):
    description: str = Field(min_length=2, max_length=255)
    amount: Decimal = Field(gt=MONEY_GT_ZERO, max_digits=14, decimal_places=2)
    type: FinancialTransactionType
    competence_date: date
    due_date: date | None = None
    category_id: UUID | None = None
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class FinancialTransactionUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=2, max_length=255)
    amount: Decimal | None = Field(
        default=None,
        gt=MONEY_GT_ZERO,
        max_digits=14,
        decimal_places=2,
    )
    type: FinancialTransactionType | None = None
    competence_date: date | None = None
    due_date: date | None = None
    category_id: UUID | None = None
    contact_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class FinancialTransactionSettle(BaseModel):
    settled_at: datetime | None = None


class FinancialTransactionResponse(BaseModel):
    id: UUID
    company_id: UUID
    category_id: UUID | None
    contact_id: UUID | None
    employee_id: UUID | None
    import_batch_id: UUID | None
    description: str
    amount: Decimal
    type: FinancialTransactionType
    status: FinancialTransactionStatus
    competence_date: date
    reference_month: date | None
    due_date: date | None
    settled_at: datetime | None
    canceled_at: datetime | None
    deleted_at: datetime | None
    notes: str | None
    source: str
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return str(amount)


class FinancialTransactionListResponse(FinancialTransactionResponse):
    pass
