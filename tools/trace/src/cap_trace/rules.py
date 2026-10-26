"""Coverage and evidence rules (03 §18.1, §4.4): TL-06, TL-08, TL-09, TL-11, TL-12.

| Check | Rule | Requirement |
|---|---|---|
| TL-06 dangling | EXECUTED_AS resolves to a run record of the producing work package; EVIDENCED_BY to a sealed bundle; SUPPORTS_CLAIM to a claim register | Item 83 #6, #9; RTM-INV-68 |
| TL-08 coverage | every active F0/F1 keeps ≥1 DERIVED_FROM, ALLOCATED_TO and VERIFIED_BY; against a base revision, none of those edges disappears without a CHG reference | FR-GOV-004, FR-GOV-005 |
| TL-09 stale claims | no SUPPORTS_CLAIM from a requirement whose evidence is STALE | Item 83 #10 |
| TL-11 class sufficiency | F0 ⇒ an integrated scenario/demo path; H0 ⇒ an executable hard asset, not inspection-only; FR verify codes E/B/R/N/D/I ⇒ matching asset kinds | 03 §4.4, §22 C-07…C-14 |
| TL-12 no VERIFIED without evidence | coverage VERIFIED or evidence CURRENT ⇒ ≥1 EVIDENCED_BY; a final NFR also needs an observed measurement | FR-GOV-010, NFR-GOV-009, RTM-INV-46 |
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, cast

from .model import Finding
from .sources import Index

COVERAGE_RELATIONS = ("DERIVED_FROM", "ALLOCATED_TO", "VERIFIED_BY")
COVERED_CLASSES = frozenset({"F0", "F1"})
INTEGRATED_ENVS = frozenset({"INTEGRATION", "EVALUATION", "DEMO", "PUBLIC_REPRO"})
HARD_KINDS = frozenset({"TEST", "DRILL", "SCENARIO"})
CHANGE = re.compile(r"\bCHG-\d{3}\b")
PREFIX_KINDS = (
    ("TEST-", "TEST"),
    ("BENCH-", "BENCH"),
    ("INSP-", "INSP"),
    ("RES-", "DRILL"),
    ("RESTORE-", "DRILL"),
    ("REPRO-", "DRILL"),
    ("E2E-", "SCENARIO"),
    ("AV-SCEN-", "SCENARIO"),
    ("DEMO-", "DEMO"),
)


def kind(asset: str, index: Index) -> str:
    """Asset kind from the 03 §9.X registry heading, else from the ID prefix."""
    if asset in index.asset_kinds:
        return index.asset_kinds[asset]
    return next((k for p, k in PREFIX_KINDS if asset.startswith(p)), "UNKNOWN")


def _nodes(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw: object = registry.get("requirements")
    return cast(dict[str, dict[str, Any]], raw) if isinstance(raw, dict) else {}


def _by_relation(registry: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    out: dict[tuple[str, str], list[str]] = defaultdict(list)
    raw: object = registry.get("edges")
    for edge in cast(list[dict[str, str]], raw if isinstance(raw, list) else []):
        out[(edge.get("from", ""), edge.get("relation", ""))].append(edge.get("to", ""))
    return out


def _class(node: dict[str, Any]) -> str:
    return str(cast(dict[str, Any], node.get("meta", {})).get("class", ""))


def dangling(registry: dict[str, Any], index: Index) -> list[Finding]:
    """TL-06."""
    findings: list[Finding] = []
    for (source, relation), targets in sorted(_by_relation(registry).items()):
        for target in targets:
            subject = f"{source} {relation} {target}"
            if relation == "EXECUTED_AS" and not index.run_exists(target):
                findings.append(
                    Finding(
                        "TL-06",
                        subject,
                        "no run record in the producing work package's evidence",
                    )
                )
            elif relation == "EVIDENCED_BY" and not index.bundle_exists(target):
                findings.append(
                    Finding("TL-06", subject, "no sealed evidence bundle with this ID")
                )
            elif relation == "SUPPORTS_CLAIM":
                findings.append(
                    Finding(
                        "TL-06",
                        subject,
                        "no ThesisClaimRegister exists to resolve the claim",
                    )
                )
    return findings


def completeness(registry: dict[str, Any], index: Index) -> list[Finding]:
    """TL-08 without a base: FR-GOV-004 (DERIVED_FROM) and FR-GOV-005 (VERIFIED_BY)."""
    findings: list[Finding] = []
    edges = _by_relation(registry)
    for requirement, node in sorted(_nodes(registry).items()):
        if requirement not in index.requirements or _class(node) not in COVERED_CLASSES:
            continue
        for relation in COVERAGE_RELATIONS:
            if not edges.get((requirement, relation)):
                findings.append(
                    Finding(
                        "TL-08",
                        requirement,
                        f"active {_class(node)} has no {relation} edge",
                    )
                )
    return findings


def regression(
    base: dict[str, Any], registry: dict[str, Any], index: Index
) -> list[Finding]:
    """TL-08 against a base revision: a coverage edge of an active F0/F1 may only
    disappear when the requirement's note cites an existing CHG record."""
    findings: list[Finding] = []
    old, new = _by_relation(base), _by_relation(registry)
    nodes = _nodes(registry)
    for requirement, node in sorted(nodes.items()):
        if requirement not in index.requirements or _class(node) not in COVERED_CLASSES:
            continue
        cited = set(CHANGE.findall(str(node.get("note", "")))) & index.changes
        for relation in COVERAGE_RELATIONS:
            lost = sorted(
                set(old.get((requirement, relation), []))
                - set(new.get((requirement, relation), []))
            )
            for target in lost if not cited else []:
                findings.append(
                    Finding(
                        "TL-08",
                        f"{requirement} {relation} {target}",
                        "coverage edge removed without a CHG reference in the requirement note",
                    )
                )
    return findings


def stale_claims(registry: dict[str, Any]) -> list[Finding]:
    """TL-09."""
    findings: list[Finding] = []
    edges = _by_relation(registry)
    for requirement, node in sorted(_nodes(registry).items()):
        state = cast(dict[str, Any], node.get("state", {}))
        if state.get("evidence") == "STALE":
            for claim in edges.get((requirement, "SUPPORTS_CLAIM"), []):
                findings.append(
                    Finding(
                        "TL-09",
                        f"{requirement} SUPPORTS_CLAIM {claim}",
                        "claim rests on STALE evidence",
                    )
                )
    return findings


def _code_satisfied(
    code: str, assets: list[str], scenarios: list[str], index: Index
) -> bool:
    kinds = {kind(a, index) for a in assets}
    if code == "E":  # integrated asset
        return (
            bool(scenarios)
            or bool(kinds & {"SCENARIO", "DEMO"})
            or any(index.asset_envs.get(a) in INTEGRATED_ENVS for a in assets)
        )
    if code == "B":
        return "BENCH" in kinds
    if code == "R":  # drill or restart test
        return "DRILL" in kinds or any("RESTART" in a for a in assets)
    if code == "N":  # an executable asset that can carry the negative paths
        return bool(kinds & {"TEST", "DRILL"})
    if code == "D":
        return "DEMO" in kinds or any(s.startswith("DEMO-") for s in scenarios)
    if code == "I":  # inspection or lint
        return bool(kinds & {"INSP", "TEST"})
    return True  # T is not an audited code (03 §22 C-08…C-13)


def sufficiency(registry: dict[str, Any], index: Index) -> list[Finding]:
    """TL-11."""
    findings: list[Finding] = []
    edges = _by_relation(registry)
    for requirement, node in sorted(_nodes(registry).items()):
        if requirement not in index.requirements:
            continue
        assets = edges.get((requirement, "VERIFIED_BY"), [])
        scenarios = edges.get((requirement, "EXERCISED_IN"), [])
        kinds = {kind(a, index) for a in assets}
        cls = _class(node)
        if cls == "F0" and not scenarios and not kinds & {"SCENARIO", "DEMO"}:
            findings.append(
                Finding(
                    "TL-11",
                    requirement,
                    "F0 without an integrated scenario or demo path",
                )
            )
        if cls == "H0" and not scenarios and not kinds & HARD_KINDS:
            findings.append(
                Finding(
                    "TL-11",
                    requirement,
                    "H0 without an executable hard asset (inspection or benchmark only)",
                )
            )
        for code in sorted(index.verify_codes.get(requirement, set())):
            if requirement.startswith("FR-") and not _code_satisfied(
                code, assets, scenarios, index
            ):
                findings.append(
                    Finding(
                        "TL-11",
                        requirement,
                        f"verify code {code} has no matching asset kind",
                    )
                )
    return findings


def unsupported_verified(registry: dict[str, Any]) -> list[Finding]:
    """TL-12."""
    findings: list[Finding] = []
    edges = _by_relation(registry)
    for requirement, node in sorted(_nodes(registry).items()):
        state = cast(dict[str, Any], node.get("state", {}))
        if state.get("coverage") != "VERIFIED" and state.get("evidence") != "CURRENT":
            continue
        if not edges.get((requirement, "EVIDENCED_BY")):
            findings.append(
                Finding(
                    "TL-12",
                    requirement,
                    "VERIFIED/CURRENT without an EVIDENCED_BY edge",
                )
            )
        measurement = cast(dict[str, Any], node.get("measurement", {}))
        if requirement.startswith("NFR-") and measurement.get("observed") is None:
            findings.append(
                Finding(
                    "TL-12",
                    requirement,
                    "final NFR VERIFIED without an observed measurement",
                )
            )
    return findings


def rule_findings(registry: dict[str, Any], index: Index) -> list[Finding]:
    return (
        dangling(registry, index)
        + completeness(registry, index)
        + stale_claims(registry)
        + sufficiency(registry, index)
        + unsupported_verified(registry)
    )
