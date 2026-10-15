from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class CheckoutSessionCreate(BaseModel):
    plan_slug: Literal["basic", "intermediate", "advanced", "pro"]

    model_config = ConfigDict(extra="forbid")


class SubscriptionUpgradeCreate(BaseModel):
    plan_slug: Literal["basic", "intermediate", "advanced", "pro"]

    model_config = ConfigDict(extra="forbid")


class HostedSessionResponse(BaseModel):
    url: str


class StripeRiskEventResponse(BaseModel):
    event_id: str
    event_type: str
    event_created_at: datetime
    received_at: datetime
    company_id: UUID | None
    company_name: str | None
    stripe_object_id: str | None
    stripe_charge_id: str | None
    review_status: Literal["open", "reviewed"]
