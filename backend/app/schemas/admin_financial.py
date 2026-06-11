from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import field_serializer

from app.models.company import SubscriptionStatus


class AdminFinancialMetrics(BaseModel):
    mrr: Decimal
    arr: Decimal
    received_current_month: Decimal
    received_last_30_days: Decimal
    forecast_current_month: Decimal
    forecast_next_30_days: Decimal
    pending_revenue: Decimal
    overdue_revenue: Decimal
    lost_cancellations: Decimal
    lost_delinquency: Decimal
    average_ticket: Decimal
    paying_customers: int
    valid_subscriptions: int
    received_today: Decimal
    received_current_week: Decimal
    received_current_month_total: Decimal
    renewals_current_month: int
    renewals_next_7_days: int
    renewals_next_30_days: int
    monthly_financial_churn_rate: Decimal
    delinquency_rate: Decimal

    @field_serializer(
        "mrr",
        "arr",
        "received_current_month",
        "received_last_30_days",
        "forecast_current_month",
        "forecast_next_30_days",
        "pending_revenue",
        "overdue_revenue",
        "lost_cancellations",
        "lost_delinquency",
        "average_ticket",
        "received_today",
        "received_current_week",
        "received_current_month_total",
        "monthly_financial_churn_rate",
        "delinquency_rate",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)


class AdminFinancialSeriesPoint(BaseModel):
    month: str
    received: Decimal
    forecast: Decimal
    mrr: Decimal
    arr: Decimal
    pending: Decimal
    churn: Decimal
    average_ticket: Decimal
    payments_received: int

    @field_serializer(
        "received",
        "forecast",
        "mrr",
        "arr",
        "pending",
        "churn",
        "average_ticket",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return str(value)


class AdminFinancialBreakdown(BaseModel):
    label: str
    value: Decimal

    @field_serializer("value")
    def serialize_value(self, value: Decimal) -> str:
        return str(value)


class AdminFinancialDashboardResponse(BaseModel):
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    metrics: AdminFinancialMetrics
    monthly_series: list[AdminFinancialSeriesPoint]
    revenue_by_plan: list[AdminFinancialBreakdown]
    revenue_by_subscription_status: list[AdminFinancialBreakdown]


class AdminFinancialTableItem(BaseModel):
    company_id: UUID
    company_name: str
    plan_id: UUID | None
    plan_name: str | None
    plan_value: Decimal
    subscription_status: SubscriptionStatus
    payment_status: str
    payment_date: datetime | None
    next_due_date: datetime | None
    days_overdue: int
    payment_method: str | None
    received_amount: Decimal
    pending_amount: Decimal
    renewed_by_admin: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("plan_value", "received_amount", "pending_amount")
    def serialize_money(self, value: Decimal) -> str:
        return str(value)


class AdminFinancialTableResponse(BaseModel):
    items: list[AdminFinancialTableItem]
    total: int
    page: int
    page_size: int
    pages: int
