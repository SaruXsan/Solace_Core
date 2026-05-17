"""RFI Center and Evidence Library."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.compliance import (
    ComplianceEvidenceLibrary,
    ComplianceRFIAnswer,
    ComplianceRFIQuestion,
    ComplianceRedactionLibrary,
)


def get_rfi_sections(db: Session) -> list[dict]:
    questions = db.scalars(
        select(ComplianceRFIQuestion).order_by(
            ComplianceRFIQuestion.sort_order, ComplianceRFIQuestion.question_code
        )
    ).all()
    answers = {
        a.question_id: a
        for a in db.scalars(select(ComplianceRFIAnswer)).all()
    }
    by_section: dict[str, list] = defaultdict(list)
    titles = {
        "general": "General Application Overview",
        "auth": "Authentication & Access Control",
        "data_security": "Data Security & Privacy",
        "network": "Network & Infrastructure Security",
        "appsec": "Application Security",
        "logging": "Logging, Monitoring & Incident Response",
        "secrets": "Secrets & Configuration Management",
    }
    for q in questions:
        ans = answers.get(q.id)
        by_section[q.section].append(
            {
                "id": str(q.id),
                "question_code": q.question_code,
                "question_text": q.question_text,
                "sort_order": q.sort_order,
                "answer_text": ans.answer_text if ans else None,
                "answer_status": ans.status if ans else None,
            }
        )
    return [
        {
            "section": sec,
            "title": titles.get(sec, sec.replace("_", " ").title()),
            "questions": items,
        }
        for sec, items in by_section.items()
    ]


def save_rfi_answer(
    db: Session, question_id: uuid.UUID, answer_text: str, status: str, user_id: uuid.UUID
) -> dict:
    q = db.get(ComplianceRFIQuestion, question_id)
    if not q:
        raise SolaceHTTPException(404, "Question not found")
    ans = db.scalar(
        select(ComplianceRFIAnswer).where(ComplianceRFIAnswer.question_id == question_id)
    )
    if ans:
        ans.answer_text = answer_text
        ans.status = status
        ans.answered_by = user_id
    else:
        ans = ComplianceRFIAnswer(
            question_id=question_id,
            answer_text=answer_text,
            status=status,
            answered_by=user_id,
        )
        db.add(ans)
    db.flush()
    return {"success": True, "question_id": str(question_id), "status": status}


def list_evidence(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(
        select(ComplianceEvidenceLibrary)
        .order_by(ComplianceEvidenceLibrary.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(e.id),
            "title": e.title,
            "control_id": e.control_id,
            "source_event_type": e.source_event_type,
            "digital_signature_hash": e.digital_signature_hash,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in rows
    ]


def list_redaction_rules(db: Session) -> list[dict]:
    rows = db.scalars(select(ComplianceRedactionLibrary).order_by(ComplianceRedactionLibrary.pattern_name)).all()
    return [
        {
            "id": str(r.id),
            "pattern_name": r.pattern_name,
            "pattern_regex": r.pattern_regex,
            "replacement": r.replacement,
            "is_active": r.is_active,
        }
        for r in rows
    ]


def create_redaction_rule(db: Session, data: dict) -> dict:
    row = ComplianceRedactionLibrary(
        pattern_name=data["pattern_name"],
        pattern_regex=data["pattern_regex"],
        replacement=data.get("replacement", "[REDACTED]"),
        is_active=data.get("is_active", True),
    )
    db.add(row)
    db.flush()
    return {
        "id": str(row.id),
        "pattern_name": row.pattern_name,
        "pattern_regex": row.pattern_regex,
        "replacement": row.replacement,
        "is_active": row.is_active,
    }
