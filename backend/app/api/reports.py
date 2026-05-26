from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps import require_valid_subscription
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import get_financial_dashboard

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(require_valid_subscription),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    return get_financial_dashboard(db, current_user)
