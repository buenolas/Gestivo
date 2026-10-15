from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"
    __table_args__ = (
        Index("ix_stripe_webhook_events_risk_review_status", "risk_review_status"),
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    company_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_object_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    risk_review_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
