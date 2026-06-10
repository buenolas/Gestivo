from uuid import UUID

from sqlalchemy.orm import Session

from app.models.usage_event import UsageEvent
from app.models.usage_event import UsageEventType


def record_usage_event(
    db: Session,
    *,
    company_id: UUID,
    user_id: UUID | None,
    event_type: UsageEventType,
    metadata: dict[str, object] | None = None,
    commit: bool = False,
) -> UsageEvent:
    event = UsageEvent(
        company_id=company_id,
        user_id=user_id,
        event_type=event_type,
        event_metadata=metadata,
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event
