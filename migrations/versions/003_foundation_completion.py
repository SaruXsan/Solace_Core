"""Foundation completion: encrypted settings updated_by, memory classification.

Revision ID: 003_foundation_completion
Revises: 002_platform_settings
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_foundation_completion"
down_revision: Union[str, None] = "002_platform_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Core_EncryptedSettings",
        sa.Column("updated_by", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "Solace_MemoryAtoms",
        sa.Column("data_classification", sa.String(32), nullable=True, server_default="INTERNAL"),
    )


def downgrade() -> None:
    op.drop_column("Solace_MemoryAtoms", "data_classification")
    op.drop_column("Core_EncryptedSettings", "updated_by")
