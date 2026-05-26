import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class ImportBatchFileType(str, enum.Enum):
    csv = "csv"
    xlsx = "xlsx"


class ImportBatchStatus(str, enum.Enum):
    uploaded = "uploaded"
    validated = "validated"
    confirmed = "confirmed"
    failed = "failed"


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[ImportBatchFileType] = mapped_column(
        Enum(ImportBatchFileType, name="import_batch_file_type"),
        nullable=False,
    )
    status: Mapped[ImportBatchStatus] = mapped_column(
        Enum(ImportBatchStatus, name="import_batch_status"),
        nullable=False,
        default=ImportBatchStatus.uploaded,
    )
    headers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    preview_rows: Mapped[list[dict[str, str | None]]] = mapped_column(JSON, nullable=False)
    raw_rows: Mapped[list[dict[str, str | None]]] = mapped_column(JSON, nullable=False)
    mapping: Mapped[dict[str, str | None] | None] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    duplicate_warnings: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    company = relationship("Company")
    creator = relationship("User", foreign_keys=[created_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])
