"""add segment reinforcements column

Revision ID: 0011
Revises: 0010
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("despiece_vigas", sa.Column("segment_reinforcements", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("despiece_vigas", "segment_reinforcements")
