import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactCreate
from app.schemas.contact import ContactUpdate


def list_contacts(db: Session, user: User) -> list[Contact]:
    return list(
        db.scalars(
            select(Contact)
            .where(Contact.company_id == user.company_id)
            .order_by(Contact.name)
        )
    )


def get_contact(
    db: Session,
    user: User,
    contact_id: uuid.UUID,
) -> Contact | None:
    return db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.company_id == user.company_id,
        )
    )


def create_contact(
    db: Session,
    user: User,
    contact_in: ContactCreate,
) -> Contact:
    contact = Contact(
        company_id=user.company_id,
        name=contact_in.name.strip(),
        type=contact_in.type,
        is_active=contact_in.is_active,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_contact(
    db: Session,
    contact: Contact,
    contact_in: ContactUpdate,
) -> Contact:
    if contact_in.name is not None:
        contact.name = contact_in.name.strip()
    if contact_in.type is not None:
        contact.type = contact_in.type
    if contact_in.is_active is not None:
        contact.is_active = contact_in.is_active

    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def deactivate_contact(db: Session, contact: Contact) -> Contact:
    contact.is_active = False
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
