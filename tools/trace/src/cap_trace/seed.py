"""Seed the trace registry from the 03 §17 requirement trace records.

03 §17 is the human-readable edge-level projection of the trace graph: one YAML
record per requirement in the controlled relation vocabulary. Seeding parses
those records exactly (no inference, no requirement text is copied, Item 83 #3)
and turns them into node attributes plus TraceEdges.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import yaml

from .model import RECORDED_RELATIONS, RELATIONS, REPO_PREFIX, SCHEMA_ID, TBD, Edge

RTM = "docs/03_Requirements_Traceability_Matrix.md"
SECTION_START = "## 17. Requirement Trace Records"
SECTION_END = "## 18. "
BLOCK = re.compile(r"^```yaml\n(.*?)^```", re.M | re.S)

# Record keys that are node attributes, not relations.
ATTRIBUTES = {
    "meta": "meta",
    "acceptance": "acceptance",
    "state": "state",
    "MEASUREMENT": "measurement",
    "note": "note",
}
META_KEYS = ("class", "owner", "anchor")
REALIZATION_KEYS = ("surface", "deployable", "ref")

# A repository path inside a REALIZED_BY reference: lowercase first segment (or
# .github), at least one slash, not preceded by a word, path or ":" character
# (so "envelope.py:new_event_id/EventEnvelope" yields only the file).
REPO_PATH = re.compile(
    r"(?<![\w/.:-])((?:\.github|[a-z0-9_][a-z0-9_.-]*)(?:/[A-Za-z0-9_.-]+)+/?)"
)


class SeedError(ValueError):
    """The 03 §17 records cannot be turned into a registry without guessing."""


def section(text: str) -> str:
    start = text.find(SECTION_START)
    if start < 0:
        raise SeedError(f"{RTM}: section 17 heading not found")
    end = text.find(SECTION_END, start)
    if end < 0:
        raise SeedError(f"{RTM}: section 18 heading not found after section 17")
    return text[start:end]


def parse_records(text: str) -> dict[str, dict[str, Any]]:
    """All requirement records of 03 §17, in document order."""
    records: dict[str, dict[str, Any]] = {}
    for number, match in enumerate(BLOCK.finditer(section(text)), start=1):
        try:
            loaded: object = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            raise SeedError(
                f"§17 YAML block {number} is not valid YAML: {exc}"
            ) from None
        if not isinstance(loaded, dict):
            raise SeedError(f"§17 YAML block {number} is not a mapping of records")
        for key, value in cast(dict[object, object], loaded).items():
            if not isinstance(key, str):
                raise SeedError(
                    f"§17 YAML block {number}: non-string record key {key!r}"
                )
            if key in records:
                raise SeedError(f"§17: requirement {key} has more than one record")
            if not isinstance(value, dict):
                raise SeedError(f"§17: record {key} is not a mapping")
            records[key] = cast(dict[str, Any], value)
    if not records:
        raise SeedError("§17 contains no YAML records")
    return records


def repo_paths(ref: str, top_level: frozenset[str] | None = None) -> list[str]:
    """Repository paths named in a REALIZED_BY reference.

    With `top_level` (the repository's top-level entries) a token whose first
    segment is not one of them is prose ("middleware/consumer"), not a path.
    Whether the full path exists is TL-02's question, not the seeder's."""
    found: list[str] = []
    for match in REPO_PATH.finditer(ref):
        path = match.group(1).rstrip(".,")
        if top_level is not None and path.split("/", 1)[0] not in top_level:
            continue
        if path not in found:
            found.append(path)
    return found


def _strings(requirement: str, relation: str, value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SeedError(f"{requirement} {relation}: expected a list, found {value!r}")
    items: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str) or not item.strip():
            raise SeedError(f"{requirement} {relation}: invalid target {item!r}")
        items.append(item.strip())
    return items


def convert(
    requirement: str,
    record: dict[str, Any],
    top_level: frozenset[str] | None = None,
) -> tuple[dict[str, Any], list[Edge]]:
    """One §17 record → (node attributes, edges). Unknown keys are refused."""
    node: dict[str, Any] = {}
    edges: list[Edge] = []
    meta = record.get("meta")
    if not isinstance(meta, dict) or any(
        not isinstance(cast(dict[str, object], meta).get(k), str) for k in META_KEYS
    ):
        raise SeedError(f"{requirement}: meta must give class, owner and anchor")
    unknown = sorted(set(record) - set(ATTRIBUTES) - set(RELATIONS))
    if unknown:
        raise SeedError(f"{requirement}: unknown relation or attribute {unknown}")
    for key, name in ATTRIBUTES.items():
        if key in record:
            node[name] = record[key]
    for relation in RELATIONS:
        if relation not in record:
            continue
        value = record[relation]
        if relation == "REALIZED_BY":
            edges.extend(_realization(requirement, value, node, top_level))
            continue
        applicability = "RECORDED" if relation in RECORDED_RELATIONS else "PLANNED"
        for target in _strings(requirement, relation, value):
            edges.append(Edge(requirement, relation, target, applicability))
    return node, edges


def _realization(
    requirement: str,
    value: object,
    node: dict[str, Any],
    top_level: frozenset[str] | None,
) -> list[Edge]:
    if not isinstance(value, dict):
        raise SeedError(f"{requirement} REALIZED_BY: expected surface/deployable/ref")
    data = cast(dict[str, object], value)
    if set(data) != set(REALIZATION_KEYS) or not all(
        isinstance(data[k], str) for k in REALIZATION_KEYS
    ):
        raise SeedError(f"{requirement} REALIZED_BY: needs exactly {REALIZATION_KEYS}")
    node["realization"] = {k: data[k] for k in REALIZATION_KEYS}
    ref = cast(str, data["ref"])
    edges = [
        Edge(requirement, "REALIZED_BY", REPO_PREFIX + path, "RECORDED")
        for path in repo_paths(ref, top_level)
    ]
    if TBD in ref or not edges:
        edges.append(Edge(requirement, "REALIZED_BY", TBD, "PLANNED"))
    return edges


def build(text: str, top_level: frozenset[str] | None = None) -> dict[str, Any]:
    """The registry document for one revision of 03."""
    requirements: dict[str, Any] = {}
    edges: list[Edge] = []
    for requirement, record in parse_records(text).items():
        node, found = convert(requirement, record, top_level)
        requirements[requirement] = node
        edges.extend(found)
    return {
        "schema": SCHEMA_ID,
        "seeded_from": {
            "document": RTM,
            "section": "17",
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "requirements": requirements,
        "edges": [edge.to_dict() for edge in edges],
    }


def dump(registry: dict[str, Any]) -> str:
    """Deterministic YAML: block style for nodes, one flow mapping per edge."""
    head = {k: registry[k] for k in ("schema", "seeded_from")}
    lines = [
        "# WP-GOV-002 trace registry (01 Item 83, 03 §18). Seeded from 03 §17 by",
        "# `python -m cap_trace seed`; see traceability/README.md before editing.",
        yaml.safe_dump(head, sort_keys=False, allow_unicode=True).rstrip(),
        "requirements:",
    ]
    nodes = yaml.safe_dump(
        registry["requirements"], sort_keys=False, allow_unicode=True, width=1000
    )
    lines.extend("  " + line for line in nodes.rstrip().splitlines())
    lines.append("edges:")
    lines.extend(_edge_lines(cast(Iterable[dict[str, str]], registry["edges"])))
    return "\n".join(lines) + "\n"


def _edge_lines(edges: Iterable[dict[str, str]]) -> list[str]:
    return ["- " + json.dumps(edge, ensure_ascii=False) for edge in edges]


def top_level_entries(root: Path) -> frozenset[str]:
    return frozenset(
        p.name
        for p in root.iterdir()
        if not p.name.startswith(".git") or p.name == ".github"
    )


def seed(root: Path) -> dict[str, Any]:
    return build((root / RTM).read_text("utf-8"), top_level_entries(root))
