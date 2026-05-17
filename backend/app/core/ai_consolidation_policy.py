"""AI governance preparation for future executive consolidation summaries.

AI must never decide access — data is filtered before any model call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.consolidation_context import get_active_consolidation_scope
from app.core.permissions import user_has_permission
from app.models.platform import CoreUser
from app.services.consolidation_guard import ConsolidationAccessRequest, evaluate_consolidation_access


@dataclass
class AIConsolidationPolicyResult:
    allowed: bool
    reason: str
    requires_redaction: bool = True
    max_classification: str | None = None
    audit_required: bool = True
    active_consolidation_scope_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "requires_redaction": self.requires_redaction,
            "max_classification": self.max_classification,
            "audit_required": self.audit_required,
            "active_consolidation_scope_id": self.active_consolidation_scope_id,
        }


def check_ai_consolidation_allowed(
    db: Session,
    user: CoreUser,
    *,
    classification: str = "Internal",
    module_source: str | None = None,
    organization_ids: list | None = None,
    country_ids: list | None = None,
) -> AIConsolidationPolicyResult:
    """Pre-flight check for future consolidation AI calls (no LLM invocation here)."""
    active = get_active_consolidation_scope()
    if active is None:
        return AIConsolidationPolicyResult(False, "no_active_consolidation_scope", audit_required=True)

    req = ConsolidationAccessRequest(
        country_ids=country_ids or [],
        organization_ids=organization_ids or [],
        module_source=module_source,
        classification=classification,
        requires_ai_summary=True,
    )
    result = evaluate_consolidation_access(db, user, req, active=active)
    if not result.allowed:
        return AIConsolidationPolicyResult(
            False,
            result.reason,
            requires_redaction=True,
            audit_required=True,
            active_consolidation_scope_id=result.consolidation_scope_id,
        )

    if not user_has_permission(db, user, "consolidation.ai_summary"):
        return AIConsolidationPolicyResult(
            False,
            "missing_consolidation.ai_summary",
            audit_required=True,
            active_consolidation_scope_id=str(active.id),
        )

    # Raw restricted/secret must not reach AI unless explicitly allowed and redacted per policy.
    requires_redaction = True
    max_class = active.max_classification_allowed
    return AIConsolidationPolicyResult(
        True,
        "allowed",
        requires_redaction=requires_redaction,
        max_classification=max_class,
        audit_required=True,
        active_consolidation_scope_id=str(active.id),
    )
