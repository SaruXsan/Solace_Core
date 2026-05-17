"""Solace memory foundation — strict user + org scoping."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SecurityException, SolaceHTTPException
from app.core.tenant_context import get_organization_id
from app.models.platform import CoreUser
from app.models.solace_intel import SolaceMemoryAtom, SolaceREMProposal, SolaceUserPersona


def list_memory_atoms(db: Session, user: CoreUser, target_user_id: uuid.UUID | None = None) -> list[dict]:
    """User A cannot read User B atoms unless admin."""
    uid = target_user_id or user.id
    if uid != user.id and not user.is_admin:
        raise SecurityException("Cross-user memory access denied")
    org_id = get_organization_id() or user.organization_id
    rows = db.scalars(
        select(SolaceMemoryAtom).where(
            SolaceMemoryAtom.organization_id == org_id,
            SolaceMemoryAtom.user_id == uid,
        )
    ).all()
    return [
        {
            "id": str(a.id),
            "user_id": str(a.user_id),
            "domain": a.domain,
            "category": a.category,
            "claim": a.claim[:200],
            "data_classification": a.data_classification,
            "memory_tier": a.memory_tier,
            "broken_link_flag": a.broken_link_flag,
        }
        for a in rows
    ]


def create_memory_atom(db: Session, user: CoreUser, data: dict) -> dict:
    org_id = get_organization_id() or user.organization_id
    uid = data.get("user_id", user.id)
    if uid != user.id and not user.is_admin:
        raise SecurityException("Cannot create memory for another user")
    atom = SolaceMemoryAtom(
        organization_id=org_id,
        user_id=uid,
        domain=data.get("domain", "USER_SELF"),
        category=data.get("category"),
        claim=data["claim"],
        data_classification=data.get("data_classification", "INTERNAL"),
        memory_tier=data.get("memory_tier", "ACTIVE_MEMORY"),
    )
    db.add(atom)
    db.flush()
    return {"id": str(atom.id)}


def list_personas(db: Session, user: CoreUser) -> list[dict]:
    org_id = get_organization_id() or user.organization_id
    rows = db.scalars(
        select(SolaceUserPersona).where(
            SolaceUserPersona.organization_id == org_id,
            SolaceUserPersona.user_id == user.id,
        )
    ).all()
    return [
        {
            "id": str(p.id),
            "persona_name": p.persona_name,
            "conflict_policy": p.conflict_policy,
        }
        for p in rows
    ]


def list_rem_proposals(db: Session, user: CoreUser) -> list[dict]:
    org_id = get_organization_id() or user.organization_id
    rows = db.scalars(
        select(SolaceREMProposal).where(
            SolaceREMProposal.organization_id == org_id,
            SolaceREMProposal.user_id == user.id,
        )
    ).all()
    return [
        {
            "id": str(r.id),
            "proposal_type": r.proposal_type,
            "status": r.status,
            "payload_preview": (r.payload_json or "")[:200],
        }
        for r in rows
    ]
