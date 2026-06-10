from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.plan import BillingCycle
from app.models.plan import Plan
from app.schemas.plan import PlanUpdate


FIXED_PLANS = (
    {
        "name": "Mensal",
        "slug": "monthly",
        "billing_cycle": BillingCycle.monthly,
        "duration_months": 1,
        "description": "Plano mensal da plataforma.",
    },
    {
        "name": "Semestral",
        "slug": "semiannual",
        "billing_cycle": BillingCycle.semiannual,
        "duration_months": 6,
        "description": "Plano semestral da plataforma.",
    },
    {
        "name": "Anual",
        "slug": "annual",
        "billing_cycle": BillingCycle.annual,
        "duration_months": 12,
        "description": "Plano anual da plataforma.",
    },
)


class PlanNotFoundError(ValueError):
    pass


def ensure_fixed_plans(db: Session) -> list[Plan]:
    plans_by_slug = {
        plan.slug: plan
        for plan in db.scalars(select(Plan).where(Plan.slug.in_([item["slug"] for item in FIXED_PLANS])))
    }

    plans: list[Plan] = []
    changed = False
    for item in FIXED_PLANS:
        plan = plans_by_slug.get(str(item["slug"]))
        if plan is None:
            plan = Plan(
                name=str(item["name"]),
                slug=str(item["slug"]),
                billing_cycle=item["billing_cycle"],
                duration_months=int(item["duration_months"]),
                price=Decimal("0.00"),
                is_active=True,
                description=str(item["description"]),
            )
            db.add(plan)
            changed = True
        else:
            if (
                plan.name != item["name"]
                or plan.billing_cycle != item["billing_cycle"]
                or plan.duration_months != item["duration_months"]
            ):
                plan.name = str(item["name"])
                plan.billing_cycle = item["billing_cycle"]
                plan.duration_months = int(item["duration_months"])
                changed = True
        plans.append(plan)

    if changed:
        db.commit()
        for plan in plans:
            db.refresh(plan)
    return plans


def list_plans(db: Session) -> list[Plan]:
    ensure_fixed_plans(db)
    return list(db.scalars(select(Plan).order_by(Plan.duration_months.asc())))


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


def update_plan(db: Session, plan_id: UUID, plan_in: PlanUpdate) -> Plan:
    plan = get_plan(db, plan_id)
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
