from datetime import UTC
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import os
from uuid import uuid4

TEST_DATABASE_URL = "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

import pytest
from fastapi import HTTPException

from app.auth.google import GoogleTokenError
from app.auth.google import GoogleUserInfo
from app.auth import google as google_auth
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
from app.services.subscription import expire_overdue_subscriptions
from app.services.subscription import get_subscription_status
from app.services.subscription import trial_end_date
from app.services.platform_admin import PlatformAdminSeedError
from app.services.platform_admin import create_platform_admin
from app.services.email_verification import confirm_email
from app.services.email_verification import token_hash

TEST_PASSWORD = "x" * 12
TEST_EMAIL_TOKEN = "t" * 32
TEST_GOOGLE_TOKEN = "g" * 32


class FakeDb:
    def __init__(
        self,
        company: Company | None = None,
        user: User | None = None,
        scalar_values: list[object] | None = None,
        scalar_many: list[object] | None = None,
    ) -> None:
        self.company = company
        self.user = user
        self.scalar_values = scalar_values
        self.scalar_many = scalar_many
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

    def scalars(self, statement):
        return self.scalar_many or []


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
        email_verified_at=datetime.now(UTC),
    )


def test_company_created_with_30_day_trial_and_company_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.email_verification.send_email_verification",
        lambda email, verification_link: None,
    )
    db = FakeDb()
    user = auth_service.create_user(
        db,
        UserCreate(
            company_name="Empresa Nova",
            name="Admin",
            email="admin@example.com",
            password=TEST_PASSWORD,
        ),
    )

    assert user.role == UserRole.company_admin
    assert user.role != UserRole.platform_admin
    assert user.company.subscription_status == SubscriptionStatus.trialing
    assert user.company.trial_ends_at - trial_end_date() < timedelta(seconds=2)
    assert user.email_verified_at is None
    assert user.email_verification_token_hash is not None
    assert user.email_verification_expires_at is not None


def test_login_keeps_working_with_overdue_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    company = make_company(
        status=SubscriptionStatus.trialing,
        trial_ends_at=datetime.now(UTC) - timedelta(days=1),
    )
    user = make_user(company)
    db = FakeDb(company=company, user=user)
    monkeypatch.setattr(auth_service, "verify_password", lambda password, password_hash: True)

    assert auth_service.authenticate_user(db, user.email, TEST_PASSWORD) == user


def test_google_login_creates_verified_company_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDb(scalar_values=[None, None])
    monkeypatch.setattr(auth_service, "hash_password", lambda password: "hash")

    user = auth_service.authenticate_google_user(
        db,
        GoogleUserInfo(
            sub="google-sub-123",
            email="Novo.Google@Example.com",
            email_verified=True,
            name="Novo Google",
        ),
    )

    assert user.email == "novo.google@example.com"
    assert user.google_sub == "google-sub-123"
    assert user.role == UserRole.company_admin
    assert user.role != UserRole.platform_admin
    assert user.email_verified_at is not None
    assert user.company.name == "Empresa de Novo Google"
    assert user.company.subscription_status == SubscriptionStatus.trialing
    assert user.company.trial_ends_at - trial_end_date() < timedelta(seconds=2)
    assert user.password_hash == "hash"
    assert db.commits == 1


def test_google_login_links_existing_email_without_overwriting_password() -> None:
    company = make_company()
    user = make_user(company)
    user.email = "cliente@example.com"
    user.password_hash = "hash-existente"
    user.google_sub = None
    user.email_verified_at = None
    db = FakeDb(company=company, user=user, scalar_values=[None, user])

    authenticated = auth_service.authenticate_google_user(
        db,
        GoogleUserInfo(
            sub="google-sub-456",
            email="CLIENTE@example.com",
            email_verified=True,
            name="Cliente Google",
        ),
    )

    assert authenticated == user
    assert user.google_sub == "google-sub-456"
    assert user.password_hash == "hash-existente"
    assert user.email_verified_at is not None
    assert db.added == []
    assert db.commits == 1


def test_google_login_does_not_duplicate_user_by_google_sub() -> None:
    company = make_company()
    user = make_user(company)
    user.google_sub = "google-sub-789"
    db = FakeDb(company=company, user=user, scalar_values=[user])

    authenticated = auth_service.authenticate_google_user(
        db,
        GoogleUserInfo(
            sub="google-sub-789",
            email="outro-email@example.com",
            email_verified=True,
            name="Outro Email",
        ),
    )

    assert authenticated == user
    assert db.added == []
    assert db.commits == 0


def test_google_token_rejects_unverified_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(google_auth.settings, "google_client_id", "client-id")
    monkeypatch.setattr(
        google_auth.google_id_token,
        "verify_oauth2_token",
        lambda token, request, audience: {
            "iss": "https://accounts.google.com",
            "sub": "google-sub",
            "email": "usuario@example.com",
            "email_verified": False,
            "name": "Usuario",
        },
    )

    with pytest.raises(GoogleTokenError):
        google_auth.verify_google_id_token(TEST_GOOGLE_TOKEN)


def test_google_token_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(google_auth.settings, "google_client_id", "client-id")

    def raise_invalid_token(token, request, audience):
        raise ValueError("invalid token")

    monkeypatch.setattr(
        google_auth.google_id_token,
        "verify_oauth2_token",
        raise_invalid_token,
    )

    with pytest.raises(GoogleTokenError):
        google_auth.verify_google_id_token(TEST_GOOGLE_TOKEN)


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


def test_financial_dependency_blocks_unverified_customer_email() -> None:
    company = make_company(status=SubscriptionStatus.trialing)
    user = make_user(company)
    user.email_verified_at = None
    db = FakeDb(company=company, user=user)

    with pytest.raises(HTTPException) as exc_info:
        require_valid_subscription(current_user=user, db=db)

    assert exc_info.value.status_code == 403


def test_confirm_email_sets_verified_at_and_clears_token() -> None:
    company = make_company()
    user = make_user(company)
    user.email_verified_at = None
    user.email_verification_token_hash = token_hash(TEST_EMAIL_TOKEN)
    user.email_verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    db = FakeDb(company=company, user=user, scalar_values=[user])

    assert confirm_email(db, TEST_EMAIL_TOKEN)
    assert user.email_verified_at is not None
    assert user.email_verification_token_hash is None
    assert user.email_verification_expires_at is None
    assert db.commits == 1


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


def test_expire_overdue_subscriptions_is_idempotent() -> None:
    checked_at = datetime.now(UTC)
    overdue_trial = make_company(
        status=SubscriptionStatus.trialing,
        trial_ends_at=checked_at - timedelta(days=1),
    )
    overdue_active = make_company(
        status=SubscriptionStatus.active,
        subscription_valid_until=checked_at - timedelta(days=1),
    )
    active_without_date = make_company(
        status=SubscriptionStatus.active,
        subscription_valid_until=None,
    )
    valid_trial = make_company(
        status=SubscriptionStatus.trialing,
        trial_ends_at=checked_at + timedelta(days=1),
    )
    platform_company = make_company(
        status=SubscriptionStatus.active,
        subscription_valid_until=checked_at - timedelta(days=1),
    )
    platform_company.is_platform_company = True
    db = FakeDb(
        scalar_many=[
            overdue_trial,
            overdue_active,
            active_without_date,
            valid_trial,
            platform_company,
        ],
    )

    assert expire_overdue_subscriptions(db, checked_at) == 3
    assert expire_overdue_subscriptions(db, checked_at) == 0
    assert overdue_trial.subscription_status == SubscriptionStatus.pending_payment
    assert overdue_active.subscription_status == SubscriptionStatus.pending_payment
    assert active_without_date.subscription_status == SubscriptionStatus.pending_payment
    assert valid_trial.subscription_status == SubscriptionStatus.trialing
    assert platform_company.subscription_status == SubscriptionStatus.active
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
        password=TEST_PASSWORD,
    )

    assert user.role == UserRole.platform_admin
    assert user.email == "admin@example.com"
    assert user.email_verified_at is not None
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
            password=TEST_PASSWORD,
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
