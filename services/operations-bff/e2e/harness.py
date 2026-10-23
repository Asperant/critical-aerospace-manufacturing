"""Browser-test harness: a real operations-bff process over HTTPS.

Serves the built Command Center from the same origin as the BFF, exactly as the
canonical single-entry-point topology does. The external boundaries are
deterministic application ports, not real services: a scripted identity provider
(no Keycloak) and fixture-backed Core and Twin readers (no real backends). The
`/__control` routes exist only here, to put those fakes into a state for a test.
Nothing in this file is part of the shipped service.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import secrets
import tempfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from operations_bff.api import create_app
from operations_bff.config import CookieSettings, LoginConfig, SessionConfig
from operations_bff.idp import AuthorizationRequest, IdentityProviderError
from operations_bff.login import InMemoryLoginStore, LoginService, pkce_challenge
from operations_bff.observability import configure_access_log
from operations_bff.overview import (
    AttentionFact,
    OverviewQuery,
    OverviewService,
    SourceSnapshot,
    SourceUnavailable,
)
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
)

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "v1"
IDENTITY = AuthenticatedIdentity(
    subject="U-E2E-01",
    display_name="E2E Operator",
    roles=("ops-controller",),
    environment_id="ENV-E2E",
)
# Held by the scripted provider and never returned by any BFF response.
PROVIDER_SECRETS = ("E2E-ACCESS-TOKEN", "E2E-REFRESH-TOKEN", "E2E-ID-TOKEN")


class ScriptedIdentityProvider:
    """Deterministic stand-in for the provider port; checks PKCE and nonce."""

    def __init__(self, origin: str) -> None:
        self._origin = origin
        self._requests: dict[str, AuthorizationRequest] = {}
        self._codes: dict[str, AuthorizationRequest] = {}

    def authorization_url(self, request: AuthorizationRequest) -> str:
        self._requests[request.state] = request
        return f"{self._origin}/__fake-idp/authorize?state={request.state}"

    def issue_code(self, state: str) -> str:
        request = self._requests.pop(state, None)
        if request is None:
            raise HTTPException(status_code=400)
        code = secrets.token_urlsafe(16)
        self._codes[code] = request
        return code

    def complete(
        self, *, code: str, code_verifier: str, nonce: str
    ) -> AuthenticatedIdentity:
        request = self._codes.pop(code, None)
        if (
            request is None
            or pkce_challenge(code_verifier) != request.code_challenge
            or nonce != request.nonce
        ):
            raise IdentityProviderError
        return IDENTITY


class FixtureReader:
    """Fixture-backed attention reader with a switchable failure mode."""

    def __init__(self, snapshot: SourceSnapshot) -> None:
        self._base = snapshot
        self.name = snapshot.source
        self.down = False
        self.freshness: str | None = None

    def read(self, query: OverviewQuery) -> SourceSnapshot:
        del query
        if self.down:
            raise SourceUnavailable
        if self.freshness is not None:
            return replace(self._base, freshness=self.freshness)
        return self._base


def fixture_readers() -> dict[str, FixtureReader]:
    fixture: dict[str, Any] = json.loads(
        (CONTRACTS / "overview-query.normal.json").read_text("utf-8")
    )
    readers: dict[str, FixtureReader] = {}
    for source in fixture["meta"]["sources"]:
        items = tuple(
            AttentionFact(
                item_id=i["item_id"],
                kind=i["kind"],
                epistemic_class=i["epistemic_class"],
                subject_type=i["subject"]["entity_type"],
                subject_id=i["subject"]["entity_id"],
                summary=i["summary"],
            )
            for i in fixture["needs_attention"]
            if i["source"] == source["source"]
        )
        readers[source["source"]] = FixtureReader(
            SourceSnapshot(
                source=source["source"],
                revision=source["revision"],
                as_of=datetime.fromisoformat(source["as_of"]),
                freshness=source["freshness"],
                items=items,
            )
        )
    return readers


def self_signed_certificate(directory: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path, cert_path = directory / "key.pem", directory / "cert.pem"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return key_path, cert_path


def build(origin: str, dist: Path) -> Any:
    sessions_store = InMemorySessionStore()
    logins_store = InMemoryLoginStore()
    manager = SessionManager(
        sessions_store,
        SessionConfig(
            absolute_ttl=timedelta(hours=1),
            idle_ttl=timedelta(minutes=30),
            rotate_after=timedelta(minutes=15),
        ),
    )
    provider = ScriptedIdentityProvider(origin)
    readers = fixture_readers()
    core, twin = readers["manufacturing-core"], readers["digital-twin-service"]
    app = create_app(
        manager,
        cookie=CookieSettings(same_site="lax"),
        login=LoginService(provider, logins_store, manager, LoginConfig()),
        overview=OverviewService(core, [twin]),
    )

    @app.get("/__fake-idp/authorize", include_in_schema=False)
    def authorize(state: str) -> RedirectResponse:  # pyright: ignore[reportUnusedFunction]
        code = provider.issue_code(state)
        return RedirectResponse(
            f"/v1/session/callback?code={code}&state={state}", status_code=302
        )

    @app.post("/__control/reset", include_in_schema=False)
    def reset() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        sessions_store._records.clear()  # pyright: ignore[reportPrivateUsage]
        logins_store._items.clear()  # pyright: ignore[reportPrivateUsage]
        for reader in readers.values():
            reader.down = False
            reader.freshness = None
        return {"status": "reset"}

    @app.post("/__control/mode/{mode}", include_in_schema=False)
    def mode(mode: str) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        if mode == "ok":
            for reader in readers.values():
                reader.down = False
                reader.freshness = None
        elif mode == "twin_down":
            twin.down = True
        elif mode == "core_down":
            core.down = True
        elif mode == "twin_stale":
            twin.freshness = "STALE"
        else:
            raise HTTPException(status_code=404)
        return {"status": mode}

    @app.post("/__control/expire-sessions", include_in_schema=False)
    def expire() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        sessions_store._records.clear()  # pyright: ignore[reportPrivateUsage]
        return {"status": "expired"}

    @app.get("/__control/provider-secrets", include_in_schema=False)
    def provider_secrets() -> list[str]:  # pyright: ignore[reportUnusedFunction]
        return list(PROVIDER_SECRETS)

    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:  # pyright: ignore[reportUnusedFunction]
        if path.startswith(("v1/", "__")):
            raise HTTPException(status_code=404)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--dist", type=Path, required=True)
    args = parser.parse_args()
    origin = f"https://127.0.0.1:{args.port}"
    configure_access_log()
    with tempfile.TemporaryDirectory() as directory:
        key_path, cert_path = self_signed_certificate(Path(directory))
        uvicorn.run(
            build(origin, args.dist),
            host="127.0.0.1",
            port=args.port,
            ssl_keyfile=str(key_path),
            ssl_certfile=str(cert_path),
            log_level="warning",
        )


if __name__ == "__main__":
    main()
