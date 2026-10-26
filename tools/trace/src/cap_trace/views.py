"""Generated views of the registry (01 Item 83 `traceability/generated/`) and the
TL-07 freshness check.

Every view is a pure function of the registry, so a view can only be stale when
the registry changed without regenerating; another owner's edit to 01, 02 or 03
never makes a view stale. CSV keeps the wide per-requirement view out of
Markdown (Item 83 #119).
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, cast

from .model import RELATIONS, Finding

GENERATED = "traceability/generated"
COVERAGE_RELATIONS = ("DERIVED_FROM", "ALLOCATED_TO", "VERIFIED_BY")
KIND_PREFIXES = (
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
REQUIREMENT_COLUMNS = (
    "requirement_id",
    "class",
    "owner",
    "anchor",
    "coverage_state",
    "planning_state",
    "evidence_state",
    *(r.lower() for r in RELATIONS),
)


def _nodes(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return cast(dict[str, dict[str, Any]], registry.get("requirements", {}))


def _targets(registry: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    out: dict[tuple[str, str], list[str]] = defaultdict(list)
    for edge in cast(list[dict[str, str]], registry.get("edges", [])):
        out[(edge["from"], edge["relation"])].append(edge["to"])
    return out


def _csv(header: tuple[str, ...], rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _sub(node: dict[str, Any], key: str) -> dict[str, Any]:
    return cast(dict[str, Any], node.get(key, {}))


def requirements_view(registry: dict[str, Any]) -> str:
    targets = _targets(registry)
    rows: list[list[str]] = []
    for requirement, node in _nodes(registry).items():
        meta, state = _sub(node, "meta"), _sub(node, "state")
        rows.append(
            [
                requirement,
                str(meta.get("class", "")),
                str(meta.get("owner", "")),
                str(meta.get("anchor", "")),
                str(state.get("coverage", "")),
                str(state.get("planning", "")),
                str(state.get("evidence", "")),
                *(" ".join(targets.get((requirement, r), [])) for r in RELATIONS),
            ]
        )
    return _csv(REQUIREMENT_COLUMNS, rows)


def asset_kind(asset: str) -> str:
    return next((k for p, k in KIND_PREFIXES if asset.startswith(p)), "UNKNOWN")


def verification_view(registry: dict[str, Any]) -> str:
    """Backward trace (Item 83 #44): each verification asset → its requirements."""
    by_asset: dict[str, list[str]] = defaultdict(list)
    for edge in cast(list[dict[str, str]], registry.get("edges", [])):
        if edge["relation"] == "VERIFIED_BY":
            by_asset[edge["to"]].append(edge["from"])
    rows = [
        [asset, asset_kind(asset), str(len(reqs)), " ".join(reqs)]
        for asset, reqs in sorted(by_asset.items())
    ]
    return _csv(("asset", "kind", "requirement_count", "requirements"), rows)


def evidence_view(registry: dict[str, Any]) -> str:
    targets = _targets(registry)
    rows: list[list[str]] = []
    for requirement, node in _nodes(registry).items():
        acceptance, state = _sub(node, "acceptance"), _sub(node, "state")
        rows.append(
            [
                requirement,
                str(_sub(node, "meta").get("class", "")),
                str(state.get("evidence", "")),
                str(acceptance.get("boundary_mode_final", "")),
                str(acceptance.get("evidence_target", "")),
                str(acceptance.get("env", "")),
                " ".join(targets.get((requirement, "EXECUTED_AS"), [])),
                " ".join(targets.get((requirement, "EVIDENCED_BY"), [])),
            ]
        )
    header = (
        "requirement_id",
        "class",
        "evidence_state",
        "boundary_mode_final",
        "evidence_target",
        "env",
        "executed_as",
        "evidenced_by",
    )
    return _csv(header, rows)


def claim_view(registry: dict[str, Any]) -> str:
    by_claim: dict[str, list[str]] = defaultdict(list)
    for edge in cast(list[dict[str, str]], registry.get("edges", [])):
        if edge["relation"] == "SUPPORTS_CLAIM":
            by_claim[edge["to"]].append(edge["from"])
    rows = [[c, " ".join(r)] for c, r in sorted(by_claim.items())]
    return _csv(("claim", "requirements"), rows)


def orphan_report(registry: dict[str, Any]) -> str:
    targets = _targets(registry)
    nodes = _nodes(registry)
    orphans = {
        relation: [r for r in nodes if not targets.get((r, relation))]
        for relation in COVERAGE_RELATIONS
    }
    planned_only = [
        r
        for r in nodes
        if targets.get((r, "REALIZED_BY")) in (None, ["TBD_BY_IMPLEMENTATION"])
    ]
    states: Counter[str] = Counter(
        str(_sub(n, "state").get("coverage", "")) for n in nodes.values()
    )
    report = {
        "schema": "cap.trace-orphans/v1",
        "requirements": len(nodes),
        "orphan_requirements": orphans,
        "without_recorded_realization": len(planned_only),
        "without_run": sum(1 for r in nodes if not targets.get((r, "EXECUTED_AS"))),
        "coverage_states": dict(sorted(states.items())),
    }
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


VIEWS = {
    "requirements.csv": requirements_view,
    "verification_coverage.csv": verification_view,
    "evidence_coverage.csv": evidence_view,
    "claim_coverage.csv": claim_view,
    "orphan_report.json": orphan_report,
}


def generate(registry: dict[str, Any]) -> dict[str, str]:
    return {name: build(registry) for name, build in VIEWS.items()}


def write(root: Path, registry: dict[str, Any]) -> list[str]:
    folder = root / GENERATED
    folder.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, content in generate(registry).items():
        (folder / name).write_text(content, encoding="utf-8")
        written.append(f"{GENERATED}/{name}")
    return written


def freshness(root: Path, registry: dict[str, Any]) -> list[Finding]:
    """TL-07: every generated view equals what the registry produces now."""
    findings: list[Finding] = []
    folder = root / GENERATED
    expected = generate(registry)
    for name, content in expected.items():
        path = folder / name
        if not path.is_file():
            findings.append(
                Finding(
                    "TL-07",
                    f"{GENERATED}/{name}",
                    "missing; run `mfgctl trace generate`",
                )
            )
        elif path.read_text("utf-8") != content:
            findings.append(
                Finding(
                    "TL-07", f"{GENERATED}/{name}", "stale; run `mfgctl trace generate`"
                )
            )
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.name not in expected:
                findings.append(
                    Finding("TL-07", f"{GENERATED}/{path.name}", "not a generated view")
                )
    return findings
