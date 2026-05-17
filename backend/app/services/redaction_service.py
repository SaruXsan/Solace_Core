"""Redaction library — masks PII/PHI/tokens before logs or AI."""

from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compliance import ComplianceRedactionLibrary

_BUILTIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("phone", re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    (
        "api_token",
        re.compile(r"\b(sk-|pk-|Bearer\s)[A-Za-z0-9\-._~+/]{8,}\b", re.I),
    ),
]


def load_patterns(db: Session) -> list[tuple[str, re.Pattern[str]]]:
    rows = db.scalars(
        select(ComplianceRedactionLibrary).where(
            ComplianceRedactionLibrary.is_active == True  # noqa: E712
        )
    ).all()
    patterns = list(_BUILTIN_PATTERNS)
    for row in rows:
        try:
            patterns.append((row.pattern_name, re.compile(row.pattern_regex)))
        except re.error:
            continue
    return patterns


def redact_text(db: Session | None, text: str) -> str:
    patterns: Iterable[tuple[str, re.Pattern[str]]] = (
        load_patterns(db) if db is not None else _BUILTIN_PATTERNS
    )
    out = text
    for _, pat in patterns:
        out = pat.sub("[REDACTED]", out)
    return out
