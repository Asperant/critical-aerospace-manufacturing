"""Trace registry, seeding and lint TL-01/TL-04/TL-05 (WP-GOV-002, TEST-GOV-002-001).

Family TEST-GOV-TRACELINT. Small fixture documents drive every rejection; the
committed registry and the real 03 are checked as well, so the gate cannot pass
on fixtures alone.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from cap_trace import (
    RELATIONS,
    SeedError,
    build,
    compare,
    dump,
    lint,
    lint_files,
    parse_records,
    repo_paths,
)
from cap_trace.__main__ import main

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "traceability/trace_schema.json").read_text("utf-8"))

RECORD = """\
FR-GOV-001:
  meta: {class: F1, owner: Asrın, anchor: "01 Item81 FR-GOV-001 L1"}
  DERIVED_FROM: [ITEM-81, FRC-INV-01]
  ALLOCATED_TO: [ARCH-PLAT-CICD]
  REALIZED_BY: {surface: "catalog", deployable: "repository governance", ref: "requirements/catalog.json; runtime middleware/consumer remains TBD_BY_IMPLEMENTATION"}
  VERIFIED_BY: [TEST-GOV-001]
  EXECUTED_AS: [RUN-GOV-001-LOCAL-002]  # local run
  EVIDENCED_BY: []
  acceptance: {boundary_mode_final: FIXTURE_ALLOWED, evidence_target: EV-L2, env: "CI", m6_freeze_sensitive: false}
  state: {coverage: EVIDENCE_PENDING, planning: EVIDENCE_PENDING, evidence: EVIDENCE_PENDING}
"""
SECOND = """\
NFR-GOV-009:
  meta: {class: H0, owner: Yavuz, anchor: "01 Item82 NFR-GOV-009 L2"}
  DERIVED_FROM: [ITEM-82]
  ALLOCATED_TO: [ARCH-PLAT-CICD, ARCH-DATA-OBJ]
  VERIFIED_BY: [TEST-GOV-TRACELINT]
  EXECUTED_AS: []
  EVIDENCED_BY: []
  acceptance: {boundary_mode_final: REAL}
  state: {coverage: ALLOCATED, planning: VERIFY_PLANNED, evidence: NOT_YET_EXECUTED}
  MEASUREMENT: {metric: "unsupported VERIFIED claims", threshold: "0", observed: null}
"""
TOP = frozenset({"requirements", "tools", "docs"})


def rtm(*blocks: str) -> str:
    body = "\n".join(f"### 17.X\n\n```yaml\n{b}```\n" for b in blocks)
    return f"# 03\n\n## 17. Requirement Trace Records\n\n{body}\n## 18. Companion\n"


def registry(*blocks: str) -> dict[str, Any]:
    return build(rtm(*(blocks or (RECORD, SECOND))), TOP)


def checks(doc: dict[str, Any]) -> set[str]:
    return {f.check for f in lint(doc, SCHEMA)}


# --- seeding -----------------------------------------------------------------


def test_seed_turns_records_into_nodes_and_edges() -> None:
    doc = registry()
    assert list(doc["requirements"]) == ["FR-GOV-001", "NFR-GOV-009"]
    node = doc["requirements"]["FR-GOV-001"]
    assert node["meta"]["owner"] == "Asrın"
    assert "SHALL" not in json.dumps(doc)  # identity only, never requirement text
    edges = {(e["relation"], e["to"], e["applicability"]) for e in doc["edges"]}
    assert ("DERIVED_FROM", "FRC-INV-01", "PLANNED") in edges
    assert ("REALIZED_BY", "repo:requirements/catalog.json", "RECORDED") in edges
    assert ("REALIZED_BY", "TBD_BY_IMPLEMENTATION", "PLANNED") in edges
    assert ("EXECUTED_AS", "RUN-GOV-001-LOCAL-002", "RECORDED") in edges
    assert doc["requirements"]["NFR-GOV-009"]["measurement"]["observed"] is None
    assert lint(doc, SCHEMA) == []


def test_seed_is_deterministic_and_round_trips() -> None:
    text = dump(registry())
    assert text == dump(registry())
    assert yaml.safe_load(text) == registry()


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        (
            "requirements/catalog.json; tools/x.py",
            ["requirements/catalog.json", "tools/x.py"],
        ),
        ("tools/env.py:new_id/Envelope (abc123)", ["tools/env.py"]),
        (
            "docs/a.json and docs/b.json, docs/c.json.",
            ["docs/a.json", "docs/b.json", "docs/c.json"],
        ),
        ("HTTP/NATS/Temporal middleware remains TBD_BY_IMPLEMENTATION", []),
        ("runtime middleware/consumer adoption", []),
    ],
)
def test_repository_paths_are_read_from_references(
    ref: str, expected: list[str]
) -> None:
    assert repo_paths(ref, TOP) == expected


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ("FR-GOV-001: [not, a, mapping]\n", "is not a mapping"),
        ("FR-GOV-001:\n  DERIVED_FROM: [ITEM-1]\n", "meta must give"),
        (RECORD.replace("DERIVED_FROM", "RELATED_TO"), "unknown relation"),
        (RECORD.replace("[ITEM-81, FRC-INV-01]", "ITEM-81"), "expected a list"),
        (RECORD.replace('surface: "catalog", ', ""), "needs exactly"),
        ("FR-GOV-001: {meta: [\n", "not valid YAML"),
    ],
)
def test_records_that_cannot_be_seeded_are_refused(block: str, message: str) -> None:
    with pytest.raises(SeedError, match=message):
        registry(block)


def test_duplicate_or_missing_records_are_refused() -> None:
    with pytest.raises(SeedError, match="more than one record"):
        registry(RECORD, RECORD)
    with pytest.raises(SeedError, match="no YAML records"):
        parse_records(rtm())
    with pytest.raises(SeedError, match="section 17"):
        parse_records("# 03 without the section\n")


# --- lint --------------------------------------------------------------------


def mutated(change: str) -> dict[str, Any]:
    doc = copy.deepcopy(registry())
    edge = doc["edges"][0]
    if change == "relation":
        edge["relation"] = "SUPPORTS_SOMEHOW"
    elif change == "vague":
        edge["relation"] = "related_to"
    elif change == "duplicate":
        doc["edges"].append(dict(edge))
    elif change == "applicability":
        edge["applicability"] = "MAYBE"
    elif change == "extra":
        edge["confidence"] = "high"
    elif change == "source":
        edge["from"] = "FR-GOV-999"
    elif change == "pattern":
        edge["from"] = "fr-gov-1"
    elif change == "target":
        edge["to"] = " padded "
    elif change == "class":
        doc["requirements"]["FR-GOV-001"]["meta"]["class"] = "F9"
    elif change == "owner":
        doc["requirements"]["FR-GOV-001"]["meta"]["owner"] = "Somebody"
    elif change == "schema":
        doc["schema"] = "cap.trace-registry/v0"
    elif change == "state":
        del doc["requirements"]["FR-GOV-001"]["state"]["evidence"]
    return doc


@pytest.mark.parametrize(
    ("change", "check"),
    [
        ("relation", "TL-04"),
        ("vague", "TL-04"),
        ("duplicate", "TL-05"),
        ("applicability", "TL-01"),
        ("extra", "TL-01"),
        ("source", "TL-01"),
        ("pattern", "TL-01"),
        ("target", "TL-01"),
        ("class", "TL-01"),
        ("owner", "TL-01"),
        ("schema", "TL-01"),
        ("state", "TL-01"),
    ],
)
def test_each_violation_is_reported_by_its_check(change: str, check: str) -> None:
    assert check in checks(mutated(change))


def test_vague_relations_name_the_prohibition() -> None:
    lines = [f.line() for f in lint(mutated("vague"), SCHEMA)]
    assert any("Item 83 #38" in line for line in lines)


def test_vocabulary_matches_03_section_4_2() -> None:
    text = (ROOT / "docs/03_Requirements_Traceability_Matrix.md").read_text("utf-8")
    start = text.index("### 4.2 Controlled relation vocabulary")
    table = text[start : text.index("### 4.3", start)]
    cells = [row.split("|")[1] for row in table.splitlines() if row.startswith("| ")]
    listed = [r.strip() for cell in cells for r in cell.split("/")]
    assert tuple(r for r in listed if r != "Relation") == RELATIONS


# --- drift -------------------------------------------------------------------


def test_drift_names_what_changed_in_03() -> None:
    old = registry()
    new = registry(RECORD.replace("FRC-INV-01", "FRC-INV-02"), SECOND)
    drift = compare(old, new)
    assert drift.added_edges == ["FR-GOV-001 DERIVED_FROM FRC-INV-02 [PLANNED]"]
    assert drift.removed_edges == ["FR-GOV-001 DERIVED_FROM FRC-INV-01 [PLANNED]"]
    assert compare(old, registry(RECORD)).removed_requirements == ["NFR-GOV-009"]
    assert compare(old, old).empty


# --- the real repository -----------------------------------------------------


def test_committed_registry_passes_and_matches_the_real_03() -> None:
    doc, findings = lint_files(ROOT)
    assert findings == []
    assert len(doc["requirements"]) == 306
    catalog = json.loads((ROOT / "requirements/catalog.json").read_text("utf-8"))
    ids = {r["id"] for r in catalog["requirements"]}
    assert set(doc["requirements"]) == ids


def test_cli_exit_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(ROOT)
    assert main(["validate"]) == 0
    assert "PASS" in capsys.readouterr().out
    assert main(["validate", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["result"] == "PASS"
    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "traceability").mkdir()
    (repo / "docs/03_Requirements_Traceability_Matrix.md").write_text(
        rtm(RECORD), "utf-8"
    )
    (repo / "traceability/trace_schema.json").write_text(json.dumps(SCHEMA), "utf-8")
    monkeypatch.chdir(repo)
    assert main(["validate"]) == 2  # no registry yet: unreadable, not "clean"
    assert main(["seed"]) == 0
    assert main(["validate"]) == 0
    assert main(["drift", "--strict"]) == 0
    (repo / "docs/03_Requirements_Traceability_Matrix.md").write_text(
        rtm(RECORD, SECOND), "utf-8"
    )
    capsys.readouterr()
    assert main(["drift"]) == 0  # reported, not failed
    assert "NFR-GOV-009" in capsys.readouterr().out
    assert main(["drift", "--strict"]) == 1
    (repo / "traceability/trace_edges.yaml").write_text("edges: [\n", "utf-8")
    assert main(["validate"]) == 2
