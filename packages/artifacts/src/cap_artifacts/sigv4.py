"""AWS Signature Version 4 for the S3 API (WP-OBJ-001).

The S3 API is the contract boundary to SeaweedFS (ADR-0005), so requests are
signed exactly as any S3 service expects; no product-specific behaviour is used.
Only what the artifact store needs is implemented: header-based signing of one
request with a known payload hash. Secrets are never logged or returned.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
ALGORITHM = "AWS4-HMAC-SHA256"


@dataclass(frozen=True)
class Credentials:
    access_key: str
    secret_key: str = ""

    def __repr__(self) -> str:  # never print the secret
        return f"Credentials(access_key={self.access_key!r}, secret_key=<redacted>)"


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def canonical_uri(path: str) -> str:
    """S3 path canonicalization: each segment URI-encoded once, '/' kept."""
    return quote(path, safe="/-_.~")


def canonical_query(query: Mapping[str, str]) -> str:
    pairs = sorted(
        (quote(k, safe="-_.~"), quote(v, safe="-_.~")) for k, v in query.items()
    )
    return "&".join(f"{k}={v}" for k, v in pairs)


def sign(
    *,
    method: str,
    host: str,
    path: str,
    query: Mapping[str, str],
    headers: Mapping[str, str],
    payload_sha256: str,
    credentials: Credentials,
    region: str,
    now: datetime,
    service: str = "s3",
) -> dict[str, str]:
    """Return the headers to send: the given ones plus x-amz-date,
    x-amz-content-sha256, host and Authorization."""
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    day = now.strftime("%Y%m%d")
    signed: dict[str, str] = {
        k.lower(): " ".join(v.strip().split()) for k, v in headers.items()
    }
    signed["host"] = host
    signed["x-amz-date"] = amz_date
    signed["x-amz-content-sha256"] = payload_sha256
    names = sorted(signed)
    canonical_headers = "".join(f"{name}:{signed[name]}\n" for name in names)
    signed_headers = ";".join(names)
    canonical_request = "\n".join(
        [
            method.upper(),
            canonical_uri(path),
            canonical_query(query),
            canonical_headers,
            signed_headers,
            payload_sha256,
        ]
    )
    scope = f"{day}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(
        [
            ALGORITHM,
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    key = _hmac(("AWS4" + credentials.secret_key).encode("utf-8"), day)
    for part in (region, service, "aws4_request"):
        key = _hmac(key, part)
    signature = hmac.new(
        key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    result = {name: signed[name] for name in names}
    result["authorization"] = (
        f"{ALGORITHM} Credential={credentials.access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    return result


UNSIGNED_PAYLOAD = "UNSIGNED-PAYLOAD"


def presign(
    *,
    method: str,
    host: str,
    path: str,
    credentials: Credentials,
    region: str,
    now: datetime,
    expires_s: int,
    service: str = "s3",
) -> dict[str, str]:
    """Query parameters of a pre-signed request (SigV4 query authentication).

    Only `host` is signed; the URL authorises exactly `method` on exactly `path`
    until now + expires_s. The result is a bearer capability: never log it."""
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    day = now.strftime("%Y%m%d")
    scope = f"{day}/{region}/{service}/aws4_request"
    query = {
        "X-Amz-Algorithm": ALGORITHM,
        "X-Amz-Credential": f"{credentials.access_key}/{scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires_s),
        "X-Amz-SignedHeaders": "host",
    }
    canonical_request = "\n".join(
        [
            method.upper(),
            canonical_uri(path),
            canonical_query(query),
            f"host:{host}\n",
            "host",
            UNSIGNED_PAYLOAD,
        ]
    )
    string_to_sign = "\n".join(
        [
            ALGORITHM,
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    key = _hmac(("AWS4" + credentials.secret_key).encode("utf-8"), day)
    for part in (region, service, "aws4_request"):
        key = _hmac(key, part)
    query["X-Amz-Signature"] = hmac.new(
        key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return query
