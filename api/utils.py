import base64
import hashlib
import hmac
import time
from typing import Dict


def decode_secret(secret: str) -> bytes:
    """
    Decodes a Formbricks webhook secret (whsec_...) to raw bytes.
    """
    b64 = secret[6:] if secret.startswith("whsec_") else secret
    return base64.b64decode(b64)


def verify_timestamp(timestamp_header: str, tolerance: int = 300) -> int:
    """
    Verifies the webhook timestamp is within tolerance.
    """
    now = int(time.time())
    try:
        timestamp = int(timestamp_header)
    except (ValueError, TypeError):
        raise ValueError("Invalid timestamp")

    if abs(now - timestamp) > tolerance:
        raise ValueError("Timestamp outside tolerance window")

    return timestamp


def compute_signature(webhook_id: str, timestamp: str, body: str, secret: str) -> str:
    """
    Computes the expected signature for a webhook payload.
    """
    signed_content = f"{webhook_id}.{timestamp}.{body}"
    secret_bytes = decode_secret(secret)
    
    signature = hmac.new(
        secret_bytes,
        signed_content.encode("utf-8"),
        hashlib.sha256
    ).digest()
    
    return base64.b64encode(signature).decode("utf-8")


def verify_formbricks_webhook(body: str, headers: Dict[str, str], secret: str) -> bool:
    """
    Verifies a Formbricks webhook request.
    :param body: Raw request body as string
    :param headers: Dictionary containing webhook-id, webhook-timestamp, webhook-signature
    :param secret: Your webhook secret (whsec_...)
    :returns: True if valid
    :raises: ValueError if verification fails
    """
    webhook_id = headers.get("webhook-id")
    webhook_timestamp = headers.get("webhook-timestamp")
    webhook_signature = headers.get("webhook-signature")

    if not all([webhook_id, webhook_timestamp, webhook_signature]):
        raise ValueError("Missing required webhook headers")

    # Verify timestamp
    verify_timestamp(webhook_timestamp)

    # Compute expected signature
    expected_signature = compute_signature(webhook_id, webhook_timestamp, body, secret)

    # Extract signature from header (format: "v1,{signature}")
    parts = webhook_signature.split(",")
    if len(parts) < 2:
        raise ValueError("Invalid signature format")
    
    received_signature = parts[1]

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, received_signature):
        raise ValueError("Invalid signature")

    return True
