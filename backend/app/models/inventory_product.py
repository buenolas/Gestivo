import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.base import Base


class InventoryProduct(Base):
    __tablename__ = "inventory_products"
    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_inventory_products_company_sku"),
        UniqueConstraint("company_id", "barcode", name="uq_inventory_products_company_barcode"),
        CheckConstraint("sale_price > 0", name="ck_inventory_products_sale_price_positive"),
        CheckConstraint("stock_quantity >= 0", name="ck_inventory_products_stock_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    stock_quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3), nullable=False, default=Decimal("0.000")
    )
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="un")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])


class InventoryMovementType(str, enum.Enum):
    inbound = "inbound"
    sale = "sale"
    adjustment = "adjustment"


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint("quantity_change != 0", name="ck_inventory_movements_nonzero_change"),
        CheckConstraint("stock_after >= 0", name="ck_inventory_movements_stock_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inventory_products.id"), nullable=False, index=True
    )
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pos_sales.id"), nullable=True, index=True
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        Enum(InventoryMovementType, name="inventory_movement_type"), nullable=False
    )
    quantity_change: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    stock_after: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    company = relationship("Company")
    product = relationship("InventoryProduct")
    creator = relationship("User")

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def product_unit(self) -> str:
        return self.product.unit
