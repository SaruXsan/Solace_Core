"""LDAP / LDAPS directory integration tables."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuthDirectorySetting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Auth_DirectorySettings"

    directory_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    directory_type: Mapped[str] = mapped_column(String(32), default="LDAP")
    host: Mapped[str | None] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=389)
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)
    use_starttls: Mapped[bool] = mapped_column(Boolean, default=False)
    bind_dn: Mapped[str | None] = mapped_column(String(512))
    bind_username: Mapped[str | None] = mapped_column(String(255))
    encrypted_bind_password: Mapped[str | None] = mapped_column(Text)
    password_key_id: Mapped[str] = mapped_column(String(16), default="v1")
    base_dn: Mapped[str | None] = mapped_column(String(512))
    user_search_filter: Mapped[str] = mapped_column(
        String(512), default="(sAMAccountName={username})"
    )
    group_search_filter: Mapped[str | None] = mapped_column(String(512))
    email_attribute: Mapped[str] = mapped_column(String(64), default="mail")
    display_name_attribute: Mapped[str] = mapped_column(String(64), default="displayName")
    department_attribute: Mapped[str] = mapped_column(String(64), default="department")
    role_group_mapping_json: Mapped[str | None] = mapped_column(Text)
    certificate_validation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_certificate_thumbprints: Mapped[str | None] = mapped_column(Text)
    ca_chain_reference: Mapped[str | None] = mapped_column(Text)
    connection_timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[str | None] = mapped_column(String(64))
    plain_ldap_warning_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    overwrite_local_on_sync: Mapped[bool] = mapped_column(Boolean, default=False)
    default_sync_country_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    default_sync_organization_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    default_sync_branch_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    default_sync_department_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)


class AuthGroupRoleMapping(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Auth_GroupRoleMappings"

    directory_group_dn: Mapped[str] = mapped_column(String(512), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
