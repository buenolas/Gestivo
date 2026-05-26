from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.models.contact import ContactType


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    type: ContactType
    is_active: bool = True


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    type: ContactType | None = None
    is_active: bool | None = None


class ContactResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    type: ContactType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
