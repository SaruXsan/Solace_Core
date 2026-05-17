"""Platform security settings table + base roles seed data.

Revision ID: 002_platform_settings
Revises: 001_foundation
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_platform_settings"
down_revision: Union[str, None] = "001_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Core_SecuritySettings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enable_mfa", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("require_mfa_for_admins", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("otp_expiry_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("otp_retry_limit", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("resend_cooldown_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("session_timeout_minutes", sa.Integer(), nullable=False, server_default="480"),
        sa.Column("login_max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("login_lockout_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("smtp_use_tls", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("smtp_username", sa.String(255), nullable=True),
        sa.Column("from_email", sa.String(320), nullable=True),
        sa.Column("app_display_name", sa.String(128), nullable=False, server_default="Solace Enterprise Core"),
        sa.Column("environment_label", sa.String(64), nullable=False, server_default="FOUNDATION"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("SYSDATETIMEOFFSET()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("SYSDATETIMEOFFSET()")),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("Core_SecuritySettings")
