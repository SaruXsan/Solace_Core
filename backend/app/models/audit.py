"""Audit and system logging tables."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditTrail(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_Trail"
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(64))
    detail_json: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))


class AuditLoginEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_LoginEvents"
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(String(128))
    auth_source: Mapped[str] = mapped_column(String(16))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_required: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_success: Mapped[bool | None] = mapped_column(nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))


class AuditMFAEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_MFAEvents"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(64))
    challenge_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))


class AuditDataAccess(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_DataAccess"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(32))


class AuditAdminAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_AdminActions"
    admin_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(128))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(128))
    detail_json: Mapped[str | None] = mapped_column(Text)


class AuditConfigChange(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_ConfigChanges"
    changed_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    setting_key: Mapped[str] = mapped_column(String(128))
    change_summary: Mapped[str] = mapped_column(String(512))


class AuditPermissionChange(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_PermissionChanges"
    changed_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    target_role_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    permission_code: Mapped[str] = mapped_column(String(128))
    granted: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLLMCall(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_LLMCalls"
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    module_code: Mapped[str | None] = mapped_column(String(64))
    purpose: Mapped[str | None] = mapped_column(String(255))
    classification: Mapped[str | None] = mapped_column(String(32))
    external_provider_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_token_estimate: Mapped[int | None] = mapped_column(Integer)


class AuditPostureViolation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Audit_PostureViolations"
    violation_type: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str | None] = mapped_column(Text)
    trend_direction: Mapped[str | None] = mapped_column(String(16))


class SystemErrorLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "System_ErrorLog"
    source: Mapped[str] = mapped_column(String(128))
    message: Mapped[str] = mapped_column(Text)
    correlation_id: Mapped[str | None] = mapped_column(String(64))


class SystemJobHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "System_JobHistory"
    job_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    detail_json: Mapped[str | None] = mapped_column(Text)


class SystemSecurityAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "System_SecurityAlerts"
    alert_type: Mapped[str] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(Text)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
