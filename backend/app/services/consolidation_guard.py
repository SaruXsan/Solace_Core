"""Consolidation access guard — explicit authority checks before cross-entity queries."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.consolidation_context import ActiveConsolidationScope, get_active_consolidation_scope
from app.core.permissions import user_has_permission
from app.models.platform import CoreConsolidationScope, CoreUser
from app.services import audit_service, consolidation_scope_service as css


@dataclass
class ConsolidationAccessRequest:
    """Requested consolidation query boundaries (foundation — no reports yet)."""

    country_ids: list[uuid.UUID] = field(default_factory=list)
    organization_ids: list[uuid.UUID] = field(default_factory=list)
    branch_ids: list[uuid.UUID] = field(default_factory=list)
    department_ids: list[uuid.UUID] = field(default_factory=list)
    module_source: str | None = None
    classification: str = "Internal"
    requires_raw_restricted: bool = False
    requires_ai_summary: bool = False
    requires_export: bool = False


@dataclass
class ConsolidationAccessResult:
    allowed: bool
    reason: str
    consolidation_scope_id: str | None = None
    covered: dict[str, list[str]] | None = None


def _request_detail(req: ConsolidationAccessRequest) -> dict[str, Any]:
    return {
        "country_ids": [str(x) for x in req.country_ids],
        "organization_ids": [str(x) for x in req.organization_ids],
        "branch_ids": [str(x) for x in req.branch_ids],
        "department_ids": [str(x) for x in req.department_ids],
        "module_source": req.module_source,
        "classification": req.classification,
        "requires_raw_restricted": req.requires_raw_restricted,
        "requires_ai_summary": req.requires_ai_summary,
        "requires_export": req.requires_export,
    }


def log_consolidation_denial(
    db: Session,
    user: CoreUser,
    req: ConsolidationAccessRequest,
    *,
    reason: str,
    action: str = "consolidation_access_denied",
    scope_id: uuid.UUID | None = None,
) -> None:
    audit_service.log_audit(
        db,
        "consolidation",
        action,
        actor_user_id=user.id,
        resource_type="consolidation_scope",
        resource_id=str(scope_id) if scope_id else None,
        detail={"reason": reason, "request": _request_detail(req), "allowed": False},
    )


def evaluate_consolidation_access(
    db: Session,
    user: CoreUser,
    req: ConsolidationAccessRequest,
    *,
    active: ActiveConsolidationScope | None = None,
    scope_row: CoreConsolidationScope | None = None,
    ip_address: str | None = None,
) -> ConsolidationAccessResult:
    """Answer whether the user may perform a consolidation-class request."""
    if not user_has_permission(db, user, "consolidation.view"):
        log_consolidation_denial(db, user, req, reason="missing_consolidation.view")
        return ConsolidationAccessResult(False, "missing_consolidation.view")

    active = active or get_active_consolidation_scope()
    if active is None:
        log_consolidation_denial(db, user, req, reason="no_active_consolidation_scope")
        return ConsolidationAccessResult(False, "no_active_consolidation_scope")

    if active.user_id != user.id:
        log_consolidation_denial(
            db,
            user,
            req,
            reason="consolidation_scope_user_mismatch",
            scope_id=active.id,
        )
        return ConsolidationAccessResult(False, "consolidation_scope_user_mismatch", str(active.id))

    scope_row = scope_row or db.get(CoreConsolidationScope, active.id)
    if scope_row is None or not scope_row.is_active:
        log_consolidation_denial(db, user, req, reason="consolidation_scope_inactive", scope_id=active.id)
        return ConsolidationAccessResult(False, "consolidation_scope_inactive", str(active.id))

    if req.requires_export and not user_has_permission(db, user, "consolidation.export"):
        log_consolidation_denial(db, user, req, reason="missing_consolidation.export", scope_id=active.id)
        return ConsolidationAccessResult(False, "missing_consolidation.export", str(active.id))

    if req.requires_export and not active.can_export:
        log_consolidation_denial(db, user, req, reason="scope_export_not_allowed", scope_id=active.id)
        return ConsolidationAccessResult(False, "scope_export_not_allowed", str(active.id))

    if req.requires_ai_summary and not user_has_permission(db, user, "consolidation.ai_summary"):
        log_consolidation_denial(db, user, req, reason="missing_consolidation.ai_summary", scope_id=active.id)
        return ConsolidationAccessResult(False, "missing_consolidation.ai_summary", str(active.id))

    if req.requires_ai_summary and not active.can_use_ai_summary:
        log_consolidation_denial(db, user, req, reason="scope_ai_summary_not_allowed", scope_id=active.id)
        return ConsolidationAccessResult(False, "scope_ai_summary_not_allowed", str(active.id))

    if req.module_source and active.allowed_modules:
        if req.module_source not in active.allowed_modules:
            log_consolidation_denial(db, user, req, reason="module_not_allowed", scope_id=active.id)
            return ConsolidationAccessResult(False, "module_not_allowed", str(active.id))

    requested_class = css.normalize_classification(req.classification)
    if css.classification_rank(requested_class) > css.classification_rank(active.max_classification_allowed):
        log_consolidation_denial(
            db,
            user,
            req,
            reason="classification_exceeds_ceiling",
            scope_id=active.id,
        )
        return ConsolidationAccessResult(False, "classification_exceeds_ceiling", str(active.id))

    raw_levels = {"restricted", "secret"}
    if req.requires_raw_restricted or requested_class.lower() in raw_levels:
        if not user_has_permission(db, user, "consolidation.view_restricted"):
            audit_service.log_audit(
                db,
                "consolidation",
                "consolidation_restricted_data_denied",
                actor_user_id=user.id,
                resource_type="consolidation_scope",
                resource_id=str(active.id),
                detail={"reason": "missing_consolidation.view_restricted", "request": _request_detail(req)},
                ip_address=ip_address,
            )
            return ConsolidationAccessResult(
                False, "missing_consolidation.view_restricted", str(active.id)
            )
        if not active.can_view_raw_restricted:
            audit_service.log_audit(
                db,
                "consolidation",
                "consolidation_restricted_data_denied",
                actor_user_id=user.id,
                resource_type="consolidation_scope",
                resource_id=str(active.id),
                detail={"reason": "scope_raw_restricted_denied", "request": _request_detail(req)},
                ip_address=ip_address,
            )
            return ConsolidationAccessResult(False, "scope_raw_restricted_denied", str(active.id))

    covered = css.resolve_covered_entity_ids(db, scope_row)

    for oid in req.organization_ids:
        if oid not in covered["organizations"]:
            log_consolidation_denial(db, user, req, reason="organization_out_of_scope", scope_id=active.id)
            return ConsolidationAccessResult(False, "organization_out_of_scope", str(active.id))

    for cid in req.country_ids:
        if cid not in covered["countries"]:
            log_consolidation_denial(db, user, req, reason="country_out_of_scope", scope_id=active.id)
            return ConsolidationAccessResult(False, "country_out_of_scope", str(active.id))

    for bid in req.branch_ids:
        if bid not in covered["branches"]:
            log_consolidation_denial(db, user, req, reason="branch_out_of_scope", scope_id=active.id)
            return ConsolidationAccessResult(False, "branch_out_of_scope", str(active.id))

    for did in req.department_ids:
        if did not in covered["departments"]:
            log_consolidation_denial(db, user, req, reason="department_out_of_scope", scope_id=active.id)
            return ConsolidationAccessResult(False, "department_out_of_scope", str(active.id))

    if req.requires_ai_summary or user_has_permission(db, user, "consolidation.report"):
        pass  # report permission validated at report layer; view already checked

    covered_out = {k: [str(x) for x in v] for k, v in covered.items()}
    audit_service.log_audit(
        db,
        "consolidation",
        "consolidation_access_granted",
        actor_user_id=user.id,
        resource_type="consolidation_scope",
        resource_id=str(active.id),
        detail={"request": _request_detail(req), "allowed": True, "covered": covered_out},
        ip_address=ip_address,
    )
    return ConsolidationAccessResult(
        True,
        "allowed",
        str(active.id),
        covered_out,
    )


def user_has_consolidation_permission(db: Session, user: CoreUser, code: str) -> bool:
    return user_has_permission(db, user, code)
