"""Apply and verify database migrations during production Vercel builds."""

import os
import socket
import subprocess
import sys

from sqlalchemy.engine import make_url

from app.db.migration_url import get_migration_database_url

PRODUCTION_DEFAULTS = {
    "APP_ENV": "production",
    "APP_DEBUG": "false",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    "EMAIL_DELIVERY_MODE": "mock",
    "EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES": "60",
    "PASSWORD_RESET_CODE_EXPIRE_MINUTES": "15",
    "PASSWORD_RESET_RESEND_INTERVAL_SECONDS": "60",
}


def main() -> None:
    if os.environ.get("VERCEL_ENV") != "production":
        print("Skipping production database migrations for this Vercel deployment.")
        return

    _configure_ipv4_migration_connection()

    for key, value in PRODUCTION_DEFAULTS.items():
        if not os.environ.get(key):
            os.environ[key] = value

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "app.scripts.check_alembic_head"],
        check=True,
    )


def _configure_ipv4_migration_connection() -> None:
    url = make_url(get_migration_database_url())
    if not url.host:
        raise RuntimeError("A database hostname is required for production migrations.")

    try:
        addresses = socket.getaddrinfo(
            url.host,
            url.port or 5432,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise RuntimeError(
            "Could not resolve an IPv4 address for the production database."
        ) from exc

    if not addresses:
        raise RuntimeError(
            "Could not resolve an IPv4 address for the production database."
        )

    ipv4_address = addresses[0][4][0]
    query = dict(url.query)
    query["hostaddr"] = ipv4_address

    # Keep the hostname in the URL for TLS verification while fixing the
    # network address selected for libpq in environments without IPv6 egress.
    os.environ["MIGRATION_DATABASE_URL"] = url.set(query=query).render_as_string(
        hide_password=False
    )
    print("Configured production database migrations to connect over IPv4.")


if __name__ == "__main__":
    main()
