from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class FinancialCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    parent_id: UUID | None = None
    is_active: bool = True


class FinancialCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_active: bool | None = None


class FinancialCategoryResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    parent_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
