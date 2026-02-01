"""create development and lap splice length tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "development_lengths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bar_mark", sa.String(length=10), nullable=False),
        sa.Column("fc_21_mpa_m", sa.Numeric(5, 2), nullable=False),
        sa.Column("fc_24_mpa_m", sa.Numeric(5, 2), nullable=False),
        sa.Column("fc_28_mpa_m", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bar_mark", name="uq_development_lengths_bar_mark"),
    )
    op.create_index(op.f("ix_development_lengths_id"), "development_lengths", ["id"], unique=False)

    op.create_table(
        "lap_splice_lengths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bar_mark", sa.String(length=10), nullable=False),
        sa.Column("fc_21_mpa_m", sa.Numeric(5, 2), nullable=False),
        sa.Column("fc_24_mpa_m", sa.Numeric(5, 2), nullable=False),
        sa.Column("fc_28_mpa_m", sa.Numeric(5, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bar_mark", name="uq_lap_splice_lengths_bar_mark"),
    )
    op.create_index(op.f("ix_lap_splice_lengths_id"), "lap_splice_lengths", ["id"], unique=False)

    development_table = sa.table(
        "development_lengths",
        sa.column("bar_mark", sa.String(length=10)),
        sa.column("fc_21_mpa_m", sa.Numeric(5, 2)),
        sa.column("fc_24_mpa_m", sa.Numeric(5, 2)),
        sa.column("fc_28_mpa_m", sa.Numeric(5, 2)),
    )

    lap_splice_table = sa.table(
        "lap_splice_lengths",
        sa.column("bar_mark", sa.String(length=10)),
        sa.column("fc_21_mpa_m", sa.Numeric(5, 2)),
        sa.column("fc_24_mpa_m", sa.Numeric(5, 2)),
        sa.column("fc_28_mpa_m", sa.Numeric(5, 2)),
    )

    development_data = [
        {"bar_mark": "#3", "fc_21_mpa_m": 0.42, "fc_24_mpa_m": 0.39, "fc_28_mpa_m": 0.36},
        {"bar_mark": "#4", "fc_21_mpa_m": 0.55, "fc_24_mpa_m": 0.52, "fc_28_mpa_m": 0.48},
        {"bar_mark": "#5", "fc_21_mpa_m": 0.69, "fc_24_mpa_m": 0.65, "fc_28_mpa_m": 0.60},
        {"bar_mark": "#6", "fc_21_mpa_m": 0.83, "fc_24_mpa_m": 0.78, "fc_28_mpa_m": 0.72},
        {"bar_mark": "#7", "fc_21_mpa_m": 0.97, "fc_24_mpa_m": 0.91, "fc_28_mpa_m": 0.84},
        {"bar_mark": "#8", "fc_21_mpa_m": 1.37, "fc_24_mpa_m": 1.28, "fc_28_mpa_m": 1.19},
        {"bar_mark": "#9", "fc_21_mpa_m": 1.54, "fc_24_mpa_m": 1.44, "fc_28_mpa_m": 1.33},
        {"bar_mark": "#10", "fc_21_mpa_m": 1.71, "fc_24_mpa_m": 1.60, "fc_28_mpa_m": 1.48},
        {"bar_mark": "#11", "fc_21_mpa_m": 1.88, "fc_24_mpa_m": 1.76, "fc_28_mpa_m": 1.63},
        {"bar_mark": "#14", "fc_21_mpa_m": 2.24, "fc_24_mpa_m": 2.10, "fc_28_mpa_m": 1.95},
        {"bar_mark": "#18", "fc_21_mpa_m": 3.08, "fc_24_mpa_m": 2.88, "fc_28_mpa_m": 2.67},
    ]

    lap_splice_data = [
        {"bar_mark": "#3", "fc_21_mpa_m": 0.55, "fc_24_mpa_m": 0.50, "fc_28_mpa_m": 0.45},
        {"bar_mark": "#4", "fc_21_mpa_m": 0.70, "fc_24_mpa_m": 0.65, "fc_28_mpa_m": 0.60},
        {"bar_mark": "#5", "fc_21_mpa_m": 0.90, "fc_24_mpa_m": 0.85, "fc_28_mpa_m": 0.80},
        {"bar_mark": "#6", "fc_21_mpa_m": 1.10, "fc_24_mpa_m": 1.00, "fc_28_mpa_m": 0.95},
        {"bar_mark": "#7", "fc_21_mpa_m": 1.25, "fc_24_mpa_m": 1.20, "fc_28_mpa_m": 1.10},
        {"bar_mark": "#8", "fc_21_mpa_m": 1.80, "fc_24_mpa_m": 1.65, "fc_28_mpa_m": 1.55},
        {"bar_mark": "#9", "fc_21_mpa_m": 2.00, "fc_24_mpa_m": 1.85, "fc_28_mpa_m": 1.75},
        {"bar_mark": "#10", "fc_21_mpa_m": 2.25, "fc_24_mpa_m": 2.10, "fc_28_mpa_m": 1.95},
        {"bar_mark": "#11", "fc_21_mpa_m": 2.45, "fc_24_mpa_m": 2.30, "fc_28_mpa_m": 2.15},
        {"bar_mark": "#14", "fc_21_mpa_m": 3.10, "fc_24_mpa_m": 2.90, "fc_28_mpa_m": 2.70},
        {"bar_mark": "#18", "fc_21_mpa_m": 4.00, "fc_24_mpa_m": 3.75, "fc_28_mpa_m": 3.45},
    ]

    op.bulk_insert(development_table, development_data)
    op.bulk_insert(lap_splice_table, lap_splice_data)


def downgrade() -> None:
    op.drop_index(op.f("ix_lap_splice_lengths_id"), table_name="lap_splice_lengths")
    op.drop_table("lap_splice_lengths")
    op.drop_index(op.f("ix_development_lengths_id"), table_name="development_lengths")
    op.drop_table("development_lengths")
