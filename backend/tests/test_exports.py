from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
import os
from uuid import uuid4

TEST_DATABASE_URL = "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

from app.api import exports as exports_api
from app.exports.financial_transactions import export_financial_transactions_csv
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.contact import Contact
from app.models.contact import ContactType
from app.models.employee import Employee
from app.models.employee import EmployeeStatus
from app.models.financial_category import FinancialCategory
from app.models.financial_category import FinancialCategoryType
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.user import User
from app.models.user import UserRole


class FakeDb:
    def __init__(self, transactions: list[FinancialTransaction]) -> None:
        self.transactions = transactions

    def scalars(self, statement):
        return self.transactions


def make_company() -> Company:
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=SubscriptionStatus.active,
        trial_ends_at=datetime.now(UTC),
        subscription_valid_until=datetime.now(UTC),
        opening_balance=Decimal("0.00"),
        is_platform_company=False,
    )


def make_user(company: Company) -> User:
    return User(
        id=uuid4(),
        company_id=company.id,
        name="Usuario Teste",
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        role=UserRole.company_admin,
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )


def make_transaction(company: Company, category: FinancialCategory) -> FinancialTransaction:
    user_id = uuid4()
    contact = Contact(
        id=uuid4(),
        company_id=company.id,
        name="Cliente ABC",
        type=ContactType.customer,
        is_active=True,
    )
    employee = Employee(
        id=uuid4(),
        company_id=company.id,
        name="Funcionario Teste",
        position="Vendas",
        salary_amount=Decimal("2000.00"),
        contract_start_date=date(2026, 1, 1),
        status=EmployeeStatus.active,
    )
    return FinancialTransaction(
        id=uuid4(),
        company_id=company.id,
        category_id=category.id,
        category=category,
        contact_id=contact.id,
        contact=contact,
        employee_id=employee.id,
        employee=employee,
        description="Venda de servico",
        amount=Decimal("1234.50"),
        type=FinancialTransactionType.income,
        status=FinancialTransactionStatus.settled,
        competence_date=date(2026, 5, 10),
        due_date=date(2026, 5, 12),
        settled_at=datetime(2026, 5, 13, 14, 30, tzinfo=UTC),
        notes="Pago via transferencia",
        product_name="Produto A",
        product_unit_price=Decimal("100.00"),
        product_quantity=Decimal("2.000"),
        product_unit="un",
        source="manual",
        created_by=user_id,
        updated_by=user_id,
    )


def test_financial_transactions_csv_uses_bom_semicolon_and_brazilian_formats() -> None:
    company = make_company()
    user = make_user(company)
    category = FinancialCategory(
        id=uuid4(),
        company_id=company.id,
        name="Servicos",
        type=FinancialCategoryType.income,
        is_active=True,
    )
    db = FakeDb([make_transaction(company, category)])

    content = export_financial_transactions_csv(db, user)
    text = content.decode("utf-8")

    assert text.startswith("\ufeff")
    assert "Descricao;Tipo;Status;Competencia;Vencimento" in text
    assert "Categoria;Cliente/Fornecedor;Funcionario;Produto;Valor unitario;Quantidade;Unidade;Valor" in text
    assert "Venda de servico;Entrada;Liquidado;10/05/2026;12/05/2026;13/05/2026 14:30;Servicos;Cliente ABC;Funcionario Teste;Produto A;100,00;2;un;1234,50;manual;Pago via transferencia" in text


def test_financial_transactions_csv_ignores_soft_deleted_transactions() -> None:
    company = make_company()
    user = make_user(company)
    category = FinancialCategory(
        id=uuid4(),
        company_id=company.id,
        name="Servicos",
        type=FinancialCategoryType.income,
        is_active=True,
    )
    visible = make_transaction(company, category)
    deleted = make_transaction(company, category)
    deleted.description = "Lancamento removido"
    deleted.deleted_at = datetime.now(UTC)
    db = FakeDb([visible, deleted])

    content = export_financial_transactions_csv(db, user)
    text = content.decode("utf-8")

    assert "Venda de servico" in text
    assert "Lancamento removido" not in text


def test_financial_transactions_csv_escapes_formula_like_text() -> None:
    company = make_company()
    user = make_user(company)
    category = FinancialCategory(
        id=uuid4(),
        company_id=company.id,
        name="@Categoria",
        type=FinancialCategoryType.income,
        is_active=True,
    )
    transaction = make_transaction(company, category)
    transaction.description = "=IMPORTXML(\"https://example.com\")"
    transaction.notes = "+observacao"
    db = FakeDb([transaction])

    content = export_financial_transactions_csv(db, user)
    text = content.decode("utf-8")

    assert "'=IMPORTXML" in text
    assert "'@Categoria" in text
    assert "'+observacao" in text


def test_export_endpoint_passes_authenticated_user_and_filters(monkeypatch) -> None:
    company = make_company()
    user = make_user(company)
    category_id = uuid4()
    captured = {}

    def fake_export(**kwargs):
        captured.update(kwargs)
        return b"\xef\xbb\xbfID\r\n"

    monkeypatch.setattr(exports_api, "export_financial_transactions_csv", fake_export)

    response = exports_api.export_financial_transactions(
        type=FinancialTransactionType.expense,
        status=FinancialTransactionStatus.pending,
        category_id=category_id,
        contact_id=uuid4(),
        employee_id=uuid4(),
        source="manual",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 31),
        search="aluguel",
        current_user=user,
        db=FakeDb([]),
    )

    assert response.body.startswith(b"\xef\xbb\xbf")
    assert captured["user"] == user
    assert captured["transaction_type"] == FinancialTransactionType.expense
    assert captured["status"] == FinancialTransactionStatus.pending
    assert captured["category_id"] == category_id
    assert captured["contact_id"] is not None
    assert captured["employee_id"] is not None
    assert captured["source"] == "manual"
    assert captured["start_date"] == date(2026, 5, 1)
    assert captured["end_date"] == date(2026, 5, 31)
    assert captured["search"] == "aluguel"
