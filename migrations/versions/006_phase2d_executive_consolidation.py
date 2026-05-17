"""Phase 2D: executive consolidation foundation.

Revision ID: 006_phase2d_consolidation
Revises: 005_phase2c_enterprise_scope
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_phase2d_consolidation"
down_revision: Union[str, None] = "005_phase2c_enterprise_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Core_ConsolidationScopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("scope_level", sa.String(32), nullable=False),
        sa.Column("include_child_scopes", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("allowed_modules", sa.Text(), nullable=True),
        sa.Column("max_classification_allowed", sa.String(32), server_default="Internal", nullable=False),
        sa.Column("can_view_raw_restricted", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("can_use_ai_summary", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("can_export", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["Core_Users.id"]),
        sa.ForeignKeyConstraint(["country_id"], ["Core_Countries.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["Core_Organizations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["Core_Branches.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["Core_Departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("IX_Core_ConsolidationScopes_user", "Core_ConsolidationScopes", ["user_id"])

    op.add_column(
        "Core_Sessions",
        sa.Column("active_consolidation_scope_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "FK_Core_Sessions_active_consolidation_scope",
        "Core_Sessions",
        "Core_ConsolidationScopes",
        ["active_consolidation_scope_id"],
        ["id"],
    )

    op.add_column("Solace_MemoryAtoms", sa.Column("visibility_scope", sa.String(64), nullable=True))
    op.add_column("Solace_MemoryAtoms", sa.Column("source_scope", sa.String(64), nullable=True))
    op.add_column("Solace_MemoryAtoms", sa.Column("included_countries", sa.Text(), nullable=True))
    op.add_column("Solace_MemoryAtoms", sa.Column("included_organizations", sa.Text(), nullable=True))
    op.add_column("Solace_MemoryAtoms", sa.Column("classification_ceiling", sa.String(32), nullable=True))
    op.add_column("Solace_MemoryAtoms", sa.Column("audit_event_id", sa.Uuid(), nullable=True))
    op.add_column("Solace_MemoryAtoms", sa.Column("review_date", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("Solace_MemoryAtoms", "review_date")
    op.drop_column("Solace_MemoryAtoms", "audit_event_id")
    op.drop_column("Solace_MemoryAtoms", "classification_ceiling")
    op.drop_column("Solace_MemoryAtoms", "included_organizations")
    op.drop_column("Solace_MemoryAtoms", "included_countries")
    op.drop_column("Solace_MemoryAtoms", "source_scope")
    op.drop_column("Solace_MemoryAtoms", "visibility_scope")
    op.drop_constraint("FK_Core_Sessions_active_consolidation_scope", "Core_Sessions", type_="foreignkey")
    op.drop_column("Core_Sessions", "active_consolidation_scope_id")
    op.drop_table("Core_ConsolidationScopes")
