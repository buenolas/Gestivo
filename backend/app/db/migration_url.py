import os
from pathlib import Path


ENV_FILES = (
    ".env.production.local",
    ".env.local",
    ".env",
)


def get_migration_database_url() -> str:
    env_values = _load_env_values()
    url = (
        env_values.get("MIGRATION_DATABASE_URL")
        or env_values.get("DATABASE_URL_UNPOOLED")
        or env_values.get("POSTGRES_URL_NON_POOLING")
        or env_values.get("DATABASE_URL")
        or env_values.get("POSTGRES_URL")
    )
    if not url:
        raise RuntimeError(
            "DATABASE_URL or MIGRATION_DATABASE_URL is required to run Alembic."
        )
    return _normalize_postgresql_driver(url)


def _load_env_values() -> dict[str, str]:
    values = {
        key: value
        for key, value in os.environ.items()
        if value is not None and value.strip() != ""
    }
    for env_file in ENV_FILES:
        path = Path(env_file)
        if path.exists():
            values.update(_read_env_file(path, existing_values=values))
    return values


def _read_env_file(path: Path, *, existing_values: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or not value or key in existing_values:
            continue
        values[key] = value
    return values


def _normalize_postgresql_driver(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url
