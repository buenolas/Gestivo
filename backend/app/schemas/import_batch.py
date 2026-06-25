from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from app.models.import_batch import ImportBatchFileType
from app.models.import_batch import ImportBatchStatus


class ImportColumnMapping(BaseModel):
    date_column: str = Field(min_length=1)
    description_column: str = Field(min_length=1)
    type_column: str | None = Field(default=None, min_length=1)
    amount_column: str | None = Field(default=None, min_length=1)
    income_amount_column: str | None = Field(default=None, min_length=1)
    expense_amount_column: str | None = Field(default=None, min_length=1)
    due_date_column: str | None = Field(default=None, min_length=1)
    payment_method_column: str | None = Field(default=None, min_length=1)
    notes_column: str | None = Field(default=None, min_length=1)


class ImportErrorItem(BaseModel):
    row_number: int
    field: str
    message: str
    value: str | None = None


class ImportDuplicateWarning(BaseModel):
    row_number: int
    scope: str
    message: str


class ImportSummary(BaseModel):
    total_rows: int
    valid_rows: int
    error_rows: int
    duplicate_warnings: int
    income_count: int
    expense_count: int
    income_total: Decimal
    expense_total: Decimal
    import_mode: str

    @field_serializer("income_total", "expense_total")
    def serialize_money(self, amount: Decimal) -> str:
        return str(amount)


class ImportBatchResponse(BaseModel):
    id: UUID
    company_id: UUID
    filename: str
    file_type: ImportBatchFileType
    status: ImportBatchStatus
    headers: list[str]
    preview_rows: list[dict[str, str | None]]
    mapping: dict[str, str | None] | None
    validation_errors: list[ImportErrorItem]
    duplicate_warnings: list[ImportDuplicateWarning]
    summary: ImportSummary | None
    created_by: UUID
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportValidationResponse(ImportBatchResponse):
    pass


class ImportConfirmationResponse(BaseModel):
    batch: ImportBatchResponse
    created_transaction_ids: list[UUID]
