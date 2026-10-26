"""Referenced IDs exist (TL-02), superseded misuse (TL-03) and prefix-boundary-safe
matching (TL-10) (WP-GOV-002, TEST-GOV-002-002, family TEST-GOV-TRACELINT).

A small repository fixture holds every identity source; the real repository is
checked too, and single-edge mutations of the real registry must each fail.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from cap_trace import Index, lint, lint_files, resolve, tokens
from cap_trace.__main__ import main
from cap_trace.sources import catalog_ids, load, sections, verification_ids

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "traceability/trace_schema.json").read_text("utf-8"))


# --- TL-10 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("see SIM-REAL-INV-01 here", {"SIM-REAL-INV-01"}),  # never REAL-INV-01
        ("NFR-RES-001 and RES-INV-03", {"NFR-RES-001", "RES-INV-03"}),  # never RES-001
        ("01 Item 34 cites ARCH-INV-04.", {"ARCH-INV-04"}),  # not ARCH-INV-004
        ("02 uses ARCH-INV-004, globally", {"ARCH-INV-004"}),  # not ARCH-INV-04
        ("(FRC-INV-01) and `TEST-GOV-001`", {"FRC-INV-01", "TEST-GOV-001"}),
        ("lower-FRC-INV-01 or FRC-INV-01x", set[str]()),  # glued to other text
    ],
)
def test_identities_match_with_prefix_boundaries(text: str, expected: set[str]) -> None:
    assert tokens(text) == expected


# --- sources -------------------------------------------------------------------


def test_sections_stop_at_the_next_heading_of_the_same_level() -> None:
    text = "## A\n### Registry\nx\n#### sub\ny\n### Other\nz\n## B\n"
    (body,) = sections(text, re.compile("Registry"))
    assert "y" in body and "z" not in body


def test_catalog_status_separates_active_and_retired() -> None:
    active, inactive = catalog_ids(
        {
            "requirements": [
                {"id": "FR-A-001", "status": None},
                {"id": "FR-A-002", "status": "SUPERSEDED"},
            ],
            "retired_ids": ["FR-A-003"],
        }
    )
    assert active == {"FR-A-001"} and inactive == {"FR-A-002", "FR-A-003"}


def test_verification_ids_come_from_registry_assets_and_strategy() -> None:
    rtm = (
        "### 9.X Verification Asset Registry\n\n| TEST-X-FAMILY | Y |\n\n## 10. Next\n"
        "## 19. Maintenance\n| Concrete asset | Family |\n|---|---|\n"
        "| TEST-X-001 (`t`) | TEST-X-FAMILY |\n\n## 20. End\n"
    )
    strategy = {
        "suites": [{"test_ids": ["TEST-X-002-001"]}],
        "test_id": {"legacy": ["TEST-OLD-001"]},
    }
    assert verification_ids(rtm, strategy) == {
        "TEST-X-FAMILY",
        "TEST-X-001",
        "TEST-X-002-001",
        "TEST-OLD-001",
    }


def test_fixture_sources_are_read(
    mini_repo: Path, write_rtm: Callable[..., None]
) -> None:
    write_rtm()
    index = load(mini_repo)
    assert index.items == {81, 82}
    assert index.architecture == {"ARCH-PLAT-CICD", "ARCH-DATA-OBJ"}
    assert "IC-AUTO-003" in index.contracts
    assert {
        "TEST-GOV-TRACELINT",
        "TEST-GOV-001",
        "TEST-GOV-002-001",
    } <= index.verification
    assert index.decisions == {"ADR-0005"}


def test_real_sources_include_the_append_only_allocations() -> None:
    index = load(ROOT)
    assert len(index.items) == 85
    assert {"ARCH-PLAT-CICD", "ARCH-AI-ML", "ARCH-VIS-DATA"} <= index.architecture
    assert not any(a.startswith("ARCH-INV-") for a in index.architecture)
    assert "IC-AUTO-003" in index.contracts
    assert "TEST-GOV-TRACELINT" in index.verification
    assert len(index.requirements) == 306


# --- TL-02 resolution ----------------------------------------------------------

INDEX = Index(
    requirements={"FR-GOV-001"},
    items={81},
    master={"FRC-INV-01", "PLAT-R01", "AV-SCEN-01", "SIM-REAL-INV-01"},
    architecture={"ARCH-PLAT-CICD"},
    contracts={"IC-AUTO-003"},
    verification={"TEST-GOV-TRACELINT"},
    decisions={"ADR-0005"},
    root=ROOT,
)


@pytest.mark.parametrize(
    ("relation", "target", "ok"),
    [
        ("DERIVED_FROM", "ITEM-81", True),
        ("DERIVED_FROM", "ITEM-99", False),
        ("DERIVED_FROM", "FRC-INV-01", True),
        ("DERIVED_FROM", "REAL-INV-01", False),  # only SIM-REAL-INV-01 exists
        ("DERIVED_FROM", "SOMETHING", False),
        ("ALLOCATED_TO", "ARCH-PLAT-CICD", True),
        ("ALLOCATED_TO", "ARCH-PLAT-NOPE", False),
        ("VERIFIED_BY", "TEST-GOV-TRACELINT", True),
        ("VERIFIED_BY", "TEST-GOV-UNKNOWN", False),
        ("DECIDED_BY", "ADR-0005", True),
        ("DECIDED_BY", "ADR-0099", False),
        ("EXERCISED_IN", "AV-SCEN-01", True),
        ("EXERCISED_IN", "AV-SCEN-99", False),
        ("MITIGATES", "PLAT-R01", True),
        ("MITIGATES", "PLAT-R99", False),
        ("MITIGATES", "some risk", False),
        ("EXPOSED_BY", "IC-AUTO-003", True),
        ("EXPOSED_BY", "IC-AUTO-999", False),
        ("EXPOSED_BY", "IC-AUTO-*", True),
        ("EXPOSED_BY", "IC-NOPE-*", False),
        ("EXPOSED_BY", "telemetry stream", True),  # descriptive surface
        ("REALIZED_BY", "TBD_BY_IMPLEMENTATION", True),
        ("REALIZED_BY", "repo:requirements/catalog.json", True),
        ("REALIZED_BY", "repo:requirements/missing.json", False),
        ("REALIZED_BY", "repo:../outside", False),
        ("REALIZED_BY", "somewhere", False),
        ("USES_DATA", "DatasetVersion", True),  # artifact type, no registry
    ],
)
def test_targets_resolve_against_their_registry(
    relation: str, target: str, ok: bool
) -> None:
    assert (resolve(relation, target, INDEX) is None) is ok


# --- TL-02/TL-03 on the real registry ------------------------------------------


@pytest.fixture(scope="module")
def real() -> tuple[dict[str, Any], Index]:
    registry, findings = lint_files(ROOT)
    assert findings == []
    return registry, load(ROOT)


def first(registry: dict[str, Any], relation: str) -> dict[str, str]:
    return next(e for e in registry["edges"] if e["relation"] == relation)


@pytest.mark.parametrize(
    ("relation", "target", "message"),
    [
        ("ALLOCATED_TO", "ARCH-PLAT-NOPE", "02 component registry"),
        ("DERIVED_FROM", "ITEM-99", "no such 01 item"),
        ("VERIFIED_BY", "TEST-NOPE-FAMILY", "verification family"),
        ("REALIZED_BY", "repo:tools/does-not-exist.py", "does not exist"),
    ],
)
def test_one_bad_edge_in_the_real_registry_fails(
    real: tuple[dict[str, Any], Index], relation: str, target: str, message: str
) -> None:
    registry, index = copy.deepcopy(real[0]), real[1]
    first(registry, relation)["to"] = target
    lines = [f.line() for f in lint(registry, SCHEMA, index)]
    assert any(line.startswith("TL-02") and message in line for line in lines), lines


def test_catalog_and_registry_nodes_must_match(
    real: tuple[dict[str, Any], Index],
) -> None:
    registry, index = copy.deepcopy(real[0]), real[1]
    node = registry["requirements"].pop("FR-GOV-010")
    registry["edges"] = [e for e in registry["edges"] if e["from"] != "FR-GOV-010"]
    lines = [f.line() for f in lint(registry, SCHEMA, index)]
    assert "TL-02 FR-GOV-010: active catalog requirement has no registry node" in lines
    registry["requirements"]["FR-GOV-999"] = node
    assert any(
        "FR-GOV-999: node is not a catalog requirement" in x
        for x in (f.line() for f in lint(registry, SCHEMA, index))
    )


def test_superseded_requirements_carry_no_edges(
    real: tuple[dict[str, Any], Index],
) -> None:
    registry = real[0]
    index = copy.deepcopy(real[1])
    index.requirements.discard("FR-GOV-010")
    index.inactive.add("FR-GOV-010")
    checks = {(f.check, f.subject) for f in lint(registry, SCHEMA, index)}
    assert ("TL-03", "FR-GOV-010") in checks


def test_cli_reports_unreadable_sources(
    mini_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (mini_repo / "traceability/trace_edges.yaml").write_text("schema: x\n", "utf-8")
    monkeypatch.chdir(mini_repo)
    assert main(["validate"]) == 2  # 03 is missing: sources unreadable, never "clean"
