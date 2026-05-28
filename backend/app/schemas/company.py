from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from app.models.company import SubscriptionStatus


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    subscription_status: SubscriptionStatus
    trial_ends_at: datetime
    subscription_valid_until: datetime | None
    opening_balance: Decimal
    opening_balance_date: date | None
    is_platform_company: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("opening_balance")
    def serialize_opening_balance(self, opening_balance: Decimal) -> str:
        return str(opening_balance)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    opening_balance: Decimal | None = Field(
        default=None,
        max_digits=14,
        decimal_places=2,
    )
    opening_balance_date: date | None = None


class OpeningBalanceUpdate(BaseModel):
    opening_balance: Decimal = Field(max_digits=14, decimal_places=2)
    opening_balance_date: date | None = None
