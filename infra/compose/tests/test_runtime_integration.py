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
    status, body = http_get(f"{required('CAP_TEMPORAL_HTTP_URL')}/api/v1/namespaces/{namespace}")
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
