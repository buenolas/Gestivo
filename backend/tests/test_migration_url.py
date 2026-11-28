from app.db import migration_url


def test_production_migration_prefers_application_url_when_provider_urls_remain(
    monkeypatch,
) -> None:
    monkeypatch.setattr(migration_url, "ENV_FILES", ())
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://vps.example/app")
    monkeypatch.setenv("MIGRATION_DATABASE_URL", "postgresql://legacy-neon.example/app")
    monkeypatch.setenv("DATABASE_URL_UNPOOLED", "postgresql://legacy-neon.example/app")
    monkeypatch.setenv("POSTGRES_URL_NON_POOLING", "postgresql://legacy-neon.example/app")

    assert (
        migration_url.get_migration_database_url()
        == "postgresql+psycopg://vps.example/app"
    )
