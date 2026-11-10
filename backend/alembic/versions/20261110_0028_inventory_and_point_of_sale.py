"""add company inventory and integrated point of sale

Revision ID: 20261110_0028
Revises: 20261106_0027
Create Date: 2026-11-10 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261110_0028"
down_revision: str | None = "20261106_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    movement_type = postgresql.ENUM(
        "inbound", "sale", "adjustment", name="inventory_movement_type", create_type=False
    )
    movement_type.create(op.get_bind(), checkfirst=True)

    payment_method = postgresql.ENUM(
        "credit",
        "debit",
        "pix",
        "boleto",
        "bank_transfer",
        "cash",
        name="financial_transaction_payment_method",
        create_type=False,
    )

    op.create_table(
        "inventory_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=True),
        sa.Column("sale_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("stock_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("sale_price > 0", name="ck_inventory_products_sale_price_positive"),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_inventory_products_stock_nonnegative"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "sku", name="uq_inventory_products_company_sku"),
    )
    op.create_index(op.f("ix_inventory_products_company_id"), "inventory_products", ["company_id"])

    op.create_table(
        "pos_sales",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("financial_transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_method", payment_method, nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("total > 0", name="ck_pos_sales_total_positive"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["financial_transaction_id"], ["financial_transactions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("financial_transaction_id"),
    )
    op.create_index(op.f("ix_pos_sales_company_id"), "pos_sales", ["company_id"])
    op.create_index(op.f("ix_pos_sales_contact_id"), "pos_sales", ["contact_id"])

    op.create_table(
        "pos_sale_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_pos_sale_items_quantity_positive"),
        sa.ForeignKeyConstraint(["product_id"], ["inventory_products.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["pos_sales.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pos_sale_items_product_id"), "pos_sale_items", ["product_id"])
    op.create_index(op.f("ix_pos_sale_items_sale_id"), "pos_sale_items", ["sale_id"])

    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("movement_type", movement_type, nullable=False),
        sa.Column("quantity_change", sa.Numeric(14, 3), nullable=False),
        sa.Column("stock_after", sa.Numeric(14, 3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity_change != 0", name="ck_inventory_movements_nonzero_change"),
        sa.CheckConstraint("stock_after >= 0", name="ck_inventory_movements_stock_nonnegative"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["inventory_products.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["pos_sales.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_movements_company_id"), "inventory_movements", ["company_id"])
    op.create_index(op.f("ix_inventory_movements_product_id"), "inventory_movements", ["product_id"])
    op.create_index(op.f("ix_inventory_movements_sale_id"), "inventory_movements", ["sale_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_movements_sale_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_product_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_company_id"), table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index(op.f("ix_pos_sale_items_sale_id"), table_name="pos_sale_items")
    op.drop_index(op.f("ix_pos_sale_items_product_id"), table_name="pos_sale_items")
    op.drop_table("pos_sale_items")
    op.drop_index(op.f("ix_pos_sales_contact_id"), table_name="pos_sales")
    op.drop_index(op.f("ix_pos_sales_company_id"), table_name="pos_sales")
    op.drop_table("pos_sales")
    op.drop_index(op.f("ix_inventory_products_company_id"), table_name="inventory_products")
    op.drop_table("inventory_products")
    postgresql.ENUM(name="inventory_movement_type").drop(op.get_bind(), checkfirst=True)
