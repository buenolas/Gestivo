from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.api.deps import require_plan_feature
from app.db.session import get_db
from app.models.user import User
from app.schemas.company_user import CompanyUserCreate
from app.schemas.company_user import CompanyUserInvitationAccept
from app.schemas.company_user import CompanyUserPasswordReset
from app.schemas.company_user import CompanyUserResponse
from app.schemas.company_user import CompanyUserStatusUpdate
from app.schemas.auth import MessageResponse
from app.services.email import EmailDeliveryError
from app.services.company_user import CompanyUserError
from app.services.company_user import accept_company_user_invitation
from app.services.company_user import create_company_user
from app.services.company_user import get_company_user
from app.services.company_user import list_company_users
from app.services.company_user import resend_company_user_invitation
from app.services.company_user import reset_company_user_password
from app.services.company_user import set_company_user_status

router = APIRouter(prefix="/company-users", tags=["company-users"])


def _get_user_or_404(db: Session, admin: User, user_id: UUID) -> User:
    user = get_company_user(db, admin, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario nao encontrado.",
        )
    return user


def _raise_company_user_error(error: CompanyUserError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(error),
    ) from error


@router.get(
    "",
    response_model=list[CompanyUserResponse],
    dependencies=[Depends(require_plan_feature("users"))],
)
def list_users(
    admin: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    return list_company_users(db, admin)


@router.post("/accept-invitation", response_model=MessageResponse)
def accept_invitation(
    invitation: CompanyUserInvitationAccept,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        accept_company_user_invitation(db, invitation.token, invitation.new_password)
    except CompanyUserError as error:
        _raise_company_user_error(error)
    return MessageResponse(message="Convite aceito. Você já pode entrar com seu e-mail e senha.")


@router.post(
    "",
    response_model=CompanyUserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_plan_feature("users"))],
)
def create_user(
    user_in: CompanyUserCreate,
    admin: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> User:
    try:
        return create_company_user(db, admin, user_in)
    except EmailDeliveryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Usuário criado como pendente, mas não foi possível enviar o convite. Verifique o envio de e-mails e tente reenviar.",
        ) from error
    except CompanyUserError as error:
        _raise_company_user_error(error)


@router.post(
    "/{user_id}/resend-invitation",
    response_model=MessageResponse,
    dependencies=[Depends(require_plan_feature("users"))],
)
def resend_invitation(
    user_id: UUID,
    admin: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = _get_user_or_404(db, admin, user_id)
    try:
        resend_company_user_invitation(db, user)
    except EmailDeliveryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível enviar o convite. Verifique o envio de e-mails e tente novamente.",
        ) from error
    except CompanyUserError as error:
        _raise_company_user_error(error)
    return MessageResponse(message=f"Convite reenviado para {user.email}.")


@router.patch(
    "/{user_id}/status",
    response_model=CompanyUserResponse,
    dependencies=[Depends(require_plan_feature("users"))],
)
def update_user_status(
    user_id: UUID,
    status_in: CompanyUserStatusUpdate,
    admin: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> User:
    user = _get_user_or_404(db, admin, user_id)
    try:
        return set_company_user_status(db, admin, user, status_in.is_active)
    except CompanyUserError as error:
        _raise_company_user_error(error)


@router.post(
    "/{user_id}/reset-password",
    response_model=CompanyUserResponse,
    dependencies=[Depends(require_plan_feature("users"))],
)
def reset_user_password(
    user_id: UUID,
    password_in: CompanyUserPasswordReset,
    admin: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> User:
    user = _get_user_or_404(db, admin, user_id)
    try:
        return reset_company_user_password(db, user, password_in.temporary_password)
    except CompanyUserError as error:
        _raise_company_user_error(error)
