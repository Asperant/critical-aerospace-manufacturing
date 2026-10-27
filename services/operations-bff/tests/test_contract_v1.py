"""Structure, resolution, boundary and freshness checks for the BFF v1 contract."""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "v1"
BASE = "https://contracts.cap.invalid/operations-bff/v1/"
SCHEMA_FILES = (
    "common.schema.json",
    "overview-query.schema.json",
    "facility-state.schema.json",
    "command.schema.json",
    "stream-message.schema.json",
    "session.schema.json",
)
FRESHNESS_ORDER = {"FRESH": 0, "DEGRADED": 1, "STALE": 2}
FORBIDDEN_NAME_PARTS = {
    "broker", "nats", "jetstream", "kafka", "amqp", "sql", "postgres",
    "database", "db", "dsn", "outbox", "topic", "queue",
}  # fmt: skip
ACTOR_NAME_PARTS = {"actor", "user", "role", "roles", "permission", "permissions"}


def load_json(name: str) -> Any:
    return json.loads((CONTRACTS / name).read_text("utf-8"))


def schemas() -> dict[str, Any]:
    return {name: load_json(name) for name in SCHEMA_FILES}


def registry() -> Registry[Any]:
    reg: Registry[Any] = Registry()
    for name, schema in schemas().items():
        reg = reg.with_resource(
            BASE + name, Resource.from_contents(schema, DRAFT202012)
        )
    return reg


def openapi() -> dict[str, Any]:
    text = (CONTRACTS / "operations-bff.openapi.yaml").read_text("utf-8")
    return cast(dict[str, Any], yaml.safe_load(text))


def validator_for(ref: str) -> Draft202012Validator:
    """Validator for a contract-relative $ref such as ``command.schema.json#/..``."""
    return Draft202012Validator({"$ref": BASE + ref}, registry=registry())


def walk(
    node: Any, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], Any]]:
    yield path, node
    if isinstance(node, dict):
        for key, value in cast(dict[str, Any], node).items():
            yield from walk(value, (*path, key))
    elif isinstance(node, list):
        for index, value in enumerate(cast(list[Any], node)):
            yield from walk(value, (*path, str(index)))


def operations() -> dict[str, tuple[str, str, dict[str, Any]]]:
    found: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for path, item in openapi()["paths"].items():
        for method, op in item.items():
            found[op["operationId"]] = (path, method, op)
    return found


def name_parts(name: str) -> set[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return {part for part in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if part}


def property_names() -> Iterator[str]:
    docs: list[Any] = [*schemas().values(), openapi()]
    for doc in docs:
        for path, node in walk(doc):
            if path and path[-1] == "properties" and isinstance(node, dict):
                yield from cast(dict[str, Any], node)


def check_composition(doc: dict[str, Any]) -> list[str]:
    """Semantic rules JSON Schema cannot express: faithful freshness labelling."""
    meta = doc["meta"]
    sources = {s["source"]: s for s in meta["sources"]}
    errors: list[str] = []
    least = max((s["freshness"] for s in sources.values()), key=FRESHNESS_ORDER.get)  # type: ignore[arg-type]
    if meta["freshness"] != least:
        errors.append("meta.freshness is not the least-fresh source freshness")
    if meta["as_of"] != min(s["as_of"] for s in sources.values()):
        errors.append("meta.as_of is not the oldest source as_of")
    for item in doc["needs_attention"]:
        source = sources.get(item["source"])
        if source is None:
            errors.append(f"{item['item_id']}: unknown source")
        elif (item["source_revision"], item["freshness"]) != (
            source["revision"],
            source["freshness"],
        ):
            errors.append(f"{item['item_id']}: revision/freshness differs from source")
    return errors


def test_schemas_are_valid_draft_2020_12() -> None:
    for name, schema in schemas().items():
        Draft202012Validator.check_schema(schema)
        assert schema["$id"] == BASE + name


def test_every_ref_resolves() -> None:
    reg = registry()
    documents: list[tuple[str, Any]] = [
        ("operations-bff.openapi.yaml", openapi()),
        *schemas().items(),
    ]
    resolved = 0
    for name, doc in documents:
        base = BASE + name
        for _, node in walk(doc):
            if not isinstance(node, dict) or "$ref" not in node:
                continue
            ref = cast(str, cast(dict[str, Any], node)["$ref"])
            if ref.startswith("#/components/"):
                target: Any = openapi()
                for part in ref.removeprefix("#/").split("/"):
                    target = target[part]
            else:
                target = reg.resolver(base_uri=base).lookup(ref).contents
            assert target is not None, (name, ref)
            resolved += 1
    assert resolved > 10


def test_openapi_structure() -> None:
    doc = openapi()
    assert doc["openapi"] == "3.1.0"
    assert doc["info"]["version"] == "1.0.0"
    assert "servers" not in doc
    assert set(doc["paths"]) == {
        "/v1/overview",
        "/v1/facility-state",
        "/v1/commands",
        "/v1/session",
        "/v1/session/login",
        "/v1/session/callback",
        "/v1/session/logout",
    }
    ops = operations()
    assert set(ops) == {
        "getManufacturingOverview",
        "getFacilityState",
        "submitCommand",
        "getSession",
        "startLogin",
        "completeLogin",
        "logout",
    }
    for operation_id, (_, method, op) in ops.items():
        kind = op["x-bff-class"]
        if kind in ("QUERY", "COMMAND"):
            assert {"QUERY": "get", "COMMAND": "post"}[kind] == method, operation_id
        assert kind in ("QUERY", "COMMAND", "SESSION"), operation_id
        assert any(code[0] in "23" for code in op["responses"]), operation_id
    assert "StreamMessage" in doc["components"]["schemas"]


def test_forbidden_browser_surfaces_are_absent() -> None:
    doc = openapi()
    names = [*doc["paths"]]
    names += [op["operationId"] for _, _, op in operations().values()]
    for _, node in walk(doc):
        if isinstance(node, dict) and "name" in node and "in" in node:
            names.append(cast(str, cast(dict[str, Any], node)["name"]))
    names += list(property_names())
    for name in names:
        assert not name_parts(name) & FORBIDDEN_NAME_PARTS, name
    for _, node in walk(doc):
        if isinstance(node, str):
            assert not re.match(r"(nats|amqp|kafka|postgres\w*|ws|wss)://", node)
    # Streaming is a boundary extension, not a path, and names no transport.
    stream = doc["x-bff-streaming"]
    assert stream["transport"] == "UNDECIDED"
    assert operations()[stream["snapshot_operation_id"]][2]["x-bff-class"] == "QUERY"


def test_command_boundary_has_no_actor_or_completion() -> None:
    request = load_json("command.schema.json")["$defs"]["CommandRequest"]
    assert not any(name_parts(n) & ACTOR_NAME_PARTS for n in request["properties"])
    assert request["additionalProperties"] is False
    outcomes = load_json("command.schema.json")["$defs"]["CommandReceipt"][
        "properties"
    ]["outcome"]["enum"]
    assert outcomes == ["ACCEPTED", "REJECTED", "CONFLICT", "STALE"]


def test_all_object_shapes_are_closed() -> None:
    for name, schema in schemas().items():
        for path, node in walk(schema):
            if (
                isinstance(node, dict)
                and "properties" in node
                and "$ref" not in node  # refinement of an already closed shape
                and path[-1:] != ("properties",)
            ):
                assert node.get("additionalProperties") is False, (name, path)


def test_overview_has_no_synthesized_overall_status() -> None:
    forbidden = {"status", "overall", "health", "state"}
    overview = load_json("overview-query.schema.json")
    for path, node in walk(overview):
        if path[-1:] == ("properties",) and isinstance(node, dict):
            for name in cast(dict[str, Any], node):
                assert not name_parts(name) & forbidden, name


def test_facility_state_keeps_independent_state_dimensions() -> None:
    state = load_json("facility-state.schema.json")
    lot = state["$defs"]["LotState"]["properties"]
    assert {"lifecycle_state", "execution_state", "hold_state"} <= set(lot)
    assert "state" not in lot


def test_normal_fixture_validates_and_is_composed_faithfully() -> None:
    fixture = load_json("overview-query.normal.json")
    validator_for("overview-query.schema.json").validate(fixture)
    assert check_composition(fixture) == []


def test_facility_state_fixture_validates() -> None:
    validator_for("facility-state.schema.json").validate(
        load_json("facility-state.normal.json")
    )


@pytest.mark.parametrize("field", ["revision", "as_of", "generated_at", "freshness"])
def test_query_meta_requires_freshness_semantics(field: str) -> None:
    fixture = load_json("overview-query.normal.json")
    del fixture["meta"][field]
    with pytest.raises(ValidationError):
        validator_for("overview-query.schema.json").validate(fixture)


def test_query_response_must_carry_meta() -> None:
    schema = load_json("overview-query.schema.json")
    assert "meta" in schema["required"]
    assert schema["properties"]["meta"]["$ref"].endswith("#/$defs/QueryMeta")
    ok = operations()["getManufacturingOverview"][2]["responses"]["200"]
    assert ok["content"]["application/json"]["schema"] == {
        "$ref": "overview-query.schema.json"
    }
    for mutate in (
        lambda d: d["meta"].update(freshness="FRESHISH"),
        lambda d: d["meta"].update(as_of="2026-10-23 09:00:00"),
        lambda d: d["needs_attention"][0].update(epistemic_class="TRUE"),
        lambda d: d.update(overall_status="OK"),
        lambda d: d["page"].update(limit=1000),
    ):
        fixture = copy.deepcopy(load_json("overview-query.normal.json"))
        mutate(fixture)
        with pytest.raises(ValidationError):
            validator_for("overview-query.schema.json").validate(fixture)


def test_composition_rejects_optimistic_freshness() -> None:
    fixture = load_json("overview-query.normal.json")
    fixture["meta"]["freshness"] = "FRESH"
    assert check_composition(fixture)
    fixture = load_json("overview-query.normal.json")
    fixture["needs_attention"][0]["freshness"] = "FRESH"
    assert check_composition(fixture)


def test_stream_messages_are_revision_aware_and_resync_via_query() -> None:
    stamp = "2026-10-23T09:00:06Z"
    world = {"world_id": "W-SYNTHETIC-TEST"}
    delta = {
        "contract_version": "bff.stream-message.v1",
        "message_type": "DELTA",
        "world": world,
        "from_revision": "view-0042",
        "to_revision": "view-0043",
        "generated_at": stamp,
        "changes": [],
    }
    resync = {
        "contract_version": "bff.stream-message.v1",
        "message_type": "RESYNC_REQUIRED",
        "connection_state": "RESYNCING",
        "reason": "REVISION_GAP",
        "resync_operation_id": "getManufacturingOverview",
        "generated_at": stamp,
    }
    validator = validator_for("stream-message.schema.json")
    validator.validate(delta)
    validator.validate(resync)
    assert resync["resync_operation_id"] in operations()
    del delta["from_revision"]
    with pytest.raises(ValidationError):
        validator.validate(delta)


PROTECTED = {
    "getManufacturingOverview": False,
    "submitCommand": True,
    "getSession": False,
    "logout": True,
}
ANONYMOUS = {"startLogin", "completeLogin"}
TOKEN_NAME_PARTS = {"access", "refresh", "bearer", "jwt", "password", "secret"}


def test_protected_operations_declare_session_and_csrf() -> None:
    doc = openapi()
    schemes = doc["components"]["securitySchemes"]
    assert set(schemes) == {"browserSession", "csrfToken"}
    assert schemes["browserSession"]["type"] == "apiKey"
    assert schemes["browserSession"]["in"] == "cookie"
    assert schemes["csrfToken"]["in"] == "header"
    cookie = schemes["browserSession"]["x-cookie-attributes"]
    assert cookie["http_only"] is True
    assert cookie["secure"] is True
    assert cookie["bounded_expiry"] is True
    assert set(cookie["same_site_one_of"]) <= {"Strict", "Lax"}
    ops = operations()
    for operation_id, needs_csrf in PROTECTED.items():
        security = ops[operation_id][2]["security"]
        expected = {"browserSession": []} | ({"csrfToken": []} if needs_csrf else {})
        assert security == [expected], operation_id
    assert {o for o, (_, _, op) in ops.items() if op["security"] == []} == ANONYMOUS
    # Every state-changing request is CSRF protected.
    for operation_id, (_, method, op) in ops.items():
        if method == "post":
            assert {"csrfToken": []}.items() <= op["security"][0].items(), operation_id
    # No bearer or OAuth scheme and no token field is exposed to the browser.
    assert all(s["type"] == "apiKey" for s in schemes.values())
    for name in property_names():
        assert not name_parts(name) & TOKEN_NAME_PARTS, name


def test_anonymous_behaviour_is_401_unauthorized_without_data() -> None:
    ops = operations()
    reg = registry()
    envelope = {
        "error_code": "SESSION_REQUIRED",
        "category": "UNAUTHORIZED",
        "message": "Authentication required",
        "retryable": False,
        "correlation_id": "C-SYNTHETIC-0002",
    }
    unauthorized = Draft202012Validator(
        {"$ref": BASE + "common.schema.json#/$defs/UnauthorizedError"}, registry=reg
    )
    unauthorized.validate(envelope)
    for bad in ("FORBIDDEN", "NOT_FOUND"):
        with pytest.raises(ValidationError):
            unauthorized.validate({**envelope, "category": bad})
    for operation_id in PROTECTED:
        responses = ops[operation_id][2]["responses"]
        assert responses["401"] == {"$ref": "#/components/responses/Unauthorized"}
        assert "302" not in responses  # never a redirect for a missing session
    components = openapi()["components"]["responses"]
    assert components["Unauthorized"]["content"]["application/json"]["schema"] == {
        "$ref": "common.schema.json#/$defs/UnauthorizedError"
    }
    assert components["Forbidden"]["content"]["application/json"]["schema"] == {
        "$ref": "common.schema.json#/$defs/ForbiddenError"
    }
    for operation_id in ("submitCommand", "logout"):
        assert ops[operation_id][2]["responses"]["403"] == {
            "$ref": "#/components/responses/Forbidden"
        }
    # OIDC entry points are anonymous by design and return only redirects.
    assert set(ops["startLogin"][2]["responses"]) >= {"302"}
    assert "200" not in ops["completeLogin"][2]["responses"]


def command(parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": "bff.command.v1",
        "command_id": "CMD-1",
        "command_type": "isolate-machine",
        "world": {"world_id": "W-SYNTHETIC-TEST"},
        "target": {"entity_type": "Machine", "entity_id": "E-CNC"},
        "parameters": parameters,
    }


def test_actor_cannot_be_injected_through_command_payloads() -> None:
    validator = validator_for("command.schema.json#/$defs/CommandRequest")
    validator.validate(command({"reason": "vibration", "limits": [{"max": 3}]}))
    injected: list[dict[str, Any]] = [
        {"actor_id": "U-ADMIN"},
        {"Actor": {"id": "U-ADMIN"}},
        {"nested": {"user": "U-ADMIN"}},
        {"items": [{"roles": ["admin"]}]},
        {"PERMISSIONS": ["all"]},
        {"session_id": "S-1"},
        {"identity": "x"},
    ]
    for parameters in injected:
        with pytest.raises(ValidationError):
            validator.validate(command(parameters))
    for top_level in ("actor", "actor_id", "user_id", "roles", "acted_as"):
        with pytest.raises(ValidationError):
            validator.validate({**command({}), top_level: "U-ADMIN"})
    for param in openapi()["paths"]["/v1/overview"]["get"]["parameters"]:
        assert not name_parts(param["name"]) & ACTOR_NAME_PARTS


def test_actor_context_is_session_derived_only() -> None:
    context = openapi()["x-bff-actor-context"]
    assert context["source"] == "SESSION"
    assert context["browser_supplied_fields"] == []
    assert set(context["propagated_to"]) == {"manufacturing-core", "automation-service"}


def test_session_fixture_and_exposed_actor_fields_are_required() -> None:
    fixture = load_json("session.normal.json")
    validator = validator_for("session.schema.json")
    validator.validate(fixture)
    for field in ("actor", "environment_id", "expires_at", "csrf_token"):
        broken = {k: v for k, v in fixture.items() if k != field}
        with pytest.raises(ValidationError):
            validator.validate(broken)
    for field in ("actor_id", "display_name", "roles", "derived_from"):
        broken = copy.deepcopy(fixture)
        del broken["actor"][field]
        with pytest.raises(ValidationError):
            validator.validate(broken)
    for mutate in (
        lambda d: d["actor"].update(derived_from="CLIENT"),
        lambda d: d["actor"].update(roles=["a", "a"]),
        lambda d: d.update(access_token="x"),
        lambda d: d["actor"].update(permissions=["all"]),
    ):
        broken = copy.deepcopy(fixture)
        mutate(broken)
        with pytest.raises(ValidationError):
            validator.validate(broken)


def test_command_receipt_echoes_session_actor() -> None:
    receipt = {
        "contract_version": "bff.command-receipt.v1",
        "command_id": "CMD-1",
        "outcome": "ACCEPTED",
        "acted_as": {"actor_id": "U-SYNTHETIC-01", "derived_from": "SESSION"},
        "correlation_id": "C-SYNTHETIC-0003",
        "received_at": "2026-10-23T09:00:07Z",
    }
    validator = validator_for("command.schema.json#/$defs/CommandReceipt")
    validator.validate(receipt)
    del receipt["acted_as"]
    with pytest.raises(ValidationError):
        validator.validate(receipt)
