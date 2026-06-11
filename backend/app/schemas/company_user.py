from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field

from app.models.user import UserRole


class CompanyUserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    temporary_password: str = Field(min_length=8, max_length=72)


class CompanyUserStatusUpdate(BaseModel):
    is_active: bool


class CompanyUserPasswordReset(BaseModel):
    temporary_password: str = Field(min_length=8, max_length=72)


class CompanyUserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
