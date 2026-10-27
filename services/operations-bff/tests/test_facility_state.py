"""Twin facility-state query: scope, freshness, validation and transport."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fakes_state import from_fixture, with_freshness
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from operations_bff.api import create_app
from operations_bff.config import COOKIE_NAME, CookieSettings
from operations_bff.facility_state import FacilityStateService
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
)
from test_contract_v1 import BASE, load_json, operations, validator_for

NOW = datetime(2026, 10, 23, 9, 0, 5, tzinfo=UTC)
WORLD = "W-SYNTHETIC-TEST"
OPERATOR = AuthenticatedIdentity("U-1", "Operator", ("ops-controller",), "ENV-1")
AUDITOR = AuthenticatedIdentity("U-2", "Auditor", ("auditor",), "ENV-1")


class Rig:
    def __init__(self, *, identity: AuthenticatedIdentity = OPERATOR) -> None:
        self.reader, self.fixture = from_fixture()
        self.manager = SessionManager(InMemorySessionStore())
        self.app = create_app(
            self.manager,
            cookie=CookieSettings(same_site="lax"),
            clock=lambda: NOW,
            facility_state=FacilityStateService(self.reader),
        )
        self.client = TestClient(
            self.app, base_url="https://testserver", follow_redirects=False
        )
        record = self.manager.create(identity, NOW)
        self.client.cookies.set(COOKIE_NAME, record.session_id)

    def get(self, query: str = f"world_id={WORLD}") -> Any:
        return self.client.get(f"/v1/facility-state?{query}")


def test_twin_state_composes_the_fixture_without_synthesizing_status() -> None:
    rig = Rig()
    response = rig.get()
    assert response.status_code == 200
    body = response.json()
    validator_for("facility-state.schema.json").validate(body)
    assert body["facility"] == rig.fixture["facility"]
    assert body["meta"]["world"] == rig.fixture["meta"]["world"]
    assert "status" not in body
    assert body["meta"]["freshness"] == "FRESH"


def test_world_branch_as_of_and_actor_are_propagated_to_the_twin_port() -> None:
    rig = Rig()
    response = rig.get(
        f"world_id={WORLD}&simulation_run_id=RUN-9&branch_id=BR-2"
        "&as_of=2026-10-23T08:30:00Z"
    )
    assert response.status_code == 200
    (query,) = rig.reader.queries
    assert (query.world_id, query.simulation_run_id, query.branch_id) == (
        WORLD,
        "RUN-9",
        "BR-2",
    )
    assert query.as_of == datetime(2026, 10, 23, 8, 30, tzinfo=UTC)
    assert query.actor.actor_id == "U-1"
    assert query.actor.world_id == WORLD
    assert response.json()["meta"]["world"] == {
        "world_id": WORLD,
        "simulation_run_id": "RUN-9",
        "branch_id": "BR-2",
    }


def test_staleness_is_visible_on_meta_and_each_entity() -> None:
    rig = Rig()
    with_freshness(rig.reader, "STALE")
    body = rig.get().json()
    validator_for("facility-state.schema.json").validate(body)
    assert body["meta"]["freshness"] == "STALE"
    assert body["meta"]["sources"][0]["freshness"] == "STALE"
    # The fixture's entities keep their source-reported labels; the BFF does not
    # silently rewrite entity freshness into a more optimistic value.
    assert {item["freshness"] for item in body["facility"]["equipment"]} == {"FRESH"}


def test_unavailable_or_invalid_twin_state_is_503_not_empty_data() -> None:
    rig = Rig()
    rig.reader.down = True
    response = rig.get()
    assert response.status_code == 503
    assert response.json()["details"] == {
        "unavailable_sources": ["digital-twin-service"],
        "required": True,
    }
    rig = Rig()
    rig.reader.snapshot = rig.reader.snapshot.__class__(
        **{**rig.reader.snapshot.__dict__, "source": "other"}
    )
    response = rig.get()
    assert response.status_code == 503
    assert "facility" not in response.json()


def test_unauthenticated_requests_do_not_reach_the_twin() -> None:
    rig = Rig()
    rig.client.cookies.clear()
    response = rig.get()
    assert response.status_code == 401
    assert rig.reader.queries == []


def test_facility_state_is_not_role_filtered() -> None:
    assert (
        Rig(identity=OPERATOR).get().json()["facility"]
        == Rig(identity=AUDITOR).get().json()["facility"]
    )


def test_route_matches_the_contract_operation() -> None:
    rig = Rig()
    routes = {
        r.operation_id: (r.path, r.methods)  # type: ignore[attr-defined]
        for r in rig.app.routes
        if getattr(r, "operation_id", None)
    }
    path, method, operation = operations()["getFacilityState"]
    assert routes["getFacilityState"] == (path, {method.upper()})
    assert operation["security"] == [{"browserSession": []}]
    response_statuses = {"200", "400", "401", "403", "503"}
    assert response_statuses <= set(operation["responses"])


def test_fixture_schema_is_closed_and_resolved() -> None:
    schema = validator_for("facility-state.schema.json")
    schema.validate(Rig().fixture)
    assert load_json("facility-state.schema.json")["$id"] == (
        BASE + "facility-state.schema.json"
    )
    Draft202012Validator.check_schema(schema.schema)
