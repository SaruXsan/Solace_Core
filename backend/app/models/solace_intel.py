"""Solace intelligence foundation tables — multi-user scoped, no advanced chat yet."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SolaceAIProviderRegistry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Solace_AIProviderRegistry"
    provider_code: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(128))
    provider_type: Mapped[str] = mapped_column(String(32))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_external: Mapped[bool] = mapped_column(Boolean, default=True)
    config_key_ref: Mapped[str | None] = mapped_column(String(128))


class SolaceAIDataHandlingPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Solace_AIDataHandlingPolicy"
    classification_code: Mapped[str] = mapped_column(String(32), unique=True)
    external_provider_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_redaction: Mapped[bool] = mapped_column(Boolean, default=True)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)


class SolaceRedactionRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Solace_RedactionRules"
    rule_name: Mapped[str] = mapped_column(String(128), unique=True)
    pattern_regex: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class SolaceMemoryAtom(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_MemoryAtoms"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(64))
    claim: Mapped[str] = mapped_column(Text)
    memory_tier: Mapped[str] = mapped_column(String(32), default="ACTIVE_MEMORY")
    data_classification: Mapped[str] = mapped_column(String(32), default="INTERNAL")
    broken_link_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    cache_ttl_seconds: Mapped[int | None] = mapped_column(Integer)


class SolaceInhibition(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_Inhibitions"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    inhibition_key: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str | None] = mapped_column(Text)


class SolaceUserPersona(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_UserPersonas"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    persona_name: Mapped[str] = mapped_column(String(128))
    traits_json: Mapped[str | None] = mapped_column(Text)
    conflict_policy: Mapped[str] = mapped_column(String(64), default="prefer_latest")


class SolaceConversationSession(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_ConversationSessions"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255))


class SolaceConversationSummary(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_ConversationSummaries"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Solace_ConversationSessions.id")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    summary_text: Mapped[str] = mapped_column(Text)


class SolaceREMProposal(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_REMProposals"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    proposal_type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")


class SolaceDailySummary(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_DailySummaries"
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    summary_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary_text: Mapped[str] = mapped_column(Text)


class SolaceRuntimeTrace(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_RuntimeTrace"
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    trace_type: Mapped[str] = mapped_column(String(64))
    detail_json: Mapped[str | None] = mapped_column(Text)


class SolaceLLMCallLog(Base, UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "Solace_LLMCallLog"
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    purpose: Mapped[str | None] = mapped_column(String(255))
    classification: Mapped[str | None] = mapped_column(String(32))
