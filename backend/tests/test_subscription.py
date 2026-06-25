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
from pydantic import ValidationError

from app.auth.google import GoogleTokenError
from app.auth.google import GoogleUserInfo
from app.api import auth as auth_api
from app.api.deps import require_platform_admin
from app.auth import google as google_auth
from app.api.deps import require_valid_subscription
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.plan import BillingCycle
from app.models.plan import Plan
from app.models.user import User
from app.models.user import UserRole
from app.schemas.auth import UserCreate
from app.schemas.auth import PasswordResetConfirm
from app.schemas.company import CompanyOnboardingComplete
from app.schemas.plan import PlanUpdate
from app.schemas.subscription import ManualRenewalCreate
from app.services import auth as auth_service
from app.services import password_reset as password_reset_service
from app.services.company import complete_company_onboarding
from app.services.plan import ensure_fixed_plans
from app.services.plan import update_plan
from app.services.subscription import SubscriptionPermissionError
from app.services.subscription import SubscriptionValidationError
from app.services.subscription import create_manual_renewal
from app.services.subscription import expire_overdue_subscriptions
from app.services.subscription import get_subscription_status
from app.services.subscription import trial_end_date
from app.services.admin_client import block_admin_client
from app.services.admin_client import cancel_admin_client
from app.services.admin_client import reactivate_admin_client
from app.services.admin_client import change_admin_client_plan
from app.services.platform_admin import PlatformAdminSeedError
from app.services.platform_admin import create_platform_admin
from app.services.email_verification import confirm_email
from app.services.email_verification import token_hash
from app.services.email import EmailDeliveryError

TEST_PASSWORD = "x" * 12
TEST_EMAIL_TOKEN = "t" * 32
TEST_GOOGLE_TOKEN = "g" * 32
DEFAULT_ONBOARDING_COMPLETED_AT = object()


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
        if isinstance(instance, Company):
            self.company = instance
        if isinstance(instance, User):
            self.user = instance

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
        if model is Plan and self.scalar_many is not None:
            for item in self.scalar_many:
                if isinstance(item, Plan) and item.id == object_id:
                    return item
        return None

    def scalar(self, statement):
        if self.scalar_values is not None:
            return self.scalar_values.pop(0)
        return self.user

    def scalars(self, statement):
        return self.scalar_many or []


class PlanSeedDb:
    def __init__(self, plans: list[Plan] | None = None) -> None:
        self.plans = plans or []
        self.commits = 0
        self.added = []

    def add(self, instance):
        self.added.append(instance)
        if isinstance(instance, Plan) and instance not in self.plans:
            self.plans.append(instance)

    def commit(self):
        self.commits += 1

    def refresh(self, instance):
        pass

    def scalars(self, statement):
        return self.plans


def make_company(
    status: SubscriptionStatus = SubscriptionStatus.trialing,
    trial_ends_at: datetime | None = None,
    subscription_valid_until: datetime | None = None,
    onboarding_completed_at: datetime | None | object = DEFAULT_ONBOARDING_COMPLETED_AT,
) -> Company:
    completed_at = (
        datetime.now(UTC)
        if onboarding_completed_at is DEFAULT_ONBOARDING_COMPLETED_AT
        else onboarding_completed_at
    )
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=status,
        trial_ends_at=trial_ends_at or datetime.now(UTC) + timedelta(days=30),
        subscription_valid_until=subscription_valid_until,
        onboarding_completed_at=completed_at,
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
            email="admin@example.com",
            password=TEST_PASSWORD,
        ),
    )

    assert user.role == UserRole.company_admin
    assert user.role != UserRole.platform_admin
    assert user.name == "admin"
    assert user.company.name == "Configurar empresa"
    assert user.company.onboarding_completed_at is None
    assert user.company.subscription_status == SubscriptionStatus.trialing
    assert user.company.trial_ends_at - trial_end_date() < timedelta(seconds=2)
    assert user.email_verified_at is None
    assert user.email_verification_token_hash is not None
    assert user.email_verification_expires_at is not None


def test_register_returns_created_user_when_verification_email_delivery_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_email_delivery(email: str, verification_link: str) -> None:
        raise EmailDeliveryError("SMTP indisponivel")

    monkeypatch.setattr(
        "app.services.email_verification.send_email_verification",
        fail_email_delivery,
    )
    db = FakeDb()

    user = auth_api.register(
        UserCreate(
            email="admin@example.com",
            password=TEST_PASSWORD,
        ),
        db,
    )

    assert user.email == "admin@example.com"
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
    assert user.company.name == "Configurar empresa"
    assert user.company.onboarding_completed_at is None
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


def test_financial_dependency_blocks_pending_onboarding() -> None:
    company = make_company(
        status=SubscriptionStatus.trialing,
        onboarding_completed_at=None,
    )


def make_plan(
    slug: str = "monthly",
    price: Decimal = Decimal("49.90"),
    duration_months: int = 1,
    is_active: bool = True,
) -> Plan:
    cycle = BillingCycle(slug)
    return Plan(
        id=uuid4(),
        name={
            "monthly": "Mensal",
            "semiannual": "Semestral",
            "annual": "Anual",
        }[slug],
        slug=slug,
        billing_cycle=cycle,
        duration_months=duration_months,
        price=price,
        is_active=is_active,
        description=None,
    )
    user = make_user(company)
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


def test_password_reset_request_existing_user_generates_hash_and_sends_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = make_company()
    user = make_user(company)
    db = FakeDb(company=company, user=user, scalar_values=[user])
    sent_codes: list[tuple[str, str]] = []
    monkeypatch.setattr(
        password_reset_service,
        "send_password_reset_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    password_reset_service.request_password_reset(db, user.email.upper())

    assert user.password_reset_code_hash is not None
    assert user.password_reset_expires_at is not None
    assert user.password_reset_requested_at is not None
    assert sent_codes == [(user.email, sent_codes[0][1])]
    assert len(sent_codes[0][1]) == 6
    assert sent_codes[0][1].isdigit()
    assert db.commits == 1


def test_password_reset_request_missing_user_returns_generic_without_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeDb(scalar_values=[None])
    sent_codes: list[tuple[str, str]] = []
    monkeypatch.setattr(
        password_reset_service,
        "send_password_reset_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    password_reset_service.request_password_reset(db, "missing@example.com")

    assert sent_codes == []
    assert db.commits == 0


def test_password_reset_request_before_resend_interval_keeps_existing_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    company = make_company()
    user = make_user(company)
    user.password_reset_code_hash = "existing-hash"
    user.password_reset_requested_at = datetime.now(UTC)
    db = FakeDb(company=company, user=user, scalar_values=[user])
    sent_codes: list[tuple[str, str]] = []
    monkeypatch.setattr(
        password_reset_service,
        "send_password_reset_code",
        lambda email, code: sent_codes.append((email, code)),
    )

    password_reset_service.request_password_reset(db, user.email)

    assert user.password_reset_code_hash == "existing-hash"
    assert sent_codes == []
    assert db.commits == 0


def test_password_reset_confirm_updates_password_and_clears_reset_fields() -> None:
    company = make_company()
    user = make_user(company)
    old_password = "SenhaAntiga123"
    new_password = "SenhaNova123"
    user.password_hash = auth_service.hash_password(old_password)
    user.must_change_password = True
    user.password_reset_code_hash = token_hash("123456")
    user.password_reset_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    user.password_reset_requested_at = datetime.now(UTC)
    db = FakeDb(company=company, user=user, scalar_values=[user])

    updated = password_reset_service.confirm_password_reset(
        db,
        user.email,
        "123456",
        new_password,
    )

    assert updated == user
    db.scalar_values = [user]
    assert not auth_service.authenticate_user(db, user.email, old_password)
    db.scalar_values = [user]
    assert auth_service.authenticate_user(db, user.email, new_password) == user
    assert user.must_change_password is False
    assert user.password_reset_code_hash is None
    assert user.password_reset_expires_at is None
    assert user.password_reset_requested_at is None
    assert db.commits == 1


def test_password_reset_confirm_rejects_expired_code() -> None:
    company = make_company()
    user = make_user(company)
    user.password_reset_code_hash = token_hash("123456")
    user.password_reset_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db = FakeDb(company=company, user=user, scalar_values=[user])

    with pytest.raises(password_reset_service.PasswordResetError):
        password_reset_service.confirm_password_reset(
            db,
            user.email,
            "123456",
            "SenhaNova123",
        )

    assert db.commits == 0


def test_password_reset_confirm_rejects_wrong_code() -> None:
    company = make_company()
    user = make_user(company)
    user.password_reset_code_hash = token_hash("123456")
    user.password_reset_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    db = FakeDb(company=company, user=user, scalar_values=[user])

    with pytest.raises(password_reset_service.PasswordResetError):
        password_reset_service.confirm_password_reset(
            db,
            user.email,
            "654321",
            "SenhaNova123",
        )

    assert db.commits == 0


def test_password_reset_schema_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        PasswordResetConfirm(
            email="usuario@example.com",
            code="123456",
            new_password="curta",
        )


def test_complete_company_onboarding_updates_company_user_and_opening_balance() -> None:
    company = make_company()
    company.name = "Configurar empresa"
    company.onboarding_completed_at = None
    user = make_user(company)
    db = FakeDb(company=company, user=user)

    updated_company = complete_company_onboarding(
        db,
        user,
        CompanyOnboardingComplete(
            company_name="Empresa Nova",
            user_name="Admin Principal",
            opening_balance=Decimal("1234.56"),
        ),
    )

    assert updated_company == company
    assert company.name == "Empresa Nova"
    assert company.opening_balance == Decimal("1234.56")
    assert company.opening_balance_date is not None
    assert company.onboarding_completed_at is not None
    assert user.name == "Admin Principal"
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


def test_plan_seed_is_idempotent_and_preserves_admin_price() -> None:
    monthly = make_plan(price=Decimal("59.90"))
    monthly.name = "Plano antigo"
    monthly.duration_months = 99
    db = PlanSeedDb([monthly])

    plans = ensure_fixed_plans(db)
    plans_again = ensure_fixed_plans(db)

    assert len(plans) == 3
    assert len(plans_again) == 3
    assert monthly.name == "Mensal"
    assert monthly.duration_months == 1
    assert monthly.price == Decimal("59.90")
    assert db.commits == 1


def test_admin_can_update_plan_price_status_and_description() -> None:
    plan = make_plan()
    db = FakeDb(
        scalar_many=[
            plan,
            make_plan(slug="semiannual", duration_months=6),
            make_plan(slug="annual", duration_months=12),
        ]
    )

    updated = update_plan(
        db,
        plan.id,
        PlanUpdate(price=Decimal("59.90"), is_active=False, description=" Novo valor "),
    )

    assert updated.price == Decimal("59.90")
    assert not updated.is_active
    assert updated.description == "Novo valor"
    assert db.commits == 1


def test_plan_update_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        PlanUpdate(price=Decimal("-0.01"))


def test_plan_update_rejects_structural_fields() -> None:
    with pytest.raises(ValidationError):
        PlanUpdate.model_validate(
            {
                "price": "49.90",
                "slug": "other",
                "billing_cycle": "annual",
                "duration_months": 12,
            }
        )


def test_common_user_cannot_access_admin_plan_dependency() -> None:
    company = make_company()
    user = make_user(company)

    with pytest.raises(HTTPException) as exc_info:
        require_platform_admin(current_user=user)

    assert exc_info.value.status_code == 403


def test_manual_renewal_uses_current_plan_price_and_duration() -> None:
    paid_at = datetime(2026, 1, 31, 12, tzinfo=UTC)
    company = make_company(status=SubscriptionStatus.pending_payment)
    admin = make_user(company, role=UserRole.platform_admin)
    plan = make_plan(slug="semiannual", price=Decimal("249.90"), duration_months=6)
    db = FakeDb(company=company, user=admin, scalar_many=[plan])

    payment = create_manual_renewal(
        db,
        admin,
        ManualRenewalCreate(company_id=company.id, plan_id=plan.id, paid_at=paid_at),
    )

    assert company.subscription_status == SubscriptionStatus.active
    assert company.current_plan_id == plan.id
    assert company.subscription_valid_until == datetime(2026, 7, 31, 12, tzinfo=UTC)
    assert payment.amount == Decimal("249.90")
    assert payment.price_at_payment == Decimal("249.90")
    assert payment.plan_slug == "semiannual"
    assert payment.duration_months == 6


def test_manual_renewal_preserves_historical_price_after_plan_change() -> None:
    company = make_company(status=SubscriptionStatus.pending_payment)
    admin = make_user(company, role=UserRole.platform_admin)
    plan = make_plan(price=Decimal("49.90"))
    db = FakeDb(company=company, user=admin, scalar_many=[plan])

    payment = create_manual_renewal(
        db,
        admin,
        ManualRenewalCreate(company_id=company.id, plan_id=plan.id),
    )
    plan.price = Decimal("59.90")

    assert payment.amount == Decimal("49.90")
    assert payment.price_at_payment == Decimal("49.90")


def test_manual_renewal_rejects_inactive_plan() -> None:
    company = make_company(status=SubscriptionStatus.pending_payment)
    admin = make_user(company, role=UserRole.platform_admin)
    plan = make_plan(is_active=False)
    db = FakeDb(company=company, user=admin, scalar_many=[plan])

    with pytest.raises(SubscriptionValidationError):
        create_manual_renewal(
            db,
            admin,
            ManualRenewalCreate(company_id=company.id, plan_id=plan.id),
        )


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


def test_admin_client_block_cancel_and_reactivate_actions() -> None:
    company = make_company(status=SubscriptionStatus.active)
    admin = make_user(company, role=UserRole.platform_admin)
    db = FakeDb(company=company, user=admin)

    blocked = block_admin_client(db, admin, company.id)
    canceled = cancel_admin_client(db, admin, company.id)
    reactivated = reactivate_admin_client(db, admin, company.id)

    assert blocked.status == SubscriptionStatus.blocked
    assert company.blocked_at is None
    assert canceled.status == SubscriptionStatus.canceled
    assert company.canceled_at is None
    assert reactivated.status == SubscriptionStatus.pending_payment
    assert db.commits == 3


def test_admin_client_plan_change_uses_existing_active_plan() -> None:
    company = make_company(status=SubscriptionStatus.active)
    admin = make_user(company, role=UserRole.platform_admin)
    plan = make_plan()
    db = FakeDb(company=company, user=admin, scalar_many=[plan])

    response = change_admin_client_plan(db, admin, company.id, plan.id)

    assert response.status == SubscriptionStatus.active
    assert company.current_plan_id == plan.id
    assert db.commits == 1


def test_subscription_status_uses_authenticated_users_company() -> None:
    company = make_company()
    user = make_user(company)
    db = FakeDb(company=company, user=user)

    status = get_subscription_status(db, db.get(Company, user.company_id))

    assert status.company_id == user.company_id
