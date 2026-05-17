"""Compliance / RFI / Evidence endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.compliance import ComplianceAccessReview, ComplianceChangeRequest, ComplianceControlMap, ComplianceEvidenceLibrary, ComplianceIncident
from app.models.platform import CoreUser
from app.schemas.compliance import EvidenceOut, RfiAnswerIn, RfiSectionOut
from app.services import audit_service, compliance_service, evidence_linker

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/rfi/sections", response_model=list[RfiSectionOut])
def rfi_sections(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("compliance.read")),
):
    return compliance_service.get_rfi_sections(db)


@router.put("/rfi/questions/{question_id}/answer")
def save_rfi_answer(
    question_id: UUID,
    body: RfiAnswerIn,
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("compliance.update")),
):
    result = compliance_service.save_rfi_answer(
        db, question_id, body.answer_text, body.status, user.id
    )
    db.commit()
    return result


@router.get("/evidence", response_model=list[EvidenceOut])
def list_evidence(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("evidence.read")),
):
    return compliance_service.list_evidence(db)


@router.post("/evidence/auto-linker/run")
def run_auto_linker(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("compliance.update")),
):
    count = evidence_linker.run_evidence_auto_linker_skeleton(db)
    audit_service.log_admin_action(
        db, user.id, "evidence_auto_linker_run", detail={"created": count}
    )
    db.commit()
    return {"created": count}


@router.post("/evidence/{evidence_id}/verify")
def verify_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("evidence.verify")),
):
    row = db.get(ComplianceEvidenceLibrary, evidence_id)
    if not row:
        return {"valid": False, "message": "Not found"}
    result = evidence_linker.verify_evidence_hash(
        row.payload_json or "{}",
        row.source_event_type or "",
        row.source_event_id or "",
        row.control_id,
        row.created_at.isoformat() if row.created_at else "",
        row.digital_signature_hash,
    )
    audit_service.log_admin_action(
        db,
        user.id,
        "evidence_hash_verified",
        target_type="evidence",
        target_id=str(evidence_id),
        detail={"valid": result.get("valid", False)},
    )
    db.commit()
    return result


@router.get("/controls")
def list_controls(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("compliance.read")),
):
    rows = db.scalars(select(ComplianceControlMap)).all()
    return [
        {"control_id": r.control_id, "framework": r.framework, "title": r.title}
        for r in rows
    ]


@router.get("/incidents")
def list_incidents(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("compliance.read")),
):
    rows = db.scalars(select(ComplianceIncident).limit(100)).all()
    return [
        {"id": str(r.id), "title": r.title, "severity": r.severity, "status": r.status}
        for r in rows
    ]


@router.get("/access-reviews")
def list_access_reviews(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("compliance.read")),
):
    rows = db.scalars(select(ComplianceAccessReview).limit(100)).all()
    return [{"id": str(r.id), "title": r.title, "status": r.status} for r in rows]


@router.get("/change-requests")
def list_change_requests(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("compliance.read")),
):
    rows = db.scalars(select(ComplianceChangeRequest).limit(100)).all()
    return [{"id": str(r.id), "title": r.title, "status": r.status} for r in rows]


@router.post("/redaction/test")
def test_redaction(
    body: dict,
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("redaction.test")),
):
    from app.services.redaction_service import redact_text

    text = body.get("text", "")
    return {"original_length": len(text), "redacted": redact_text(db, text)}
