"""TEST-EVT-001-003: pinned offline schema references and fail-closed boundaries."""

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from cap_contracts import (
    BoundaryValidator,
    ContractDeclaration,
    ContractError,
    ContractViolation,
    FileRef,
    Registry,
)
from cap_contracts.references import resolve_references
from cap_contracts.registry import load_schema

PACKAGE = "packages/contracts/schemas/"
REPO = Path(__file__).resolve().parents[2]


def write(root: Path, name: str, value: object) -> FileRef:
    path = root / PACKAGE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    return FileRef(PACKAGE + name, hashlib.sha256(raw).hexdigest())


def declaration(
    output: FileRef, fixture: FileRef, request: FileRef | None = None
) -> ContractDeclaration:
    base = ContractDeclaration.from_mapping(
        json.loads(
            (REPO / "packages/contracts/registry/core.order-query.v1.json").read_text()
        )
    )
    return replace(
        base, output_schema=output, input_schema=request, fixtures=(fixture,)
    )


def test_pinned_transitive_references_validate_both_boundaries_and_registry(
    tmp_path: Path,
) -> None:
    leaf = write(tmp_path, "leaf.json", {"type": "string", "minLength": 2})
    shared = write(tmp_path, "shared.json", {"$defs": {"id": {"$ref": "leaf.json"}}})
    root = write(
        tmp_path,
        "root.json",
        {
            "type": "object",
            "properties": {"id": {"$ref": "shared.json#/$defs/id"}},
            "required": ["id"],
        },
    )
    fixture = write(tmp_path, "fixture.json", {"id": "AB"})
    decl = declaration(root, fixture, root)
    pins = (shared, leaf)
    validator = BoundaryValidator(decl, tmp_path, schema_refs=pins)
    for role in ("producer", "consumer"):
        validator.validate({"id": "AB"}, role=role)
        validator.validate_request({"id": "AB"}, role=role)
        with pytest.raises(ContractViolation):
            validator.validate({"id": "A"}, role=role)
        with pytest.raises(ContractViolation):
            validator.validate_request({"id": 7}, role=role)
    Registry({decl.contract_id: decl}).verify(tmp_path, schema_refs=pins)
    first = load_schema(root, tmp_path, schema_refs=pins)
    assert first == load_schema(root, tmp_path, schema_refs=tuple(reversed(pins)))
    assert "$ref" not in json.dumps(first)


def test_fragments_escaped_pointers_and_siblings_preserve_semantics(
    tmp_path: Path,
) -> None:
    document = {
        "$defs": {"a/b~c": {"type": "string", "minLength": 2}},
        "type": "object",
        "properties": {"id": {"$ref": "#/$defs/a~1b~0c", "maxLength": 3}},
    }
    before = copy.deepcopy(document)
    root = write(tmp_path, "root.json", document)
    fixture = write(tmp_path, "fixture.json", {"id": "AB"})
    validator = BoundaryValidator(declaration(root, fixture), tmp_path)
    validator.validate({"id": "AB"}, role="consumer")
    for value in ("A", "ABCD", 3):
        with pytest.raises(ContractViolation):
            validator.validate({"id": value}, role="consumer")
    assert document == before
    assert resolve_references(document) == resolve_references(document)


@pytest.mark.parametrize(
    "reference",
    [
        "https://example.test/schema",
        "http://127.0.0.1/schema",
        "file:///etc/passwd",
        "//example.test/schema",
        "/etc/passwd",
        "../outside.json",
        "sub/../../outside.json",
        "sub/./x.json",
        "sub\\x.json",
        "%2e%2e/outside.json",
        "x.json?query",
        "#anchor",
        "#/$defs/bad~2escape",
    ],
)
def test_external_and_noncanonical_references_are_rejected_without_network(
    tmp_path: Path, reference: str
) -> None:
    root = write(tmp_path, "root.json", {"$ref": reference})
    with (
        patch(
            "urllib.request.urlopen", side_effect=AssertionError("network forbidden")
        ),
        pytest.raises(ContractError) as caught,
    ):
        load_schema(root, tmp_path)
    assert caught.value.code == "SCHEMA_REF_FORBIDDEN"


@pytest.mark.parametrize("reference", ["#/$defs/missing", "#/$defs/a/missing"])
def test_missing_fragments_are_rejected(tmp_path: Path, reference: str) -> None:
    root = write(
        tmp_path, "root.json", {"$defs": {"a": {"type": "string"}}, "$ref": reference}
    )
    with pytest.raises(ContractError, match="SCHEMA_REF_MISSING"):
        load_schema(root, tmp_path)


def test_unapproved_file_is_rejected_even_if_present(tmp_path: Path) -> None:
    write(tmp_path, "child.json", {"type": "string"})
    root = write(tmp_path, "root.json", {"$ref": "child.json"})
    with pytest.raises(ContractError, match="SCHEMA_REF_UNAPPROVED"):
        load_schema(root, tmp_path)


def test_missing_pinned_file_is_rejected(tmp_path: Path) -> None:
    root = write(tmp_path, "root.json", {"$ref": "missing.json"})
    with pytest.raises(ContractError, match="FILE_MISSING"):
        load_schema(
            root, tmp_path, schema_refs=(FileRef(PACKAGE + "missing.json", "0" * 64),)
        )


@pytest.mark.parametrize("changed", ["root.json", "child.json"])
def test_root_and_dependency_drift_still_fail_closed(
    tmp_path: Path, changed: str
) -> None:
    child = write(tmp_path, "child.json", {"type": "string"})
    root = write(tmp_path, "root.json", {"$ref": "child.json"})
    (tmp_path / PACKAGE / changed).write_text('{"type":"integer"}')
    with pytest.raises(ContractError, match="SCHEMA_DRIFT"):
        load_schema(root, tmp_path, schema_refs=(child,))


def test_symlink_escape_outside_package_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    raw = b'{"type":"string"}'
    outside.write_bytes(raw)
    root = write(tmp_path, "root.json", {"$ref": "link.json"})
    (tmp_path / PACKAGE / "link.json").symlink_to(outside)
    pin = FileRef(PACKAGE + "link.json", hashlib.sha256(raw).hexdigest())
    with pytest.raises(ContractError, match="SCHEMA_REF_FORBIDDEN"):
        load_schema(root, tmp_path, schema_refs=(pin,))


@pytest.mark.parametrize(
    "document",
    [
        {"$ref": "#"},
        {
            "$defs": {"a": {"$ref": "#/$defs/b"}, "b": {"$ref": "#/$defs/a"}},
            "type": "string",
        },
    ],
)
def test_internal_cycles_including_unused_definitions_are_rejected(
    tmp_path: Path, document: dict[str, Any]
) -> None:
    root = write(tmp_path, "root.json", document)
    with pytest.raises(ContractError, match="SCHEMA_REF_CYCLE"):
        load_schema(root, tmp_path)


def test_cross_file_cycle_is_rejected(tmp_path: Path) -> None:
    root = write(tmp_path, "root.json", {"$ref": "child.json"})
    child = write(tmp_path, "child.json", {"$ref": "root.json"})
    with pytest.raises(ContractError, match="SCHEMA_REF_CYCLE"):
        load_schema(root, tmp_path, schema_refs=(child, root))


@pytest.mark.parametrize(
    "child",
    [
        {"type": "invalid"},
        {"$dynamicRef": "#"},
        {"$id": "https://example.test/rebase", "type": "string"},
    ],
)
def test_invalid_and_unsupported_child_schemas_are_rejected(
    tmp_path: Path, child: dict[str, Any]
) -> None:
    root = write(
        tmp_path, "root.json", {"type": "object", "properties": {"value": child}}
    )
    with pytest.raises(ContractError):
        load_schema(root, tmp_path)


def test_duplicate_pins_fail_closed(tmp_path: Path) -> None:
    root = write(tmp_path, "root.json", {"type": "string"})
    with pytest.raises(ContractError, match="SCHEMA_REF_AMBIGUOUS"):
        load_schema(root, tmp_path, schema_refs=(root, root))


def test_ref_like_payload_constants_are_not_treated_as_schemas(tmp_path: Path) -> None:
    root = write(
        tmp_path, "root.json", {"const": {"$ref": "https://example.test/payload"}}
    )
    assert load_schema(root, tmp_path)["const"] == {
        "$ref": "https://example.test/payload"
    }


def test_missing_reference_in_request_fails_at_boundary_construction(
    tmp_path: Path,
) -> None:
    output = write(tmp_path, "output.json", {"type": "string"})
    request = write(tmp_path, "request.json", {"$ref": "#/$defs/missing"})
    fixture = write(tmp_path, "fixture.json", "valid")
    with pytest.raises(ContractError, match="SCHEMA_REF_MISSING"):
        BoundaryValidator(declaration(output, fixture, request), tmp_path)


def test_existing_core_exemplar_internal_references_remain_valid() -> None:
    Registry.load(REPO / "packages/contracts/registry").verify(REPO)


def test_unevaluated_properties_sees_referenced_property_annotations(
    tmp_path: Path,
) -> None:
    root = write(
        tmp_path,
        "root.json",
        {
            "$defs": {
                "base": {"type": "object", "properties": {"id": {"type": "string"}}}
            },
            "$ref": "#/$defs/base",
            "unevaluatedProperties": False,
        },
    )
    fixture = write(tmp_path, "fixture.json", {"id": "AB"})
    validator = BoundaryValidator(declaration(root, fixture), tmp_path)
    validator.validate({"id": "AB"}, role="consumer")
    with pytest.raises(ContractViolation):
        validator.validate({"id": "AB", "extra": True}, role="consumer")


def test_root_schema_symlink_cannot_escape_package(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    raw = b'{"type":"string"}'
    outside.write_bytes(raw)
    root = write(tmp_path, "root.json", {"type": "string"})
    (tmp_path / root.path).unlink()
    (tmp_path / root.path).symlink_to(outside)
    with pytest.raises(ContractError, match="SCHEMA_REF_FORBIDDEN"):
        load_schema(FileRef(root.path, hashlib.sha256(raw).hexdigest()), tmp_path)


def test_json_pointer_can_address_schema_array(tmp_path: Path) -> None:
    root = write(
        tmp_path,
        "root.json",
        {
            "$defs": {"tuple": {"type": "array", "prefixItems": [{"type": "string"}]}},
            "$ref": "#/$defs/tuple/prefixItems/0",
        },
    )
    fixture = write(tmp_path, "fixture.json", "AB")
    validator = BoundaryValidator(declaration(root, fixture), tmp_path)
    validator.validate("AB", role="consumer")
    with pytest.raises(ContractViolation):
        validator.validate(1, role="consumer")


def test_expansion_budget_fails_closed() -> None:
    document = {
        "type": "object",
        "properties": {str(index): {"type": "string"} for index in range(10001)},
    }
    with pytest.raises(ContractError, match="SCHEMA_REF_LIMIT"):
        resolve_references(document)


def test_pointer_to_invalid_schema_in_annotation_is_rejected(tmp_path: Path) -> None:
    root = write(
        tmp_path, "root.json", {"default": {"type": "not-a-type"}, "$ref": "#/default"}
    )
    with pytest.raises(ContractError, match="SCHEMA_REF_INVALID"):
        load_schema(root, tmp_path)
