"""Platform security / MFA / SMTP settings (singleton row)."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CoreSecuritySettings(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_SecuritySettings"

    # MFA policy
    enable_mfa: Mapped[bool] = mapped_column(Boolean, default=False)
    require_mfa_for_admins: Mapped[bool] = mapped_column(Boolean, default=True)
    otp_expiry_minutes: Mapped[int] = mapped_column(Integer, default=10)
    otp_retry_limit: Mapped[int] = mapped_column(Integer, default=5)
    resend_cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)

    # Session / lockout
    session_timeout_minutes: Mapped[int] = mapped_column(Integer, default=480)
    login_max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    login_lockout_minutes: Mapped[int] = mapped_column(Integer, default=5)

    # SMTP (password encrypted separately in Core_EncryptedSettings key smtp_password)
    smtp_host: Mapped[str | None] = mapped_column(String(255))
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_username: Mapped[str | None] = mapped_column(String(255))
    from_email: Mapped[str | None] = mapped_column(String(320))

    # System display
    app_display_name: Mapped[str] = mapped_column(String(128), default="Solace Enterprise Core")
    environment_label: Mapped[str] = mapped_column(String(64), default="FOUNDATION")
