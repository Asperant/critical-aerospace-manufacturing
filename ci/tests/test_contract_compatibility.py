"""TEST-EVT-001-002: pure compatibility detector; no integration readiness claim."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from cap_contracts import ContractDeclaration, compare_contracts, compare_schemas


def schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
        "additionalProperties": False,
    }


def declaration() -> ContractDeclaration:
    path = (
        Path(__file__).resolve().parents[2]
        / "packages/contracts/registry/core.order-query.v1.json"
    )
    return ContractDeclaration.from_mapping(json.loads(path.read_text()))


def test_optional_addition_is_compatible_and_inputs_are_unchanged() -> None:
    old, new = schema(), schema()
    new["properties"]["note"] = {"type": "string"}
    snapshots = copy.deepcopy((old, new))
    assert compare_schemas(old, new).compatible
    assert (old, new) == snapshots
    assert compare_schemas(old, new) == compare_schemas(old, new)


def test_nested_optional_addition_is_compatible() -> None:
    old: dict[str, Any] = {"type": "array", "items": schema()}
    new = copy.deepcopy(old)
    new["items"]["properties"]["note"] = {"type": "string"}
    assert compare_schemas(old, new).compatible


@pytest.mark.parametrize(
    "change", ["remove", "unrequire", "require", "type", "unit", "enum", "constraint"]
)
def test_incompatible_changes_are_breaking(change: str) -> None:
    old, new = schema(), schema()
    if change == "remove":
        del new["properties"]["id"]
        new["required"] = []
    elif change == "unrequire":
        new["required"] = []
    elif change == "require":
        new["properties"]["note"] = {"type": "string"}
        new["required"].append("note")
    elif change == "type":
        new["properties"]["id"]["type"] = "integer"
    elif change == "unit":
        old["properties"]["id"]["description"] = "length in mm"
        new["properties"]["id"]["description"] = "length in inches"
    elif change == "enum":
        old["properties"]["id"]["enum"] = ["A", "B"]
        new["properties"]["id"]["enum"] = ["A"]
    else:
        new["properties"]["id"]["minLength"] = 2
    result = compare_schemas(old, new)
    assert not result.compatible
    assert result.breaking
    assert not result.unverifiable


@pytest.mark.parametrize(
    "bad",
    [
        None,
        True,
        [],
        {"type": "invalid"},
        {},
        {"$ref": "https://example.test/schema"},
        {"type": "string", "format": "unknown"},
        {"type": "object", "required": ["missing"]},
        {"type": "object", "anyOf": [schema()]},
        {"type": "string", "$schema": "http://json-schema.org/draft-07/schema#"},
    ],
)
def test_unverifiable_schemas_fail_closed_on_either_side(bad: object) -> None:
    for before, after in ((bad, schema()), (schema(), bad), (bad, bad)):
        result = compare_schemas(before, after)
        assert not result.compatible
        assert result.unverifiable


@pytest.mark.parametrize(
    "field,value",
    [
        ("canonical_producer", "vision"),
        ("semantic_owner", "another owner"),
        ("authority_level", "execution authority"),
        ("sync_semantics", "ASYNC"),
        ("semantics", {"revision": "numeric"}),
        ("purpose", "repurposed"),
    ],
)
def test_contract_authority_and_semantics_changes_are_breaking(
    field: str, value: object
) -> None:
    old = declaration()
    new = replace(old, **{field: value})
    result = compare_contracts(
        old,
        new,
        old_output_schema=schema(),
        new_output_schema=schema(),
        old_input_schema=schema(),
        new_input_schema=schema(),
    )
    assert result.breaking
    assert not result.compatible


def test_new_major_does_not_hide_breaking_change() -> None:
    old = declaration()
    new = replace(
        old, contract_id="core.order-query.v2", version=2, canonical_producer="vision"
    )
    result = compare_contracts(
        old,
        new,
        old_output_schema=schema(),
        new_output_schema=schema(),
        old_input_schema=schema(),
        new_input_schema=schema(),
    )
    assert result.breaking


def test_contract_input_changes_are_checked() -> None:
    old = declaration()
    before, after = schema(), schema()
    after["properties"]["id"]["type"] = "integer"
    result = compare_contracts(
        old,
        old,
        old_output_schema=schema(),
        new_output_schema=schema(),
        old_input_schema=before,
        new_input_schema=after,
    )
    assert result.breaking
    assert all(item.startswith("input") for item in result.breaking)


def test_missing_declared_input_fails_closed() -> None:
    old = declaration()
    result = compare_contracts(
        old, old, old_output_schema=schema(), new_output_schema=schema()
    )
    assert result.unverifiable
    assert not result.compatible


def test_optional_output_addition_with_same_contract_is_compatible() -> None:
    old = replace(declaration(), input_schema=None)
    before, after = schema(), schema()
    after["properties"]["note"] = {"type": "string"}
    assert compare_contracts(
        old, old, old_output_schema=before, new_output_schema=after
    ).compatible


def test_unrelated_contract_families_fail_closed() -> None:
    old = replace(declaration(), input_schema=None)
    new = replace(old, contract_id="other.query.v1")
    assert compare_contracts(
        old, new, old_output_schema=schema(), new_output_schema=schema()
    ).unverifiable


@pytest.mark.parametrize(
    "bad",
    [
        {"type": "number", "const": float("nan")},
        {"type": "string", "const": object()},
        {1: "unknown"},
    ],
)
def test_non_json_inputs_fail_closed(bad: object) -> None:
    assert compare_schemas(bad, schema()).unverifiable


def test_boolean_and_numeric_constants_are_distinct() -> None:
    result = compare_schemas(
        {"type": ["boolean", "integer"], "const": True},
        {"type": ["boolean", "integer"], "const": 1},
    )
    assert result.breaking
