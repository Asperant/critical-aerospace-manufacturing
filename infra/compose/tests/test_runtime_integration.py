"""REAL platform `infra` profile checks (WP-PLAT-001; TEST-PLAT-COMPOSE).

Run after ``infra/compose/stack.sh up infra`` with its ``env`` output exported:

    eval "$(infra/compose/stack.sh env | sed 's/^/export /')"
    uv run --project ci --locked python -m pytest infra/compose/tests -m integration

Every profile must render, and each infrastructure service must answer its
real protocol. Missing services FAIL, never skip.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import pytest

pytestmark = pytest.mark.integration
HERE = Path(__file__).resolve().parents[1]
PROFILES = ["infra", "core", "vision", "ai", "planning", "platform", "full", "e2e"]


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.fail(
            f"{name} is not set: run infra/compose/stack.sh up and export its env"
        )
    return value


def http_get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        pytest.fail(f"{url} unreachable: {exc.reason}")


@pytest.mark.parametrize("profile", PROFILES)
def test_profile_renders(profile: str) -> None:
    result = subprocess.run(
        [str(HERE / "stack.sh"), "config", profile],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_postgres_accepts_queries() -> None:
    import psycopg

    with psycopg.connect(required("CAP_PG_DSN"), connect_timeout=10) as connection:
        version = connection.execute("SHOW server_version").fetchone()
    assert version and str(version[0]).startswith("18.")


def test_nats_jetstream_is_enabled() -> None:
    status, body = http_get(required("CAP_NATS_MONITOR_URL") + "/jsz")
    assert status == 200
    assert json.loads(body).get("config") is not None, "JetStream disabled"


def test_valkey_answers_ping() -> None:
    url = urlparse(required("CAP_VALKEY_URL"))
    assert url.hostname and url.port, url
    with socket.create_connection((url.hostname, url.port), timeout=5) as conn:
        conn.sendall(b"*1\r\n$4\r\nPING\r\n")
        assert conn.recv(16).startswith(b"+PONG")


def test_seaweedfs_master_and_s3_answer() -> None:
    status, body = http_get(required("CAP_SEAWEED_MASTER_URL") + "/cluster/status")
    assert status == 200 and b"IsLeader" in body
    status, _ = http_get(required("CAP_S3_ENDPOINT") + "/")
    assert status in {200, 403}, f"S3 endpoint answered HTTP {status}"


def test_keycloak_serves_the_master_realm() -> None:
    status, body = http_get(required("CAP_KEYCLOAK_URL") + "/realms/master")
    assert status == 200
    assert json.loads(body).get("realm") == "master"


# ------------------------------------------- WP-PLAT-003: planning profile ---


def test_temporal_serves_the_platform_namespace() -> None:
    """Temporal on PostgreSQL answers its frontend API and the namespace is registered."""
    namespace = required("CAP_TEMPORAL_NAMESPACE")
    status, body = http_get(
        f"{required('CAP_TEMPORAL_HTTP_URL')}/api/v1/namespaces/{namespace}"
    )
    assert status == 200, body[:300]
    info = json.loads(body)["namespaceInfo"]
    assert info["name"] == namespace
    assert info["state"] == "NAMESPACE_STATE_REGISTERED"


def test_temporal_persists_in_postgresql() -> None:
    """02: PostgreSQL persistence, no Cassandra; both Temporal databases carry a schema."""
    import psycopg

    with psycopg.connect(required("CAP_PG_DSN"), connect_timeout=10) as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT datname FROM pg_database WHERE datname LIKE 'temporal%'"
            )
        }
    assert names == {"temporal", "temporal_visibility"}
    base = required("CAP_PG_DSN").rsplit("/", 1)[0]
    for database in sorted(names):
        with psycopg.connect(f"{base}/{database}", connect_timeout=10) as connection:
            (version,) = connection.execute(
                "SELECT curr_version FROM schema_version"
            ).fetchone()
        assert version, f"{database}: no Temporal schema version"


# ------------------------------------------------ WP-PLAT-003: ai profile ---


def http_json(
    method: str,
    url: str,
    payload: object | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except urllib.error.URLError as exc:
        pytest.fail(f"{url} unreachable: {exc.reason}")


def test_qdrant_requires_its_api_key() -> None:
    base = required("CAP_QDRANT_URL")
    assert http_get(base + "/readyz")[0] == 200
    status, _ = http_json("GET", base + "/collections")
    assert status == 401, f"anonymous request answered HTTP {status}"


def test_qdrant_round_trips_a_vector() -> None:
    base = required("CAP_QDRANT_URL")
    key = {"api-key": required("CAP_QDRANT_API_KEY")}
    name = f"cap-smoke-{os.getpid()}"
    status, _ = http_json(
        "PUT",
        f"{base}/collections/{name}",
        {"vectors": {"size": 4, "distance": "Cosine"}},
        key,
    )
    assert status == 200
    try:
        status, _ = http_json(
            "PUT",
            f"{base}/collections/{name}/points?wait=true",
            {"points": [{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4]}]},
            key,
        )
        assert status == 200
        status, body = http_json(
            "POST",
            f"{base}/collections/{name}/points/query",
            {"query": [0.1, 0.2, 0.3, 0.4], "limit": 1},
            key,
        )
        assert status == 200 and body["result"]["points"][0]["id"] == 1
    finally:
        http_json("DELETE", f"{base}/collections/{name}", None, key)


def test_mlflow_tracks_in_postgresql_and_serves_artifacts_from_s3() -> None:
    """02: metadata in PostgreSQL, artifacts in SeaweedFS (proxied by the server)."""
    import psycopg

    base = required("CAP_MLFLOW_URL")
    assert http_get(base + "/health")[0] == 200
    name = f"cap-smoke-{os.getpid()}"
    status, body = http_json(
        "POST", f"{base}/api/2.0/mlflow/experiments/create", {"name": name}
    )
    assert status == 200, f"experiment create answered HTTP {status}"
    experiment = body["experiment_id"]
    try:
        payload = f"artifact {name}".encode()
        path = f"{base}/api/2.0/mlflow-artifacts/artifacts/{name}/smoke.txt"
        upload = urllib.request.Request(path, data=payload, method="PUT")
        with urllib.request.urlopen(upload, timeout=15) as response:
            assert response.status == 200
        assert http_get(path) == (200, payload)

        dsn = required("CAP_PG_DSN").rsplit("/", 1)[0] + "/mlflow"
        with psycopg.connect(dsn, connect_timeout=10) as connection:
            row = connection.execute(
                "SELECT name FROM experiments WHERE experiment_id = %s",
                (int(experiment),),
            ).fetchone()
        assert row == (name,)
    finally:
        http_json(
            "POST",
            f"{base}/api/2.0/mlflow/experiments/delete",
            {"experiment_id": experiment},
        )


# ------------------------------------------- WP-PLAT-003: platform realm ---


def token_request(secret: str) -> tuple[int, dict]:
    import base64
    from urllib.parse import urlencode

    url = (
        f"{required('CAP_KEYCLOAK_URL')}/realms/{required('CAP_KEYCLOAK_REALM')}"
        "/protocol/openid-connect/token"
    )
    client = required("CAP_KEYCLOAK_SMOKE_CLIENT_ID")
    request = urllib.request.Request(
        url,
        data=urlencode({"grant_type": "client_credentials"}).encode(),
        method="POST",
    )
    credentials = base64.b64encode(f"{client}:{secret}".encode()).decode()
    request.add_header("Authorization", f"Basic {credentials}")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def test_keycloak_issues_a_real_token_for_the_platform_realm() -> None:
    """DEP-010: the realm is deployed from code and the identity provider issues tokens."""
    import base64

    status, body = token_request(required("CAP_KEYCLOAK_SMOKE_CLIENT_SECRET"))
    assert status == 200 and body.get("token_type", "").lower() == "bearer"
    payload = body["access_token"].split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert claims["iss"].endswith(f"/realms/{required('CAP_KEYCLOAK_REALM')}")
    assert claims["azp"] == required("CAP_KEYCLOAK_SMOKE_CLIENT_ID")


def test_keycloak_rejects_a_wrong_client_secret() -> None:
    status, body = token_request("not-the-secret")
    assert status == 401 and "access_token" not in body
