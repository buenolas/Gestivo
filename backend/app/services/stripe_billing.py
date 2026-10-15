from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from decimal import Decimal
import secrets
import string
from typing import Any
from uuid import UUID

import stripe
from stripe import StripeClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.plan import BillingCycle
from app.models.plan import Plan
from app.models.stripe_webhook_event import StripeWebhookEvent
from app.models.user import User
from app.services.subscription import refresh_subscription_status

STRIPE_API_VERSION = "2026-09-30.endive"
STRIPE_RISK_EVENT_TYPES = {
    "charge.refunded",
    "charge.dispute.created",
    "radar.early_fraud_warning.created",
}


class StripeBillingNotConfigured(ValueError):
    pass


class StripeBillingConflict(ValueError):
    pass


def create_checkout_session(db: Session, company: Company, user: User, plan_slug: str) -> str:
    secret_key = _configured_api_key()

    refresh_subscription_status(db, company)
    if company.subscription_status == SubscriptionStatus.blocked:
        raise StripeBillingConflict("Esta conta foi bloqueada pelo administrador da plataforma.")
    if company.subscription_status in {SubscriptionStatus.active, SubscriptionStatus.trialing}:
        raise StripeBillingConflict("A assinatura ainda está válida.")
    if company.subscription_status not in {
        SubscriptionStatus.pending_payment,
        SubscriptionStatus.canceled,
    }:
        raise StripeBillingConflict("A assinatura não pode iniciar um novo checkout neste estado.")
    if company.stripe_subscription_id and company.stripe_subscription_status not in {
        "canceled",
        "incomplete_expired",
    }:
        raise StripeBillingConflict(
            "Já existe uma assinatura Stripe vinculada. Atualize o pagamento pela área de cobrança."
        )

    plan = db.scalar(select(Plan).where(Plan.slug == plan_slug))
    if plan is None or not plan.is_active or plan.billing_cycle != BillingCycle.monthly:
        raise StripeBillingConflict("O plano selecionado não está disponível.")

    price_id = settings.stripe_price_id_for_plan(plan.slug)
    if not price_id:
        raise StripeBillingNotConfigured("O preço Stripe deste plano ainda não está configurado.")

    metadata = {"company_id": str(company.id), "plan_slug": plan.slug}
    frontend_url = settings.frontend_url.rstrip("/")
    integration_suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
    try:
        client = StripeClient(secret_key)
        stripe_price = client.v1.prices.retrieve(
            price_id,
            options={"stripe_version": STRIPE_API_VERSION},
        )
        _validate_monthly_brl_price(stripe_price, plan.price)
        checkout_params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{frontend_url}/?checkout=success#/transactions",
            "cancel_url": f"{frontend_url}/?checkout=cancelled#/transactions",
            "client_reference_id": str(company.id),
            "metadata": metadata,
            "subscription_data": {"metadata": metadata},
            "integration_identifier": f"gestivo-subscription-{integration_suffix}",
        }
        if company.stripe_customer_id:
            checkout_params["customer"] = company.stripe_customer_id
        else:
            checkout_params["customer_email"] = user.email
        session = client.v1.checkout.sessions.create(
            checkout_params,
            options={"stripe_version": STRIPE_API_VERSION},
        )
    except stripe.StripeError as error:
        raise StripeBillingNotConfigured("Não foi possível iniciar o checkout Stripe.") from error

    checkout_url = _value(session, "url")
    if not isinstance(checkout_url, str) or not checkout_url.startswith("https://"):
        raise StripeBillingNotConfigured("O Stripe não retornou um endereço de checkout válido.")
    return checkout_url


def _validate_monthly_brl_price(price: Any, expected_amount: Decimal) -> None:
    recurring = _value(price, "recurring", {})
    unit_amount = _value(price, "unit_amount")
    expected_minor_units = int(expected_amount * Decimal("100"))
    if (
        _value(price, "active") is not True
        or str(_value(price, "currency", "")).lower() != "brl"
        or _value(recurring, "interval") != "month"
        or _value(recurring, "interval_count", 1) != 1
        or isinstance(unit_amount, bool)
        or not isinstance(unit_amount, int)
        or unit_amount != expected_minor_units
    ):
        raise StripeBillingNotConfigured(
            "O Price Stripe precisa estar ativo, ser mensal em BRL e ter o mesmo valor do plano."
        )


def create_subscription_upgrade_session(db: Session, company: Company, plan_slug: str) -> str:
    secret_key = _configured_api_key()
    refresh_subscription_status(db, company)
    if company.subscription_status != SubscriptionStatus.active:
        raise StripeBillingConflict("Somente assinaturas ativas podem fazer upgrade de plano.")
    if not company.stripe_customer_id or not company.stripe_subscription_id:
        raise StripeBillingConflict("Esta empresa não possui uma assinatura Stripe ativa vinculada.")

    plan = db.scalar(select(Plan).where(Plan.slug == plan_slug))
    if plan is None or not plan.is_active or plan.billing_cycle != BillingCycle.monthly:
        raise StripeBillingConflict("O plano selecionado não está disponível.")
    target_price_id = settings.stripe_price_id_for_plan(plan.slug)
    if not target_price_id:
        raise StripeBillingNotConfigured("O preço Stripe deste plano ainda não está configurado.")

    plan_order = {"basic": 0, "intermediate": 1, "advanced": 2, "pro": 3}
    client = StripeClient(secret_key)
    try:
        subscription = client.v1.subscriptions.retrieve(
            company.stripe_subscription_id,
            options={"stripe_version": STRIPE_API_VERSION},
        )
        if _object_id(_value(subscription, "customer")) != company.stripe_customer_id:
            raise StripeBillingConflict("A assinatura Stripe não pertence a esta empresa.")
        if _value(subscription, "status") != "active":
            raise StripeBillingConflict("A assinatura Stripe não está ativa para receber um upgrade.")

        items = _value(_value(subscription, "items", {}), "data", []) or []
        if len(items) != 1:
            raise StripeBillingConflict("Não foi possível identificar o plano atual da assinatura.")
        current_item = items[0]
        current_item_id = _object_id(current_item)
        current_price_id = _object_id(_value(current_item, "price"))
        current_plan_slug = _plan_slug_for_price_id(current_price_id)
        if not current_item_id or current_plan_slug is None:
            raise StripeBillingConflict("Não foi possível identificar o plano atual da assinatura.")
        if plan_order[plan.slug] <= plan_order[current_plan_slug]:
            raise StripeBillingConflict("Escolha um plano acima do seu plano atual para fazer upgrade.")

        target_price = client.v1.prices.retrieve(
            target_price_id,
            options={"stripe_version": STRIPE_API_VERSION},
        )
        _validate_monthly_brl_price(target_price, plan.price)
        quantity = _value(current_item, "quantity", 1)
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity != 1:
            raise StripeBillingConflict("A assinatura possui uma quantidade incompatível com os planos Gestivo.")

        frontend_url = settings.frontend_url.rstrip("/")
        params: dict[str, Any] = {
            "customer": company.stripe_customer_id,
            "return_url": f"{frontend_url}/#/plans",
            "flow_data": {
                "type": "subscription_update_confirm",
                "subscription_update_confirm": {
                    "subscription": company.stripe_subscription_id,
                    "items": [{"id": current_item_id, "quantity": quantity, "price": target_price_id}],
                },
                "after_completion": {
                    "type": "redirect",
                    "redirect": {"return_url": f"{frontend_url}/#/plans"},
                },
            },
        }
        configuration_id = settings.stripe_billing_portal_configuration_id.strip()
        if configuration_id:
            params["configuration"] = configuration_id
        session = client.v1.billing_portal.sessions.create(
            params,
            options={"stripe_version": STRIPE_API_VERSION},
        )
    except StripeBillingConflict:
        raise
    except stripe.StripeError as error:
        raise StripeBillingNotConfigured(
            "Não foi possível preparar o upgrade. Verifique se o portal Stripe permite troca de planos e inclui este preço."
        ) from error

    portal_url = _value(session, "url")
    if not isinstance(portal_url, str) or not portal_url.startswith("https://"):
        raise StripeBillingNotConfigured("O Stripe não retornou um endereço de confirmação válido.")
    return portal_url


def _plan_slug_for_price_id(price_id: str | None) -> str | None:
    if not price_id:
        return None
    for slug in ("basic", "intermediate", "advanced", "pro"):
        if settings.stripe_price_id_for_plan(slug) == price_id:
            return slug
    return None


def _configured_api_key() -> str:
    secret_key = settings.stripe_secret_key.strip()
    if not secret_key:
        raise StripeBillingNotConfigured("A chave secreta Stripe ainda não está configurada.")
    if settings.app_env.lower() == "production":
        if not secret_key.startswith(("sk_live_", "rk_live_")):
            raise StripeBillingNotConfigured(
                "Configure uma chave Stripe de produção no ambiente de produção."
            )
    elif not secret_key.startswith(("sk_test_", "rk_test_")):
        raise StripeBillingNotConfigured(
            "Use uma chave Stripe de teste enquanto o ambiente não for produção."
        )
    return secret_key


def create_billing_portal_session(company: Company) -> str:
    secret_key = _configured_api_key()
    if not company.stripe_customer_id:
        raise StripeBillingConflict("Esta empresa ainda não possui uma conta de cobrança Stripe.")

    params: dict[str, Any] = {
        "customer": company.stripe_customer_id,
        "return_url": f"{settings.frontend_url.rstrip('/')}/#/transactions",
    }
    if settings.stripe_billing_portal_configuration_id.strip():
        params["configuration"] = settings.stripe_billing_portal_configuration_id.strip()
    try:
        client = StripeClient(secret_key)
        session = client.v1.billing_portal.sessions.create(
            params,
            options={"stripe_version": STRIPE_API_VERSION},
        )
    except stripe.StripeError as error:
        raise StripeBillingNotConfigured("Não foi possível abrir a área de cobrança Stripe.") from error

    portal_url = _value(session, "url")
    if not isinstance(portal_url, str) or not portal_url.startswith("https://"):
        raise StripeBillingNotConfigured("O Stripe não retornou um endereço de cobrança válido.")
    return portal_url


def process_stripe_event(db: Session, event: Any) -> bool:
    event_id = _value(event, "id")
    event_type = _value(event, "type")
    event_created = _epoch_datetime(_value(event, "created"))
    if not isinstance(event_id, str) or not event_id or not isinstance(event_type, str):
        raise ValueError("Evento Stripe inválido")
    if event_created is None:
        raise ValueError("Evento Stripe sem data válida")
    if db.get(StripeWebhookEvent, event_id) is not None:
        return False

    event_record = StripeWebhookEvent(
        id=event_id,
        event_type=event_type,
        event_created_at=event_created,
    )
    db.add(event_record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return False

    data = _value(event, "data", {})
    resource = _value(data, "object", {})
    try:
        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            _remember_checkout(db, resource, event_created)
        elif event_type == "checkout.session.async_payment_failed":
            _remember_failed_checkout(db, resource, event_created)
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            _apply_subscription_snapshot(db, resource, event_type, event_created)
        elif event_type in {"invoice.paid", "invoice.payment_failed"}:
            _apply_invoice_event(db, resource, event_type, event_created)
        elif event_type in STRIPE_RISK_EVENT_TYPES:
            _record_stripe_risk_event(db, event_record, event_type, resource)

        event_record.processed_at = datetime.now(UTC)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def _record_stripe_risk_event(
    db: Session,
    event_record: StripeWebhookEvent,
    event_type: str,
    resource: Any,
) -> None:
    event_record.risk_review_status = "open"
    event_record.risk_object_id = _object_id(resource)

    if event_type == "charge.refunded":
        charge = resource
        charge_id = _object_id(resource)
    else:
        charge = _value(resource, "charge")
        charge_id = _object_id(charge)

    event_record.risk_charge_id = charge_id
    customer_id = _object_id(_value(charge, "customer")) or _object_id(
        _value(resource, "customer")
    )

    # Disputes and Radar warnings usually include only a charge ID. Resolve it
    # with read access when possible; keep the event if the key is restricted
    # or Stripe is temporarily unavailable.
    if not customer_id and charge_id:
        charge = _retrieve_charge_for_risk_event(charge_id)
        customer_id = _object_id(_value(charge, "customer"))

    company = _find_company(db, customer_id=customer_id)
    if company is not None and not company.is_platform_company:
        event_record.company_id = company.id


def _retrieve_charge_for_risk_event(charge_id: str) -> Any | None:
    try:
        client = StripeClient(_configured_api_key())
        return client.v1.charges.retrieve(
            charge_id,
            options={"stripe_version": STRIPE_API_VERSION},
        )
    except (StripeBillingNotConfigured, stripe.StripeError):
        return None


def _remember_checkout(db: Session, session: Any, event_created: datetime) -> None:
    if _value(session, "mode") != "subscription":
        return
    metadata = _value(session, "metadata", {})
    company = _find_company(
        db,
        company_id=_value(metadata, "company_id") or _value(session, "client_reference_id"),
    )
    if company is None or company.is_platform_company:
        return
    subscription_id = _object_id(_value(session, "subscription"))
    if _is_stale_event(company, event_created):
        return
    if subscription_id and not _accept_subscription_event(
        company,
        subscription_id,
        "customer.subscription.created",
    ):
        return
    _copy_external_ids(company, _object_id(_value(session, "customer")), subscription_id)
    company.stripe_subscription_event_created_at = event_created


def _remember_failed_checkout(db: Session, session: Any, event_created: datetime) -> None:
    if _value(session, "mode") != "subscription":
        return
    metadata = _value(session, "metadata", {})
    company = _find_company(
        db,
        company_id=_value(metadata, "company_id") or _value(session, "client_reference_id"),
    )
    if company is None or company.is_platform_company or _is_stale_event(company, event_created):
        return
    customer_id = _object_id(_value(session, "customer"))
    subscription_id = _object_id(_value(session, "subscription"))
    if subscription_id and not _accept_subscription_event(
        company,
        subscription_id,
        "customer.subscription.created",
    ):
        return
    _copy_external_ids(company, customer_id, subscription_id)
    company.stripe_subscription_status = "incomplete"
    company.stripe_subscription_event_created_at = event_created
    if company.subscription_status != SubscriptionStatus.blocked:
        company.subscription_status = SubscriptionStatus.pending_payment


def _apply_subscription_snapshot(
    db: Session,
    subscription: Any,
    event_type: str,
    event_created: datetime,
) -> None:
    metadata = _value(subscription, "metadata", {})
    subscription_id = _object_id(subscription)
    customer_id = _object_id(_value(subscription, "customer"))
    company = _find_company(
        db,
        company_id=_value(metadata, "company_id"),
        subscription_id=subscription_id,
        customer_id=customer_id,
    )
    if company is None or company.is_platform_company:
        return
    if not _accept_subscription_event(company, subscription_id, event_type):
        return
    if _is_stale_event(company, event_created):
        return

    _copy_external_ids(company, customer_id, subscription_id)
    stripe_status = "canceled" if event_type == "customer.subscription.deleted" else str(
        _value(subscription, "status", "")
    )
    company.stripe_subscription_status = stripe_status[:32]
    company.stripe_subscription_event_created_at = event_created

    if company.subscription_status == SubscriptionStatus.blocked:
        return

    if stripe_status == "active":
        period_start = _subscription_period_start(subscription)
        period_end = _subscription_period_end(subscription)
        if period_end is None:
            company.subscription_status = SubscriptionStatus.pending_payment
            return
        company.subscription_status = SubscriptionStatus.active
        company.subscription_valid_until = period_end
        if period_start is not None:
            company.subscription_period_start = period_start
        company.blocked_at = None
        company.canceled_at = None
        items = _value(_value(subscription, "items", {}), "data", []) or []
        price_id = _object_id(_value(items[0], "price")) if len(items) == 1 else None
        plan_slug = _plan_slug_for_price_id(price_id) or _value(metadata, "plan_slug")
        _apply_plan_metadata(db, company, plan_slug)
    elif stripe_status == "trialing":
        period_end = _subscription_period_end(subscription)
        company.subscription_status = SubscriptionStatus.trialing
        if period_end is not None:
            company.trial_ends_at = period_end
    elif stripe_status == "canceled":
        company.subscription_status = SubscriptionStatus.canceled
        company.subscription_valid_until = None
        company.canceled_at = _epoch_datetime(_value(subscription, "canceled_at")) or event_created
    else:
        company.subscription_status = SubscriptionStatus.pending_payment
        company.subscription_valid_until = None


def _apply_invoice_event(
    db: Session,
    invoice: Any,
    event_type: str,
    event_created: datetime,
) -> None:
    subscription_id = _invoice_subscription_id(invoice)
    customer_id = _object_id(_value(invoice, "customer"))
    parent = _value(invoice, "parent", {})
    subscription_details = _value(parent, "subscription_details", {})
    metadata = _value(subscription_details, "metadata", {}) or _value(invoice, "metadata", {})
    company = _find_company(
        db,
        company_id=_value(metadata, "company_id"),
        subscription_id=subscription_id,
        customer_id=customer_id,
    )
    if company is None or company.is_platform_company:
        return
    if subscription_id and company.stripe_subscription_id not in {None, subscription_id}:
        return
    if _is_stale_event(company, event_created):
        return
    if company.subscription_status == SubscriptionStatus.blocked:
        return
    if company.stripe_subscription_status == "canceled":
        return

    if event_type == "invoice.payment_failed":
        if not subscription_id or company.stripe_subscription_id in {None, subscription_id}:
            company.stripe_subscription_status = "past_due"
            company.stripe_subscription_event_created_at = event_created
            company.subscription_status = SubscriptionStatus.pending_payment
            company.subscription_valid_until = None
        return

    period_end = _invoice_period_end(invoice)
    if period_end is None:
        return
    if subscription_id:
        company.stripe_subscription_id = subscription_id
    if customer_id:
        company.stripe_customer_id = customer_id
    company.stripe_subscription_status = "active"
    company.stripe_subscription_event_created_at = event_created
    company.subscription_status = SubscriptionStatus.active
    company.subscription_valid_until = period_end
    company.blocked_at = None
    company.canceled_at = None


def _accept_subscription_event(company: Company, subscription_id: str | None, event_type: str) -> bool:
    current_id = company.stripe_subscription_id
    if not subscription_id or current_id in {None, subscription_id}:
        return True
    if event_type == "customer.subscription.created" and company.subscription_status in {
        SubscriptionStatus.canceled,
        SubscriptionStatus.pending_payment,
    }:
        return True
    return False


def _is_stale_event(company: Company, event_created: datetime) -> bool:
    last_event = company.stripe_subscription_event_created_at
    if last_event is None:
        return False
    if last_event.tzinfo is None:
        last_event = last_event.replace(tzinfo=UTC)
    return event_created <= last_event.astimezone(UTC)


def _find_company(
    db: Session,
    *,
    company_id: Any = None,
    subscription_id: str | None = None,
    customer_id: str | None = None,
) -> Company | None:
    identified_companies: list[Company] = []
    if subscription_id:
        company = db.scalar(
            select(Company).where(Company.stripe_subscription_id == subscription_id)
        )
        if company is not None:
            identified_companies.append(company)
    if customer_id:
        company = db.scalar(select(Company).where(Company.stripe_customer_id == customer_id))
        if company is not None:
            identified_companies.append(company)

    if identified_companies:
        company_ids = {company.id for company in identified_companies}
        return identified_companies[0] if len(company_ids) == 1 else None

    if company_id:
        try:
            return db.get(Company, UUID(str(company_id)))
        except ValueError:
            return None
    return None


def _copy_external_ids(company: Company, customer_id: str | None, subscription_id: str | None) -> None:
    if customer_id:
        company.stripe_customer_id = customer_id
    if subscription_id:
        company.stripe_subscription_id = subscription_id


def _apply_plan_metadata(db: Session, company: Company, plan_slug: Any) -> None:
    if not isinstance(plan_slug, str):
        return
    plan = db.scalar(select(Plan).where(Plan.slug == plan_slug))
    if plan is None:
        return
    company.current_plan_id = plan.id
    company.subscription_price = plan.price
    company.subscription_duration_months = plan.duration_months


def _invoice_subscription_id(invoice: Any) -> str | None:
    direct = _object_id(_value(invoice, "subscription"))
    if direct:
        return direct
    parent = _value(invoice, "parent", {})
    details = _value(parent, "subscription_details", {})
    return _object_id(_value(details, "subscription"))


def _subscription_period_start(subscription: Any) -> datetime | None:
    direct = _epoch_datetime(_value(subscription, "current_period_start"))
    if direct is not None:
        return direct
    return _subscription_item_period(subscription, "current_period_start")


def _subscription_period_end(subscription: Any) -> datetime | None:
    direct = _epoch_datetime(_value(subscription, "current_period_end"))
    if direct is not None:
        return direct
    return _subscription_item_period(subscription, "current_period_end")


def _subscription_item_period(subscription: Any, field: str) -> datetime | None:
    items = _value(_value(subscription, "items", {}), "data", []) or []
    periods = [
        _epoch_datetime(_value(item, field))
        for item in items
        if _epoch_datetime(_value(item, field)) is not None
    ]
    return max(periods) if periods else None


def _invoice_period_end(invoice: Any) -> datetime | None:
    direct = _epoch_datetime(_value(invoice, "period_end"))
    if direct is not None:
        return direct
    lines = _value(_value(invoice, "lines", {}), "data", []) or []
    periods = [
        _epoch_datetime(_value(_value(line, "period", {}), "end"))
        for line in lines
        if _epoch_datetime(_value(_value(line, "period", {}), "end")) is not None
    ]
    return max(periods) if periods else None


def _epoch_datetime(value: Any) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    try:
        return datetime.fromtimestamp(value, UTC)
    except (OverflowError, OSError, ValueError):
        return None


def _object_id(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    identifier = _value(value, "id")
    return identifier if isinstance(identifier, str) else None


def _value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except TypeError:
            pass
    return getattr(value, key, default)
