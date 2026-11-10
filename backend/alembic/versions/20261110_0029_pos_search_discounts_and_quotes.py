"""add barcode search, POS discounts, and saved quotes

Revision ID: 20261110_0029
Revises: 20261110_0028
Create Date: 2026-11-10 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261110_0029"
down_revision: str | None = "20261110_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    quote_status = postgresql.ENUM("open", "converted", name="pos_quote_status", create_type=False)
    quote_status.create(op.get_bind(), checkfirst=True)

    op.add_column("inventory_products", sa.Column("barcode", sa.String(length=80), nullable=True))
    op.create_unique_constraint(
        "uq_inventory_products_company_barcode", "inventory_products", ["company_id", "barcode"]
    )

    op.add_column("pos_sale_items", sa.Column("barcode", sa.String(length=80), nullable=True))

    op.add_column("pos_sales", sa.Column("subtotal", sa.Numeric(14, 2), nullable=True))
    op.add_column(
        "pos_sales",
        sa.Column("discount_type", sa.String(length=20), server_default="none", nullable=False),
    )
    op.add_column(
        "pos_sales",
        sa.Column("discount_value", sa.Numeric(14, 2), server_default="0.00", nullable=False),
    )
    op.add_column(
        "pos_sales",
        sa.Column("discount_amount", sa.Numeric(14, 2), server_default="0.00", nullable=False),
    )
    op.execute("UPDATE pos_sales SET subtotal = total WHERE subtotal IS NULL")
    op.alter_column("pos_sales", "subtotal", nullable=False)
    op.alter_column("pos_sales", "discount_type", server_default=None)
    op.alter_column("pos_sales", "discount_value", server_default=None)
    op.alter_column("pos_sales", "discount_amount", server_default=None)
    op.create_check_constraint("ck_pos_sales_subtotal_positive", "pos_sales", "subtotal > 0")
    op.create_check_constraint("ck_pos_sales_discount_nonnegative", "pos_sales", "discount_amount >= 0")
    op.create_check_constraint(
        "ck_pos_sales_total_matches_discount", "pos_sales", "total = subtotal - discount_amount"
    )

    op.create_table(
        "pos_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("status", quote_status, nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("total > 0", name="ck_pos_quotes_total_positive"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pos_quotes_company_id"), "pos_quotes", ["company_id"])
    op.create_index(op.f("ix_pos_quotes_contact_id"), "pos_quotes", ["contact_id"])

    op.create_table(
        "pos_quote_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=True),
        sa.Column("barcode", sa.String(length=80), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_pos_quote_items_quantity_positive"),
        sa.ForeignKeyConstraint(["product_id"], ["inventory_products.id"]),
        sa.ForeignKeyConstraint(["quote_id"], ["pos_quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pos_quote_items_product_id"), "pos_quote_items", ["product_id"])
    op.create_index(op.f("ix_pos_quote_items_quote_id"), "pos_quote_items", ["quote_id"])

    op.add_column("pos_sales", sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_unique_constraint("uq_pos_sales_quote_id", "pos_sales", ["quote_id"])
    op.create_foreign_key("fk_pos_sales_quote_id_pos_quotes", "pos_sales", "pos_quotes", ["quote_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_pos_sales_quote_id_pos_quotes", "pos_sales", type_="foreignkey")
    op.drop_constraint("uq_pos_sales_quote_id", "pos_sales", type_="unique")
    op.drop_column("pos_sales", "quote_id")

    op.drop_index(op.f("ix_pos_quote_items_quote_id"), table_name="pos_quote_items")
    op.drop_index(op.f("ix_pos_quote_items_product_id"), table_name="pos_quote_items")
    op.drop_table("pos_quote_items")
    op.drop_index(op.f("ix_pos_quotes_contact_id"), table_name="pos_quotes")
    op.drop_index(op.f("ix_pos_quotes_company_id"), table_name="pos_quotes")
    op.drop_table("pos_quotes")
    postgresql.ENUM(name="pos_quote_status").drop(op.get_bind(), checkfirst=True)

    op.drop_constraint("ck_pos_sales_total_matches_discount", "pos_sales", type_="check")
    op.drop_constraint("ck_pos_sales_discount_nonnegative", "pos_sales", type_="check")
    op.drop_constraint("ck_pos_sales_subtotal_positive", "pos_sales", type_="check")
    op.drop_column("pos_sales", "discount_amount")
    op.drop_column("pos_sales", "discount_value")
    op.drop_column("pos_sales", "discount_type")
    op.drop_column("pos_sales", "subtotal")
    op.drop_column("pos_sale_items", "barcode")
    op.drop_constraint("uq_inventory_products_company_barcode", "inventory_products", type_="unique")
    op.drop_column("inventory_products", "barcode")
