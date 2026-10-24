"""Pure, conservative contract comparison; no file, broker or registry mutation.

Only optional property additions are proven compatible. Other supported schema
changes are conservatively breaking. Unsupported constructs are unverifiable even
when unchanged: equality alone cannot prove reference or vocabulary semantics.
"""

import json
from dataclasses import dataclass
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .registry import ContractDeclaration

# This is deliberately a bounded subset, not a general JSON Schema implication solver.
_MAPS = {"properties"}
_CHILDREN = {"items"}
_KEYWORDS = {
    "$schema",
    "type",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "enum",
    "const",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
    "title",
    "description",
    "default",
    "examples",
    "readOnly",
    "writeOnly",
    "deprecated",
}
_DIALECT = "https://json-schema.org/draft/2020-12/schema"


@dataclass(frozen=True)
class CompatibilityResult:
    breaking: tuple[str, ...] = ()
    unverifiable: tuple[str, ...] = ()

    @property
    def compatible(self) -> bool:
        """True only when compatibility was positively established."""
        return not self.breaking and not self.unverifiable


def _pointer(path: str, part: str) -> str:
    return path + "/" + part.replace("~", "~0").replace("/", "~1")


def _supported(schema: Any, path: str, issues: list[str]) -> None:
    if not isinstance(schema, dict):
        issues.append(f"{path}: schema object required")
        return
    if not all(isinstance(key, str) for key in schema):
        issues.append(f"{path}: non-string schema keyword")
        return
    for key in sorted(set(schema) - _KEYWORDS):
        issues.append(f"{_pointer(path, key)}: unsupported keyword")
    if "$schema" in schema and schema["$schema"] != _DIALECT:
        issues.append(f"{path}: unsupported dialect")
    # Without an explicit type, property applicability is ambiguous.
    if "type" not in schema:
        issues.append(f"{path}: explicit type required")
    for name in schema.get("required", []):
        if name not in schema.get("properties", {}):
            issues.append(f"{path}: required field lacks a property schema")
    if isinstance(schema.get("additionalProperties"), dict):
        issues.append(f"{path}: schema-valued additionalProperties unsupported")
    for key in _MAPS:
        for name, child in schema.get(key, {}).items():
            _supported(child, _pointer(_pointer(path, key), name), issues)
    for key in _CHILDREN & schema.keys():
        _supported(schema[key], _pointer(path, key), issues)


def _compare(
    old: dict[str, Any], new: dict[str, Any], path: str, changes: list[str]
) -> None:
    for key in sorted((old.keys() | new.keys()) - _MAPS - _CHILDREN - {"required"}):
        if (key in old) != (key in new) or json.dumps(
            old.get(key), sort_keys=True
        ) != json.dumps(new.get(key), sort_keys=True):
            changes.append(f"{_pointer(path, key)}: value or semantics changed")
    if set(old.get("required", [])) != set(new.get("required", [])):
        changes.append(f"{path}/required: required fields changed")
    old_props, new_props = old.get("properties", {}), new.get("properties", {})
    for name in sorted(old_props.keys() | new_props.keys()):
        child_path = _pointer(_pointer(path, "properties"), name)
        if name not in new_props:
            changes.append(f"{child_path}: field removed")
        elif name not in old_props:
            if name in new.get("required", []):
                changes.append(f"{child_path}: required field added")
        else:
            _compare(old_props[name], new_props[name], child_path, changes)
    for key in sorted(_CHILDREN & (old.keys() | new.keys())):
        child_path = _pointer(path, key)
        if key not in old or key not in new:
            changes.append(f"{child_path}: schema added or removed")
        else:
            _compare(old[key], new[key], child_path, changes)


def compare_schemas(old: object, new: object) -> CompatibilityResult:
    """Compare old -> new using the architecture's optional-addition policy.

    This is a structural policy check, not proof that every strict old consumer
    accepts new payloads. Consumer compatibility tests remain separately required.
    No semantic meaning is inferred from prose; changed annotations are breaking.
    """
    issues: list[str] = []
    for label, schema in (("old", old), ("new", new)):
        if not isinstance(schema, dict):
            issues.append(f"{label}: schema object required")
            continue
        try:
            json.dumps(schema, sort_keys=True, allow_nan=False)
            Draft202012Validator.check_schema(schema)
        except (SchemaError, TypeError, ValueError, RecursionError):
            issues.append(f"{label}: invalid JSON Schema")
            continue
        _supported(schema, label, issues)
    if issues:
        return CompatibilityResult(unverifiable=tuple(sorted(issues)))
    changes: list[str] = []
    _compare(cast(dict[str, Any], old), cast(dict[str, Any], new), "", changes)
    return CompatibilityResult(breaking=tuple(changes))


def compare_contracts(
    old: ContractDeclaration,
    new: ContractDeclaration,
    *,
    old_output_schema: object,
    new_output_schema: object,
    old_input_schema: object = None,
    new_input_schema: object = None,
) -> CompatibilityResult:
    """Compare declarations and already loaded schema documents without I/O.

    Callers load/hash-verify documents with the existing registry primitives.
    Version bumps never hide a breaking change. File paths, hashes, fixtures,
    consumers and deprecation are catalog metadata, not schema compatibility proof.
    """
    breaking: list[str] = []
    unknown: list[str] = []
    if old.parsed_id.family != new.parsed_id.family or new.version < old.version:
        unknown.append("contract_id: unrelated family or reversed versions")
    for field in (
        "semantic_owner",
        "canonical_producer",
        "authority_level",
        "contract_type",
        "sync_semantics",
        "security_classification",
        "purpose",
        "semantics",
        "name",
    ):
        if getattr(old, field) != getattr(new, field):
            breaking.append(f"{field}: authority or semantics changed")
    for label, old_ref, new_ref, before, after in (
        (
            "output",
            old.output_schema,
            new.output_schema,
            old_output_schema,
            new_output_schema,
        ),
        (
            "input",
            old.input_schema,
            new.input_schema,
            old_input_schema,
            new_input_schema,
        ),
    ):
        if (old_ref is None) != (new_ref is None):
            breaking.append(f"{label}: schema presence changed")
        if (old_ref is None) != (before is None) or (new_ref is None) != (
            after is None
        ):
            unknown.append(f"{label}: schema document/declaration mismatch")
        elif before is not None and after is not None:
            result = compare_schemas(before, after)
            breaking.extend(f"{label}{item}" for item in result.breaking)
            unknown.extend(f"{label}: {item}" for item in result.unverifiable)
    return CompatibilityResult(tuple(breaking), tuple(unknown))
