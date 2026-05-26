from calendar import monthrange
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.schemas.dashboard import DashboardAmountSummary
from app.schemas.dashboard import DashboardResponse

ZERO = Decimal("0.00")


def get_financial_dashboard(db: Session, user: User) -> DashboardResponse:
    today = date.today()
    period_start = today.replace(day=1)
    period_end = today.replace(day=monthrange(today.year, today.month)[1])
    transactions = list(
        db.scalars(
            select(FinancialTransaction).where(
                FinancialTransaction.company_id == user.company_id,
                FinancialTransaction.status != FinancialTransactionStatus.canceled,
            )
        )
    )

    current_balance = ZERO
    month_income = ZERO
    month_expense = ZERO
    open_payables_total = ZERO
    open_receivables_total = ZERO
    overdue_payables_total = ZERO
    overdue_receivables_total = ZERO
    forecast_payables_total = ZERO
    forecast_receivables_total = ZERO
    open_payables_count = 0
    open_receivables_count = 0
    overdue_payables_count = 0
    overdue_receivables_count = 0

    for transaction in transactions:
        amount = transaction.amount

        if transaction.status == FinancialTransactionStatus.settled:
            if transaction.type == FinancialTransactionType.income:
                current_balance += amount
            else:
                current_balance -= amount

        if period_start <= transaction.competence_date <= period_end:
            if transaction.type == FinancialTransactionType.income:
                month_income += amount
            else:
                month_expense += amount

        if transaction.status != FinancialTransactionStatus.pending:
            continue

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
        month_end_balance_forecast=month_end_balance_forecast,
        calculation_criteria=_calculation_criteria(),
    )


def _calculation_criteria() -> dict[str, str]:
    return {
        "current_balance": (
            "Settled income minus settled expense. Opening balance is not included "
            "because companies do not have opening_balance yet."
        ),
        "month_income": "Non-canceled income with competence_date inside the current month.",
        "month_expense": "Non-canceled expense with competence_date inside the current month.",
        "month_result": "month_income minus month_expense.",
        "open_payables": "Pending expense transactions.",
        "open_receivables": "Pending income transactions.",
        "overdue_payables": "Pending expense transactions with due_date before today.",
        "overdue_receivables": "Pending income transactions with due_date before today.",
        "month_end_balance_forecast": (
            "current_balance plus pending receivables due by month end minus pending "
            "payables due by month end."
        ),
    }
