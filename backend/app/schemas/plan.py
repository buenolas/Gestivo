from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from app.models.plan import BillingCycle


class PlanResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    billing_cycle: BillingCycle
    duration_months: int
    price: Decimal
    is_active: bool
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("price")
    def serialize_price(self, price: Decimal) -> str:
        return str(price)


class PlanUpdate(BaseModel):
    price: Decimal | None = Field(default=None, ge=Decimal("0"), max_digits=14, decimal_places=2)
    is_active: bool | None = None
    description: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="forbid")
