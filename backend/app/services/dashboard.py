from calendar import monthrange
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionPaymentMethod
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.schemas.dashboard import DashboardAmountSummary
from app.schemas.dashboard import DashboardDueAlert
from app.schemas.dashboard import DashboardPaymentMethodSummary
from app.schemas.dashboard import DashboardResponse

ZERO = Decimal("0.00")
PAYMENT_METHOD_LABELS = {
    FinancialTransactionPaymentMethod.credit: "Credito",
    FinancialTransactionPaymentMethod.debit: "Debito",
    FinancialTransactionPaymentMethod.pix: "Pix",
    FinancialTransactionPaymentMethod.boleto: "Boleto",
    FinancialTransactionPaymentMethod.bank_transfer: "Transferencia",
    FinancialTransactionPaymentMethod.cash: "Dinheiro",
}


def get_financial_dashboard(db: Session, user: User) -> DashboardResponse:
    today = date.today()
    period_start = today.replace(day=1)
    period_end = today.replace(day=monthrange(today.year, today.month)[1])
    company = db.get(Company, user.company_id)
    transactions = list(
        db.scalars(
            select(FinancialTransaction).where(
                FinancialTransaction.company_id == user.company_id,
                FinancialTransaction.status != FinancialTransactionStatus.canceled,
                FinancialTransaction.deleted_at.is_(None),
            ).options(
                selectinload(FinancialTransaction.category),
                selectinload(FinancialTransaction.contact),
            )
        )
    )

    current_balance = company.opening_balance if company is not None else ZERO
    month_income = ZERO
    month_expense = ZERO
    open_payables_total = ZERO
    open_receivables_total = ZERO
    overdue_payables_total = ZERO
    overdue_receivables_total = ZERO
    forecast_payables_total = ZERO
    forecast_receivables_total = ZERO
    due_alerts: list[DashboardDueAlert] = []
    payment_method_totals = {
        payment_method: {
            "income_total": ZERO,
            "expense_total": ZERO,
            "count": 0,
        }
        for payment_method in FinancialTransactionPaymentMethod
    }
    open_payables_count = 0
    open_receivables_count = 0
    overdue_payables_count = 0
    overdue_receivables_count = 0

    for transaction in transactions:
        if transaction.status == FinancialTransactionStatus.canceled:
            continue
        if transaction.deleted_at is not None:
            continue

        amount = transaction.amount

        if _transaction_impacts_current_balance(transaction, company):
            if transaction.type == FinancialTransactionType.income:
                current_balance += amount
            else:
                current_balance -= amount

        if (
            transaction.status == FinancialTransactionStatus.settled
            and transaction.settled_at is not None
            and period_start <= transaction.settled_at.date() <= period_end
        ):
            if transaction.type == FinancialTransactionType.income:
                month_income += amount
            else:
                month_expense += amount
            if transaction.payment_method is not None:
                summary = payment_method_totals[transaction.payment_method]
                summary["count"] += 1
                if transaction.type == FinancialTransactionType.income:
                    summary["income_total"] += amount
                else:
                    summary["expense_total"] += amount

        if transaction.status != FinancialTransactionStatus.pending:
            continue

        due_alert = _build_due_alert(transaction, today)
        if due_alert is not None:
            due_alerts.append(due_alert)

        if transaction.type == FinancialTransactionType.expense:
            open_payables_total += amount
            open_payables_count += 1
            if transaction.due_date is not None and transaction.due_date < today:
                overdue_payables_total += amount
                overdue_payables_count += 1
            if transaction.due_date is not None and transaction.due_date <= period_end:
                forecast_payables_total += amount
        else:
            open_receivables_total += amount
            open_receivables_count += 1
            if transaction.due_date is not None and transaction.due_date < today:
                overdue_receivables_total += amount
                overdue_receivables_count += 1
            if transaction.due_date is not None and transaction.due_date <= period_end:
                forecast_receivables_total += amount

    month_result = month_income - month_expense
    month_end_balance_forecast = (
        current_balance + forecast_receivables_total - forecast_payables_total
    )
    due_alerts.sort(key=lambda alert: (alert.days_until_due, alert.due_date, alert.title))

    return DashboardResponse(
        period_start=period_start,
        period_end=period_end,
        generated_at=datetime.now(UTC),
        current_balance=current_balance,
        month_income=month_income,
        month_expense=month_expense,
        month_result=month_result,
        open_payables=DashboardAmountSummary(
            count=open_payables_count,
            total=open_payables_total,
        ),
        open_receivables=DashboardAmountSummary(
            count=open_receivables_count,
            total=open_receivables_total,
        ),
        overdue_payables=DashboardAmountSummary(
            count=overdue_payables_count,
            total=overdue_payables_total,
        ),
        overdue_receivables=DashboardAmountSummary(
            count=overdue_receivables_count,
            total=overdue_receivables_total,
        ),
        payment_methods=_build_payment_method_summaries(payment_method_totals),
        due_alerts=due_alerts,
        month_end_balance_forecast=month_end_balance_forecast,
        calculation_criteria=_calculation_criteria(),
    )


def _calculation_criteria() -> dict[str, str]:
    return {
        "current_balance": (
            "opening_balance plus settled income minus settled expense. If "
            "opening_balance_date exists, only settled transactions with settled_at on or "
            "after that date are included. Canceled and soft-deleted transactions are ignored."
        ),
        "month_income": "Settled, non-deleted income with settled_at inside the current month.",
        "month_expense": "Settled, non-deleted expense with settled_at inside the current month.",
        "month_result": "Settled month income minus settled month expense.",
        "payment_methods": (
            "Settled, non-deleted transactions inside the current month grouped by "
            "the manually selected payment method."
        ),
        "open_payables": "Pending expense transactions.",
        "open_receivables": "Pending income transactions.",
        "overdue_payables": "Pending expense transactions with due_date before today.",
        "overdue_receivables": "Pending income transactions with due_date before today.",
        "due_alerts": (
            "Pending income and expense transactions due today, overdue, or due within "
            "the next 5 days. Severity is red for overdue or due today, orange for up "
            "to 2 days, and yellow for up to 5 days."
        ),
        "month_end_balance_forecast": (
            "current_balance plus pending receivables due by month end minus pending "
            "payables due by month end."
        ),
    }


def _transaction_impacts_current_balance(
    transaction: FinancialTransaction,
    company: Company | None,
) -> bool:
    if transaction.status != FinancialTransactionStatus.settled:
        return False
    if company is None or company.opening_balance_date is None:
        return True
    if transaction.settled_at is None:
        return False
    return transaction.settled_at.date() >= company.opening_balance_date


def _build_payment_method_summaries(
    totals: dict[FinancialTransactionPaymentMethod, dict[str, Decimal | int]],
) -> list[DashboardPaymentMethodSummary]:
    summaries: list[DashboardPaymentMethodSummary] = []
    for payment_method in FinancialTransactionPaymentMethod:
        item = totals[payment_method]
        income_total = item["income_total"]
        expense_total = item["expense_total"]
        assert isinstance(income_total, Decimal)
        assert isinstance(expense_total, Decimal)
        count = item["count"]
        assert isinstance(count, int)
        summaries.append(
            DashboardPaymentMethodSummary(
                payment_method=payment_method,
                label=PAYMENT_METHOD_LABELS[payment_method],
                income_total=income_total,
                expense_total=expense_total,
                net_total=income_total - expense_total,
                count=count,
            )
        )
    return summaries


def _build_due_alert(
    transaction: FinancialTransaction,
    today: date,
) -> DashboardDueAlert | None:
    if transaction.due_date is None:
        return None

    days_until_due = (transaction.due_date - today).days
    if days_until_due > 5:
        return None

    if days_until_due <= 0:
        severity = "red"
    elif days_until_due <= 2:
        severity = "orange"
    else:
        severity = "yellow"

    kind_label = "pagar" if transaction.type == FinancialTransactionType.expense else "receber"
    return DashboardDueAlert(
        transaction_id=transaction.id,
        kind=transaction.type,
        severity=severity,
        title=f"Conta a {kind_label}",
        description=transaction.description,
        amount=transaction.amount,
        due_date=transaction.due_date,
        days_until_due=days_until_due,
        contact_name=_related_name(transaction.contact),
        category_name=_related_name(transaction.category),
    )


def _related_name(value) -> str | None:
    if value is None:
        return None
    return getattr(value, "name", None)
