from app.db.session import SessionLocal
from app.services.subscription import expire_overdue_subscriptions


def main() -> None:
    db = SessionLocal()
    try:
        updated_count = expire_overdue_subscriptions(db)
        print(f"Assinaturas atualizadas para pending_payment: {updated_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
