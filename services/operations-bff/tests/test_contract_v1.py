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
    "command.schema.json",
    "stream-message.schema.json",
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
    assert set(doc["paths"]) == {"/v1/overview", "/v1/commands"}
    ops = operations()
    assert set(ops) == {"getManufacturingOverview", "submitCommand"}
    for operation_id, (_, method, op) in ops.items():
        kind = op["x-bff-class"]
        assert {"QUERY": "get", "COMMAND": "post"}[kind] == method, operation_id
        assert any(code.startswith("2") for code in op["responses"]), operation_id
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


def test_normal_fixture_validates_and_is_composed_faithfully() -> None:
    fixture = load_json("overview-query.normal.json")
    validator_for("overview-query.schema.json").validate(fixture)
    assert check_composition(fixture) == []


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
