from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyResponse
from app.schemas.company import CompanyUpdate
from app.schemas.company import OpeningBalanceUpdate
from app.services.company import get_user_company
from app.services.company import update_opening_balance
from app.services.company import update_user_company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyResponse)
def get_my_company(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Company:
    company = get_user_company(db, current_user)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada",
        )
    return company


@router.patch("/me", response_model=CompanyResponse)
def update_my_company(
    company_in: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Company:
    company = update_user_company(db, current_user, company_in)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada",
        )
    return company


@router.patch("/me/opening-balance", response_model=CompanyResponse)
def update_my_opening_balance(
    balance_in: OpeningBalanceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Company:
    company = update_opening_balance(db, current_user, balance_in)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada",
        )
    return company
