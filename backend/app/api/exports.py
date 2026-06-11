from datetime import date
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin
from app.db.session import get_db
from app.exports.financial_transactions import export_financial_transactions_csv
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/financial-transactions.csv")
def export_financial_transactions(
    type: FinancialTransactionType | None = None,
    status: FinancialTransactionStatus | None = None,
    category_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = Query(default=None, max_length=120),
    current_user: User = Depends(require_company_admin),
    db: Session = Depends(get_db),
) -> Response:
    csv_content = export_financial_transactions_csv(
        db=db,
        user=current_user,
        transaction_type=type,
        status=status,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="lancamentos-financeiros.csv"',
        },
    )
