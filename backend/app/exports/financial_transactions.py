import csv
import io
from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.services.financial_transaction import list_financial_transactions

CSV_EXCEL_BOM = "\ufeff"
CSV_DELIMITER = ";"
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")


def export_financial_transactions_csv(
    db: Session,
    user: User,
    transaction_type: FinancialTransactionType | None = None,
    status: FinancialTransactionStatus | None = None,
    category_id: UUID | None = None,
    contact_id: UUID | None = None,
    employee_id: UUID | None = None,
    source: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
) -> bytes:
    transactions = list_financial_transactions(
        db=db,
        user=user,
        transaction_type=transaction_type,
        status=status,
        category_id=category_id,
        contact_id=contact_id,
        employee_id=employee_id,
        source=source,
        start_date=start_date,
        end_date=end_date,
        search=search,
    )

    output = io.StringIO()
    output.write(CSV_EXCEL_BOM)
    writer = csv.writer(output, delimiter=CSV_DELIMITER, lineterminator="\r\n")
    writer.writerow(
        [
            "ID",
            "Descricao",
            "Tipo",
            "Status",
            "Competencia",
            "Vencimento",
            "Liquidado em",
            "Categoria",
            "Cliente/Fornecedor",
            "Funcionario",
            "Produto",
            "Valor unitario",
            "Quantidade",
            "Unidade",
            "Valor",
            "Origem",
            "Observacoes",
        ]
    )
    for transaction in transactions:
        writer.writerow(_transaction_row(transaction))

    return output.getvalue().encode("utf-8")


def _transaction_row(transaction: FinancialTransaction) -> list[str]:
    return [
        str(transaction.id),
        _safe_csv_text(transaction.description),
        _type_label(transaction.type),
        _status_label(transaction.status),
        _format_date(transaction.competence_date),
        _format_date(transaction.due_date),
        _format_datetime(transaction.settled_at),
        _safe_csv_text(_category_name(transaction)),
        _safe_csv_text(_contact_name(transaction)),
        _safe_csv_text(_employee_name(transaction)),
        _safe_csv_text(transaction.product_name or ""),
        _format_optional_money(transaction.product_unit_price),
        _format_quantity(transaction.product_quantity),
        _safe_csv_text(transaction.product_unit or ""),
        _format_money(transaction.amount),
        transaction.source,
        _safe_csv_text(transaction.notes or ""),
    ]


def _safe_csv_text(value: str) -> str:
    if value.startswith(CSV_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def _category_name(transaction: FinancialTransaction) -> str:
    category = getattr(transaction, "category", None)
    if category is not None:
        return category.name
    return str(transaction.category_id) if transaction.category_id is not None else ""


def _contact_name(transaction: FinancialTransaction) -> str:
    contact = getattr(transaction, "contact", None)
    if contact is not None:
        return contact.name
    return str(transaction.contact_id) if transaction.contact_id is not None else ""


def _employee_name(transaction: FinancialTransaction) -> str:
    employee = getattr(transaction, "employee", None)
    if employee is not None:
        return employee.name
    return str(transaction.employee_id) if transaction.employee_id is not None else ""


def _format_money(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01'))}".replace(".", ",")


def _format_optional_money(amount: Decimal | None) -> str:
    if amount is None:
        return ""
    return _format_money(amount)


def _format_quantity(quantity: Decimal | None) -> str:
    if quantity is None:
        return ""
    return f"{quantity.normalize()}".replace(".", ",")


def _format_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d/%m/%Y")


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")


def _type_label(transaction_type: FinancialTransactionType) -> str:
    if transaction_type == FinancialTransactionType.income:
        return "Entrada"
    return "Saida"


def _status_label(status: FinancialTransactionStatus) -> str:
    labels = {
        FinancialTransactionStatus.pending: "Pendente",
        FinancialTransactionStatus.settled: "Liquidado",
        FinancialTransactionStatus.canceled: "Cancelado",
    }
    return labels[status]
