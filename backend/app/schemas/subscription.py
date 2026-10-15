from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from app.models.company import SubscriptionStatus

MONEY_GT_ZERO = Decimal("0")


class SubscriptionStatusResponse(BaseModel):
    company_id: UUID
    status: SubscriptionStatus
    is_valid: bool
    can_manage_billing: bool = False
    trial_ends_at: datetime
    subscription_valid_until: datetime | None
    access_until: datetime | None
    plan_id: UUID | None = None
    plan_name: str | None = None
    plan_slug: str | None = None
    feature_codes: list[str] = Field(default_factory=list)
    ai_daily_limit: int | None = None
    ai_interactions_used_today: int = 0


class AdminCompanySubscriptionResponse(SubscriptionStatusResponse):
    company_name: str
    current_plan_id: UUID | None = None
    current_plan_name: str | None = None


class ManualRenewalCreate(BaseModel):
    company_id: UUID
    plan_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=MONEY_GT_ZERO, max_digits=14, decimal_places=2)
    paid_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class ManualPaymentResponse(BaseModel):
    id: UUID
    company_id: UUID
    plan_id: UUID | None
    plan_slug: str | None
    billing_cycle: str | None
    duration_months: int | None
    price_at_payment: Decimal | None
    amount: Decimal
    status: str
    payment_method: str
    paid_at: datetime | None
    due_date: datetime | None
    period_start: datetime
    period_end: datetime
    notes: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return str(amount)

    @field_serializer("price_at_payment")
    def serialize_price_at_payment(self, price: Decimal | None) -> str | None:
        if price is None:
            return None
        return str(price)
