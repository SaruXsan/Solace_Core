"""Infrastructure and AppSec evidence skeleton tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InfraApplication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_Applications"
    name: Mapped[str] = mapped_column(String(255))
    owner: Mapped[str | None] = mapped_column(String(255))


class InfraEnvironment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_Environments"
    name: Mapped[str] = mapped_column(String(128))
    environment_type: Mapped[str] = mapped_column(String(32))


class InfraServer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_Servers"
    hostname: Mapped[str] = mapped_column(String(255))
    environment_id: Mapped[str | None] = mapped_column(String(64))


class InfraNetworkZone(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_NetworkZones"
    name: Mapped[str] = mapped_column(String(128))
    zone_type: Mapped[str | None] = mapped_column(String(64))


class InfraOpenPort(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_OpenPorts"
    server_id: Mapped[str | None] = mapped_column(String(64))
    port: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(16))


class InfraCertificate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_Certificates"
    common_name: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InfraFirewallRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_FirewallRules"
    rule_name: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(32))


class InfraPatchRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_PatchRecords"
    target: Mapped[str] = mapped_column(String(255))
    patch_id: Mapped[str | None] = mapped_column(String(128))


class InfraHardeningCheck(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_HardeningChecks"
    check_name: Mapped[str] = mapped_column(String(255))
    passed: Mapped[bool] = mapped_column(Boolean, default=False)


class InfraRemoteAccessRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_RemoteAccessRules"
    rule_name: Mapped[str] = mapped_column(String(255))


class InfraBackupRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_BackupRecords"
    system_name: Mapped[str] = mapped_column(String(255))
    last_backup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InfraSecurityTool(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Infra_SecurityTools"
    tool_name: Mapped[str] = mapped_column(String(255))
    vendor: Mapped[str | None] = mapped_column(String(128))


class AppSecSSDLCRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_SSDLCRecords"
    project_name: Mapped[str] = mapped_column(String(255))
    phase: Mapped[str | None] = mapped_column(String(64))


class AppSecCodeReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_CodeReviews"
    repository: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))


class AppSecSASTScan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_SASTScans"
    tool: Mapped[str] = mapped_column(String(128))
    findings_count: Mapped[int] = mapped_column(Integer, default=0)


class AppSecDASTScan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_DASTScans"
    target_url: Mapped[str] = mapped_column(String(512))
    findings_count: Mapped[int] = mapped_column(Integer, default=0)


class AppSecPenTest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_PenTests"
    scope: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32))


class AppSecDependencyScan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_DependencyScans"
    project: Mapped[str] = mapped_column(String(255))
    critical_count: Mapped[int] = mapped_column(Integer, default=0)


class AppSecSecurityHeader(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_SecurityHeaders"
    endpoint: Mapped[str] = mapped_column(String(512))
    compliant: Mapped[bool] = mapped_column(Boolean, default=False)


class AppSecAPIControl(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_APIControls"
    api_name: Mapped[str] = mapped_column(String(255))
    auth_required: Mapped[bool] = mapped_column(Boolean, default=True)


class AppSecVulnerability(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_Vulnerabilities"
    cve_id: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="open")


class AppSecRemediationAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "AppSec_RemediationActions"
    vulnerability_id: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(Text)
