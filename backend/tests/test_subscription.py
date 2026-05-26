from datetime import UTC
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import os
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

import pytest
from fastapi import HTTPException

from app.api.deps import require_valid_subscription
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.user import User
from app.models.user import UserRole
from app.schemas.auth import UserCreate
from app.schemas.subscription import ManualRenewalCreate
from app.services import auth as auth_service
from app.services.subscription import SubscriptionPermissionError
from app.services.subscription import create_manual_renewal
from app.services.subscription import get_subscription_status
from app.services.subscription import trial_end_date
from app.services.platform_admin import PlatformAdminSeedError
from app.services.platform_admin import create_platform_admin


class FakeDb:
    def __init__(
        self,
        company: Company | None = None,
        user: User | None = None,
        scalar_values: list[object] | None = None,
    ) -> None:
        self.company = company
        self.user = user
        self.scalar_values = scalar_values
        self.added = []
        self.commits = 0
        self.flushes = 0

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1

    def refresh(self, instance):
        pass

    def get(self, model, object_id):
        if model is Company and self.company is not None and self.company.id == object_id:
            return self.company
        if model is User and self.user is not None and self.user.id == object_id:
            return self.user
        return None

    def scalar(self, statement):
        if self.scalar_values is not None:
            return self.scalar_values.pop(0)
        return self.user


def make_company(
    status: SubscriptionStatus = SubscriptionStatus.trialing,
    trial_ends_at: datetime | None = None,
    subscription_valid_until: datetime | None = None,
) -> Company:
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=status,
        trial_ends_at=trial_ends_at or datetime.now(UTC) + timedelta(days=30),
        subscription_valid_until=subscription_valid_until,
        is_platform_company=False,
    )


def make_user(company: Company, role: UserRole = UserRole.company_admin) -> User:
    return User(
        id=uuid4(),
        company_id=company.id,
        name="Usuário Teste",
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        role=role,
        is_active=True,
    )


def test_company_created_with_30_day_trial_and_company_admin() -> None:
    db = FakeDb()
    user = auth_service.create_user(
        db,
        UserCreate(
            company_name="Empresa Nova",
            name="Admin",
            email="admin@example.com",
            password="senha-segura",
        ),
    )

    assert user.role == UserRole.company_admin
    assert user.role != UserRole.platform_admin
    assert user.company.subscription_status == SubscriptionStatus.trialing
    assert user.company.trial_ends_at - trial_end_date() < timedelta(seconds=2)


def test_login_keeps_working_with_overdue_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    company = make_company(
        status=SubscriptionStatus.trialing,
        trial_ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    user = make_user(company)
    db = FakeDb(company=company, user=user)
    monkeypatch.setattr(auth_service, "verify_password", lambda password, password_hash: True)

    assert auth_service.authenticate_user(db, user.email, "qualquer-senha") == user


def test_financial_dependency_blocks_invalid_subscription() -> None:
    company = make_company(
        status=SubscriptionStatus.pending_payment,
        trial_ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    user = make_user(company)
    db = FakeDb(company=company, user=user)

    with pytest.raises(HTTPException) as exc_info:
        require_valid_subscription(current_user=user, db=db)

    assert exc_info.value.status_code == 402


def test_financial_dependency_allows_valid_trialing_subscription() -> None:
    company = make_company(status=SubscriptionStatus.trialing)
    user = make_user(company)
    db = FakeDb(company=company, user=user)

    assert require_valid_subscription(current_user=user, db=db) == user


def test_financial_dependency_allows_valid_active_subscription() -> None:
    company = make_company(
        status=SubscriptionStatus.active,
        subscription_valid_until=datetime.now(UTC) + timedelta(days=5),
    )
    user = make_user(company)
    db = FakeDb(company=company, user=user)

    assert require_valid_subscription(current_user=user, db=db) == user


def test_overdue_trial_becomes_pending_payment() -> None:
    company = make_company(
        status=SubscriptionStatus.trialing,
        trial_ends_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db = FakeDb(company=company)

    status = get_subscription_status(db, company)

    assert status.status == SubscriptionStatus.pending_payment
    assert not status.is_valid
    assert company.subscription_status == SubscriptionStatus.pending_payment
    assert db.commits == 1


def test_platform_admin_manual_renewal_extends_active_period() -> None:
    current_end = datetime.now(UTC) + timedelta(days=10)
    company = make_company(
        status=SubscriptionStatus.active,
        subscription_valid_until=current_end,
    )
    admin = make_user(company, role=UserRole.platform_admin)
    db = FakeDb(company=company, user=admin)

    payment = create_manual_renewal(
        db,
        admin,
        ManualRenewalCreate(company_id=company.id, amount=Decimal("99.90")),
    )

    assert company.subscription_status == SubscriptionStatus.active
    assert company.subscription_valid_until == current_end + timedelta(days=30)
    assert payment.amount == Decimal("99.90")
    assert payment.company_id == company.id
    assert payment.created_by == admin.id


def test_platform_admin_manual_renewal_starts_from_payment_when_overdue() -> None:
    paid_at = datetime.now(UTC)
    company = make_company(
        status=SubscriptionStatus.active,
        subscription_valid_until=paid_at - timedelta(days=2),
    )
    admin = make_user(company, role=UserRole.platform_admin)
    db = FakeDb(company=company, user=admin)

    payment = create_manual_renewal(
        db,
        admin,
        ManualRenewalCreate(
            company_id=company.id,
            amount=Decimal("99.90"),
            paid_at=paid_at,
        ),
    )

    assert company.subscription_status == SubscriptionStatus.active
    assert payment.period_start == paid_at
    assert payment.period_end == paid_at + timedelta(days=30)


def test_manual_renewal_accepts_naive_database_dates_with_aware_payment_date() -> None:
    current_end = datetime.now().replace(microsecond=0) + timedelta(days=10)
    paid_at = datetime.now(UTC).replace(microsecond=0)
    company = make_company(
        status=SubscriptionStatus.active,
        subscription_valid_until=current_end,
    )
    admin = make_user(company, role=UserRole.platform_admin)
    db = FakeDb(company=company, user=admin)

    payment = create_manual_renewal(
        db,
        admin,
        ManualRenewalCreate(
            company_id=company.id,
            amount=Decimal("99.90"),
            paid_at=paid_at,
        ),
    )

    expected_start = current_end.replace(tzinfo=UTC)
    assert payment.period_start == expected_start
    assert payment.period_end == expected_start + timedelta(days=30)


def test_common_user_cannot_renew_subscription() -> None:
    company = make_company()
    user = make_user(company)
    db = FakeDb(company=company, user=user)

    with pytest.raises(SubscriptionPermissionError):
        create_manual_renewal(
            db,
            user,
            ManualRenewalCreate(company_id=company.id, amount=Decimal("99.90")),
        )


def test_create_platform_admin_uses_platform_company_and_role(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDb(scalar_values=[None, None])
    monkeypatch.setattr("app.services.platform_admin.hash_password", lambda password: "hash")

    user = create_platform_admin(
        db,
        name="Admin Plataforma",
        email="ADMIN@EXAMPLE.COM",
        password="senha-segura",
    )

    assert user.role == UserRole.platform_admin
    assert user.email == "admin@example.com"
    assert user.company.is_platform_company
    assert user.company.subscription_status == SubscriptionStatus.active
    assert db.flushes == 1
    assert db.commits == 1


def test_create_platform_admin_rejects_duplicate_email() -> None:
    company = make_company()
    existing_user = make_user(company)
    db = FakeDb(scalar_values=[existing_user])

    with pytest.raises(PlatformAdminSeedError):
        create_platform_admin(
            db,
            name="Admin Plataforma",
            email=existing_user.email,
            password="senha-segura",
        )


def test_platform_admin_cannot_access_financial_dependency() -> None:
    company = make_company()
    admin = make_user(company, role=UserRole.platform_admin)
    db = FakeDb(company=company, user=admin)

    with pytest.raises(HTTPException) as exc_info:
        require_valid_subscription(current_user=admin, db=db)

    assert exc_info.value.status_code == 403


def test_subscription_status_uses_authenticated_users_company() -> None:
    company = make_company()
    user = make_user(company)
    db = FakeDb(company=company, user=user)

    status = get_subscription_status(db, db.get(Company, user.company_id))

    assert status.company_id == user.company_id
