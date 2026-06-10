from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from app.models.company import SubscriptionStatus


class AdminMetricCard(BaseModel):
    key: str
    label: str
    value: int | Decimal

    @field_serializer("value")
    def serialize_value(self, value: int | Decimal) -> int | str:
        if isinstance(value, Decimal):
            return str(value)
        return value


class AdminChartPoint(BaseModel):
    label: str
    value: int | Decimal

    @field_serializer("value")
    def serialize_value(self, value: int | Decimal) -> int | str:
        if isinstance(value, Decimal):
            return str(value)
        return value


class AdminClientDashboardResponse(BaseModel):
    cards: list[AdminMetricCard]
    subscription_status: list[AdminChartPoint]
    new_clients_by_month: list[AdminChartPoint]
    trial_conversions_by_month: list[AdminChartPoint]
    cancellations_by_month: list[AdminChartPoint]
    active_base_by_month: list[AdminChartPoint]
    active_vs_risk: list[AdminChartPoint]
    plan_distribution: list[AdminChartPoint]
    most_active_by_transactions: list[AdminChartPoint]
    highest_financial_volume: list[AdminChartPoint]


class AdminClientListItem(BaseModel):
    company_id: UUID
    company_name: str
    admin_name: str | None
    admin_email: str | None
    subscription_status: SubscriptionStatus
    plan_id: UUID | None
    plan_name: str | None
    plan_price: Decimal | None
    created_at: datetime
    trial_started_at: datetime | None
    trial_ends_at: datetime
    subscription_started_at: datetime | None
    subscription_valid_until: datetime | None
    days_remaining: int | None
    last_login_at: datetime | None
    users_count: int
    financial_transactions_count: int
    imports_count: int
    usage_status: str
    is_at_risk: bool

    @field_serializer("plan_price")
    def serialize_price(self, price: Decimal | None) -> str | None:
        if price is None:
            return None
        return str(price)


class AdminClientListResponse(BaseModel):
    items: list[AdminClientListItem]
    total: int
    page: int
    page_size: int
    pages: int


class AdminClientDetailResponse(AdminClientListItem):
    blocked_at: datetime | None
    canceled_at: datetime | None
    users: list[dict[str, str | bool | None]]
    renewal_history: list[dict[str, str | None]]
    payment_history: list[dict[str, str | None]]
    usage_events: list[dict[str, str | None]]
    last_import_at: datetime | None


class AdminClientRenewRequest(BaseModel):
    plan_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=Decimal("0"), max_digits=14, decimal_places=2)
    paid_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class AdminClientPlanUpdate(BaseModel):
    plan_id: UUID


class AdminClientActionResponse(BaseModel):
    company_id: UUID
    status: SubscriptionStatus
    message: str

    model_config = ConfigDict(from_attributes=True)
