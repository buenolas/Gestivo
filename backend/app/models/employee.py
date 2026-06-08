import enum
import uuid
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class EmployeeStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    ended = "ended"


class Employee(Base):
    __tablename__ = "employees"

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
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)
    salary_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    contract_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    contract_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, name="employee_status"),
        nullable=False,
        default=EmployeeStatus.active,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
