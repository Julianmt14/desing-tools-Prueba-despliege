"""create hook_lengths table

Revision ID: 0008
Revises: 0007
Create Date: 2026-01-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hook_lengths",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bar_mark", sa.String(length=10), nullable=False),
        sa.Column("longitudinal_90_m", sa.Numeric(5, 3), nullable=False),
        sa.Column("longitudinal_180_m", sa.Numeric(5, 3), nullable=False),
        sa.Column("stirrup_135_m", sa.Numeric(5, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bar_mark", name="uq_hook_lengths_bar_mark"),
    )
    op.create_index(op.f("ix_hook_lengths_id"), "hook_lengths", ["id"], unique=False)

    hook_lengths_table = sa.table(
        "hook_lengths",
        sa.column("bar_mark", sa.String(length=10)),
        sa.column("longitudinal_90_m", sa.Numeric(5, 3)),
        sa.column("longitudinal_180_m", sa.Numeric(5, 3)),
        sa.column("stirrup_135_m", sa.Numeric(5, 3)),
    )

    hook_data = [
        {"bar_mark": "#2", "longitudinal_90_m": 0.10, "longitudinal_180_m": 0.065, "stirrup_135_m": 0.075},
        {"bar_mark": "#3", "longitudinal_90_m": 0.15, "longitudinal_180_m": 0.076, "stirrup_135_m": 0.095},
        {"bar_mark": "#4", "longitudinal_90_m": 0.20, "longitudinal_180_m": 0.102, "stirrup_135_m": 0.127},
        {"bar_mark": "#5", "longitudinal_90_m": 0.25, "longitudinal_180_m": 0.127, "stirrup_135_m": 0.159},
        {"bar_mark": "#6", "longitudinal_90_m": 0.30, "longitudinal_180_m": 0.152, "stirrup_135_m": 0.191},
        {"bar_mark": "#7", "longitudinal_90_m": 0.36, "longitudinal_180_m": 0.178, "stirrup_135_m": 0.222},
        {"bar_mark": "#8", "longitudinal_90_m": 0.41, "longitudinal_180_m": 0.203, "stirrup_135_m": 0.254},
        {"bar_mark": "#9", "longitudinal_90_m": 0.46, "longitudinal_180_m": 0.229, "stirrup_135_m": 0.286},
        {"bar_mark": "#10", "longitudinal_90_m": 0.51, "longitudinal_180_m": 0.254, "stirrup_135_m": 0.318},
        {"bar_mark": "#11", "longitudinal_90_m": 0.59, "longitudinal_180_m": 0.314, "stirrup_135_m": None},
        {"bar_mark": "#14", "longitudinal_90_m": 0.80, "longitudinal_180_m": 0.445, "stirrup_135_m": None},
        {"bar_mark": "#18", "longitudinal_90_m": 1.03, "longitudinal_180_m": 0.572, "stirrup_135_m": None},
    ]

    op.bulk_insert(hook_lengths_table, hook_data)


def downgrade() -> None:
    op.drop_index(op.f("ix_hook_lengths_id"), table_name="hook_lengths")
    op.drop_table("hook_lengths")
