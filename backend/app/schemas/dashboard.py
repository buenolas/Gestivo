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


class DashboardTrendPoint(BaseModel):
    date: date
    income: Decimal
    expense: Decimal
    result: Decimal
    transaction_count: int

    @field_serializer("income", "expense", "result")
    def serialize_money(self, amount: Decimal) -> str:
        return str(amount)


class DashboardCategorySummary(BaseModel):
    type: FinancialTransactionType
    name: str
    total: Decimal
    count: int

    @field_serializer("total")
    def serialize_total(self, total: Decimal) -> str:
        return str(total)


class DashboardComparison(BaseModel):
    period_start: date
    period_end: date
    income: Decimal
    expense: Decimal
    result: Decimal
    income_change: Decimal
    expense_change: Decimal
    result_change: Decimal
    income_change_percent: Decimal | None
    expense_change_percent: Decimal | None
    result_change_percent: Decimal | None
    transaction_count: int

    @field_serializer(
        "income",
        "expense",
        "result",
        "income_change",
        "expense_change",
        "result_change",
        "income_change_percent",
        "expense_change_percent",
        "result_change_percent",
    )
    def serialize_decimal(self, amount: Decimal | None) -> str | None:
        return str(amount) if amount is not None else None


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
    transaction_count: int
    trend_granularity: Literal["day", "month"]
    trend_series: list[DashboardTrendPoint]
    category_totals: list[DashboardCategorySummary]
    comparison: DashboardComparison | None
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
