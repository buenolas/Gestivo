from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer

from app.models.financial_transaction import FinancialTransactionType
from app.schemas.financial_transaction import FinancialTransactionResponse

MONEY_GT_ZERO = Decimal("0")


class CashFlowEntryCreate(BaseModel):
    description: str = Field(min_length=2, max_length=255)
    amount: Decimal = Field(gt=MONEY_GT_ZERO, max_digits=14, decimal_places=2)
    type: FinancialTransactionType
    competence_date: date
    contact_id: UUID | None = None
    employee_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)


class CashFlowSummary(BaseModel):
    income_total: Decimal
    expense_total: Decimal
    result: Decimal

    @field_serializer("income_total", "expense_total", "result")
    def serialize_money(self, amount: Decimal) -> str:
        return str(amount)


class CashFlowResponse(BaseModel):
    generated_at: datetime
    summary: CashFlowSummary
    items: list[FinancialTransactionResponse]
