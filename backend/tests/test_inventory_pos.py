from datetime import UTC
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.inventory_product import InventoryMovement
from app.models.inventory_product import InventoryMovementType
from app.models.inventory_product import InventoryProduct
from app.models.pos_sale import POSQuoteStatus
from app.models.user import User
from app.models.user import UserRole
from app.schemas.inventory import InventoryStockAdjustment
from app.schemas.pos import POSCartItem
from app.schemas.pos import POSCheckoutRequest
from app.schemas.pos import POSQuoteCreateRequest
from app.services.financial_transaction import FinancialTransactionValidationError
from app.services.financial_transaction import soft_delete_financial_transaction
from app.services.inventory import set_product_stock
from app.services.company_deletion import purge_due_company_deletions
from app.services.pos import POSValidationError
from app.services.pos import checkout_pos_sale
from app.services.pos import create_pos_quote
from app.services.pos import list_pos_products
from app.services.pos import quote_pos_sale

_UNSET = object()


class FakeDb:
    def __init__(self, products: list[InventoryProduct], scalar_result=_UNSET) -> None:
        self.products = products
        self.scalar_result = scalar_result
        self.added = []
        self.queries = []
        self.commits = 0
        self.rollbacks = 0

    def scalars(self, query):
        self.queries.append(query)
        return self.products

    def scalar(self, query):
        self.queries.append(query)
        if self.scalar_result is not _UNSET:
            return self.scalar_result
        return self.products[0] if self.products else None

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, _item):
        pass


class FakePurgeDb:
    def __init__(self, company_id) -> None:
        self.company_id = company_id
        self.statements = []
        self.commits = 0

    class Rows:
        def __init__(self, company_id) -> None:
            self.company_id = company_id

        def all(self):
            return [self.company_id]

    def scalars(self, _query):
        return self.Rows(self.company_id)

    def execute(self, statement):
        self.statements.append(statement)

    def commit(self):
        self.commits += 1


def make_user() -> User:
    return User(
        id=uuid4(),
        company_id=uuid4(),
        name="Caixa Teste",
        email=f"{uuid4()}@example.com",
        password_hash="hash",
        role=UserRole.company_admin,
        is_active=True,
        email_verified_at=datetime.now(UTC),
    )


def make_product(user: User, *, stock: str = "3.000", price: str = "12.50") -> InventoryProduct:
    return InventoryProduct(
        id=uuid4(),
        company_id=user.company_id,
        name="Café",
        sku="CAF-01",
        barcode="7891234567890",
        sale_price=Decimal(price),
        stock_quantity=Decimal(stock),
        unit="un",
        is_active=True,
        created_by=user.id,
        updated_by=user.id,
    )


def test_quote_uses_database_price_and_decimal_rounding() -> None:
    user = make_user()
    product = make_product(user, stock="2.000", price="10.00")
    db = FakeDb([product])

    quote = quote_pos_sale(db, user, [POSCartItem(product_id=product.id, quantity=Decimal("1.235"))])

    assert quote.total == Decimal("12.35")
    assert quote.items[0].unit_price == Decimal("10.00")
    assert "inventory_products.company_id" in str(db.queries[0])


def test_pos_search_is_empty_without_term_and_matches_barcode() -> None:
    user = make_user()
    product = make_product(user)
    db = FakeDb([product])

    assert list_pos_products(db, user) == []
    assert db.queries == []
    assert list_pos_products(db, user, "7891234567890") == [product]
    query_text = str(db.queries[0])
    assert "inventory_products.barcode" in query_text
    assert "inventory_products.company_id" in query_text
    assert "LIMIT" in query_text


def test_pos_discount_uses_decimal_and_rejects_total_discount() -> None:
    user = make_user()
    product = make_product(user, stock="2.000", price="10.00")
    db = FakeDb([product])
    items = [POSCartItem(product_id=product.id, quantity=Decimal("1.000"))]

    percent = quote_pos_sale(db, user, items, discount_type="percentage", discount_value=Decimal("12.50"))
    assert percent.subtotal == Decimal("10.00")
    assert percent.discount_amount == Decimal("1.25")
    assert percent.total == Decimal("8.75")

    amount = quote_pos_sale(db, user, items, discount_type="amount", discount_value=Decimal("2.35"))
    assert amount.discount_amount == Decimal("2.35")
    assert amount.total == Decimal("7.65")

    with pytest.raises(POSValidationError, match="menor que o subtotal"):
        quote_pos_sale(db, user, items, discount_type="amount", discount_value=Decimal("10.00"))


def test_saving_quote_does_not_reserve_or_decrement_stock() -> None:
    user = make_user()
    product = make_product(user, stock="3.000", price="12.50")
    db = FakeDb([product])

    quote = create_pos_quote(
        db,
        user,
        POSQuoteCreateRequest(
            customer_name="Cliente de teste",
            items=[POSCartItem(product_id=product.id, quantity=Decimal("2.000"))],
        ),
    )

    assert quote.customer_name == "Cliente de teste"
    assert quote.total == Decimal("25.00")
    assert quote.items[0].unit_price == Decimal("12.50")
    assert quote.status.value == "open"
    assert product.stock_quantity == Decimal("3.000")
    assert not any(isinstance(item, InventoryMovement) for item in db.added)


def test_quote_conversion_keeps_saved_price_checks_stock_and_marks_quote_converted() -> None:
    user = make_user()
    product = make_product(user, stock="3.000", price="12.50")
    db = FakeDb([product])
    quote = create_pos_quote(
        db,
        user,
        POSQuoteCreateRequest(
            customer_name="Cliente de teste",
            items=[POSCartItem(product_id=product.id, quantity=Decimal("2.000"))],
        ),
    )
    product.sale_price = Decimal("15.00")
    db.scalar_result = quote
    sale = checkout_pos_sale(
        db,
        user,
        POSCheckoutRequest(
            items=[POSCartItem(product_id=product.id, quantity=Decimal("2.000"))],
            payment_method="pix",
            discount_type="percentage",
            discount_value=Decimal("10.00"),
            quote_id=quote.id,
        ),
    )

    assert quote.status == POSQuoteStatus.converted
    assert sale.quote_id == quote.id
    assert sale.subtotal == Decimal("25.00")
    assert sale.discount_amount == Decimal("2.50")
    assert sale.total == Decimal("22.50")
    assert product.stock_quantity == Decimal("1.000")
    transaction = next(item for item in db.added if getattr(item, "source", None) == "pos")
    assert transaction.amount == Decimal("22.50")


def test_pos_rejects_quantity_greater_than_stock_without_mutation() -> None:
    user = make_user()
    product = make_product(user, stock="1.000")
    db = FakeDb([product])
    sale_in = POSCheckoutRequest(
        items=[POSCartItem(product_id=product.id, quantity=Decimal("1.001"))],
        payment_method="pix",
    )

    with pytest.raises(POSValidationError, match="Estoque insuficiente"):
        checkout_pos_sale(db, user, sale_in)

    assert product.stock_quantity == Decimal("1.000")
    assert db.commits == 0
    assert db.rollbacks == 1
    assert "FOR UPDATE" in str(db.queries[0])


def test_pos_checkout_decrements_stock_and_creates_financial_sale_atomically() -> None:
    user = make_user()
    product = make_product(user, stock="3.000", price="12.50")
    db = FakeDb([product])
    sale_in = POSCheckoutRequest(
        items=[POSCartItem(product_id=product.id, quantity=Decimal("2.000"))],
        payment_method="cash",
    )

    sale = checkout_pos_sale(db, user, sale_in)

    assert product.stock_quantity == Decimal("1.000")
    assert sale.total == Decimal("25.00")
    assert sale.items[0].line_total == Decimal("25.00")
    assert db.commits == 1
    assert len([item for item in db.added if isinstance(item, InventoryMovement)]) == 1
    movement = next(item for item in db.added if isinstance(item, InventoryMovement))
    assert movement.movement_type == InventoryMovementType.sale
    assert movement.quantity_change == Decimal("-2.000")
    assert movement.stock_after == Decimal("1.000")


def test_manual_stock_adjustment_records_signed_movement_and_company_scope() -> None:
    user = make_user()
    product = make_product(user, stock="3.000")
    db = FakeDb([product])

    updated = set_product_stock(
        db,
        user,
        product.id,
        adjustment=InventoryStockAdjustment(
            quantity=Decimal("5.000"), notes="Reposição"
        ),
    )

    movement = next(item for item in db.added if isinstance(item, InventoryMovement))
    assert updated.stock_quantity == Decimal("5.000")
    assert movement.quantity_change == Decimal("2.000")
    assert "inventory_products.company_id" in str(db.queries[0])
    assert db.commits == 1


def test_pos_financial_entry_cannot_be_soft_deleted_outside_pos() -> None:
    user = make_user()
    from app.models.financial_transaction import FinancialTransaction
    from app.models.financial_transaction import FinancialTransactionStatus
    from app.models.financial_transaction import FinancialTransactionType

    transaction = FinancialTransaction(
        id=uuid4(),
        company_id=user.company_id,
        description="Venda PDV",
        amount=Decimal("10.00"),
        type=FinancialTransactionType.income,
        status=FinancialTransactionStatus.settled,
        competence_date=datetime.now(UTC).date(),
        source="pos",
        created_by=user.id,
        updated_by=user.id,
    )

    with pytest.raises(FinancialTransactionValidationError, match="módulo PDV"):
        soft_delete_financial_transaction(FakeDb([]), user, transaction)


def test_company_retention_purge_removes_pos_and_inventory_before_company() -> None:
    company_id = uuid4()
    db = FakePurgeDb(company_id)

    assert purge_due_company_deletions(db) == 1

    sql = [str(statement) for statement in db.statements]
    tables_in_order = [
        next(name for name in (
            "inventory_movements",
            "pos_sale_items",
            "pos_sales",
            "pos_quote_items",
            "pos_quotes",
            "financial_transactions",
            "inventory_products",
            "companies",
        ) if f"DELETE FROM {name}" in statement)
        for statement in sql
        if "DELETE FROM" in statement
        and any(
            f"DELETE FROM {name}" in statement
            for name in (
                "inventory_movements",
                "pos_sale_items",
                "pos_sales",
                "pos_quote_items",
                "pos_quotes",
                "financial_transactions",
                "inventory_products",
                "companies",
            )
        )
    ]
    assert tables_in_order == [
        "inventory_movements",
        "pos_sale_items",
        "pos_sales",
        "pos_quote_items",
        "pos_quotes",
        "financial_transactions",
        "inventory_products",
        "companies",
    ]
    assert db.commits == 1
