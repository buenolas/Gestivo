"""Apply and verify database migrations during production Vercel builds."""

import os
import subprocess
import sys

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


if __name__ == "__main__":
    main()
