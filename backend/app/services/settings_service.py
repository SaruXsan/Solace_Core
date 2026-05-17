"""Core settings and encrypted settings vault."""

from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value, encrypt_value, mask_secret
from app.models.platform import CoreEncryptedSetting, CoreSetting


def get_setting(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.scalar(select(CoreSetting).where(CoreSetting.key == key))
    return row.value if row else default


def set_setting(db: Session, key: str, value: str, category: str = "system") -> None:
    row = db.scalar(select(CoreSetting).where(CoreSetting.key == key))
    if row:
        row.value = value
        row.category = category
    else:
        db.add(CoreSetting(key=key, value=value, category=category))


def get_encrypted_setting(db: Session, key: str) -> str | None:
    row = db.scalar(select(CoreEncryptedSetting).where(CoreEncryptedSetting.key == key))
    if not row:
        return None
    return decrypt_value(row.encrypted_value, row.key_id)


def set_encrypted_setting(
    db: Session,
    key: str,
    plaintext: str,
    category: str = "secret",
    key_id: str = "v1",
    updated_by: uuid.UUID | None = None,
) -> None:
    enc = encrypt_value(plaintext, key_id)
    row = db.scalar(select(CoreEncryptedSetting).where(CoreEncryptedSetting.key == key))
    if row:
        row.encrypted_value = enc
        row.key_id = key_id
        row.category = category
        if updated_by:
            row.updated_by = updated_by
    else:
        db.add(
            CoreEncryptedSetting(
                key=key,
                encrypted_value=enc,
                key_id=key_id,
                category=category,
                updated_by=updated_by,
            )
        )


def get_encrypted_masked(db: Session, key: str) -> str | None:
    val = get_encrypted_setting(db, key)
    if val is None:
        return None
    return mask_secret(val)
