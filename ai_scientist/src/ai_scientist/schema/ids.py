from __future__ import annotations

import hashlib
import json
import secrets
import time
from typing import Any

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def new_id(prefix: str) -> str:
    """Sortable-ish short id: <prefix>_<base36 ms><random>."""
    ms = int(time.time() * 1000)
    digits = []
    while ms:
        ms, rem = divmod(ms, 36)
        digits.append(_ALPHABET[rem])
    stamp = "".join(reversed(digits))
    return f"{prefix}_{stamp}{secrets.token_hex(3)}"


def content_hash(payload: Any) -> str:
    """Stable hash of a JSON-serializable payload."""
    blob = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()
