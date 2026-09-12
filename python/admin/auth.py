from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Header, HTTPException

from python.admin.store import AdminStore

_TOKEN_HASH_KEY = "owner_token_hash"
_PIN_HASH_KEY = "owner_pin_hash"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_credentials() -> tuple[str, str]:
    """Generate a new (token, pin) pair. Callers must persist it with
    `set_credentials` — plaintext is never stored, only its hash."""
    token = secrets.token_urlsafe(32)
    pin = f"{secrets.randbelow(10 ** 6):06d}"
    return token, pin


def set_credentials(store: AdminStore, token: str, pin: str) -> None:
    store.set_setting(_TOKEN_HASH_KEY, _hash(token))
    store.set_setting(_PIN_HASH_KEY, _hash(pin))


def has_credentials(store: AdminStore) -> bool:
    return store.get_setting(_TOKEN_HASH_KEY) is not None


def verify_token(store: AdminStore, token: str) -> bool:
    stored = store.get_setting(_TOKEN_HASH_KEY)
    if not stored or not token:
        return False
    return hmac.compare_digest(stored, _hash(token))


def verify_pin(store: AdminStore, pin: str) -> bool:
    stored = store.get_setting(_PIN_HASH_KEY)
    if not stored or not pin:
        return False
    return hmac.compare_digest(stored, _hash(pin))


def make_owner_dependency(store: AdminStore):
    """Build a FastAPI dependency enforcing the X-Owner-Token header that the
    MiAI Admin Android app sends on every /admin/* request."""

    def require_owner(x_owner_token: str = Header(default="", alias="X-Owner-Token")) -> str:
        if not has_credentials(store):
            raise HTTPException(
                status_code=503,
                detail=(
                    "No hay Owner Token configurado en este Core. Genera uno con "
                    "'python scripts/generate_owner_token.py --url <URL>' antes de vincular la app."
                ),
            )
        if not verify_token(store, x_owner_token):
            store.log_audit("admin:auth_failed", level="security")
            raise HTTPException(status_code=401, detail="Owner Token inválido o ausente.")
        return x_owner_token

    return require_owner
