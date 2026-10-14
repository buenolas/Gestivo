from calendar import monthrange
from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from decimal import ROUND_HALF_UP

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
from app.schemas.dashboard import DashboardCategorySummary
from app.schemas.dashboard import DashboardComparison
from app.schemas.dashboard import DashboardDueAlert
from app.schemas.dashboard import DashboardPaymentMethodSummary
from app.schemas.dashboard import DashboardResponse
from app.schemas.dashboard import DashboardTrendPoint

ZERO = Decimal("0.00")
PAYMENT_METHOD_LABELS = {
    FinancialTransactionPaymentMethod.credit: "Credito",
    FinancialTransactionPaymentMethod.debit: "Debito",
    FinancialTransactionPaymentMethod.pix: "Pix",
    FinancialTransactionPaymentMethod.boleto: "Boleto",
    FinancialTransactionPaymentMethod.bank_transfer: "Transferencia",
    FinancialTransactionPaymentMethod.cash: "Dinheiro",
}


def get_financial_dashboard(
    db: Session,
    user: User,
    *,
    period: str = "month",
    month: date | None = None,
    comparison_start: date | None = None,
    comparison_end: date | None = None,
) -> DashboardResponse:
    today = date.today()
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

    period_start, period_end = _resolve_period(period, month, transactions, today)
    if (comparison_start is None) != (comparison_end is None):
        raise ValueError("Informe as datas inicial e final do período de comparação.")
    if (
        comparison_start is not None
        and comparison_end is not None
        and comparison_start > comparison_end
    ):
        raise ValueError("A data inicial da comparação precisa ser anterior à data final.")

    current_balance = company.opening_balance if company is not None else ZERO
    period_income = ZERO
    period_expense = ZERO
    period_transaction_count = 0
    comparison_income = ZERO
    comparison_expense = ZERO
    comparison_transaction_count = 0
    trend_totals: dict[date, dict[str, Decimal | int]] = {}
    category_totals: dict[
        tuple[FinancialTransactionType, str], dict[str, Decimal | int]
    ] = {}
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
    current_month_end = _month_end(today.replace(day=1))

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

        is_settled = (
            transaction.status == FinancialTransactionStatus.settled
            and transaction.settled_at is not None
        )
        settled_date = transaction.settled_at.date() if is_settled else None
        if (
            is_settled
            and settled_date is not None
            and period_start <= settled_date <= period_end
        ):
            period_transaction_count += 1
            trend_summary = trend_totals.setdefault(
                settled_date,
                {"income": ZERO, "expense": ZERO, "count": 0},
            )
            category_name = _related_name(transaction.category) or "Sem categoria"
            category_summary = category_totals.setdefault(
                (transaction.type, category_name),
                {"total": ZERO, "count": 0},
            )
            category_summary["total"] = category_summary["total"] + amount
            category_summary["count"] = category_summary["count"] + 1

            if transaction.type == FinancialTransactionType.income:
                period_income += amount
                trend_summary["income"] = trend_summary["income"] + amount
            else:
                period_expense += amount
                trend_summary["expense"] = trend_summary["expense"] + amount
            trend_summary["count"] = trend_summary["count"] + 1

            if transaction.payment_method is not None:
                summary = payment_method_totals[transaction.payment_method]
                summary["count"] += 1
                if transaction.type == FinancialTransactionType.income:
                    summary["income_total"] += amount
                else:
                    summary["expense_total"] += amount

        if (
            is_settled
            and settled_date is not None
            and comparison_start is not None
            and comparison_end is not None
            and comparison_start <= settled_date <= comparison_end
        ):
            comparison_transaction_count += 1
            if transaction.type == FinancialTransactionType.income:
                comparison_income += amount
            else:
                comparison_expense += amount

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
            if transaction.due_date is not None and transaction.due_date <= current_month_end:
                forecast_payables_total += amount
        else:
            open_receivables_total += amount
            open_receivables_count += 1
            if transaction.due_date is not None and transaction.due_date < today:
                overdue_receivables_total += amount
                overdue_receivables_count += 1
            if transaction.due_date is not None and transaction.due_date <= current_month_end:
                forecast_receivables_total += amount

    period_result = period_income - period_expense
    month_end_balance_forecast = (
        current_balance + forecast_receivables_total - forecast_payables_total
    )
    due_alerts.sort(key=lambda alert: (alert.days_until_due, alert.due_date, alert.title))

    trend_granularity = "day" if period == "month" else "month"
    trend_end = min(period_end, today) if trend_granularity == "day" else period_end
    trend_series = _build_trend_series(
        period_start,
        trend_end,
        trend_totals,
        granularity=trend_granularity,
    )
    category_summaries = _build_category_summaries(category_totals)
    comparison = None
    if comparison_start is not None and comparison_end is not None:
        comparison_result = comparison_income - comparison_expense
        comparison = _build_comparison(
            period_start=comparison_start,
            period_end=comparison_end,
            income=period_income,
            expense=period_expense,
            result=period_result,
            comparison_income=comparison_income,
            comparison_expense=comparison_expense,
            comparison_result=comparison_result,
            transaction_count=comparison_transaction_count,
        )

    return DashboardResponse(
        period_start=period_start,
        period_end=period_end,
        generated_at=datetime.now(UTC),
        current_balance=current_balance,
        month_income=period_income,
        month_expense=period_expense,
        month_result=period_result,
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
        transaction_count=period_transaction_count,
        trend_granularity=trend_granularity,
        trend_series=trend_series,
        category_totals=category_summaries,
        comparison=comparison,
        calculation_criteria=_calculation_criteria(),
    )


def _resolve_period(
    period: str,
    month: date | None,
    transactions: list[FinancialTransaction],
    today: date,
) -> tuple[date, date]:
    current_month = today.replace(day=1)
    if period == "all":
        settled_months = [
            transaction.settled_at.date().replace(day=1)
            for transaction in transactions
            if transaction.status == FinancialTransactionStatus.settled
            and transaction.settled_at is not None
            and transaction.deleted_at is None
        ]
        return min(settled_months, default=current_month), _month_end(current_month)

    month_count_by_period = {"month": 1, "3m": 3, "6m": 6, "12m": 12}
    month_count = month_count_by_period.get(period)
    if month_count is None:
        raise ValueError("Selecione um período válido para o dashboard.")

    anchor_month = (month or today).replace(day=1)
    if anchor_month > current_month:
        raise ValueError("O mês de referência não pode ser futuro.")
    period_start = _shift_month(anchor_month, -(month_count - 1))
    return period_start, _month_end(anchor_month)


def _month_end(month_start: date) -> date:
    return date(
        month_start.year,
        month_start.month,
        monthrange(month_start.year, month_start.month)[1],
    )


def _shift_month(month_start: date, months: int) -> date:
    month_index = month_start.year * 12 + month_start.month - 1 + months
    return date(month_index // 12, month_index % 12 + 1, 1)


def _build_trend_series(
    period_start: date,
    period_end: date,
    totals: dict[date, dict[str, Decimal | int]],
    *,
    granularity: str,
) -> list[DashboardTrendPoint]:
    points: list[DashboardTrendPoint] = []
    current = period_start if granularity == "day" else period_start.replace(day=1)
    last = period_end if granularity == "day" else period_end.replace(day=1)
    while current <= last:
        if granularity == "day":
            summary = totals.get(current, {})
        else:
            summary: dict[str, Decimal | int] = {
                "income": ZERO,
                "expense": ZERO,
                "count": 0,
            }
            for transaction_date, day_totals in totals.items():
                if transaction_date.replace(day=1) == current:
                    summary["income"] += day_totals["income"]
                    summary["expense"] += day_totals["expense"]
                    summary["count"] += day_totals["count"]
        income = summary.get("income", ZERO)
        expense = summary.get("expense", ZERO)
        count = summary.get("count", 0)
        assert isinstance(income, Decimal)
        assert isinstance(expense, Decimal)
        assert isinstance(count, int)
        points.append(
            DashboardTrendPoint(
                date=current,
                income=income,
                expense=expense,
                result=income - expense,
                transaction_count=count,
            )
        )
        current = current + timedelta(days=1) if granularity == "day" else _shift_month(current, 1)
    return points


def _build_category_summaries(
    totals: dict[tuple[FinancialTransactionType, str], dict[str, Decimal | int]],
) -> list[DashboardCategorySummary]:
    summaries: list[DashboardCategorySummary] = []
    for (transaction_type, name), values in totals.items():
        total = values["total"]
        count = values["count"]
        assert isinstance(total, Decimal)
        assert isinstance(count, int)
        summaries.append(
            DashboardCategorySummary(
                type=transaction_type,
                name=name,
                total=total,
                count=count,
            )
        )
    return sorted(summaries, key=lambda item: (item.type.value, -item.total, item.name.lower()))


def _build_comparison(
    *,
    period_start: date,
    period_end: date,
    income: Decimal,
    expense: Decimal,
    result: Decimal,
    comparison_income: Decimal,
    comparison_expense: Decimal,
    comparison_result: Decimal,
    transaction_count: int,
) -> DashboardComparison:
    return DashboardComparison(
        period_start=period_start,
        period_end=period_end,
        income=comparison_income,
        expense=comparison_expense,
        result=comparison_result,
        income_change=income - comparison_income,
        expense_change=expense - comparison_expense,
        result_change=result - comparison_result,
        income_change_percent=_percentage_change(income, comparison_income),
        expense_change_percent=_percentage_change(expense, comparison_expense),
        result_change_percent=_percentage_change(result, comparison_result),
        transaction_count=transaction_count,
    )


def _percentage_change(current: Decimal, comparison: Decimal) -> Decimal | None:
    if comparison == ZERO:
        return None
    return (((current - comparison) / abs(comparison)) * Decimal("100")).quantize(
        Decimal("0.1"),
        rounding=ROUND_HALF_UP,
    )


def _calculation_criteria() -> dict[str, str]:
    return {
        "current_balance": (
            "opening_balance plus settled income minus settled expense. If "
            "opening_balance_date exists, only settled transactions with settled_at on or "
            "after that date are included. Canceled and soft-deleted transactions are ignored."
        ),
        "month_income": "Settled, non-deleted income with settled_at inside the selected period.",
        "month_expense": "Settled, non-deleted expense with settled_at inside the selected period.",
        "month_result": "Settled income minus settled expense inside the selected period.",
        "payment_methods": (
            "Settled, non-deleted transactions inside the selected period grouped by "
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
