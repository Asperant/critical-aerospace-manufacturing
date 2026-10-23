"""Overview query path: composition, freshness, world, pagination and transport."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fakes_overview import FakeReader, from_fixture, many_items
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from operations_bff.api import create_app
from operations_bff.composition import RuntimeSettings, build_app
from operations_bff.config import COOKIE_NAME, CookieSettings
from operations_bff.overview import OverviewService, StaleCursor
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
)
from test_composition import ENV
from test_contract_v1 import (
    BASE,
    check_composition,
    openapi,
    operations,
    registry,
    validator_for,
)

NOW = datetime(2026, 10, 23, 9, 0, 5, tzinfo=UTC)
OPERATOR = AuthenticatedIdentity("U-1", "Operator", ("ops-controller",), "ENV-1")
AUDITOR = AuthenticatedIdentity("U-2", "Auditor", ("auditor",), "ENV-1")
SRC = Path(__file__).resolve().parents[1] / "src" / "operations_bff"
WORLD = "W-SYNTHETIC-TEST"


class Rig:
    def __init__(self, *, identity: AuthenticatedIdentity = OPERATOR) -> None:
        self.core, self.twin, self.fixture = from_fixture()
        self.manager = SessionManager(InMemorySessionStore())
        self.service = OverviewService(self.core, [self.twin])
        self.app = create_app(
            self.manager,
            cookie=CookieSettings(same_site="lax"),
            clock=lambda: NOW,
            overview=self.service,
        )
        self.client = TestClient(
            self.app, base_url="https://testserver", follow_redirects=False
        )
        self.record = self.manager.create(identity, NOW)
        self.client.cookies.set(COOKIE_NAME, self.record.session_id)

    def get(self, query: str = f"world_id={WORLD}") -> Any:
        return self.client.get(f"/v1/overview?{query}")


def envelope_ok(body: dict[str, Any]) -> None:
    Draft202012Validator(
        {"$ref": BASE + "common.schema.json#/$defs/ErrorEnvelope"},
        registry=registry(),
    ).validate(body)


def test_composition_matches_the_contract_fixture() -> None:
    rig = Rig()
    response = rig.get()
    assert response.status_code == 200
    body = response.json()
    validator_for("overview-query.schema.json").validate(body)
    assert check_composition(body) == []
    fixture = rig.fixture
    assert body["needs_attention"] == fixture["needs_attention"]
    assert body["page"] == fixture["page"]
    for key in ("as_of", "generated_at", "freshness", "world", "sources"):
        assert body["meta"][key] == fixture["meta"][key], key
    assert response.headers["cache-control"] == "no-store"
    assert not {"status", "overall_status", "health"} & set(body)


def test_metadata_is_deterministic_and_independent_of_registration_order() -> None:
    first = Rig().get().json()["meta"]
    second = Rig().get().json()["meta"]
    assert first["revision"] == second["revision"]
    assert first["revision"].startswith("view-")
    assert first["correlation_id"] != second["correlation_id"]  # per request

    swapped = Rig()
    swapped.service = OverviewService(swapped.core, [swapped.twin])
    other = OverviewService(swapped.twin, [swapped.core])
    a = swapped.service.get(
        _query(), limit=50, cursor=None, now=NOW, correlation_id="c"
    )
    b = other.get(_query(), limit=50, cursor=None, now=NOW, correlation_id="c")
    assert a == b

    changed = Rig()
    changed.core.snapshot = _bump(changed.core)
    assert changed.get().json()["meta"]["revision"] != first["revision"]
    other_world = Rig().get("world_id=W-OTHER").json()["meta"]["revision"]
    assert other_world != first["revision"]


def _query(world: str = WORLD) -> Any:
    from operations_bff.actor import ActorContext
    from operations_bff.overview import OverviewQuery

    return OverviewQuery(
        world, None, None, None, ActorContext("U-1", (), "ENV-1", world), "C-TEST"
    )


def _bump(reader: FakeReader) -> Any:
    from dataclasses import replace

    return replace(reader.snapshot, revision=reader.snapshot.revision + "-next")


def test_world_and_actor_are_propagated_to_every_read_port() -> None:
    rig = Rig()
    response = rig.get(
        f"world_id={WORLD}&simulation_run_id=RUN-9&branch_id=BR-2"
        "&as_of=2026-10-23T08:30:00Z"
    )
    assert response.status_code == 200
    assert response.json()["meta"]["world"] == {
        "world_id": WORLD,
        "simulation_run_id": "RUN-9",
        "branch_id": "BR-2",
    }
    for reader in (rig.core, rig.twin):
        (query,) = reader.queries
        assert (query.world_id, query.simulation_run_id, query.branch_id) == (
            WORLD,
            "RUN-9",
            "BR-2",
        )
        assert query.as_of == datetime(2026, 10, 23, 8, 30, tzinfo=UTC)
        assert query.actor.actor_id == "U-1"
        assert query.actor.world_id == WORLD
        assert query.actor.derived_from == "SESSION"
    assert Rig().get().json()["meta"]["world"] == {"world_id": WORLD}


@pytest.mark.parametrize(
    "twin,core,expected",
    [
        ("STALE", "FRESH", "STALE"),
        ("FRESH", "DEGRADED", "DEGRADED"),
        ("FRESH", "FRESH", "FRESH"),
    ],
)
def test_freshness_is_the_least_fresh_source_and_kept_per_item(
    twin: str, core: str, expected: str
) -> None:
    rig = Rig()
    rig.twin.with_freshness(twin)
    rig.core.with_freshness(core)
    body = rig.get().json()
    validator_for("overview-query.schema.json").validate(body)
    assert body["meta"]["freshness"] == expected
    assert check_composition(body) == []
    by_source = {s["source"]: s["freshness"] for s in body["meta"]["sources"]}
    for item in body["needs_attention"]:
        assert item["freshness"] == by_source[item["source"]]


def test_as_of_is_the_oldest_source() -> None:
    rig = Rig()
    rig.core.snapshot = _shift(rig.core, minutes=-30)
    body = rig.get().json()
    assert body["meta"]["as_of"] == "2026-10-23T08:30:03Z"


def _shift(reader: FakeReader, minutes: int) -> Any:
    from dataclasses import replace

    return replace(
        reader.snapshot, as_of=reader.snapshot.as_of + timedelta(minutes=minutes)
    )


@pytest.mark.parametrize("down", ["core", "twin", "both"])
def test_any_unavailable_source_is_a_503_never_an_empty_overview(down: str) -> None:
    rig = Rig()
    if down in ("core", "both"):
        rig.core.down = True
    if down in ("twin", "both"):
        rig.twin.down = True
    response = rig.get()
    assert response.status_code == 503
    body = response.json()
    envelope_ok(body)
    assert body["category"] == "DEPENDENCY_UNAVAILABLE"
    assert "needs_attention" not in body
    expected = {
        "core": ["manufacturing-core"],
        "twin": ["digital-twin-service"],
        "both": ["digital-twin-service", "manufacturing-core"],
    }[down]
    assert body["details"]["unavailable_sources"] == expected
    assert body["details"]["required"] is (down != "twin")


def test_an_invalid_upstream_snapshot_is_treated_as_unavailable() -> None:
    from dataclasses import replace

    rig = Rig()
    rig.twin.snapshot = replace(rig.twin.snapshot, freshness="PRISTINE")
    assert rig.get().status_code == 503
    rig = Rig()
    rig.core.snapshot = replace(rig.core.snapshot, source="someone-else")
    assert rig.get().status_code == 503


def test_cursor_pagination_is_server_side_complete_and_stable() -> None:
    rig = Rig()
    many_items(rig.core, 5)  # 7 items in total
    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        query = f"world_id={WORLD}&limit=3" + (f"&cursor={cursor}" if cursor else "")
        body = rig.get(query).json()
        validator_for("overview-query.schema.json").validate(body)
        assert len(body["needs_attention"]) <= 3
        assert body["page"]["limit"] == 3
        seen += [i["item_id"] for i in body["needs_attention"]]
        pages += 1
        cursor = body["page"]["next_cursor"]
        if cursor is None:
            break
    assert pages == 3
    assert len(seen) == len(set(seen)) == 7
    full = [
        i["item_id"] for i in rig.get("world_id=" + WORLD).json()["needs_attention"]
    ]
    assert seen == full


def test_cursors_are_bound_to_the_view_and_validated() -> None:
    rig = Rig()
    many_items(rig.core, 5)
    cursor = rig.get(f"world_id={WORLD}&limit=2").json()["page"]["next_cursor"]
    rig.core.snapshot = _bump(rig.core)  # the view moved on
    stale = rig.get(f"world_id={WORLD}&limit=2&cursor={cursor}")
    assert stale.status_code == 400
    assert stale.json()["category"] == StaleCursor.category
    envelope_ok(stale.json())
    for bad in ("not-a-cursor", "e30", "eyJvIjotMSwidiI6Ing9fQ"):
        response = rig.get(f"world_id={WORLD}&cursor={bad}")
        assert response.status_code == 400
        assert response.json()["category"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "query",
    [
        "",
        "world_id=",
        f"world_id={WORLD}&limit=0",
        f"world_id={WORLD}&limit=101",
        f"world_id={WORLD}&limit=many",
        f"world_id={WORLD}&as_of=yesterday",
        f"world_id={WORLD}&as_of=2026-13-45T00:00:00Z",
        f"world_id={WORLD}&branch_id=",
    ],
)
def test_invalid_query_parameters_are_400(query: str) -> None:
    response = Rig().get(query)
    assert response.status_code == 400
    envelope_ok(response.json())


def test_unauthenticated_requests_get_401_before_anything_else() -> None:
    rig = Rig()
    rig.client.cookies.clear()
    for query in (f"world_id={WORLD}", "", "limit=0&as_of=bad"):
        response = rig.get(query)
        assert response.status_code == 401
        assert response.json()["category"] == "UNAUTHORIZED"
    assert rig.core.queries == [] and rig.twin.queries == []
    rig.client.cookies.set(COOKIE_NAME, "not-a-session")
    assert rig.get().status_code == 401


def test_the_bff_applies_no_role_based_filtering() -> None:
    as_operator = Rig(identity=OPERATOR).get().json()
    as_auditor = Rig(identity=AUDITOR).get().json()
    assert as_operator["needs_attention"] == as_auditor["needs_attention"]
    assert as_operator["meta"]["revision"] == as_auditor["meta"]["revision"]


def test_route_matches_the_contract_operation() -> None:
    rig = Rig()
    routes = {
        r.operation_id: (r.path, r.methods)  # type: ignore[attr-defined]
        for r in rig.app.routes
        if getattr(r, "operation_id", None)
    }
    path, method, op = operations()["getManufacturingOverview"]
    assert routes["getManufacturingOverview"] == (path, {method.upper()})
    assert op["security"] == [{"browserSession": []}]
    declared = {p["name"] for p in openapi()["paths"][path]["get"]["parameters"]}
    assert declared == {
        "world_id",
        "simulation_run_id",
        "branch_id",
        "as_of",
        "limit",
        "cursor",
    }
    # A GET never needs CSRF.
    assert rig.get().status_code == 200


def test_the_route_exists_only_when_a_service_is_supplied() -> None:
    manager = SessionManager(InMemorySessionStore())
    bare = create_app(manager, cookie=CookieSettings(same_site="lax"))
    record = manager.create(OPERATOR, datetime.now(UTC))
    client = TestClient(bare, base_url="https://testserver")
    client.cookies.set(COOKIE_NAME, record.session_id)
    assert client.get(f"/v1/overview?world_id={WORLD}").status_code == 404
    built = build_app(RuntimeSettings.from_environ(ENV))
    assert not [
        r
        for r in built.routes
        if getattr(r, "operation_id", "") == "getManufacturingOverview"
    ]


def test_duplicate_reader_names_are_refused() -> None:
    core, _, _ = from_fixture()
    with pytest.raises(ValueError):
        OverviewService(core, [core])


def test_the_query_path_has_no_database_or_broker_dependency() -> None:
    text = (SRC / "overview.py").read_text()
    for name in (
        "nats",
        "psycopg",
        "sqlalchemy",
        "redis",
        "valkey",
        "httpx",
        "fastapi",
        "starlette",
    ):
        assert not re.search(rf"^\s*(from|import)\s+{name}\b", text, re.M), name
    assert "authorize" not in text.lower() and "permission" not in text.lower()
