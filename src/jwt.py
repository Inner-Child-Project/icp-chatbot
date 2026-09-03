import base64
import hashlib
import hmac
import json
import time

_JWT_ALG = "HS256"
_JWT_TYP = "JWT"


def sign_jwt(
    *,
    secret: str,
    sub: str,
    iss: str = "icp-funnel",
    aud: str = "n8n-icp-lead",
    ttl_seconds: int = 300,
) -> str:
    """Sign a short-lived HS256 JWT for the n8n lead webhook."""
    now = int(time.time())
    header = {"alg": _JWT_ALG, "typ": _JWT_TYP}
    payload = {
        "iss": iss,
        "sub": sub,
        "aud": aud,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    signing_input = _b64url(_json_bytes(header)) + "." + _b64url(_json_bytes(payload))
    signature = hmac.new(
        secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256
    ).digest()
    return signing_input + "." + _b64url(signature)


def _json_bytes(obj: dict) -> bytes:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")