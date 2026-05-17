"""Seed placeholder modules, RFI sections, classifications, redaction patterns."""

from __future__ import annotations

import json

from sqlalchemy import select  # noqa: F401 — used in seed_foundation_data
from sqlalchemy.orm import Session

from app.models.compliance import (
    ComplianceDataClassification,
    ComplianceRedactionLibrary,
    ComplianceRFIQuestion,
)
from app.models.platform import CoreModule, CoreNavigationItem, CorePermission
from app.models.solace_intel import SolaceAIProviderRegistry, SolaceAIDataHandlingPolicy

PLACEHOLDER_MODULES = [
    ("document_hub", "Document Hub", "doc"),
    ("operations", "Operations", "ops"),
    ("hr", "Human Resources", "hr"),
    ("legal", "Legal", "legal"),
    ("it_network", "IT / Network", "it"),
    ("email_intelligence", "Email Intelligence", "email"),
]

RFI_SECTIONS = [
    ("general", "General Application Overview", 1),
    ("auth", "Authentication & Access Control", 2),
    ("data_security", "Data Security & Privacy", 3),
    ("network", "Network & Infrastructure Security", 4),
    ("appsec", "Application Security", 5),
    ("logging", "Logging, Monitoring & Incident Response", 6),
    ("secrets", "Secrets & Configuration Management", 7),
]

CLASSIFICATIONS = [
    ("PUBLIC", "Public", True, False, False),
    ("INTERNAL", "Internal", True, False, False),
    ("CONFIDENTIAL", "Confidential", False, True, False),
    ("RESTRICTED", "Restricted", False, True, True),
    ("SECRET", "Secret", False, True, True),
]


def seed_foundation_data(db: Session) -> None:
    from app.models.platform import CoreOrganization
    from app.models.settings import CoreSecuritySettings
    from app.services import role_service

    _seed_modules(db)
    _seed_permissions(db)
    _seed_navigation(db)
    _seed_rfi(db)
    _seed_classifications(db)
    _seed_redaction(db)
    _seed_ai_providers(db)
    if db.scalar(select(CoreSecuritySettings).limit(1)) is None:
        db.add(CoreSecuritySettings())
    org = db.scalar(select(CoreOrganization).limit(1))
    if org:
        role_service.seed_base_roles(db, org.id)


def _seed_modules(db: Session) -> None:
    for name, display, prefix in PLACEHOLDER_MODULES:
        exists = db.scalar(select(CoreModule).where(CoreModule.module_name == name))
        if exists:
            continue
        db.add(
            CoreModule(
                module_name=name,
                display_name=display,
                enabled=False,
                is_placeholder=True,
                database_prefix=prefix,
                description=f"{display} — placeholder module (not implemented)",
                permissions_json=json.dumps([f"{name}.view"]),
            )
        )


def _seed_permissions(db: Session) -> None:
    from app.services import permission_seed_service

    permission_seed_service.ensure_permissions(db)


def _seed_navigation(db: Session) -> None:
    items = [
        ("Dashboard", "Main dashboard", "/", "dashboard", 0, None),
        ("Users", "Users", "/platform/users", "platform", 10, None),
        ("Roles & Permissions", "Roles", "/platform/roles", "platform", 20, None),
        ("Modules", "Modules", "/platform/modules", "platform", 30, None),
        ("Settings", "Settings", "/platform/settings", "platform", 40, None),
        ("RFI Center", "RFI Center", "/compliance/rfi", "compliance", 50, None),
        ("Evidence Library", "Evidence", "/compliance/evidence", "compliance", 60, None),
    ]
    for label, _desc, route, section, order, mod in items:
        if db.scalar(select(CoreNavigationItem).where(CoreNavigationItem.route == route)):
            continue
        db.add(
            CoreNavigationItem(
                section=section, label=label, route=route, sort_order=order, module_code=mod
            )
        )


def _seed_rfi(db: Session) -> None:
    for section_id, title, order in RFI_SECTIONS:
        code = f"RFI-{section_id.upper()}"
        if db.scalar(select(ComplianceRFIQuestion).where(ComplianceRFIQuestion.question_code == code)):
            continue
        db.add(
            ComplianceRFIQuestion(
                section=section_id,
                question_code=code,
                question_text=title,
                sort_order=order,
            )
        )


def _seed_classifications(db: Session) -> None:
    for code, name, ext, redact, review in CLASSIFICATIONS:
        if db.scalar(
            select(ComplianceDataClassification).where(
                ComplianceDataClassification.code == code
            )
        ):
            continue
        db.add(
            ComplianceDataClassification(
                code=code,
                name=name,
                external_ai_allowed=ext,
                requires_redaction=redact,
                human_review_required=review,
            )
        )
        if not db.scalar(
            select(SolaceAIDataHandlingPolicy).where(
                SolaceAIDataHandlingPolicy.classification_code == code
            )
        ):
            db.add(
                SolaceAIDataHandlingPolicy(
                    classification_code=code,
                    external_provider_allowed=ext,
                    requires_redaction=redact,
                    human_review_required=review,
                )
            )


def _seed_redaction(db: Session) -> None:
    patterns = [
        ("phone_us", r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        ("ssn", r"\b\d{3}-\d{2}-\d{4}\b"),
        ("api_key", r"\b(sk-|pk-)[A-Za-z0-9]{16,}\b"),
    ]
    for name, regex in patterns:
        if db.scalar(
            select(ComplianceRedactionLibrary).where(
                ComplianceRedactionLibrary.pattern_name == name
            )
        ):
            continue
        db.add(
            ComplianceRedactionLibrary(
                pattern_name=name, pattern_regex=regex, replacement="[REDACTED]"
            )
        )


def _seed_ai_providers(db: Session) -> None:
    providers = [
        ("openai", "OpenAI", "openai", True),
        ("ollama", "Ollama", "ollama", False),
    ]
    for code, name, ptype, external in providers:
        if db.scalar(
            select(SolaceAIProviderRegistry).where(
                SolaceAIProviderRegistry.provider_code == code
            )
        ):
            continue
        db.add(
            SolaceAIProviderRegistry(
                provider_code=code,
                display_name=name,
                provider_type=ptype,
                is_enabled=False,
                is_external=external,
            )
        )
