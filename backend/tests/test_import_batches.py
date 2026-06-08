from datetime import UTC
from datetime import datetime
from decimal import Decimal
import io
import os
import zipfile
from uuid import uuid4

import pytest

TEST_DATABASE_URL = "postgresql+psycopg://" + "test" + ":" + "test" + "@localhost:5432/test"

os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("JWT_SECRET_KEY", "x" * 32)

from app.api import import_batches as import_batches_api
from app.models.company import Company
from app.models.company import SubscriptionStatus
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.import_batch import ImportBatch
from app.models.import_batch import ImportBatchFileType
from app.models.import_batch import ImportBatchStatus
from app.models.user import User
from app.models.user import UserRole
from app.schemas.import_batch import ImportColumnMapping
from app.services.import_batch import _parse_file
from app.services.import_batch import build_import_template_csv
from app.services.import_batch import confirm_import_batch
from app.services.import_batch import create_import_batch
from app.services.import_batch import ImportBatchValidationError
from app.services.import_batch import MAX_XLSX_UNCOMPRESSED_BYTES


class FakeDb:
    def __init__(self, scalar_values: list[object] | None = None) -> None:
        self.scalar_values = scalar_values or []
        self.added = []
        self.added_all = []
        self.commits = 0

    def add(self, instance):
        self.added.append(instance)

    def add_all(self, instances):
        self.added_all.extend(instances)

    def commit(self):
        self.commits += 1

    def refresh(self, instance):
        pass

    def scalar(self, statement):
        del statement
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None


def make_company() -> Company:
    return Company(
        id=uuid4(),
        name="Empresa Teste",
        subscription_status=SubscriptionStatus.active,
        trial_ends_at=datetime.now(UTC),
        subscription_valid_until=datetime.now(UTC),
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


def make_xlsx_bytes() -> bytes:
    output = io.BytesIO()
    sheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>Data</t></is></c>
      <c r="B1" t="inlineStr"><is><t>Descricao</t></is></c>
      <c r="C1" t="inlineStr"><is><t>Tipo</t></is></c>
      <c r="D1" t="inlineStr"><is><t>Valor</t></is></c>
    </row>
    <row r="2">
      <c r="A2"><v>46157</v></c>
      <c r="B2" t="inlineStr"><is><t>Venda de servico</t></is></c>
      <c r="C2" t="inlineStr"><is><t>entrada</t></is></c>
      <c r="D2"><v>1500.25</v></c>
    </row>
  </sheetData>
</worksheet>"""
    with zipfile.ZipFile(output, "w") as workbook:
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return output.getvalue()


def test_template_csv_uses_bom_semicolon_and_example_rows() -> None:
    content = build_import_template_csv()
    text = content.decode("utf-8")

    assert text.startswith("\ufeff")
    assert "Data;Descricao;Tipo;Valor;Vencimento;Observacoes" in text
    assert "15/05/2026;Venda de servico;entrada;1500,00;15/05/2026;Exemplo de receita" in text


def test_template_endpoint_returns_downloadable_csv() -> None:
    response = import_batches_api.download_import_template_csv(current_user=make_user(make_company()))

    assert response.body.startswith(b"\xef\xbb\xbf")
    assert response.headers["Content-Disposition"] == 'attachment; filename="modelo-importacao-lancamentos.csv"'


def test_create_import_batch_reads_csv_preview_without_confirming_transactions() -> None:
    company = make_company()
    user = make_user(company)
    db = FakeDb()
    content = b"Data;Descricao;Tipo;Valor\r\n15/05/2026;Venda de servico;entrada;1500,00\r\n"

    batch = create_import_batch(db, user, "lancamentos.csv", content)

    assert batch.company_id == user.company_id
    assert batch.status == ImportBatchStatus.uploaded
    assert batch.headers == ["Data", "Descricao", "Tipo", "Valor"]
    assert batch.preview_rows == [{"Data": "15/05/2026", "Descricao": "Venda de servico", "Tipo": "entrada", "Valor": "1500,00"}]
    assert db.added_all == []


def test_xlsx_parser_reads_first_sheet_rows() -> None:
    headers, rows = _parse_file(make_xlsx_bytes(), ImportBatchFileType.xlsx)

    assert headers == ["Data", "Descricao", "Tipo", "Valor"]
    assert rows[0]["Descricao"] == "Venda de servico"
    assert rows[0]["Valor"] == "1500.25"


def test_xlsx_parser_rejects_large_uncompressed_archive() -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("xl/worksheets/sheet1.xml", "x" * (MAX_XLSX_UNCOMPRESSED_BYTES + 1))

    with pytest.raises(ImportBatchValidationError):
        _parse_file(output.getvalue(), ImportBatchFileType.xlsx)


def test_confirm_import_allows_duplicate_warnings_and_preserves_company_id() -> None:
    company = make_company()
    user = make_user(company)
    db = FakeDb()
    batch = ImportBatch(
        id=uuid4(),
        company_id=user.company_id,
        filename="lancamentos.csv",
        file_type=ImportBatchFileType.csv,
        status=ImportBatchStatus.validated,
        headers=["Data", "Descricao", "Tipo", "Valor"],
        preview_rows=[],
        raw_rows=[
            {"Data": "15/05/2026", "Descricao": "Venda de servico", "Tipo": "entrada", "Valor": "1500,00"},
            {"Data": "15/05/2026", "Descricao": "Venda de servico", "Tipo": "entrada", "Valor": "1500,00"},
        ],
        mapping=ImportColumnMapping(
            date_column="Data",
            description_column="Descricao",
            type_column="Tipo",
            amount_column="Valor",
        ).model_dump(),
        validation_errors=[],
        duplicate_warnings=[],
        created_by=user.id,
    )

    confirmed_batch, created_ids = confirm_import_batch(db, user, batch)

    assert confirmed_batch.status == ImportBatchStatus.confirmed
    assert len(created_ids) == 2
    assert len(confirmed_batch.duplicate_warnings) == 2
    assert all(transaction.company_id == user.company_id for transaction in db.added_all)
    assert all(transaction.source == "import" for transaction in db.added_all)
    assert db.added_all[0].amount == Decimal("1500.00")
    assert db.added_all[0].type == FinancialTransactionType.income
    assert db.added_all[0].status == FinancialTransactionStatus.pending
