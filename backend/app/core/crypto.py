"""Encrypted settings vault — all secrets encrypted with SOLACE_MASTER_KEY."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_master_key


def _derive_fernet_key(master_key: str) -> bytes:
    digest = hashlib.sha256(master_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet(key_id: str = "v1") -> Fernet:
    # key_id reserved for future rotation
    _ = key_id
    return Fernet(_derive_fernet_key(get_master_key()))


def encrypt_value(plaintext: str, key_id: str = "v1") -> str:
    token = get_fernet(key_id).encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt_value(ciphertext: str, key_id: str = "v1") -> str:
    try:
        return get_fernet(key_id).decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Decryption failed — wrong master key or corrupted data") from e


def encrypt_json(data: dict[str, Any], key_id: str = "v1") -> str:
    return encrypt_value(json.dumps(data), key_id)


def decrypt_json(ciphertext: str, key_id: str = "v1") -> dict[str, Any]:
    return json.loads(decrypt_value(ciphertext, key_id))


def hash_otp(otp: str, salt: str) -> str:
    """Hash OTP for storage — never store plaintext OTP."""
    combined = f"{salt}:{otp}:{get_master_key()[:16]}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def mask_secret(value: str, visible: int = 4) -> str:
    if len(value) <= visible:
        return "****"
    return value[:visible] + "****"
