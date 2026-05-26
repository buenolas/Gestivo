from datetime import date
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_serializer


class DashboardAmountSummary(BaseModel):
    count: int
    total: Decimal

    @field_serializer("total")
    def serialize_total(self, total: Decimal) -> str:
        return str(total)


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
