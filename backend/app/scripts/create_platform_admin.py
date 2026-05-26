import argparse
import getpass

from app.db.session import SessionLocal
from app.services.platform_admin import PlatformAdminSeedError
from app.services.platform_admin import create_platform_admin


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria um usuário platform_admin fora do cadastro público.",
    )
    parser.add_argument("--name", required=True, help="Nome do administrador")
    parser.add_argument("--email", required=True, help="E-mail do administrador")
    parser.add_argument(
        "--password",
        help="Senha do administrador. Se omitida, será solicitada no terminal.",
    )
    args = parser.parse_args()

    password = args.password or getpass.getpass("Senha: ")
    with SessionLocal() as db:
        try:
            user = create_platform_admin(
                db,
                name=args.name,
                email=args.email,
                password=password,
            )
        except PlatformAdminSeedError as error:
            raise SystemExit(str(error)) from error

    print(f"platform_admin criado: {user.email}")


if __name__ == "__main__":
    main()
