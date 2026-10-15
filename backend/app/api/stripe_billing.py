from typing import Literal

import stripe
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_company_admin_account
from app.api.deps import require_platform_admin
from app.core.config import settings
from app.db.session import get_db
from app.models.company import Company
from app.models.stripe_webhook_event import StripeWebhookEvent
from app.models.user import User
from app.schemas.stripe_billing import CheckoutSessionCreate
from app.schemas.stripe_billing import HostedSessionResponse
from app.schemas.stripe_billing import StripeRiskEventResponse
from app.schemas.stripe_billing import SubscriptionUpgradeCreate
from app.services.stripe_billing import StripeBillingConflict
from app.services.stripe_billing import StripeBillingNotConfigured
from app.services.stripe_billing import create_billing_portal_session
from app.services.stripe_billing import create_checkout_session
from app.services.stripe_billing import create_subscription_upgrade_session
from app.services.stripe_billing import process_stripe_event

router = APIRouter(tags=["stripe-billing"])


@router.get("/admin/stripe/risk-events", response_model=list[StripeRiskEventResponse])
def list_stripe_risk_events(
    review_status: Literal["open", "reviewed"] = "open",
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[StripeRiskEventResponse]:
    events = db.scalars(
        select(StripeWebhookEvent)
        .where(StripeWebhookEvent.risk_review_status == review_status)
        .order_by(StripeWebhookEvent.event_created_at.desc())
        .limit(limit)
    ).all()
    company_ids = {event.company_id for event in events if event.company_id is not None}
    companies = (
        {
            company.id: company.name
            for company in db.scalars(select(Company).where(Company.id.in_(company_ids))).all()
        }
        if company_ids
        else {}
    )
    return [_risk_event_response(event, companies.get(event.company_id)) for event in events]


@router.patch(
    "/admin/stripe/risk-events/{event_id}/reviewed",
    response_model=StripeRiskEventResponse,
)
def mark_stripe_risk_event_reviewed(
    event_id: str,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> StripeRiskEventResponse:
    event = db.get(StripeWebhookEvent, event_id)
    if event is None or event.risk_review_status is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta não encontrado")
    event.risk_review_status = "reviewed"
    db.commit()
    db.refresh(event)
    company = db.get(Company, event.company_id) if event.company_id else None
    return _risk_event_response(event, company.name if company else None)


def _risk_event_response(
    event: StripeWebhookEvent,
    company_name: str | None,
) -> StripeRiskEventResponse:
    return StripeRiskEventResponse(
        event_id=event.id,
        event_type=event.event_type,
        event_created_at=event.event_created_at,
        received_at=event.received_at,
        company_id=event.company_id,
        company_name=company_name,
        stripe_object_id=event.risk_object_id,
        stripe_charge_id=event.risk_charge_id,
        review_status=event.risk_review_status,
    )


@router.post("/subscription/checkout", response_model=HostedSessionResponse)
def start_subscription_checkout(
    checkout_in: CheckoutSessionCreate,
    current_user: User = Depends(require_company_admin_account),
    db: Session = Depends(get_db),
) -> HostedSessionResponse:
    if not current_user.email_verified_at or current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirme seu e-mail e atualize sua senha antes de continuar.",
        )
    company = db.get(Company, current_user.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    if company.is_platform_company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operação indisponível")

    try:
        return HostedSessionResponse(
            url=create_checkout_session(db, company, current_user, checkout_in.plan_slug)
        )
    except StripeBillingConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except StripeBillingNotConfigured as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/subscription/upgrade", response_model=HostedSessionResponse)
def start_subscription_upgrade(
    upgrade_in: SubscriptionUpgradeCreate,
    current_user: User = Depends(require_company_admin_account),
    db: Session = Depends(get_db),
) -> HostedSessionResponse:
    if not current_user.email_verified_at or current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirme seu e-mail e atualize sua senha antes de continuar.",
        )
    company = db.get(Company, current_user.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    if company.is_platform_company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operação indisponível")

    try:
        return HostedSessionResponse(
            url=create_subscription_upgrade_session(db, company, upgrade_in.plan_slug)
        )
    except StripeBillingConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except StripeBillingNotConfigured as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/subscription/billing-portal", response_model=HostedSessionResponse)
def start_billing_portal(
    current_user: User = Depends(require_company_admin_account),
    db: Session = Depends(get_db),
) -> HostedSessionResponse:
    if not current_user.email_verified_at or current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirme seu e-mail e atualize sua senha antes de continuar.",
        )
    company = db.get(Company, current_user.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")
    if company.is_platform_company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operação indisponível")

    try:
        return HostedSessionResponse(url=create_billing_portal_session(company))
    except StripeBillingConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except StripeBillingNotConfigured as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/webhooks/stripe")
async def receive_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    webhook_secret = settings.stripe_webhook_secret.strip()
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook Stripe não está configurado.",
        )

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature or "", webhook_secret)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assinatura ou conteúdo do webhook Stripe inválido.",
        ) from error

    try:
        process_stripe_event(db, event)
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível processar o evento Stripe.",
        ) from error
    return {"received": True}
