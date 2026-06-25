import secrets

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Header
from fastapi import HTTPException
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.admin_clients import router as admin_clients_router
from app.api.admin_financial import router as admin_financial_router
from app.api.cash_flow import router as cash_flow_router
from app.api.companies import router as companies_router
from app.api.company_users import router as company_users_router
from app.api.contacts import router as contacts_router
from app.api.employees import router as employees_router
from app.api.exports import router as exports_router
from app.api.financial_categories import router as financial_categories_router
from app.api.financial_transactions import router as financial_transactions_router
from app.api.import_batches import router as import_batches_router
from app.api.payables import router as payables_router
from app.api.plans import router as plans_admin_router
from app.api.product_outputs import router as product_outputs_router
from app.api.reports import router as reports_router
from app.api.receivables import router as receivables_router
from app.api.subscriptions import admin_router as subscription_admin_router
from app.api.subscriptions import router as subscription_router
from app.core.config import settings
from app.db.session import get_db
from app.services.subscription import expire_overdue_subscriptions

fastapi_app = FastAPI(title=settings.app_name, debug=settings.app_debug)

fastapi_app.include_router(auth_router)
fastapi_app.include_router(admin_clients_router)
fastapi_app.include_router(admin_financial_router)
fastapi_app.include_router(cash_flow_router)
fastapi_app.include_router(companies_router)
fastapi_app.include_router(company_users_router)
fastapi_app.include_router(contacts_router)
fastapi_app.include_router(employees_router)
fastapi_app.include_router(exports_router)
fastapi_app.include_router(financial_categories_router)
fastapi_app.include_router(financial_transactions_router)
fastapi_app.include_router(import_batches_router)
fastapi_app.include_router(payables_router)
fastapi_app.include_router(plans_admin_router)
fastapi_app.include_router(product_outputs_router)
fastapi_app.include_router(receivables_router)
fastapi_app.include_router(reports_router)
fastapi_app.include_router(subscription_router)
fastapi_app.include_router(subscription_admin_router)


@fastapi_app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@fastapi_app.get("/internal/cron/expire-subscriptions", include_in_schema=False)
def expire_subscriptions_cron(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    expected_authorization = f"Bearer {settings.cron_secret}"
    if not authorization or not secrets.compare_digest(
        authorization,
        expected_authorization,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nao autorizado",
        )

    updated_count = expire_overdue_subscriptions(db)
    return {"status": "ok", "updated_count": updated_count}


app = CORSMiddleware(
    fastapi_app,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
