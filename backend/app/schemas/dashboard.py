from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_serializer

from app.models.financial_transaction import FinancialTransactionPaymentMethod
from app.models.financial_transaction import FinancialTransactionType


class DashboardAmountSummary(BaseModel):
    count: int
    total: Decimal

    @field_serializer("total")
    def serialize_total(self, total: Decimal) -> str:
        return str(total)


class DashboardDueAlert(BaseModel):
    transaction_id: UUID
    kind: FinancialTransactionType
    severity: Literal["yellow", "orange", "red"]
    title: str
    description: str
    amount: Decimal
    due_date: date
    days_until_due: int
    contact_name: str | None
    category_name: str | None

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return str(amount)


class DashboardPaymentMethodSummary(BaseModel):
    payment_method: FinancialTransactionPaymentMethod
    label: str
    income_total: Decimal
    expense_total: Decimal
    net_total: Decimal
    count: int

    @field_serializer("income_total", "expense_total", "net_total")
    def serialize_money(self, amount: Decimal) -> str:
        return str(amount)


class DashboardResponse(BaseModel):
    period_start: date
    period_end: date
    generated_at: datetime
    current_balance: Decimal
    month_income: Decimal
    month_expense: Decimal
    month_result: Decimal
    open_payables: DashboardAmountSummary
    open_receivables: DashboardAmountSummary
    overdue_payables: DashboardAmountSummary
    overdue_receivables: DashboardAmountSummary
    payment_methods: list[DashboardPaymentMethodSummary]
    due_alerts: list[DashboardDueAlert]
    month_end_balance_forecast: Decimal
    calculation_criteria: dict[str, str]

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "current_balance",
        "month_income",
        "month_expense",
        "month_result",
        "month_end_balance_forecast",
    )
    def serialize_money(self, amount: Decimal) -> str:
        return str(amount)
