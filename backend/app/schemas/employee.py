from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer
from pydantic import model_validator

from app.models.employee import EmployeeStatus
from app.schemas.financial_transaction import FinancialTransactionResponse

MONEY_GT_ZERO = Decimal("0")


class EmployeeBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    position: str | None = Field(default=None, max_length=120)
    salary_amount: Decimal = Field(gt=MONEY_GT_ZERO, max_digits=14, decimal_places=2)
    contract_start_date: date
    contract_end_date: date | None = None
    status: EmployeeStatus = EmployeeStatus.active
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_contract_dates(self):
        if (
            self.contract_end_date is not None
            and self.contract_end_date < self.contract_start_date
        ):
            raise ValueError("A data final do contrato deve ser posterior ao inicio")
        return self


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    position: str | None = Field(default=None, max_length=120)
    salary_amount: Decimal | None = Field(
        default=None,
        gt=MONEY_GT_ZERO,
        max_digits=14,
        decimal_places=2,
    )
    contract_start_date: date | None = None
    contract_end_date: date | None = None
    status: EmployeeStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)


class EmployeeResponse(BaseModel):
    id: UUID
    company_id: UUID
    name: str
    position: str | None
    salary_amount: Decimal
    contract_start_date: date
    contract_end_date: date | None
    status: EmployeeStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("salary_amount")
    def serialize_salary_amount(self, salary_amount: Decimal) -> str:
        return str(salary_amount)


class EmployeeOptionResponse(BaseModel):
    id: UUID
    name: str
    status: EmployeeStatus

    model_config = ConfigDict(from_attributes=True)


class SalaryExpenseGenerationCreate(BaseModel):
    reference_month: date = Field(
        description="Qualquer data dentro do mes de competencia a gerar."
    )
    due_date: date | None = None


class SalaryExpenseGenerationResponse(BaseModel):
    reference_month: date
    created_count: int
    skipped_count: int
    transactions: list[FinancialTransactionResponse]
