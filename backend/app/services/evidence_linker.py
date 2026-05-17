"""Evidence Auto-Linker skeleton — creates signed evidence records."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.compliance import ComplianceEvidenceLibrary
from app.models.audit import SystemJobHistory


def compute_evidence_hash(
    payload: dict,
    source_event_type: str,
    source_event_id: str,
    control_id: str | None,
    timestamp: datetime,
) -> str:
    canonical = json.dumps(
        {
            "payload": payload,
            "source_event_type": source_event_type,
            "source_event_id": source_event_id,
            "control_id": control_id,
            "timestamp": timestamp.isoformat(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_evidence_hash(
    payload_json: str,
    source_event_type: str,
    source_event_id: str,
    control_id: str | None,
    timestamp_iso: str,
    expected_hash: str,
) -> dict:
    from datetime import datetime

    ts = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    payload = json.loads(payload_json) if isinstance(payload_json, str) else payload_json
    computed = compute_evidence_hash(payload, source_event_type, source_event_id, control_id, ts)
    return {
        "valid": computed == expected_hash,
        "computed_hash": computed,
        "expected_hash": expected_hash,
    }


def run_evidence_auto_linker_skeleton(db: Session) -> int:
    """Skeleton job: create one signed evidence record from latest audit event."""
    job = SystemJobHistory(
        job_name="EvidenceAutoLinker",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()

    now = datetime.now(timezone.utc)
    payload = {"skeleton": True, "message": "Auto-linker foundation placeholder"}
    sig = compute_evidence_hash(
        payload, "skeleton", str(job.id), "CTRL-FOUNDATION-001", now
    )
    db.add(
        ComplianceEvidenceLibrary(
            title="[SYSTEM-GENERATED] Foundation skeleton evidence",
            control_id="CTRL-FOUNDATION-001",
            source_event_type="skeleton",
            source_event_id=str(job.id),
            payload_json=json.dumps({**payload, "system_generated": True}),
            digital_signature_hash=sig,
        )
    )
    job.status = "completed"
    job.finished_at = now
    return 1
