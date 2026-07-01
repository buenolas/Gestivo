import logging

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.auth.google import GoogleTokenError
from app.auth.google import verify_google_id_token
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import EmailVerificationConfirm
from app.schemas.auth import GoogleLogin
from app.schemas.auth import MessageResponse
from app.schemas.auth import PasswordChange
from app.schemas.auth import PasswordResetConfirm
from app.schemas.auth import PasswordResetRequest
from app.schemas.auth import TokenResponse
from app.schemas.auth import UserCreate
from app.schemas.auth import UserLogin
from app.schemas.auth import UserResponse
from app.services.auth import authenticate_user
from app.services.auth import authenticate_google_user
from app.services.auth import change_user_password
from app.services.auth import create_user
from app.services.auth import GoogleLoginError
from app.services.auth import PasswordChangeError
from app.services.auth import get_user_by_email
from app.services.email_verification import EmailVerificationError
from app.services.email_verification import confirm_email
from app.services.email_verification import send_user_email_verification
from app.services.email import EmailDeliveryError
from app.services.password_reset import PASSWORD_RESET_GENERIC_MESSAGE
from app.services.password_reset import PasswordResetError
from app.services.password_reset import confirm_password_reset
from app.services.password_reset import request_password_reset
from app.models.usage_event import UsageEventType
from app.services.usage_event import record_usage_event

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    if get_user_by_email(db, user_in.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nao foi possivel concluir o cadastro com os dados informados.",
        )
    try:
        return create_user(db, user_in)
    except EmailVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmailDeliveryError as exc:
        created_user = get_user_by_email(db, user_in.email)
        if created_user is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nao foi possivel enviar o e-mail de verificacao.",
            ) from exc

        logger.warning(
            "User %s was registered, but verification e-mail delivery failed.",
            created_user.id,
        )
        return created_user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, credentials.email, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
        )

    record_usage_event(
        db,
        company_id=user.company_id,
        user_id=user.id,
        event_type=UsageEventType.login,
        commit=True,
    )
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/google", response_model=TokenResponse)
def google_login(credentials: GoogleLogin, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        google_user = verify_google_id_token(credentials.id_token)
        user = authenticate_google_user(db, google_user)
    except GoogleTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except (EmailVerificationError, GoogleLoginError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    record_usage_event(
        db,
        company_id=user.company_id,
        user_id=user.id,
        event_type=UsageEventType.login,
        commit=True,
    )
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", response_model=UserResponse)
def change_password(
    password_in: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    try:
        return change_user_password(
            db,
            current_user,
            password_in.current_password,
            password_in.new_password,
        )
    except PasswordChangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/password/forgot", response_model=MessageResponse)
def forgot_password(
    reset_in: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        request_password_reset(db, reset_in.email)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel enviar o codigo de recuperacao.",
        ) from exc
    return MessageResponse(message=PASSWORD_RESET_GENERIC_MESSAGE)


@router.post("/password/reset", response_model=MessageResponse)
def reset_password(
    reset_in: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        confirm_password_reset(
            db,
            reset_in.email,
            reset_in.code,
            reset_in.new_password,
        )
    except PasswordResetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MessageResponse(message="Senha redefinida. Entre com sua nova senha.")


@router.post("/email/confirm", response_model=MessageResponse)
def confirm_email_address(
    confirmation: EmailVerificationConfirm,
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not confirm_email(db, confirmation.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de verificacao invalido ou expirado.",
        )
    return MessageResponse(message="E-mail confirmado com sucesso.")


@router.post("/email/verification/resend", response_model=MessageResponse)
def resend_email_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        send_user_email_verification(db, current_user)
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel enviar o e-mail de verificacao.",
        ) from exc
    return MessageResponse(
        message="Se a conta ainda precisar de confirmacao, enviamos um novo link.",
    )
