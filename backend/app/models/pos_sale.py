import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime
from sqlalchemy import CheckConstraint
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.financial_transaction import FinancialTransactionPaymentMethod


class POSSale(Base):
    __tablename__ = "pos_sales"
    __table_args__ = (
        CheckConstraint("total > 0", name="ck_pos_sales_total_positive"),
        CheckConstraint("subtotal > 0", name="ck_pos_sales_subtotal_positive"),
        CheckConstraint("discount_amount >= 0", name="ck_pos_sales_discount_nonnegative"),
        CheckConstraint("total = subtotal - discount_amount", name="ck_pos_sales_total_matches_discount"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    financial_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financial_transactions.id"), nullable=False, unique=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True, index=True
    )
    quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_quotes.id"), nullable=True, unique=True
    )
    payment_method: Mapped[FinancialTransactionPaymentMethod] = mapped_column(
        ENUM(FinancialTransactionPaymentMethod, name="financial_transaction_payment_method", create_type=False),
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    discount_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    company = relationship("Company")
    transaction = relationship("FinancialTransaction")
    contact = relationship("Contact")
    quote = relationship("POSQuote", back_populates="sale")
    creator = relationship("User")
    items = relationship("POSSaleItem", back_populates="sale", cascade="all, delete-orphan")


class POSSaleItem(Base):
    __tablename__ = "pos_sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pos_sale_items_quantity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_products.id"), nullable=False, index=True
    )
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    sale = relationship("POSSale", back_populates="items")
    product = relationship("InventoryProduct")


class POSQuoteStatus(str, enum.Enum):
    open = "open"
    converted = "converted"


class POSQuote(Base):
    __tablename__ = "pos_quotes"
    __table_args__ = (
        CheckConstraint("total > 0", name="ck_pos_quotes_total_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[POSQuoteStatus] = mapped_column(
        Enum(POSQuoteStatus, name="pos_quote_status"), nullable=False, default=POSQuoteStatus.open
    )
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company")
    contact = relationship("Contact")
    creator = relationship("User")
    sale = relationship("POSSale", back_populates="quote", uselist=False)
    items = relationship("POSQuoteItem", back_populates="quote", cascade="all, delete-orphan")


class POSQuoteItem(Base):
    __tablename__ = "pos_quote_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_pos_quote_items_quantity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_quotes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_products.id"), nullable=False, index=True
    )
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    quote = relationship("POSQuote", back_populates="items")
    product = relationship("InventoryProduct")

    @property
    def stock_quantity(self) -> Decimal:
        return self.product.stock_quantity
