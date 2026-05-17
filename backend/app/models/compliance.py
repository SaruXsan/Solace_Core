"""Compliance / RFI foundation tables."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ComplianceRFIQuestion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_RFIQuestions"
    section: Mapped[str] = mapped_column(String(128), nullable=False)
    question_code: Mapped[str] = mapped_column(String(64), unique=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ComplianceRFIAnswer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_RFIAnswers"
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Compliance_RFIQuestions.id"))
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    answered_by: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")


class ComplianceControlMap(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_ControlMap"
    control_id: Mapped[str] = mapped_column(String(64), unique=True)
    framework: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)


class ComplianceAccessReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_AccessReviews"
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ComplianceAccessReviewItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_AccessReviewItems"
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("Compliance_AccessReviews.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    decision: Mapped[str | None] = mapped_column(String(32))


class ComplianceChangeRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_ChangeRequests"
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="draft")


class ComplianceChangeApproval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_ChangeApprovals"
    change_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("Compliance_ChangeRequests.id")
    )
    approver_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    decision: Mapped[str] = mapped_column(String(32))


class ComplianceIncident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_Incidents"
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="open")


class ComplianceDataClassification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_DataClassifications"
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    external_ai_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_redaction: Mapped[bool] = mapped_column(Boolean, default=True)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)


class ComplianceRetentionPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_RetentionPolicies"
    name: Mapped[str] = mapped_column(String(255))
    retention_days: Mapped[int] = mapped_column(Integer)


class ComplianceVendorRegister(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_VendorRegister"
    vendor_name: Mapped[str] = mapped_column(String(255))
    risk_tier: Mapped[str | None] = mapped_column(String(32))


class ComplianceEvidenceLibrary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_EvidenceLibrary"
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    control_id: Mapped[str | None] = mapped_column(String(64))
    source_event_type: Mapped[str | None] = mapped_column(String(128))
    source_event_id: Mapped[str | None] = mapped_column(String(128))
    payload_json: Mapped[str | None] = mapped_column(Text)
    digital_signature_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CompliancePolicyRegister(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_PolicyRegister"
    policy_code: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(32))
    content: Mapped[str | None] = mapped_column(Text)


class ComplianceRedactionLibrary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "Compliance_RedactionLibrary"
    pattern_name: Mapped[str] = mapped_column(String(128), unique=True)
    pattern_regex: Mapped[str] = mapped_column(String(512))
    replacement: Mapped[str] = mapped_column(String(64), default="[REDACTED]")
    data_class: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
