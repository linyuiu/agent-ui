from __future__ import annotations

import base64
import json
import secrets
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException


_KEY_SIZE = 2048
_KEY_ID = secrets.token_hex(8)
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=_KEY_SIZE)
_PUBLIC_KEY_PEM = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")


def get_login_public_key() -> dict[str, str]:
    return {
        "key_id": _KEY_ID,
        "algorithm": "RSA-OAEP-256",
        "public_key_pem": _PUBLIC_KEY_PEM,
    }


def decrypt_login_payload(encrypted_payload: str, key_id: str | None = None) -> dict[str, Any]:
    if not encrypted_payload:
        raise HTTPException(status_code=400, detail="缺少加密登录数据")
    if key_id and key_id != _KEY_ID:
        raise HTTPException(status_code=400, detail="登录密钥已过期，请刷新页面后重试")
    try:
        decoded = base64.b64decode(encrypted_payload)
        payload: dict[str, Any]
        try:
            envelope = json.loads(decoded.decode("utf-8"))
        except Exception:
            envelope = None

        if isinstance(envelope, dict) and envelope.get("encrypted_key"):
            encrypted_key = base64.b64decode(str(envelope.get("encrypted_key") or ""))
            iv = base64.b64decode(str(envelope.get("iv") or ""))
            ciphertext = base64.b64decode(str(envelope.get("ciphertext") or ""))
            aes_key = _PRIVATE_KEY.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            plaintext = AESGCM(aes_key).decrypt(iv, ciphertext, None)
            payload = json.loads(plaintext.decode("utf-8"))
        else:
            plaintext = _PRIVATE_KEY.decrypt(
                decoded,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            payload = json.loads(plaintext.decode("utf-8"))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="登录数据解密失败，请刷新页面后重试") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="登录数据格式错误")
    return payload
