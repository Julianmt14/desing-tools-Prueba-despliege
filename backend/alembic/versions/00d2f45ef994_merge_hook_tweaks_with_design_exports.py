"""merge hook tweaks with design exports"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "00d2f45ef994"
down_revision = ("0013", "0014")

branch_labels = None
depends_on = None


def upgrade() -> None:
    """Metadata-only merge; no schema changes."""
    pass


def downgrade() -> None:
    """Merge-only downgrade."""
    pass
