from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactCreate
from app.schemas.contact import ContactResponse
from app.schemas.contact import ContactUpdate
from app.services.contact import create_contact
from app.services.contact import deactivate_contact
from app.services.contact import get_contact
from app.services.contact import list_contacts
from app.services.contact import update_contact

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _get_user_contact_or_404(
    db: Session,
    current_user: User,
    contact_id: UUID,
) -> Contact:
    contact = get_contact(db, current_user, contact_id)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contato não encontrado",
        )
    return contact


@router.get("", response_model=list[ContactResponse])
def list_user_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Contact]:
    return list_contacts(db, current_user)


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_user_contact(
    contact_in: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Contact:
    return create_contact(db, current_user, contact_in)


@router.get("/{contact_id}", response_model=ContactResponse)
def get_user_contact(
    contact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Contact:
    return _get_user_contact_or_404(db, current_user, contact_id)


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_user_contact(
    contact_id: UUID,
    contact_in: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Contact:
    contact = _get_user_contact_or_404(db, current_user, contact_id)
    return update_contact(db, contact, contact_in)


@router.delete("/{contact_id}", response_model=ContactResponse)
def delete_user_contact(
    contact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Contact:
    contact = _get_user_contact_or_404(db, current_user, contact_id)
    return deactivate_contact(db, contact)
