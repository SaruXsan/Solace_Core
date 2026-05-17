"""Phase 2A: security and directory completion fields.

Revision ID: 004_phase2a_security_directory
Revises: 003_foundation_completion
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_phase2a_security_directory"
down_revision: Union[str, None] = "003_foundation_completion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "Core_Users",
        sa.Column("mfa_disabled_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "Core_Users",
        sa.Column("mfa_disable_reason", sa.String(512), nullable=True),
    )
    op.add_column(
        "Auth_DirectorySettings",
        sa.Column("overwrite_local_on_sync", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("Auth_DirectorySettings", "overwrite_local_on_sync")
    op.drop_column("Core_Users", "mfa_disable_reason")
    op.drop_column("Core_Users", "mfa_disabled_until")
