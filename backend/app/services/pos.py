import uuid
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.contact import Contact
from app.models.financial_transaction import FinancialTransaction
from app.models.financial_transaction import FinancialTransactionStatus
from app.models.financial_transaction import FinancialTransactionType
from app.models.inventory_product import InventoryMovement
from app.models.inventory_product import InventoryMovementType
from app.models.inventory_product import InventoryProduct
from app.models.pos_sale import POSSale
from app.models.pos_sale import POSSaleItem
from app.models.pos_sale import POSQuote
from app.models.pos_sale import POSQuoteItem
from app.models.pos_sale import POSQuoteStatus
from app.models.usage_event import UsageEventType
from app.models.user import User
from app.schemas.pos import POSCartItem
from app.schemas.pos import POSCheckoutRequest
from app.schemas.pos import POSPricingResponse
from app.schemas.pos import POSQuoteCreateRequest
from app.schemas.pos import POSQuoteLine
from app.services.usage_event import record_usage_event

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_TRANSACTION_AMOUNT = Decimal("999999999999.99")
POS_PRODUCT_SEARCH_LIMIT = 20


class POSValidationError(ValueError):
    pass


def list_pos_products(db: Session, user: User, search: str | None = None) -> list[InventoryProduct]:
    search_text = (search or "").strip()
    if not search_text:
        return []

    term = f"%{search_text}%"
    exact = case(
        (InventoryProduct.barcode == search_text, 0),
        (InventoryProduct.sku == search_text.upper(), 1),
        (func.lower(InventoryProduct.name) == search_text.lower(), 2),
        else_=3,
    )
    query = (
        select(InventoryProduct)
        .where(
            InventoryProduct.company_id == user.company_id,
            InventoryProduct.is_active.is_(True),
            or_(
                InventoryProduct.name.ilike(term),
                InventoryProduct.sku.ilike(term),
                InventoryProduct.barcode.ilike(term),
            ),
        )
        .order_by(exact, InventoryProduct.name.asc())
        .limit(POS_PRODUCT_SEARCH_LIMIT)
    )
    return list(db.scalars(query))


def quote_pos_sale(
    db: Session,
    user: User,
    items: list[POSCartItem],
    *,
    discount_type: str = "none",
    discount_value: Decimal = ZERO,
    quote_id: UUID | None = None,
) -> POSPricingResponse:
    if quote_id is not None:
        saved_quote = _get_open_quote(db, user, quote_id, lock=False)
        if saved_quote is None:
            raise POSValidationError("Esse orçamento não está disponível para conversão.")
        _, lines = _load_quote_products(db, user, items, saved_quote, lock=False)
    else:
        _, lines = _load_cart_products(db, user, items, lock=False)

    subtotal = sum((line.line_total for line in lines), start=ZERO)
    normalized_discount_value = ZERO if discount_type == "none" else discount_value
    discount_amount, total = _apply_discount(subtotal, discount_type, normalized_discount_value)
    return POSPricingResponse(
        items=lines,
        subtotal=subtotal,
        discount_type=discount_type,
        discount_value=normalized_discount_value,
        discount_amount=discount_amount,
        total=total,
    )


def create_pos_quote(db: Session, user: User, quote_in: POSQuoteCreateRequest) -> POSQuote:
    try:
        customer_name = quote_in.customer_name.strip()
        if not customer_name:
            raise POSValidationError("Informe o nome da pessoa ou empresa para o orçamento.")
        _validate_contact(db, user, quote_in.contact_id)
        _, lines = _load_cart_products(db, user, quote_in.items, lock=False, check_stock=False)
        total = sum((line.line_total for line in lines), start=ZERO)
        if total <= ZERO:
            raise POSValidationError("O valor do orçamento precisa ser maior que R$ 0,00.")
        if total > MAX_TRANSACTION_AMOUNT:
            raise POSValidationError("O valor do orçamento excede o limite permitido.")

        quote = POSQuote(
            id=uuid.uuid4(),
            company_id=user.company_id,
            contact_id=quote_in.contact_id,
            customer_name=customer_name,
            status=POSQuoteStatus.open,
            total=total,
            notes=_strip_optional_text(quote_in.notes),
            created_by=user.id,
            items=[],
        )
        for line in lines:
            quote.items.append(
                POSQuoteItem(
                    id=uuid.uuid4(),
                    product_id=line.product_id,
                    product_name=line.product_name,
                    sku=line.sku,
                    barcode=line.barcode,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_price=line.unit_price,
                    line_total=line.line_total,
                )
            )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        return quote
    except Exception:
        db.rollback()
        raise


def list_pos_quotes(db: Session, user: User) -> list[POSQuote]:
    query = (
        select(POSQuote)
        .where(POSQuote.company_id == user.company_id)
        .options(selectinload(POSQuote.items).selectinload(POSQuoteItem.product))
        .order_by(POSQuote.created_at.desc())
        .limit(50)
    )
    return list(db.scalars(query))


def checkout_pos_sale(db: Session, user: User, sale_in: POSCheckoutRequest) -> POSSale:
    try:
        _validate_contact(db, user, sale_in.contact_id)
        saved_quote: POSQuote | None = None
        if sale_in.quote_id is not None:
            saved_quote = _get_open_quote(db, user, sale_in.quote_id, lock=True)
            if saved_quote is None:
                raise POSValidationError("Esse orçamento já foi convertido ou não pertence a esta empresa.")
            products, lines = _load_quote_products(db, user, sale_in.items, saved_quote, lock=True)
        else:
            products, lines = _load_cart_products(db, user, sale_in.items, lock=True)

        subtotal = sum((line.line_total for line in lines), start=ZERO)
        normalized_discount_value = ZERO if sale_in.discount_type == "none" else sale_in.discount_value
        discount_amount, total = _apply_discount(subtotal, sale_in.discount_type, normalized_discount_value)
        if total > MAX_TRANSACTION_AMOUNT:
            raise POSValidationError("O valor da venda excede o limite permitido.")

        now = datetime.now(UTC)
        transaction_id = uuid.uuid4()
        sale_id = uuid.uuid4()
        transaction = FinancialTransaction(
            id=transaction_id,
            company_id=user.company_id,
            contact_id=sale_in.contact_id,
            description=f"Venda no PDV ({sale_id.hex[:8].upper()})",
            amount=total,
            type=FinancialTransactionType.income,
            status=FinancialTransactionStatus.settled,
            payment_method=sale_in.payment_method,
            competence_date=date.today(),
            settled_at=now,
            notes=_strip_optional_text(sale_in.notes),
            source="pos",
            created_by=user.id,
            updated_by=user.id,
        )
        sale = POSSale(
            id=sale_id,
            company_id=user.company_id,
            financial_transaction_id=transaction_id,
            contact_id=sale_in.contact_id,
            quote_id=saved_quote.id if saved_quote else None,
            payment_method=sale_in.payment_method,
            subtotal=subtotal,
            discount_type=sale_in.discount_type,
            discount_value=normalized_discount_value,
            discount_amount=discount_amount,
            total=total,
            notes=_strip_optional_text(sale_in.notes),
            sold_at=now,
            created_by=user.id,
            items=[],
        )
        db.add(transaction)
        db.add(sale)

        requested = _quantities_by_product(sale_in.items)
        products_by_id = {product.id: product for product in products}
        for product_id, quantity in requested.items():
            product = products_by_id[product_id]
            product.stock_quantity -= quantity
            product.updated_by = user.id
            db.add(product)
            db.add(
                InventoryMovement(
                    id=uuid.uuid4(),
                    company_id=user.company_id,
                    product_id=product.id,
                    sale_id=sale_id,
                    movement_type=InventoryMovementType.sale,
                    quantity_change=-quantity,
                    stock_after=product.stock_quantity,
                    notes="Baixa por venda no PDV",
                    created_by=user.id,
                )
            )
        for line in lines:
            sale.items.append(
                POSSaleItem(
                    id=uuid.uuid4(),
                    product_id=line.product_id,
                    product_name=line.product_name,
                    sku=line.sku,
                    barcode=line.barcode,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_price=line.unit_price,
                    line_total=line.line_total,
                )
            )
        if saved_quote is not None:
            saved_quote.status = POSQuoteStatus.converted
            db.add(saved_quote)

        record_usage_event(
            db,
            company_id=user.company_id,
            user_id=user.id,
            event_type=UsageEventType.financial_entry_created,
            metadata={"source": "pos", "sale_id": str(sale_id)},
        )
        db.commit()
        db.refresh(sale)
        return sale
    except Exception:
        db.rollback()
        raise


def list_pos_sales(db: Session, user: User) -> list[POSSale]:
    query = (
        select(POSSale)
        .where(POSSale.company_id == user.company_id)
        .options(selectinload(POSSale.items))
        .order_by(POSSale.sold_at.desc())
        .limit(50)
    )
    return list(db.scalars(query))


def _load_cart_products(
    db: Session,
    user: User,
    items: list[POSCartItem],
    *,
    lock: bool,
    check_stock: bool = True,
) -> tuple[list[InventoryProduct], list[POSQuoteLine]]:
    quantities = _quantities_by_product(items)
    if not quantities:
        raise POSValidationError("Adicione ao menos um produto para continuar.")

    query = select(InventoryProduct).where(
        InventoryProduct.company_id == user.company_id,
        InventoryProduct.id.in_(quantities),
        InventoryProduct.is_active.is_(True),
    ).order_by(InventoryProduct.id.asc())
    if lock:
        query = query.with_for_update()
    products = list(db.scalars(query))
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(quantities):
        raise POSValidationError("Um ou mais produtos não estão disponíveis para venda.")

    lines: list[POSQuoteLine] = []
    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        if check_stock and product.stock_quantity < quantity:
            raise POSValidationError(
                f"Estoque insuficiente para {product.name}. Disponível: "
                f"{product.stock_quantity} {product.unit}."
            )
        line_total = (product.sale_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)
        if line_total <= ZERO:
            raise POSValidationError(
                f"A quantidade informada para {product.name} gera um valor menor que R$ 0,01."
            )
        lines.append(
            POSQuoteLine(
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                barcode=product.barcode,
                quantity=quantity,
                unit=product.unit,
                unit_price=product.sale_price,
                line_total=line_total,
                stock_quantity=product.stock_quantity,
            )
        )
    return products, lines


def _load_quote_products(
    db: Session,
    user: User,
    items: list[POSCartItem],
    saved_quote: POSQuote,
    *,
    lock: bool,
) -> tuple[list[InventoryProduct], list[POSQuoteLine]]:
    requested = _quantities_by_product(items)
    quoted = {item.product_id: item.quantity for item in saved_quote.items}
    if not requested or requested != quoted:
        raise POSValidationError("Os itens do carrinho não correspondem ao orçamento selecionado.")

    query = select(InventoryProduct).where(
        InventoryProduct.company_id == user.company_id,
        InventoryProduct.id.in_(quoted),
        InventoryProduct.is_active.is_(True),
    ).order_by(InventoryProduct.id.asc())
    if lock:
        query = query.with_for_update()
    products = list(db.scalars(query))
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(quoted):
        raise POSValidationError("Um ou mais produtos do orçamento não estão mais disponíveis.")

    quote_items = {item.product_id: item for item in saved_quote.items}
    lines: list[POSQuoteLine] = []
    for product_id, quantity in requested.items():
        product = products_by_id[product_id]
        if product.stock_quantity < quantity:
            raise POSValidationError(
                f"Estoque insuficiente para {product.name}. Disponível: "
                f"{product.stock_quantity} {product.unit}."
            )
        item = quote_items[product_id]
        lines.append(
            POSQuoteLine(
                product_id=product_id,
                product_name=item.product_name,
                sku=item.sku,
                barcode=item.barcode,
                quantity=quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                line_total=item.line_total,
                stock_quantity=product.stock_quantity,
            )
        )
    return products, lines


def _quantities_by_product(items: list[POSCartItem]) -> dict[UUID, Decimal]:
    quantities: dict[UUID, Decimal] = {}
    for item in items:
        quantities[item.product_id] = quantities.get(item.product_id, Decimal("0.000")) + item.quantity
    return quantities


def _apply_discount(subtotal: Decimal, discount_type: str, discount_value: Decimal) -> tuple[Decimal, Decimal]:
    if subtotal <= ZERO:
        raise POSValidationError("O valor total precisa ser maior que R$ 0,00.")
    if discount_type == "none":
        discount_amount = ZERO
    elif discount_type == "percentage":
        if discount_value < ZERO or discount_value >= Decimal("100.00"):
            raise POSValidationError("O desconto percentual deve ser maior ou igual a 0% e menor que 100%.")
        discount_amount = (subtotal * discount_value / Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP)
    elif discount_type == "amount":
        discount_amount = discount_value.quantize(CENT, rounding=ROUND_HALF_UP)
    else:
        raise POSValidationError("Tipo de desconto inválido.")

    total = subtotal - discount_amount
    if discount_amount < ZERO or total <= ZERO:
        raise POSValidationError("O desconto precisa ser menor que o subtotal da venda.")
    return discount_amount, total.quantize(CENT, rounding=ROUND_HALF_UP)


def _get_open_quote(db: Session, user: User, quote_id: UUID, *, lock: bool) -> POSQuote | None:
    query = (
        select(POSQuote)
        .where(
            POSQuote.id == quote_id,
            POSQuote.company_id == user.company_id,
            POSQuote.status == POSQuoteStatus.open,
        )
        .options(selectinload(POSQuote.items))
    )
    if lock:
        query = query.with_for_update()
    return db.scalar(query)


def _validate_contact(db: Session, user: User, contact_id: UUID | None) -> None:
    if contact_id is None:
        return
    contact = db.scalar(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.company_id == user.company_id,
            Contact.is_active.is_(True),
        )
    )
    if contact is None:
        raise POSValidationError("Contraparte não encontrada para a empresa autenticada.")


def _strip_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
