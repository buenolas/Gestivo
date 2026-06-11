from uuid import UUID

import jwt
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.models.user import UserRole
from app.services.email_verification import can_access_customer_financial_routes
from app.services.subscription import get_subscription_status

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais de autenticação inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = UUID(str(payload.get("sub")))
    except (jwt.InvalidTokenError, ValueError):
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_valid_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if current_user.role == UserRole.platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administradores da plataforma não acessam rotas financeiras de empresas.",
        )

    if not can_access_customer_financial_routes(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirme seu e-mail para acessar recursos financeiros.",
        )

    if current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Altere sua senha temporaria antes de acessar o sistema.",
        )

    company = db.get(Company, current_user.company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa não encontrada",
        )

    if company.onboarding_completed_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conclua as configuracoes iniciais para acessar recursos financeiros.",
        )

    subscription = get_subscription_status(db, company)
    if not subscription.is_valid:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Assinatura inválida. Regularize a assinatura para acessar recursos financeiros.",
        )
    return current_user


def require_company_admin(
    current_user: User = Depends(require_valid_subscription),
) -> User:
    if current_user.role != UserRole.company_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores da empresa podem acessar este recurso.",
        )
    return current_user


def require_company_admin_account(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.company_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores da empresa podem acessar este recurso.",
        )
    return current_user


def require_platform_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores da plataforma podem acessar este recurso.",
        )
    return current_user
