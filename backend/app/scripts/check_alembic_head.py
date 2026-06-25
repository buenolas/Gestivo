from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from app.db.migration_url import get_migration_database_url


def main() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())

    engine = create_engine(get_migration_database_url(), poolclass=NullPool)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_heads = set(context.get_current_heads())

    if current_heads != expected_heads:
        expected = ", ".join(sorted(expected_heads)) or "<none>"
        current = ", ".join(sorted(current_heads)) or "<none>"
        raise SystemExit(
            "Database schema is not at Alembic head. "
            f"Current revision(s): {current}. Expected head(s): {expected}."
        )

    print(
        "Database schema is at Alembic head: "
        f"{', '.join(sorted(expected_heads))}."
    )


if __name__ == "__main__":
    main()
