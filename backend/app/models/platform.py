"""Core platform tables — organizations, users, RBAC, modules."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    SoftDeleteMixin,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class CoreCountry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Country / jurisdiction — legal and regulatory context."""

    __tablename__ = "Core_Countries"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    default_language: Mapped[str] = mapped_column(String(16), default="en")
    supported_languages: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rtl_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    legal_system_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    court_structure_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)


class CoreOrganization(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Company / legal entity (table name retained: Core_Organizations)."""

    __tablename__ = "Core_Organizations"

    country_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Countries.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    commercial_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tax_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    default_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    default_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CoreBranch(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Branch / site — operational location."""

    __tablename__ = "Core_Branches"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=False, index=True
    )
    country_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Countries.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    branch_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    branch_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CoreDepartment(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Department / business unit."""

    __tablename__ = "Core_Departments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Branches.id"), nullable=True
    )
    parent_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Departments.id"), nullable=True
    )
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CoreUser(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "Core_Users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("Core_Branches.id"))
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Departments.id")
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_service_account: Mapped[bool] = mapped_column(Boolean, default=False)
    is_privileged_account: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    directory_source: Mapped[str] = mapped_column(String(16), default="local")
    directory_object_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_directory_user: Mapped[bool] = mapped_column(Boolean, default=False)
    last_directory_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mfa_disabled_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mfa_disable_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    default_country_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Countries.id"), nullable=True
    )
    default_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=True
    )
    default_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Branches.id"), nullable=True
    )
    default_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Departments.id"), nullable=True
    )


class CoreUserScope(Base, UUIDPrimaryKeyMixin, CreatedAtMixin):
    """Assignable enterprise scope for a user."""

    __tablename__ = "Core_UserScopes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Users.id"), nullable=False, index=True)
    country_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("Core_Countries.id"), nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("Core_Branches.id"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Departments.id"), nullable=True
    )
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)


class CoreUserProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_UserProfiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Users.id"), unique=True, nullable=False
    )
    job_title: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(64))
    locale: Mapped[str] = mapped_column(String(16), default="en-US")


class CoreRole(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "Core_Roles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    requires_mfa: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)


class CorePermission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_Permissions"

    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    module_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text)


class CoreUserRole(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_UserRoles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Roles.id"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), default="global", nullable=False)
    country_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("Core_Countries.id"), nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("Core_Branches.id"), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Departments.id"), nullable=True
    )


class CoreRolePermission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_RolePermissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id"),)

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Roles.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Permissions.id"), nullable=False
    )


class CoreUserPermission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_UserPermissions"
    __table_args__ = (UniqueConstraint("user_id", "permission_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Users.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Permissions.id"), nullable=False
    )
    granted: Mapped[bool] = mapped_column(Boolean, default=True)


class CoreSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_Sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Users.id"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Organizations.id"), nullable=False
    )
    active_country_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Countries.id"), nullable=True
    )
    active_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Branches.id"), nullable=True
    )
    active_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("Core_Departments.id"), nullable=True
    )
    active_scope_type: Mapped[str] = mapped_column(String(32), default="organization", nullable=False)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CoreLoginAttempt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_LoginAttempts"

    username: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_source: Mapped[str] = mapped_column(String(16), default="local")
    failure_reason: Mapped[str | None] = mapped_column(String(255))


class CoreSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_Settings"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="system")


class CoreEncryptedSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_EncryptedSettings"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    key_id: Mapped[str] = mapped_column(String(16), default="v1")
    category: Mapped[str] = mapped_column(String(64), default="secret")
    updated_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)


class CoreModule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_Modules"

    module_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="0.0.0-placeholder")
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=True)
    database_prefix: Mapped[str | None] = mapped_column(String(32))
    routes_json: Mapped[str | None] = mapped_column(Text)
    menu_items_json: Mapped[str | None] = mapped_column(Text)
    permissions_json: Mapped[str | None] = mapped_column(Text)


class CoreModuleSetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_ModuleSettings"

    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Modules.id"))
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class CoreNavigationItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_NavigationItems"

    section: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    module_code: Mapped[str | None] = mapped_column(String(64))


class CoreNotification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_Notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Core_Users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
