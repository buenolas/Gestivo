import asyncio
import os

TEST_DATABASE_URL = (
    "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"
)

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

import pytest
from fastapi import HTTPException

from app import main as main_module
from app.core.config import Settings


def test_migration_database_url_defaults_to_runtime_database_url() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://pooled.example/app",
        jwt_secret_key="x" * 32,
        _env_file=None,
    )

    assert settings.alembic_database_url == settings.database_url


def test_migration_database_url_prefers_direct_connection() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://pooled.example/app",
        migration_database_url="postgresql+psycopg://direct.example/app",
        jwt_secret_key="x" * 32,
        _env_file=None,
    )

    assert settings.alembic_database_url == "postgresql+psycopg://direct.example/app"


def test_neon_postgresql_urls_use_psycopg_driver() -> None:
    settings = Settings(
        database_url="postgresql://pooled.example/app?sslmode=require",
        migration_database_url="postgres://direct.example/app?sslmode=require",
        jwt_secret_key="x" * 32,
        _env_file=None,
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.alembic_database_url.startswith("postgresql+psycopg://")


def test_cron_endpoint_rejects_missing_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module.settings, "cron_secret", "c" * 32)

    with pytest.raises(HTTPException) as exc_info:
        main_module.expire_subscriptions_cron(authorization=None, db=object())

    assert exc_info.value.status_code == 401


def test_cron_endpoint_expires_subscriptions_when_authorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module.settings, "cron_secret", "c" * 32)
    monkeypatch.setattr(
        main_module,
        "expire_overdue_subscriptions",
        lambda db: 4,
    )

    response = main_module.expire_subscriptions_cron(
        authorization=f"Bearer {'c' * 32}",
        db=object(),
    )

    assert response == {"status": "ok", "updated_count": 4}


def test_cors_headers_are_included_on_unhandled_errors() -> None:
    @main_module.fastapi_app.get("/__test__/unhandled-error")
    def unhandled_error() -> None:
        raise RuntimeError("Erro interno simulado")

    response_start = asyncio.run(
        _call_app_and_get_response_start("/__test__/unhandled-error")
    )

    assert response_start["status"] == 500
    assert (
        dict(response_start["headers"])[b"access-control-allow-origin"]
        == b"http://localhost:5173"
    )


async def _call_app_and_get_response_start(path: str) -> dict:
    messages: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": [
            (b"host", b"testserver"),
            (b"origin", b"http://localhost:5173"),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    try:
        await main_module.app(scope, receive, send)
    except RuntimeError:
        pass

    return next(message for message in messages if message["type"] == "http.response.start")
