"""Trace linter (03 §18.1). Slice 1: TL-01 schema, TL-04 vocabulary, TL-05 duplicates.

Every finding names its check, the subject it is about and what is wrong, so a
failing CI run is readable without opening the registry. The linter never fixes
anything and never downgrades a finding.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import exceptions, validators

from .model import PROHIBITED, RELATIONS

REGISTRY = "traceability/trace_edges.yaml"
SCHEMA = "traceability/trace_schema.json"
IMPLEMENTED_CHECKS = ("TL-01", "TL-04", "TL-05")


class RegistryError(ValueError):
    """The registry or its schema cannot be read at all."""


@dataclass(frozen=True, order=True)
class Finding:
    check: str
    subject: str
    message: str

    def line(self) -> str:
        return f"{self.check} {self.subject}: {self.message}"


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded: object = yaml.safe_load(path.read_text("utf-8"))
    except OSError as exc:
        raise RegistryError(f"{path.name}: cannot read: {exc.strerror}") from None
    except yaml.YAMLError as exc:
        raise RegistryError(f"{path.name}: not valid YAML: {exc}") from None
    if not isinstance(loaded, dict):
        raise RegistryError(f"{path.name}: top level must be a mapping")
    return cast(dict[str, Any], loaded)


def load_schema(path: Path) -> dict[str, Any]:
    try:
        loaded: object = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"{path.name}: unreadable schema: {exc}") from None
    if not isinstance(loaded, dict):
        raise RegistryError(f"{path.name}: schema must be an object")
    return cast(dict[str, Any], loaded)


def schema_findings(registry: dict[str, Any], schema: dict[str, Any]) -> list[Finding]:
    """TL-01: the registry validates against trace_schema.json."""
    # jsonschema's public API is only partially typed; keep the boundary explicit.
    validator_cls: Any = cast(Any, validators).validator_for(schema)
    try:
        validator_cls.check_schema(schema)
    except exceptions.SchemaError as exc:
        raise RegistryError(f"trace schema is invalid: {exc.message}") from None
    errors: list[Any] = list(validator_cls(schema).iter_errors(registry))
    findings: list[Finding] = []
    for error in errors:
        where = "/".join(str(part) for part in error.absolute_path) or "<root>"
        findings.append(Finding("TL-01", where, str(error.message)))
    return findings


def _edges(registry: dict[str, Any]) -> list[dict[str, Any]]:
    raw: object = registry.get("edges")
    if not isinstance(raw, list):
        return []
    return [
        cast(dict[str, Any], e) for e in cast(list[object], raw) if isinstance(e, dict)
    ]


def edge_findings(registry: dict[str, Any]) -> list[Finding]:
    """TL-01 (declared source), TL-04 (vocabulary) and TL-05 (identity)."""
    findings: list[Finding] = []
    raw_nodes: object = registry.get("requirements")
    nodes: set[str] = set()
    if isinstance(raw_nodes, dict):
        nodes = {str(k) for k in cast(dict[object, object], raw_nodes)}
    identities: Counter[tuple[str, str, str]] = Counter()
    for number, edge in enumerate(_edges(registry)):
        source, relation, target = (
            str(edge.get(k, "")) for k in ("from", "relation", "to")
        )
        subject = f"edges/{number} ({source} {relation} {target})"
        if source not in nodes:
            findings.append(
                Finding("TL-01", subject, "source requirement is not declared")
            )
        if relation not in RELATIONS:
            if relation.lower() in PROHIBITED:
                why = "vague relation prohibited by Item 83 #38"
            else:
                why = "not in the controlled relation vocabulary (03 §4.2)"
            findings.append(Finding("TL-04", subject, f"relation {relation!r}: {why}"))
        identities[(source, relation, target)] += 1
    for (source, relation, target), count in sorted(identities.items()):
        if count > 1:
            findings.append(
                Finding(
                    "TL-05",
                    f"{source} {relation} {target}",
                    f"edge identity appears {count} times; from+relation+to must be unique",
                )
            )
    return findings


def lint(registry: dict[str, Any], schema: dict[str, Any]) -> list[Finding]:
    return sorted(schema_findings(registry, schema) + edge_findings(registry))


def lint_files(root: Path) -> tuple[dict[str, Any], list[Finding]]:
    registry = load_yaml(root / REGISTRY)
    return registry, lint(registry, load_schema(root / SCHEMA))
