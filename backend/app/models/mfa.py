"""Email MFA challenge table."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CoreMFAChallenge(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Core_MFAChallenges"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Core_Users.id"), nullable=False, index=True
    )
    challenge_type: Mapped[str] = mapped_column(String(32), default="email_otp")
    destination_masked: Mapped[str] = mapped_column(String(320), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    otp_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_resend_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
