"""TL-02 referenced IDs exist, TL-03 superseded misuse (03 §18.1).

Each relation is resolved against the registry its 03 §4.2 constraint names.
Relations whose targets are artifact *types* (USES_DATA, USES_MODEL,
GOVERNED_BY, descriptive EXPOSED_BY surfaces) have no identity registry yet and
are counted as not resolvable rather than guessed. EXECUTED_AS, EVIDENCED_BY and
SUPPORTS_CLAIM are TL-06's (run and evidence identities).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, cast

from .model import REPO_PREFIX, TBD, Finding
from .sources import Index

ITEM = re.compile(r"^ITEM-(\d{1,3})$")
INVARIANT = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-INV-\d+$")
CONTRACT = re.compile(r"^IC-[A-Z]+-\d{3}$")
CONTRACT_FAMILY = re.compile(r"^(IC-[A-Z]+)-\*$")
RISK = re.compile(r"^[A-Z]+-R\d{2}$")
TYPE_RELATIONS = frozenset({"USES_DATA", "USES_MODEL", "GOVERNED_BY"})
RUN_RELATIONS = frozenset({"EXECUTED_AS", "EVIDENCED_BY", "SUPPORTS_CLAIM"})


def _edges(registry: dict[str, Any]) -> list[dict[str, str]]:
    raw: object = registry.get("edges")
    if not isinstance(raw, list):
        return []
    return [
        cast(dict[str, str], e) for e in cast(list[object], raw) if isinstance(e, dict)
    ]


def resolve(relation: str, target: str, index: Index) -> str | None:
    """None if the target resolves (or is not resolvable by design); otherwise
    the reason it does not."""
    if relation == "DERIVED_FROM":
        item = ITEM.match(target)
        if item:
            return None if int(item.group(1)) in index.items else "no such 01 item"
        if INVARIANT.match(target):
            return None if target in index.master else "invariant not in 01"
        return "not a decision reference (ITEM-nn or <FAMILY>-INV-nn)"
    if relation == "ALLOCATED_TO":
        return (
            None if target in index.architecture else "not in the 02 component registry"
        )
    if relation == "VERIFIED_BY":
        return (
            None
            if target in index.verification
            else "not a registered verification family or asset"
        )
    if relation == "DECIDED_BY":
        return None if target in index.decisions else "no such ADR in docs/adr"
    if relation == "EXERCISED_IN":
        return None if target in index.master else "scenario not in 01"
    if relation == "MITIGATES":
        if not RISK.match(target):
            return "not a risk register ID (<AREA>-Rnn)"
        return None if target in index.master else "risk not in the 01 register"
    if relation == "EXPOSED_BY":
        family = CONTRACT_FAMILY.match(target)
        if family:
            prefix = family.group(1) + "-"
            known = any(c.startswith(prefix) for c in index.contracts)
            return None if known else "contract namespace not in 01/02"
        if CONTRACT.match(target):
            return None if target in index.contracts else "contract not in 01/02"
        return (
            None  # descriptive interface surface; exact schema versions TBD (03 §4.2)
        )
    if relation == "REALIZED_BY":
        if target == TBD:
            return None
        if not target.startswith(REPO_PREFIX):
            return "not a repository path or TBD_BY_IMPLEMENTATION"
        path = target.removeprefix(REPO_PREFIX)
        return None if index.path_exists(path) else "repository path does not exist"
    return None


def reference_findings(registry: dict[str, Any], index: Index) -> list[Finding]:
    findings: list[Finding] = []
    raw_nodes: object = registry.get("requirements")
    nodes: set[str] = set()
    if isinstance(raw_nodes, dict):
        nodes = {str(k) for k in cast(dict[object, object], raw_nodes)}
    for requirement in sorted(index.requirements - nodes):
        findings.append(
            Finding(
                "TL-02", requirement, "active catalog requirement has no registry node"
            )
        )
    for requirement in sorted(nodes - index.requirements - index.inactive):
        findings.append(
            Finding("TL-02", requirement, "node is not a catalog requirement")
        )
    for requirement in sorted(nodes & index.inactive):
        findings.append(
            Finding(
                "TL-03",
                requirement,
                "retired or superseded requirement still carries a node and edges",
            )
        )
    for edge in _edges(registry):
        relation, target = edge.get("relation", ""), edge.get("to", "")
        why = resolve(relation, target, index)
        if why:
            findings.append(
                Finding("TL-02", f"{edge.get('from')} {relation} {target}", why)
            )
    return findings


def coverage(registry: dict[str, Any]) -> Counter[str]:
    """How many edges each mode covers: checked, by type only, or left to TL-06."""
    counts: Counter[str] = Counter()
    for edge in _edges(registry):
        relation, target = edge.get("relation", ""), edge.get("to", "")
        if relation in TYPE_RELATIONS:
            counts["artifact type (no identity registry)"] += 1
        elif relation in RUN_RELATIONS:
            counts["run/evidence (TL-06)"] += 1
        elif relation == "EXPOSED_BY" and not (
            CONTRACT.match(target) or CONTRACT_FAMILY.match(target)
        ):
            counts["descriptive interface surface"] += 1
        else:
            counts["resolved against a registry"] += 1
    return counts
