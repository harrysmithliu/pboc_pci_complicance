import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


def canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def webhook_signing_message(*, timestamp: int, nonce: str, payload: dict[str, Any]) -> str:
    return f"{timestamp}.{nonce}.{canonical_payload(payload)}"


def sign_webhook_payload(*, timestamp: int, nonce: str, payload: dict[str, Any]) -> str:
    message = webhook_signing_message(timestamp=timestamp, nonce=nonce, payload=payload)
    return hmac.new(
        settings.webhook_hmac_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(
    *,
    timestamp: int,
    nonce: str,
    payload: dict[str, Any],
    signature: str,
) -> bool:
    expected = sign_webhook_payload(timestamp=timestamp, nonce=nonce, payload=payload)
    return hmac.compare_digest(expected, signature)


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(payload).encode("utf-8")).hexdigest()


def current_timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def generate_nonce() -> str:
    return secrets.token_urlsafe(16)


def timestamp_is_fresh(timestamp: int) -> bool:
    delta = abs(current_timestamp() - timestamp)
    return delta <= settings.webhook_timestamp_tolerance_seconds

