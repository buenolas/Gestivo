from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.models.company import SubscriptionStatus


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    subscription_status: SubscriptionStatus
    trial_ends_at: datetime
    subscription_valid_until: datetime | None
    is_platform_company: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
