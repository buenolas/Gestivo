from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=72)


class GoogleLogin(BaseModel):
    id_token: str = Field(min_length=20, max_length=5000)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmailVerificationConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=300)


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    must_change_password: bool
    email_verified_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
