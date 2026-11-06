from app.db.session import SessionLocal
from app.services.company_deletion import purge_due_company_deletions
from app.services.subscription import expire_overdue_subscriptions


def main() -> None:
    db = SessionLocal()
    try:
        updated_count = expire_overdue_subscriptions(db)
        purged_count = purge_due_company_deletions(db)
        print(f"Assinaturas atualizadas para pending_payment: {updated_count}")
        print(f"Empresas excluídas após retenção: {purged_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
