from decimal import Decimal
from uuid import UUID

from sqlalchemy import case
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.plan import BillingCycle
from app.models.plan import Plan
from app.schemas.plan import PlanUpdate

BASIC_FEATURE_CODES = (
    "dashboard",
    "transactions",
    "payables",
    "receivables",
    "categories",
    "contacts",
)

ALL_FEATURE_CODES = (
    "dashboard",
    "assistant",
    "cashflow",
    "product_outputs",
    "transactions",
    "payables",
    "receivables",
    "categories",
    "imports",
    "employees",
    "users",
    "contacts",
)

FIXED_PLANS = (
    {
        "name": "Básico",
        "slug": "basic",
        "billing_cycle": BillingCycle.monthly,
        "duration_months": 1,
        "price": Decimal("10.90"),
        "description": "Lançamentos, contas a pagar e a receber, visão geral, categorias e contatos.",
        "feature_codes": list(BASIC_FEATURE_CODES),
        "ai_daily_limit": 0,
    },
    {
        "name": "Intermediário",
        "slug": "intermediate",
        "billing_cycle": BillingCycle.monthly,
        "duration_months": 1,
        "price": Decimal("21.90"),
        "description": "Todos os recursos, com até 2 interações com a IA por dia.",
        "feature_codes": list(ALL_FEATURE_CODES),
        "ai_daily_limit": 2,
    },
    {
        "name": "Avançado",
        "slug": "advanced",
        "billing_cycle": BillingCycle.monthly,
        "duration_months": 1,
        "price": Decimal("29.90"),
        "description": "Todos os recursos, com até 10 interações com a IA por dia.",
        "feature_codes": list(ALL_FEATURE_CODES),
        "ai_daily_limit": 10,
    },
    {
        "name": "Pro",
        "slug": "pro",
        "billing_cycle": BillingCycle.monthly,
        "duration_months": 1,
        "price": Decimal("39.90"),
        "description": "Todos os recursos, com interações ilimitadas com a IA.",
        "feature_codes": list(ALL_FEATURE_CODES),
        "ai_daily_limit": None,
    },
)

PLAN_SLUGS = tuple(str(item["slug"]) for item in FIXED_PLANS)
LEGACY_PLAN_SLUGS = ("semiannual", "annual")


class PlanNotFoundError(ValueError):
    pass


def ensure_fixed_plans(db: Session) -> list[Plan]:
    plans_by_slug = {
        plan.slug: plan
        for plan in db.scalars(select(Plan).where(Plan.slug.in_(PLAN_SLUGS)))
    }

    plans: list[Plan] = []
    changed = False
    for item in FIXED_PLANS:
        slug = str(item["slug"])
        plan = plans_by_slug.get(slug)
        if plan is None:
            plan = Plan(
                name=str(item["name"]),
                slug=slug,
                billing_cycle=item["billing_cycle"],
                duration_months=int(item["duration_months"]),
                price=item["price"],
                feature_codes=list(item["feature_codes"]),
                ai_daily_limit=item["ai_daily_limit"],
                is_active=True,
                description=str(item["description"]),
            )
            db.add(plan)
            changed = True
        else:
            fixed_fields = {
                "name": str(item["name"]),
                "billing_cycle": item["billing_cycle"],
                "duration_months": int(item["duration_months"]),
                "feature_codes": list(item["feature_codes"]),
                "ai_daily_limit": item["ai_daily_limit"],
            }
            for field, value in fixed_fields.items():
                if getattr(plan, field) != value:
                    setattr(plan, field, value)
                    changed = True
        plans.append(plan)

    legacy_plans = db.scalars(
        select(Plan).where(Plan.slug.in_(LEGACY_PLAN_SLUGS), Plan.is_active.is_(True))
    )
    for plan in legacy_plans:
        plan.is_active = False
        changed = True

    if changed:
        db.commit()
        for plan in plans:
            db.refresh(plan)
    return plans


def list_plans(db: Session) -> list[Plan]:
    ensure_fixed_plans(db)
    plan_order = case(
        *[(Plan.slug == slug, index) for index, slug in enumerate(PLAN_SLUGS)],
        else_=len(PLAN_SLUGS),
    )
    return list(
        db.scalars(
            select(Plan).where(Plan.slug.in_(PLAN_SLUGS)).order_by(plan_order)
        )
    )


def get_plan(db: Session, plan_id: UUID) -> Plan:
    ensure_fixed_plans(db)
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise PlanNotFoundError("Plano nao encontrado")
    return plan


def get_plan_by_slug(db: Session, slug: str) -> Plan:
    ensure_fixed_plans(db)
    plan = db.scalar(select(Plan).where(Plan.slug == slug))
    if plan is None:
        raise PlanNotFoundError("Plano nao encontrado")
    return plan


def get_company_plan(db: Session, company: Company) -> Plan:
    ensure_fixed_plans(db)
    if company.current_plan_id is not None:
        plan = db.get(Plan, company.current_plan_id)
        if plan is not None:
            return plan
    return db.scalar(select(Plan).where(Plan.slug == "basic")) or get_plan_by_slug(db, "basic")


def update_plan(db: Session, plan_id: UUID, plan_in: PlanUpdate) -> Plan:
    plan = get_plan(db, plan_id)
    if plan.slug not in PLAN_SLUGS:
        raise PlanNotFoundError("Plano legado não está disponível para edição")

    update_data = plan_in.model_dump(exclude_unset=True)
    if "price" in update_data:
        plan.price = update_data["price"]
    if "is_active" in update_data:
        plan.is_active = update_data["is_active"]
    if "description" in update_data:
        plan.description = _strip_optional_text(update_data["description"])
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
