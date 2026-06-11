from datetime import UTC
from datetime import datetime
import os
from uuid import uuid4

TEST_DATABASE_URL = "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

import pytest
from fastapi import HTTPException

from app.api.deps import require_company_admin
from app.core.security import hash_password
from app.core.security import verify_password
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.user import User
from app.models.user import UserRole
from app.schemas.company_user import CompanyUserCreate
from app.services.auth import PasswordChangeError
from app.services.auth import authenticate_user
from app.services.auth import change_user_password
from app.services.company_user import CompanyUserError
from app.services.company_user import create_company_user
from app.services.company_user import get_company_user
from app.services.company_user import reset_company_user_password
from app.services.company_user import set_company_user_status


class FakeDb:
    def __init__(self, scalar_values: list[object] | None = None) -> None:
        self.scalar_values = scalar_values or []
        self.added: list[object] = []
        self.commits = 0
        self.refreshed: list[object] = []
        self.statements: list[object] = []

    def scalar(self, statement):
        self.statements.append(statement)
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def refresh(self, instance):
        self.refreshed.append(instance)


def make_company() -> Company:
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=SubscriptionStatus.active,
        trial_ends_at=datetime.now(UTC),
        subscription_valid_until=datetime.now(UTC),
        onboarding_completed_at=datetime.now(UTC),
        is_platform_company=False,
    )


def make_user(
    company: Company,
    role: UserRole = UserRole.company_admin,
    password: str = "SenhaInicial123",
) -> User:
    return User(
        id=uuid4(),
        company_id=company.id,
        name="Usuario Teste",
        email=f"{uuid4()}@example.com",
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        must_change_password=False,
        email_verified_at=datetime.now(UTC),
    )


def test_admin_creates_fixed_employee_user_for_own_company() -> None:
    company = make_company()
    admin = make_user(company)
    db = FakeDb(scalar_values=[None])

    user = create_company_user(
        db,
        admin,
        CompanyUserCreate(
            name=" Maria Silva ",
            email="MARIA@example.com",
            temporary_password="Temporaria123",
        ),
    )

    assert user.company_id == admin.company_id
    assert user.role == UserRole.user
    assert user.name == "Maria Silva"
    assert user.email == "maria@example.com"
    assert user.email_verified_at is not None
    assert user.must_change_password is True
    assert verify_password("Temporaria123", user.password_hash)
    assert db.commits == 1


def test_company_user_lookup_is_scoped_to_admin_company() -> None:
    company = make_company()
    admin = make_user(company)
    db = FakeDb()

    assert get_company_user(db, admin, uuid4()) is None
    sql = str(db.statements[0])
    assert "users.company_id" in sql
    assert "users.id" in sql


def test_admin_cannot_block_self_or_change_another_admin() -> None:
    company = make_company()
    admin = make_user(company)
    db = FakeDb()

    with pytest.raises(CompanyUserError):
        set_company_user_status(db, admin, admin, False)


def test_blocked_user_cannot_authenticate() -> None:
    company = make_company()
    user = make_user(company, role=UserRole.user)
    user.is_active = False
    db = FakeDb(scalar_values=[user])

    assert authenticate_user(db, user.email, "SenhaInicial123") is None


def test_password_reset_requires_change_and_change_password_clears_flag() -> None:
    company = make_company()
    user = make_user(company, role=UserRole.user)
    db = FakeDb()

    reset_company_user_password(db, user, "Temporaria456")
    assert user.must_change_password is True
    assert verify_password("Temporaria456", user.password_hash)

    changed = change_user_password(db, user, "Temporaria456", "NovaSenha789")
    assert changed.must_change_password is False
    assert verify_password("NovaSenha789", changed.password_hash)


def test_change_password_rejects_wrong_current_password() -> None:
    company = make_company()
    user = make_user(company, role=UserRole.user)
    db = FakeDb()

    with pytest.raises(PasswordChangeError):
        change_user_password(db, user, "SenhaErrada", "NovaSenha789")


def test_employee_role_cannot_use_company_admin_dependency() -> None:
    company = make_company()
    user = make_user(company, role=UserRole.user)

    with pytest.raises(HTTPException) as exc:
        require_company_admin(current_user=user)

    assert exc.value.status_code == 403
