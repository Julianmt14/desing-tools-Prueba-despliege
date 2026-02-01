"""add beam_total_length_m column

Revision ID: 0010
Revises: 0009
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("despiece_vigas", sa.Column("beam_total_length_m", sa.Float(), nullable=True))
    op.execute("UPDATE despiece_vigas SET beam_total_length_m = 0 WHERE beam_total_length_m IS NULL")
    op.alter_column("despiece_vigas", "beam_total_length_m", nullable=False)


def downgrade() -> None:
    op.drop_column("despiece_vigas", "beam_total_length_m")
