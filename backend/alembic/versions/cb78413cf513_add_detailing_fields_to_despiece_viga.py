"""add detailing fields to despiece viga

Revision ID: 0012
Revises: 0011
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "despiece_vigas",
        sa.Column("detailing_computed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("despiece_vigas", sa.Column("detailing_results", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("detailing_warnings", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("bar_detailing", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("prohibited_zones", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("material_list", sa.JSON(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("total_bars_count", sa.Integer(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("total_rebar_weight_kg", sa.Float(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("waste_percentage", sa.Float(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("optimization_score", sa.Float(), nullable=True))
    op.add_column("despiece_vigas", sa.Column("detailing_version", sa.String(length=20), nullable=True))
    op.add_column("despiece_vigas", sa.Column("detailing_computed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("despiece_vigas", "detailing_computed_at")
    op.drop_column("despiece_vigas", "detailing_version")
    op.drop_column("despiece_vigas", "optimization_score")
    op.drop_column("despiece_vigas", "waste_percentage")
    op.drop_column("despiece_vigas", "total_rebar_weight_kg")
    op.drop_column("despiece_vigas", "total_bars_count")
    op.drop_column("despiece_vigas", "material_list")
    op.drop_column("despiece_vigas", "prohibited_zones")
    op.drop_column("despiece_vigas", "bar_detailing")
    op.drop_column("despiece_vigas", "detailing_warnings")
    op.drop_column("despiece_vigas", "detailing_results")
    op.drop_column("despiece_vigas", "detailing_computed")
