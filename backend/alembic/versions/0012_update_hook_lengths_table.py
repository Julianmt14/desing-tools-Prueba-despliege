"""update hook lengths table to NSR-10 C.7.1 values

Revision ID: 0012
Revises: 0011
Create Date: 2026-02-01
"""

from __future__ import annotations

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


hook_lengths_table = sa.table(
    "hook_lengths",
    sa.column("bar_mark", sa.String(length=10)),
    sa.column("longitudinal_90_m", sa.Numeric(5, 3)),
    sa.column("longitudinal_180_m", sa.Numeric(5, 3)),
    sa.column("stirrup_135_m", sa.Numeric(5, 3)),
)


def _decimal(value: str | float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


NEW_VALUES = [
    {"bar_mark": "#2", "longitudinal_90_m": _decimal("0.10"), "longitudinal_180_m": _decimal("0.080"), "stirrup_135_m": _decimal("0.075")},
    {"bar_mark": "#3", "longitudinal_90_m": _decimal("0.15"), "longitudinal_180_m": _decimal("0.130"), "stirrup_135_m": _decimal("0.095")},
    {"bar_mark": "#4", "longitudinal_90_m": _decimal("0.20"), "longitudinal_180_m": _decimal("0.150"), "stirrup_135_m": _decimal("0.127")},
    {"bar_mark": "#5", "longitudinal_90_m": _decimal("0.25"), "longitudinal_180_m": _decimal("0.180"), "stirrup_135_m": _decimal("0.159")},
    {"bar_mark": "#6", "longitudinal_90_m": _decimal("0.30"), "longitudinal_180_m": _decimal("0.210"), "stirrup_135_m": _decimal("0.191")},
    {"bar_mark": "#7", "longitudinal_90_m": _decimal("0.36"), "longitudinal_180_m": _decimal("0.250"), "stirrup_135_m": _decimal("0.222")},
    {"bar_mark": "#8", "longitudinal_90_m": _decimal("0.41"), "longitudinal_180_m": _decimal("0.300"), "stirrup_135_m": _decimal("0.254")},
    {"bar_mark": "#9", "longitudinal_90_m": _decimal("0.49"), "longitudinal_180_m": _decimal("0.340"), "stirrup_135_m": None},
    {"bar_mark": "#10", "longitudinal_90_m": _decimal("0.54"), "longitudinal_180_m": _decimal("0.400"), "stirrup_135_m": None},
    {"bar_mark": "#11", "longitudinal_90_m": _decimal("0.59"), "longitudinal_180_m": _decimal("0.430"), "stirrup_135_m": None},
    {"bar_mark": "#14", "longitudinal_90_m": _decimal("0.80"), "longitudinal_180_m": _decimal("0.445"), "stirrup_135_m": None},
    {"bar_mark": "#18", "longitudinal_90_m": _decimal("1.03"), "longitudinal_180_m": _decimal("0.572"), "stirrup_135_m": None},
]

OLD_VALUES = [
    {"bar_mark": "#2", "longitudinal_90_m": _decimal("0.10"), "longitudinal_180_m": _decimal("0.065"), "stirrup_135_m": _decimal("0.075")},
    {"bar_mark": "#3", "longitudinal_90_m": _decimal("0.15"), "longitudinal_180_m": _decimal("0.076"), "stirrup_135_m": _decimal("0.095")},
    {"bar_mark": "#4", "longitudinal_90_m": _decimal("0.20"), "longitudinal_180_m": _decimal("0.102"), "stirrup_135_m": _decimal("0.127")},
    {"bar_mark": "#5", "longitudinal_90_m": _decimal("0.25"), "longitudinal_180_m": _decimal("0.127"), "stirrup_135_m": _decimal("0.159")},
    {"bar_mark": "#6", "longitudinal_90_m": _decimal("0.30"), "longitudinal_180_m": _decimal("0.152"), "stirrup_135_m": _decimal("0.191")},
    {"bar_mark": "#7", "longitudinal_90_m": _decimal("0.36"), "longitudinal_180_m": _decimal("0.178"), "stirrup_135_m": _decimal("0.222")},
    {"bar_mark": "#8", "longitudinal_90_m": _decimal("0.41"), "longitudinal_180_m": _decimal("0.203"), "stirrup_135_m": _decimal("0.254")},
    {"bar_mark": "#9", "longitudinal_90_m": _decimal("0.46"), "longitudinal_180_m": _decimal("0.229"), "stirrup_135_m": _decimal("0.286")},
    {"bar_mark": "#10", "longitudinal_90_m": _decimal("0.51"), "longitudinal_180_m": _decimal("0.254"), "stirrup_135_m": _decimal("0.318")},
    {"bar_mark": "#11", "longitudinal_90_m": _decimal("0.59"), "longitudinal_180_m": _decimal("0.314"), "stirrup_135_m": None},
    {"bar_mark": "#14", "longitudinal_90_m": _decimal("0.80"), "longitudinal_180_m": _decimal("0.445"), "stirrup_135_m": None},
    {"bar_mark": "#18", "longitudinal_90_m": _decimal("1.03"), "longitudinal_180_m": _decimal("0.572"), "stirrup_135_m": None},
]


def _apply(values: list[dict[str, Decimal | None]]) -> None:
    for row in values:
        stmt = (
            hook_lengths_table.update()
            .where(hook_lengths_table.c.bar_mark == row["bar_mark"])
            .values(
                longitudinal_90_m=row["longitudinal_90_m"],
                longitudinal_180_m=row["longitudinal_180_m"],
                stirrup_135_m=row["stirrup_135_m"],
            )
        )
        op.execute(stmt)


def upgrade() -> None:
    _apply(NEW_VALUES)


def downgrade() -> None:
    _apply(OLD_VALUES)
