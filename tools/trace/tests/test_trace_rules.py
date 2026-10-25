"""Coverage and evidence rules TL-06, TL-08, TL-09, TL-11, TL-12 (WP-GOV-002,
TEST-GOV-002-003, family TEST-GOV-TRACELINT).

The real registry passes; each test changes one fact of it and expects exactly
the rule that owns that fact to fail. Sources are parsed from small fixtures.
"""

from __future__ import annotations

import copy
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from cap_trace import Index, RegistryError, lint, lint_files
from cap_trace.lint import load_base
from cap_trace.rules import kind
from cap_trace.sources import asset_table, load, verify_codes

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "traceability/trace_schema.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def real() -> tuple[dict[str, Any], Index]:
    registry, findings = lint_files(ROOT)
    assert findings == []
    return registry, load(ROOT)


Mutate = Callable[[dict[str, Any]], None]


def run(real: tuple[dict[str, Any], Index], mutate: Mutate) -> list[str]:
    registry = copy.deepcopy(real[0])
    mutate(registry)
    return [f.line() for f in lint(registry, SCHEMA, real[1])]


def edge(
    source: str, relation: str, target: str, applicability: str = "PLANNED"
) -> dict[str, str]:
    return {
        "from": source,
        "relation": relation,
        "to": target,
        "applicability": applicability,
    }


def drop(registry: dict[str, Any], source: str, relation: str) -> None:
    registry["edges"] = [
        e
        for e in registry["edges"]
        if not (e["from"] == source and e["relation"] == relation)
    ]


def node(registry: dict[str, Any], requirement: str) -> dict[str, Any]:
    return registry["requirements"][requirement]


# --- TL-06 ---------------------------------------------------------------------


def _unknown_run(r: dict[str, Any]) -> None:
    next(e for e in r["edges"] if e["relation"] == "EXECUTED_AS")["to"] = (
        "RUN-GOV-001-LOCAL-999"
    )


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_unknown_run, "TL-06 FR-GOV-001 EXECUTED_AS RUN-GOV-001-LOCAL-999"),
        (
            lambda r: r["edges"].append(
                edge("FR-GOV-001", "EVIDENCED_BY", "EVID-GOV-001", "RECORDED")
            ),
            "TL-06 FR-GOV-001 EVIDENCED_BY EVID-GOV-001: no sealed evidence bundle",
        ),
        (
            lambda r: r["edges"].append(
                edge("FR-GOV-001", "SUPPORTS_CLAIM", "CLAIM-01", "RECORDED")
            ),
            "TL-06 FR-GOV-001 SUPPORTS_CLAIM CLAIM-01: no ThesisClaimRegister",
        ),
    ],
)
def test_runs_evidence_and_claims_must_resolve(
    real: tuple[dict[str, Any], Index], mutate: Mutate, expected: str
) -> None:
    assert any(line.startswith(expected) for line in run(real, mutate))


def test_run_records_are_found_by_name_or_token(tmp_path: Path) -> None:
    folder = tmp_path / "evidence/WP-ABC-001"
    (folder / "RUN-ABC-001-DEV-001").mkdir(parents=True)
    (folder / "RUN-ABC-001-LOCAL-002.json").write_text("{}", "utf-8")
    (folder / "SLICE.md").write_text("recorded as RUN-ABC-001-SLICE-003.\n", "utf-8")
    (folder / "NOTE.md").write_text("XRUN-ABC-001-SLICE-004 is not a run\n", "utf-8")
    index = Index(root=tmp_path)
    assert index.run_exists("RUN-ABC-001-DEV-001")
    assert index.run_exists("RUN-ABC-001-LOCAL-002")
    assert index.run_exists("RUN-ABC-001-SLICE-003")
    assert not index.run_exists("RUN-ABC-001-SLICE-004")
    assert not index.run_exists("RUN-XYZ-001-DEV-001")  # other work package
    assert not index.run_exists("run-abc")
    assert not index.bundle_exists("EVID-ABC-001")


# --- TL-08 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("relation", "requirement"),
    [
        ("DERIVED_FROM", "FR-GOV-004"),
        ("ALLOCATED_TO", "FR-CORE-001"),
        ("VERIFIED_BY", "FR-GOV-005"),
    ],
)
def test_active_f0_f1_keep_their_coverage_edges(
    real: tuple[dict[str, Any], Index], relation: str, requirement: str
) -> None:
    lines = run(real, lambda r: drop(r, requirement, relation))
    assert (
        f"TL-08 {requirement}: active F{'0' if requirement == 'FR-CORE-001' else '1'} has no {relation} edge"
        in lines
    )


def test_h0_requirements_are_outside_the_f0_f1_completeness_rule(
    real: tuple[dict[str, Any], Index],
) -> None:
    lines = run(real, lambda r: drop(r, "NFR-GOV-001", "ALLOCATED_TO"))
    assert not any(line.startswith("TL-08") for line in lines)


def regress(real: tuple[dict[str, Any], Index], note: str | None) -> list[str]:
    base = real[0]
    current = copy.deepcopy(base)
    current["edges"] = [
        e
        for e in current["edges"]
        if not (e["from"] == "FR-SIM-007" and e["to"] == "BENCH-SIMVAL-001")
    ]
    if note is not None:
        node(current, "FR-SIM-007")["note"] = note
    return [f.line() for f in lint(current, SCHEMA, real[1], base)]


def test_a_removed_coverage_edge_needs_a_change_reference(
    real: tuple[dict[str, Any], Index],
) -> None:
    removed = "TL-08 FR-SIM-007 VERIFIED_BY BENCH-SIMVAL-001: coverage edge removed"
    assert any(line.startswith(removed) for line in regress(real, None))
    assert any(
        line.startswith(removed) for line in regress(real, "see CHG-999")
    )  # no such record
    assert not any(
        line.startswith(removed) for line in regress(real, "split per CHG-018")
    )


def test_base_registry_is_read_from_git(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True
        )

    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (tmp_path / "README.md").write_text("x\n", "utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "first")
    assert load_base(tmp_path, "HEAD") is None  # registry not introduced yet
    (tmp_path / "traceability").mkdir()
    (tmp_path / "traceability/trace_edges.yaml").write_text(
        "schema: x\nedges: []\n", "utf-8"
    )
    git("add", ".")
    git("commit", "-q", "-m", "second")
    assert load_base(tmp_path, "HEAD") == {"schema": "x", "edges": []}
    with pytest.raises(RegistryError, match="not available"):
        load_base(tmp_path, "no-such-revision")


# --- TL-09 ---------------------------------------------------------------------


def test_claims_on_stale_evidence_are_refused(
    real: tuple[dict[str, Any], Index],
) -> None:
    def stale(r: dict[str, Any]) -> None:
        node(r, "FR-GOV-001")["state"]["evidence"] = "STALE"
        r["edges"].append(edge("FR-GOV-001", "SUPPORTS_CLAIM", "CLAIM-01", "RECORDED"))

    assert any(
        line.startswith("TL-09 FR-GOV-001 SUPPORTS_CLAIM CLAIM-01")
        for line in run(real, stale)
    )


# --- TL-11 ---------------------------------------------------------------------


def _no_integrated_path(r: dict[str, Any]) -> None:
    drop(r, "FR-CORE-001", "EXERCISED_IN")
    r["edges"] = [
        e
        for e in r["edges"]
        if not (e["from"] == "FR-CORE-001" and e["to"] == "BENCH-E2E-001")
    ]


def _inspection_only(r: dict[str, Any]) -> None:
    drop(r, "NFR-GOV-001", "VERIFIED_BY")
    r["edges"].append(edge("NFR-GOV-001", "VERIFIED_BY", "INSP-GOV-NFR"))


def _no_benchmark(r: dict[str, Any]) -> None:
    r["edges"] = [
        e
        for e in r["edges"]
        if not (e["from"] == "FR-SIM-007" and e["to"] == "BENCH-SIMVAL-001")
    ]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (_no_integrated_path, "TL-11 FR-CORE-001: F0 without an integrated scenario"),
        (_inspection_only, "TL-11 NFR-GOV-001: H0 without an executable hard asset"),
        (_no_benchmark, "TL-11 FR-SIM-007: verify code B has no matching asset kind"),
        (
            _no_integrated_path,
            "TL-11 FR-CORE-001: verify code E has no matching asset kind",
        ),
    ],
)
def test_class_sufficiency(
    real: tuple[dict[str, Any], Index], mutate: Mutate, expected: str
) -> None:
    assert any(line.startswith(expected) for line in run(real, mutate))


@pytest.mark.parametrize(
    ("asset", "expected"),
    [
        ("TEST-GOV-001", "TEST"),
        ("BENCH-RQ1-001", "BENCH"),
        ("INSP-GOV-ACCEPT", "INSP"),
        ("RESTORE-HOST-001", "DRILL"),
        ("AV-SCEN-03", "SCENARIO"),
        ("DEMO-GS01-001", "DEMO"),
        ("WHATEVER-1", "UNKNOWN"),
    ],
)
def test_asset_kind_by_prefix(asset: str, expected: str) -> None:
    assert kind(asset, Index()) == expected


def test_registry_kinds_environments_and_codes_are_parsed() -> None:
    rtm = (
        "## 9. View D\n\n| ID | Class | Verify codes | X |\n|---|---|---|---|\n"
        "| FR-A-001 | F1 | T/E/N | TEST-A |\n| NFR-B-001 | H0 | I/T (derived) | INSP-B |\n\n"
        "### 9.X Verification Asset Registry\n\n#### TEST (1)\n\n"
        "| Asset family | Owner | Scope | Lane | Min env | EV |\n|---|---|---|---|---|---|\n"
        "| TEST-A | Y | s | L | INTEGRATION | EV-L3 |\n\n#### INSP (1)\n\n"
        "| INSP-B | Y | s | L | CI | EV-L2 |\n\n## 10. Next\n"
    )
    assert verify_codes(rtm) == {"FR-A-001": {"T", "E", "N"}, "NFR-B-001": {"I", "T"}}
    kinds, envs = asset_table(rtm)
    assert kinds == {"TEST-A": "TEST", "INSP-B": "INSP"}
    assert envs == {"TEST-A": "INTEGRATION", "INSP-B": "CI"}


# --- TL-12 ---------------------------------------------------------------------


def test_verified_needs_evidence(real: tuple[dict[str, Any], Index]) -> None:
    def verified(r: dict[str, Any]) -> None:
        node(r, "FR-GOV-001")["state"]["coverage"] = "VERIFIED"
        node(r, "NFR-GOV-001")["state"]["evidence"] = "CURRENT"

    lines = run(real, verified)
    assert "TL-12 FR-GOV-001: VERIFIED/CURRENT without an EVIDENCED_BY edge" in lines
    assert (
        "TL-12 NFR-GOV-001: final NFR VERIFIED without an observed measurement" in lines
    )


def test_cli_accepts_a_base_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    from cap_trace.__main__ import main

    monkeypatch.chdir(ROOT)
    assert main(["validate", "--base", "HEAD"]) == 0
    assert main(["validate", "--base", "no-such-revision"]) == 2
