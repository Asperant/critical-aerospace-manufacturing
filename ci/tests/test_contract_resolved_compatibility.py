"""TEST-EVT-001-004: effective local-definition compatibility, no readiness claim."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from cap_contracts import (
    CompatibilityResult,
    ContractDeclaration,
    FileRef,
    compare_contracts,
    compare_schema_files,
    compare_schemas,
)

PACKAGE = "packages/contracts/schemas/"


def record() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
        "additionalProperties": False,
    }


def referenced(shape: dict[str, Any]) -> dict[str, Any]:
    return {"$defs": {"Record": shape}, "$ref": "#/$defs/Record"}


def write(root: Path, name: str, value: object) -> FileRef:
    path = root / PACKAGE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    return FileRef(PACKAGE + name, hashlib.sha256(raw).hexdigest())


def compare_files(
    old_root: Path, new_root: Path, before: dict[str, Any], after: dict[str, Any]
):
    old_leaf = write(old_root, "leaf.json", referenced(before))
    new_leaf = write(new_root, "leaf.json", referenced(after))
    old = write(old_root, "root.json", {"$ref": "leaf.json#/$defs/Record"})
    new = write(new_root, "root.json", {"$ref": "leaf.json#/$defs/Record"})
    return compare_schema_files(
        old,
        new,
        old_repo_root=old_root,
        new_repo_root=new_root,
        old_schema_refs=(old_leaf,),
        new_schema_refs=(new_leaf,),
    )


def test_unchanged_definition_compares_effective_shape_without_mutation() -> None:
    old = referenced(record())
    new = copy.deepcopy(old)
    snapshot = copy.deepcopy((old, new))
    assert compare_schemas(old, new).compatible
    assert compare_schemas(old, record()).compatible
    assert compare_schemas(old, new) == compare_schemas(old, new)
    assert (old, new) == snapshot


@pytest.mark.parametrize("files", [False, True])
def test_optional_referenced_field_is_nonbreaking(tmp_path: Path, files: bool) -> None:
    old, new = record(), record()
    new["properties"]["note"] = {"type": "string"}
    result = (
        compare_files(tmp_path / "old", tmp_path / "new", old, new)
        if files
        else compare_schemas(referenced(old), referenced(new))
    )
    assert result.compatible


@pytest.mark.parametrize("files", [False, True])
@pytest.mark.parametrize("change", ["remove", "type", "semantic", "required", "enum"])
def test_breaking_change_inside_referenced_definition(
    tmp_path: Path, files: bool, change: str
) -> None:
    old, new = record(), record()
    if change == "remove":
        new["properties"].pop("id")
        new["required"] = []
    elif change == "type":
        new["properties"]["id"]["type"] = "integer"
    elif change == "semantic":
        old["properties"]["id"]["description"] = "immutable component identity"
        new["properties"]["id"]["description"] = "mutable batch identity"
    elif change == "required":
        new["properties"]["note"] = {"type": "string"}
        new["required"].append("note")
    else:
        old["properties"]["id"]["enum"] = ["A", "B"]
        new["properties"]["id"]["enum"] = ["A"]
    result = (
        compare_files(tmp_path / "old", tmp_path / "new", old, new)
        if files
        else compare_schemas(referenced(old), referenced(new))
    )
    assert result.breaking
    assert not result.compatible
    assert not result.unverifiable
    assert any(
        "/properties/id" in reason or "required" in reason for reason in result.breaking
    )


@pytest.mark.parametrize("different_shape", [False, True])
def test_changed_reference_target_compares_actual_shape(different_shape: bool) -> None:
    alternative = record()
    if different_shape:
        alternative["properties"]["id"]["type"] = "integer"
    old = {"$defs": {"A": record(), "B": alternative}, "$ref": "#/$defs/A"}
    new = copy.deepcopy(old)
    new["$ref"] = "#/$defs/B"
    result = compare_schemas(old, new)
    assert result.compatible is not different_shape
    assert bool(result.breaking) is different_shape


def test_nested_internal_references_detect_leaf_change() -> None:
    old: dict[str, Any] = {
        "$defs": {
            "Id": {"type": "string"},
            "Record": {"type": "object", "properties": {"id": {"$ref": "#/$defs/Id"}}},
        },
        "type": "array",
        "items": {"$ref": "#/$defs/Record"},
    }
    new = copy.deepcopy(old)
    assert compare_schemas(old, new).compatible
    new["$defs"]["Id"]["type"] = "integer"
    result = compare_schemas(old, new)
    assert result.breaking == ("/items/properties/id/type: value or semantics changed",)


def test_nested_pinned_package_references_compare_leaf_shape(tmp_path: Path) -> None:
    roots = (tmp_path / "old", tmp_path / "new")
    entries: list[FileRef] = []
    approvals: list[tuple[FileRef, ...]] = []
    for root in roots:
        leaf = write(root, "leaf.json", record())
        middle = write(
            root, "middle.json", {"$defs": {"Record": {"$ref": "leaf.json"}}}
        )
        entries.append(
            write(
                root,
                "root.json",
                {"type": "array", "items": {"$ref": "middle.json#/$defs/Record"}},
            )
        )
        approvals.append((leaf, middle))

    def compare() -> CompatibilityResult:
        return compare_schema_files(
            entries[0],
            entries[1],
            old_repo_root=roots[0],
            new_repo_root=roots[1],
            old_schema_refs=approvals[0],
            new_schema_refs=approvals[1],
        )

    assert compare().compatible
    new_shape = record()
    new_shape["properties"]["note"] = {"type": "string"}
    approvals[1] = (write(roots[1], "leaf.json", new_shape), approvals[1][1])
    assert compare().compatible
    new_shape["properties"]["id"]["type"] = "integer"
    approvals[1] = (write(roots[1], "leaf.json", new_shape), approvals[1][1])
    assert compare().breaking


@pytest.mark.parametrize(
    "bad",
    [
        {"$ref": "#/$defs/missing"},
        {"$ref": "#"},
        {"$ref": "leaf.json"},
        {"$ref": "https://example.test/schema"},
        {"$defs": {"Id": {"type": "invalid"}}, "$ref": "#/$defs/Id"},
        {"default": {"type": "invalid"}, "$ref": "#/default"},
        {
            "$defs": {"A": {"$ref": "#/$defs/B"}, "B": {"$ref": "#/$defs/A"}},
            "$ref": "#/$defs/A",
        },
    ],
)
def test_unresolvable_references_never_compare_equal(bad: dict[str, Any]) -> None:
    for old, new in ((bad, bad), (bad, record()), (record(), bad)):
        result = compare_schemas(old, new)
        assert result.unverifiable
        assert not result.compatible


@pytest.mark.parametrize(
    "failure",
    [
        "unapproved",
        "missing",
        "invalid",
        "cycle",
        "drift",
        "root_drift",
        "escape",
        "remote",
    ],
)
def test_file_comparison_preserves_resolution_and_hash_failures(
    tmp_path: Path, failure: str
) -> None:
    leaf = write(tmp_path, "leaf.json", record())
    target = "leaf.json"
    pins = (leaf,)
    if failure == "unapproved":
        pins = ()
    elif failure == "missing":
        (tmp_path / leaf.path).unlink()
    elif failure == "invalid":
        pins = (write(tmp_path, "leaf.json", {"type": "invalid"}),)
    elif failure == "cycle":
        pins = (write(tmp_path, "leaf.json", {"$ref": "root.json"}),)
    elif failure == "drift":
        write(tmp_path, "leaf.json", {"type": "integer"})
    elif failure == "escape":
        target = "../leaf.json"
    elif failure == "remote":
        target = "https://example.test/schema"
    root = write(tmp_path, "root.json", {"$ref": target})
    if failure == "root_drift":
        write(tmp_path, "root.json", record())
    result = compare_schema_files(
        root,
        root,
        old_repo_root=tmp_path,
        new_repo_root=tmp_path,
        old_schema_refs=pins,
        new_schema_refs=pins,
    )
    assert result.unverifiable
    assert not result.compatible
    expected = {
        "unapproved": "SCHEMA_REF_UNAPPROVED",
        "missing": "FILE_MISSING",
        "invalid": "SCHEMA_INVALID",
        "cycle": "SCHEMA_REF_CYCLE",
        "drift": "SCHEMA_DRIFT",
        "root_drift": "SCHEMA_DRIFT",
        "escape": "SCHEMA_REF_FORBIDDEN",
        "remote": "SCHEMA_REF_FORBIDDEN",
    }[failure]
    assert result.unverifiable == (f"old: {expected}", f"new: {expected}")
    assert any(reason.startswith("old:") for reason in result.unverifiable)
    assert any(reason.startswith("new:") for reason in result.unverifiable)


def test_reference_sibling_constraints_are_not_lost() -> None:
    old = referenced(record())
    new = copy.deepcopy(old)
    old["description"] = "meaning A"
    new["description"] = "meaning B"
    assert compare_schemas(old, new).breaking
    new["type"] = "string"  # Conflicting conjunction must remain unverifiable.
    assert compare_schemas(old, new).unverifiable


def test_contract_comparison_uses_resolved_shape_and_still_checks_authority() -> None:
    repo = Path(__file__).resolve().parents[2]
    old = replace(
        ContractDeclaration.from_mapping(
            json.loads(
                (
                    repo / "packages/contracts/registry/core.order-query.v1.json"
                ).read_text()
            )
        ),
        input_schema=None,
    )
    new = replace(old, canonical_producer="vision")
    result = compare_contracts(
        old,
        new,
        old_output_schema=referenced(record()),
        new_output_schema=referenced(record()),
    )
    assert result.breaking == ("canonical_producer: authority or semantics changed",)
    assert not result.unverifiable


def test_reference_validation_siblings_preserve_fail_closed_scope() -> None:
    # additionalProperties only sees properties in its own schema object.
    # Merging these scopes would change which payloads satisfy the schema.
    document = referenced(record())
    document["additionalProperties"] = False
    result = compare_schemas(document, document)
    assert result.unverifiable
    assert not result.compatible


@pytest.mark.parametrize("different_shape", [False, True])
def test_changed_approved_file_target_is_resolved(
    tmp_path: Path, different_shape: bool
) -> None:
    first = write(tmp_path, "first.json", record())
    alternative = record()
    if different_shape:
        alternative["properties"]["id"]["type"] = "integer"
    second = write(tmp_path, "second.json", alternative)
    old = write(tmp_path, "old.json", {"$ref": "first.json"})
    new = write(tmp_path, "new.json", {"$ref": "second.json"})
    result = compare_schema_files(
        old,
        new,
        old_repo_root=tmp_path,
        new_repo_root=tmp_path,
        old_schema_refs=(first,),
        new_schema_refs=(second,),
    )
    assert result.compatible is not different_shape
    assert bool(result.breaking) is different_shape
