"""Structured logging with secret sanitization."""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

_SENSITIVE_PATTERNS = [
    re.compile(r"(password|passwd|secret|token|api[_-]?key|otp|bind_password)\s*[:=]\s*\S+", re.I),
    re.compile(r"\b\d{6}\b"),  # bare OTP-like
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.I),
]


def _sanitize_message(msg: str) -> str:
    out = msg
    for pat in _SENSITIVE_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


class SanitizingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = record.getMessage()
        record.msg = _sanitize_message(str(original))
        record.args = ()
        return super().format(record)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        SanitizingFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def safe_log_extra(**kwargs: Any) -> dict[str, Any]:
    """Build log extra dict with sensitive keys stripped."""
    blocked = {"password", "otp", "token", "secret", "bind_password", "api_key"}
    return {k: v for k, v in kwargs.items() if k.lower() not in blocked}
