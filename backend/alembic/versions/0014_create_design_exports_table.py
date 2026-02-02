"""create design exports table

Revision ID: 0014
Revises: cb78413cf513
Create Date: 2026-02-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014"
down_revision = "cb78413cf513"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "design_exports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("design_id", sa.Integer(), sa.ForeignKey("designs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template", sa.String(length=100), nullable=False),
        sa.Column("format", sa.String(length=10), nullable=False),
        sa.Column("scale", sa.Float(), nullable=False, server_default="50"),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="es-CO"),
        sa.Column("include_preview", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("preview_path", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ux_design_exports_job_id", "design_exports", ["job_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_design_exports_job_id", table_name="design_exports")
    op.drop_table("design_exports")
