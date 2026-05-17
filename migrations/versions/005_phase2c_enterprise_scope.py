"""Phase 2C: enterprise scope and isolation model.

Revision ID: 005_phase2c_enterprise_scope
Revises: 004_phase2a_security_directory
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_phase2c_enterprise_scope"
down_revision: Union[str, None] = "004_phase2a_security_directory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "Core_Countries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("default_language", sa.String(16), server_default="en", nullable=False),
        sa.Column("supported_languages", sa.Text(), nullable=True),
        sa.Column("currency_code", sa.String(8), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("date_format", sa.String(32), nullable=True),
        sa.Column("rtl_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("legal_system_notes", sa.Text(), nullable=True),
        sa.Column("court_structure_notes", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.add_column("Core_Organizations", sa.Column("country_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Organizations", sa.Column("legal_name", sa.String(512), nullable=True))
    op.add_column("Core_Organizations", sa.Column("commercial_name", sa.String(255), nullable=True))
    op.add_column("Core_Organizations", sa.Column("company_code", sa.String(64), nullable=True))
    op.add_column("Core_Organizations", sa.Column("registration_number", sa.String(128), nullable=True))
    op.add_column("Core_Organizations", sa.Column("tax_number", sa.String(128), nullable=True))
    op.add_column("Core_Organizations", sa.Column("default_currency", sa.String(8), nullable=True))
    op.add_column("Core_Organizations", sa.Column("default_language", sa.String(16), nullable=True))
    op.add_column("Core_Organizations", sa.Column("timezone", sa.String(64), nullable=True))
    op.create_foreign_key(
        "FK_Core_Organizations_country",
        "Core_Organizations",
        "Core_Countries",
        ["country_id"],
        ["id"],
    )

    op.add_column("Core_Branches", sa.Column("country_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Branches", sa.Column("branch_code", sa.String(64), nullable=True))
    op.add_column("Core_Branches", sa.Column("branch_type", sa.String(64), nullable=True))
    op.add_column("Core_Branches", sa.Column("address", sa.String(512), nullable=True))
    op.add_column("Core_Branches", sa.Column("city", sa.String(128), nullable=True))
    op.add_column("Core_Branches", sa.Column("region", sa.String(128), nullable=True))
    op.add_column("Core_Branches", sa.Column("timezone", sa.String(64), nullable=True))
    op.add_column("Core_Branches", sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False))
    op.create_foreign_key(
        "FK_Core_Branches_country",
        "Core_Branches",
        "Core_Countries",
        ["country_id"],
        ["id"],
    )

    op.add_column("Core_Departments", sa.Column("parent_department_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Departments", sa.Column("manager_user_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Departments", sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False))
    op.create_foreign_key(
        "FK_Core_Departments_parent",
        "Core_Departments",
        "Core_Departments",
        ["parent_department_id"],
        ["id"],
    )
    op.create_foreign_key(
        "FK_Core_Departments_manager",
        "Core_Departments",
        "Core_Users",
        ["manager_user_id"],
        ["id"],
    )

    op.add_column("Core_Users", sa.Column("default_country_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Users", sa.Column("default_organization_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Users", sa.Column("default_branch_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Users", sa.Column("default_department_id", sa.Uuid(), nullable=True))

    op.create_table(
        "Core_UserScopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("country_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("department_id", sa.Uuid(), nullable=True),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["Core_Users.id"]),
        sa.ForeignKeyConstraint(["country_id"], ["Core_Countries.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["Core_Organizations.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["Core_Branches.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["Core_Departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("IX_Core_UserScopes_user", "Core_UserScopes", ["user_id"])

    op.add_column("Core_UserRoles", sa.Column("scope_type", sa.String(32), server_default="global", nullable=False))
    op.add_column("Core_UserRoles", sa.Column("country_id", sa.Uuid(), nullable=True))
    op.add_column("Core_UserRoles", sa.Column("organization_id", sa.Uuid(), nullable=True))
    op.add_column("Core_UserRoles", sa.Column("branch_id", sa.Uuid(), nullable=True))
    op.add_column("Core_UserRoles", sa.Column("department_id", sa.Uuid(), nullable=True))

    op.add_column("Core_Sessions", sa.Column("active_country_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Sessions", sa.Column("active_branch_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Sessions", sa.Column("active_department_id", sa.Uuid(), nullable=True))
    op.add_column("Core_Sessions", sa.Column("active_scope_type", sa.String(32), server_default="organization", nullable=False))

    op.add_column("Auth_DirectorySettings", sa.Column("default_sync_country_id", sa.Uuid(), nullable=True))
    op.add_column("Auth_DirectorySettings", sa.Column("default_sync_organization_id", sa.Uuid(), nullable=True))
    op.add_column("Auth_DirectorySettings", sa.Column("default_sync_branch_id", sa.Uuid(), nullable=True))
    op.add_column("Auth_DirectorySettings", sa.Column("default_sync_department_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column("Auth_DirectorySettings", "default_sync_department_id")
    op.drop_column("Auth_DirectorySettings", "default_sync_branch_id")
    op.drop_column("Auth_DirectorySettings", "default_sync_organization_id")
    op.drop_column("Auth_DirectorySettings", "default_sync_country_id")
    op.drop_column("Core_Sessions", "active_scope_type")
    op.drop_column("Core_Sessions", "active_department_id")
    op.drop_column("Core_Sessions", "active_branch_id")
    op.drop_column("Core_Sessions", "active_country_id")
    op.drop_column("Core_UserRoles", "department_id")
    op.drop_column("Core_UserRoles", "branch_id")
    op.drop_column("Core_UserRoles", "organization_id")
    op.drop_column("Core_UserRoles", "country_id")
    op.drop_column("Core_UserRoles", "scope_type")
    op.drop_table("Core_UserScopes")
    op.drop_column("Core_Users", "default_department_id")
    op.drop_column("Core_Users", "default_branch_id")
    op.drop_column("Core_Users", "default_organization_id")
    op.drop_column("Core_Users", "default_country_id")
    op.drop_constraint("FK_Core_Departments_manager", "Core_Departments", type_="foreignkey")
    op.drop_constraint("FK_Core_Departments_parent", "Core_Departments", type_="foreignkey")
    op.drop_column("Core_Departments", "is_active")
    op.drop_column("Core_Departments", "manager_user_id")
    op.drop_column("Core_Departments", "parent_department_id")
    op.drop_constraint("FK_Core_Branches_country", "Core_Branches", type_="foreignkey")
    op.drop_column("Core_Branches", "is_active")
    op.drop_column("Core_Branches", "timezone")
    op.drop_column("Core_Branches", "region")
    op.drop_column("Core_Branches", "city")
    op.drop_column("Core_Branches", "address")
    op.drop_column("Core_Branches", "branch_type")
    op.drop_column("Core_Branches", "branch_code")
    op.drop_column("Core_Branches", "country_id")
    op.drop_constraint("FK_Core_Organizations_country", "Core_Organizations", type_="foreignkey")
    op.drop_column("Core_Organizations", "timezone")
    op.drop_column("Core_Organizations", "default_language")
    op.drop_column("Core_Organizations", "default_currency")
    op.drop_column("Core_Organizations", "tax_number")
    op.drop_column("Core_Organizations", "registration_number")
    op.drop_column("Core_Organizations", "company_code")
    op.drop_column("Core_Organizations", "commercial_name")
    op.drop_column("Core_Organizations", "legal_name")
    op.drop_column("Core_Organizations", "country_id")
    op.drop_table("Core_Countries")
