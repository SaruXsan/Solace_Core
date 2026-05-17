"""Encrypted bootstrap store for DB connection prior to / outside migrations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.crypto import decrypt_value, encrypt_value

_BOOTSTRAP_PATH = Path(__file__).resolve().parents[2] / "data" / "bootstrap.enc"


def _ensure_dir() -> None:
    _BOOTSTRAP_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_bootstrap() -> dict[str, Any]:
    if not _BOOTSTRAP_PATH.exists():
        return {}
    raw = _BOOTSTRAP_PATH.read_text(encoding="utf-8")
    return json.loads(decrypt_value(raw))


def save_bootstrap(data: dict[str, Any]) -> None:
    _ensure_dir()
    _BOOTSTRAP_PATH.write_text(encrypt_value(json.dumps(data)), encoding="utf-8")


def get_db_connection_url() -> str | None:
    return load_bootstrap().get("database_url")


def is_setup_complete() -> bool:
    return bool(load_bootstrap().get("setup_complete"))


def mark_setup_complete() -> None:
    data = load_bootstrap()
    data["setup_complete"] = True
    save_bootstrap(data)


def save_database_url(url: str) -> None:
    data = load_bootstrap()
    data["database_url"] = url
    save_bootstrap(data)
