import csv
import io
import re
import uuid
import zipfile
from collections import Counter
from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from decimal import InvalidOperation
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.import_batch import ImportBatch
from app.models.import_batch import ImportBatchFileType
from app.models.import_batch import ImportBatchStatus
from app.models.user import User
from app.schemas.import_batch import ImportColumnMapping

MAX_IMPORT_FILE_SIZE_BYTES = 5 * 1024 * 1024
PREVIEW_ROW_LIMIT = 10


class ImportBatchValidationError(ValueError):
    pass


def create_import_batch(
    db: Session,
    user: User,
    filename: str,
    content: bytes,
) -> ImportBatch:
    if len(content) > MAX_IMPORT_FILE_SIZE_BYTES:
        raise ImportBatchValidationError("O arquivo excede o limite de 5 MB")

    file_type = _get_file_type(filename)
    headers, rows = _parse_file(content, file_type)
    if not headers:
        raise ImportBatchValidationError("O arquivo deve conter uma linha de cabeçalho")
    if not rows:
        raise ImportBatchValidationError("O arquivo deve conter ao menos uma linha de dados")

    batch = ImportBatch(
        company_id=user.company_id,
        filename=filename[:255],
        file_type=file_type,
        status=ImportBatchStatus.uploaded,
        headers=headers,
        preview_rows=rows[:PREVIEW_ROW_LIMIT],
        raw_rows=rows,
        validation_errors=[],
        duplicate_warnings=[],
        created_by=user.id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def get_import_batch(
    db: Session,
    user: User,
    batch_id: uuid.UUID,
) -> ImportBatch | None:
    return db.scalar(
        select(ImportBatch).where(
            ImportBatch.id == batch_id,
            ImportBatch.company_id == user.company_id,
        )
    )


def validate_import_batch(
    db: Session,
    user: User,
    batch: ImportBatch,
    mapping: ImportColumnMapping,
) -> ImportBatch:
    if batch.status == ImportBatchStatus.confirmed:
        raise ImportBatchValidationError("Lotes de importação confirmados não podem ser validados novamente")

    mapping_dict = mapping.model_dump()
    _validate_mapping_columns(batch.headers, mapping)
    validated_rows, errors, duplicate_warnings, summary = _validate_rows(
        db=db,
        user=user,
        rows=batch.raw_rows,
        mapping=mapping,
    )
    del validated_rows

    batch.mapping = mapping_dict
    batch.validation_errors = errors
    batch.duplicate_warnings = duplicate_warnings
    batch.summary = summary
    batch.status = ImportBatchStatus.validated if not errors else ImportBatchStatus.failed
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def confirm_import_batch(
    db: Session,
    user: User,
    batch: ImportBatch,
) -> tuple[ImportBatch, list[uuid.UUID]]:
    if batch.status == ImportBatchStatus.confirmed:
        raise ImportBatchValidationError("O lote de importação já foi confirmado")
    if not batch.mapping:
        raise ImportBatchValidationError("O lote de importação deve ser validado antes da confirmação")

    mapping = ImportColumnMapping(**batch.mapping)
    validated_rows, errors, duplicate_warnings, summary = _validate_rows(
        db=db,
        user=user,
        rows=batch.raw_rows,
        mapping=mapping,
    )
    if errors:
        batch.validation_errors = errors
        batch.duplicate_warnings = duplicate_warnings
        batch.summary = summary
        batch.status = ImportBatchStatus.failed
        db.add(batch)
        db.commit()
        raise ImportBatchValidationError("O lote de importação contém erros de validação")
    if duplicate_warnings:
        batch.validation_errors = []
        batch.duplicate_warnings = duplicate_warnings
        batch.summary = summary
        batch.status = ImportBatchStatus.validated
        db.add(batch)
        db.commit()
        raise ImportBatchValidationError("O lote de importação contém possíveis lançamentos duplicados")

    transactions = [
        FinancialTransaction(
            company_id=user.company_id,
            description=row["description"],
            amount=row["amount"],
            type=row["type"],
            status=FinancialTransactionStatus.pending,
            competence_date=row["competence_date"],
            due_date=row["due_date"],
            notes=row["notes"],
            source="import",
            import_batch_id=batch.id,
            created_by=user.id,
            updated_by=user.id,
        )
        for row in validated_rows
    ]
    db.add_all(transactions)
    batch.status = ImportBatchStatus.confirmed
    batch.validation_errors = []
    batch.duplicate_warnings = []
    batch.summary = summary
    batch.confirmed_by = user.id
    batch.confirmed_at = datetime.now(UTC)
    db.add(batch)
    db.commit()
    for transaction in transactions:
        db.refresh(transaction)
    db.refresh(batch)
    return batch, [transaction.id for transaction in transactions]


def _get_file_type(filename: str) -> ImportBatchFileType:
    lowered = filename.lower()
    if lowered.endswith(".csv"):
        return ImportBatchFileType.csv
    if lowered.endswith(".xlsx"):
        return ImportBatchFileType.xlsx
    raise ImportBatchValidationError("Somente arquivos .csv e .xlsx são aceitos")


def _parse_file(
    content: bytes,
    file_type: ImportBatchFileType,
) -> tuple[list[str], list[dict[str, str | None]]]:
    if file_type == ImportBatchFileType.csv:
        return _parse_csv(content)
    return _parse_xlsx(content)


def _parse_csv(content: bytes) -> tuple[list[str], list[dict[str, str | None]]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1252")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [_normalize_header(header) for header in (reader.fieldnames or [])]
    rows = [_normalize_row(headers, row) for row in reader]
    return headers, _drop_empty_rows(rows)


def _parse_xlsx(content: bytes) -> tuple[list[str], list[dict[str, str | None]]]:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as workbook:
            shared_strings = _read_shared_strings(workbook)
            sheet_xml = workbook.read("xl/worksheets/sheet1.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ImportBatchValidationError("Arquivo .xlsx inválido") from exc

    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(sheet_xml)
    parsed_rows: list[list[str | None]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values_by_index: dict[int, str | None] = {}
        for cell in row.findall("x:c", namespace):
            ref = cell.attrib.get("r", "")
            index = _column_ref_to_index(ref)
            values_by_index[index] = _read_xlsx_cell(cell, shared_strings, namespace)
        if values_by_index:
            max_index = max(values_by_index)
            parsed_rows.append([values_by_index.get(index) for index in range(max_index + 1)])

    if not parsed_rows:
        return [], []
    headers = [_normalize_header(value or "") for value in parsed_rows[0]]
    rows = [
        _normalize_row(headers, dict(zip(headers, data_row, strict=False)))
        for data_row in parsed_rows[1:]
    ]
    return headers, _drop_empty_rows(rows)


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    try:
        xml = workbook.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ElementTree.fromstring(xml)
    strings: list[str] = []
    for item in root.findall("x:si", namespace):
        texts = [text.text or "" for text in item.findall(".//x:t", namespace)]
        strings.append("".join(texts))
    return strings


def _read_xlsx_cell(
    cell: ElementTree.Element,
    shared_strings: list[str],
    namespace: dict[str, str],
) -> str | None:
    value_element = cell.find("x:v", namespace)
    if value_element is None or value_element.text is None:
        inline_text = cell.find(".//x:t", namespace)
        return inline_text.text if inline_text is not None else None
    value = value_element.text
    if cell.attrib.get("t") == "s":
        index = int(value)
        return shared_strings[index] if index < len(shared_strings) else None
    return value


def _column_ref_to_index(ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", ref.upper())
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - ord("A") + 1
    return max(index - 1, 0)


def _normalize_header(value: str) -> str:
    return str(value).strip()


def _normalize_row(
    headers: list[str],
    row: dict[str, object],
) -> dict[str, str | None]:
    normalized: dict[str, str | None] = {}
    for header in headers:
        value = row.get(header)
        if value is None:
            normalized[header] = None
            continue
        stripped = str(value).strip()
        normalized[header] = stripped or None
    return normalized


def _drop_empty_rows(rows: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    return [row for row in rows if any(value for value in row.values())]


def _validate_mapping_columns(headers: list[str], mapping: ImportColumnMapping) -> None:
    header_set = set(headers)
    selected_columns = [value for value in mapping.model_dump().values() if value is not None]
    missing = sorted(column for column in selected_columns if column not in header_set)
    if missing:
        raise ImportBatchValidationError(f"Colunas mapeadas não encontradas: {', '.join(missing)}")

    has_single_amount = mapping.amount_column is not None
    has_split_amount = mapping.income_amount_column is not None or mapping.expense_amount_column is not None
    if has_single_amount == has_split_amount:
        raise ImportBatchValidationError(
            "Use a coluna de valor único ou as colunas de entrada/saída, não ambas"
        )
    if has_split_amount and not (mapping.income_amount_column and mapping.expense_amount_column):
        raise ImportBatchValidationError(
            "As colunas de entrada e saída são obrigatórias na importação com valores separados"
        )
    if has_single_amount and mapping.type_column is None:
        raise ImportBatchValidationError(
            "A coluna de tipo é obrigatória quando a importação usa valor único"
        )


def _validate_rows(
    db: Session,
    user: User,
    rows: list[dict[str, str | None]],
    mapping: ImportColumnMapping,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    validated_rows: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []

    for index, row in enumerate(rows, start=2):
        parsed, row_errors = _validate_row(row, mapping, index)
        errors.extend(row_errors)
        if parsed is not None:
            validated_rows.append(parsed)

    duplicate_warnings = _find_duplicate_warnings(db, user, validated_rows)
    summary = _build_summary(rows, validated_rows, errors, duplicate_warnings, mapping)
    return validated_rows, errors, duplicate_warnings, summary


def _validate_row(
    row: dict[str, str | None],
    mapping: ImportColumnMapping,
    row_number: int,
) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    errors: list[dict[str, object]] = []
    competence_date = _parse_date(_get_cell(row, mapping.date_column))
    if competence_date is None:
        errors.append(_error(row_number, "date", "Data inválida ou ausente", _get_cell(row, mapping.date_column)))

    description = (_get_cell(row, mapping.description_column) or "").strip()
    if len(description) < 2:
        errors.append(_error(row_number, "description", "A descrição deve ter ao menos 2 caracteres", description))
    if len(description) > 255:
        errors.append(_error(row_number, "description", "A descrição deve ter no máximo 255 caracteres", description))

    transaction_type: FinancialTransactionType | None = None
    amount: Decimal | None = None
    if mapping.amount_column is not None:
        amount, amount_error = _parse_money(_get_cell(row, mapping.amount_column))
        if amount_error:
            errors.append(_error(row_number, "amount", amount_error, _get_cell(row, mapping.amount_column)))
        transaction_type = _parse_transaction_type(_get_cell(row, mapping.type_column))
        if transaction_type is None:
            errors.append(_error(row_number, "type", "Tipo de lançamento inválido ou ausente", _get_cell(row, mapping.type_column)))
    else:
        income_amount, income_error = _parse_optional_money(_get_cell(row, mapping.income_amount_column))
        expense_amount, expense_error = _parse_optional_money(_get_cell(row, mapping.expense_amount_column))
        if income_error:
            errors.append(_error(row_number, "income_amount", income_error, _get_cell(row, mapping.income_amount_column)))
        if expense_error:
            errors.append(_error(row_number, "expense_amount", expense_error, _get_cell(row, mapping.expense_amount_column)))
        if income_amount is not None and expense_amount is not None:
            errors.append(_error(row_number, "amount", "Use valor de entrada ou valor de saída, não ambos", None))
        elif income_amount is not None:
            amount = income_amount
            transaction_type = FinancialTransactionType.income
        elif expense_amount is not None:
            amount = expense_amount
            transaction_type = FinancialTransactionType.expense
        else:
            errors.append(_error(row_number, "amount", "Valor de entrada ou saída ausente", None))

    due_date = _parse_date(_get_cell(row, mapping.due_date_column)) if mapping.due_date_column else None
    notes = _get_cell(row, mapping.notes_column) if mapping.notes_column else None

    if errors:
        return None, errors
    return {
        "row_number": row_number,
        "competence_date": competence_date,
        "due_date": due_date,
        "description": description,
        "amount": amount,
        "type": transaction_type,
        "notes": notes,
    }, []


def _get_cell(row: dict[str, str | None], column: str | None) -> str | None:
    if column is None:
        return None
    return row.get(column)


def _parse_date(value: str | None) -> date | None:
    if value is None or not value.strip():
        return None
    stripped = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue
    if re.fullmatch(r"\d+(\.0+)?", stripped):
        serial = int(Decimal(stripped))
        if 1 <= serial <= 60000:
            return date(1899, 12, 30) + timedelta(days=serial)
    return None


def _parse_money(value: str | None) -> tuple[Decimal | None, str | None]:
    parsed, error = _parse_optional_money(value)
    if parsed is None and error is None:
        return None, "Valor ausente"
    return parsed, error


def _parse_optional_money(value: str | None) -> tuple[Decimal | None, str | None]:
    if value is None or not value.strip():
        return None, None
    normalized = _normalize_money(value)
    try:
        amount = Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None, "Valor inválido"
    if amount <= Decimal("0"):
        return None, "O valor deve ser maior que zero"
    if amount >= Decimal("1000000000000"):
        return None, "O valor excede o limite aceito"
    return amount, None


def _normalize_money(value: str) -> str:
    stripped = value.strip().replace("R$", "").replace("$", "").replace(" ", "")
    if stripped.startswith("(") and stripped.endswith(")"):
        stripped = f"-{stripped[1:-1]}"
    if "," in stripped and "." in stripped:
        if stripped.rfind(",") > stripped.rfind("."):
            stripped = stripped.replace(".", "").replace(",", ".")
        else:
            stripped = stripped.replace(",", "")
    elif "," in stripped:
        stripped = stripped.replace(".", "").replace(",", ".")
    return stripped


def _parse_transaction_type(value: str | None) -> FinancialTransactionType | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    income_values = {"income", "entrada", "receita", "recebimento", "credito", "crédito"}
    expense_values = {"expense", "saida", "saída", "despesa", "pagamento", "debito", "débito"}
    if normalized in income_values:
        return FinancialTransactionType.income
    if normalized in expense_values:
        return FinancialTransactionType.expense
    return None


def _find_duplicate_warnings(
    db: Session,
    user: User,
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    warnings: list[dict[str, object]] = []
    keys = [
        (
            row["competence_date"],
            row["description"].strip().lower(),
            row["amount"],
            row["type"],
        )
        for row in rows
    ]
    repeated_keys = {key for key, count in Counter(keys).items() if count > 1}
    for row, key in zip(rows, keys, strict=False):
        if key in repeated_keys:
            warnings.append(
                {
                    "row_number": row["row_number"],
                    "scope": "batch",
                    "message": "Possível linha duplicada neste lote de importação",
                }
            )

    for row in rows:
        exists = db.scalar(
            select(FinancialTransaction.id).where(
                FinancialTransaction.company_id == user.company_id,
                FinancialTransaction.competence_date == row["competence_date"],
                FinancialTransaction.description == row["description"],
                FinancialTransaction.amount == row["amount"],
                FinancialTransaction.type == row["type"],
                FinancialTransaction.status != FinancialTransactionStatus.canceled,
            )
        )
        if exists is not None:
            warnings.append(
                {
                    "row_number": row["row_number"],
                    "scope": "company",
                    "message": "Possível lançamento duplicado já existente para esta empresa",
                }
            )
    return warnings


def _build_summary(
    rows: list[dict[str, str | None]],
    validated_rows: list[dict[str, object]],
    errors: list[dict[str, object]],
    duplicate_warnings: list[dict[str, object]],
    mapping: ImportColumnMapping,
) -> dict[str, object]:
    income_total = sum(
        (row["amount"] for row in validated_rows if row["type"] == FinancialTransactionType.income),
        Decimal("0.00"),
    )
    expense_total = sum(
        (row["amount"] for row in validated_rows if row["type"] == FinancialTransactionType.expense),
        Decimal("0.00"),
    )
    error_row_numbers = {error["row_number"] for error in errors}
    return {
        "total_rows": len(rows),
        "valid_rows": len(validated_rows),
        "error_rows": len(error_row_numbers),
        "duplicate_warnings": len(duplicate_warnings),
        "income_count": sum(1 for row in validated_rows if row["type"] == FinancialTransactionType.income),
        "expense_count": sum(1 for row in validated_rows if row["type"] == FinancialTransactionType.expense),
        "income_total": str(income_total),
        "expense_total": str(expense_total),
        "import_mode": "single_amount_column" if mapping.amount_column else "split_income_expense_columns",
    }


def _error(row_number: int, field: str, message: str, value: str | None) -> dict[str, object]:
    return {
        "row_number": row_number,
        "field": field,
        "message": message,
        "value": value,
    }
