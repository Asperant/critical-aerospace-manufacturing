"""Generated views and TL-07 freshness (WP-GOV-002, TEST-GOV-002-004, family
TEST-GOV-TRACELINT).
"""

from __future__ import annotations

import copy
import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from cap_trace.__main__ import main
from cap_trace.views import GENERATED, VIEWS, freshness, generate, write

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def registry() -> dict[str, Any]:
    loaded = yaml.safe_load((ROOT / "traceability/trace_edges.yaml").read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def rows(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


def test_views_are_pure_and_deterministic(registry: dict[str, Any]) -> None:
    first = generate(registry)
    assert first == generate(copy.deepcopy(registry))
    assert sorted(first) == sorted(VIEWS)


def test_requirements_view_has_one_row_per_requirement(
    registry: dict[str, Any],
) -> None:
    table = rows(generate(registry)["requirements.csv"])
    assert [r["requirement_id"] for r in table] == list(registry["requirements"])
    gov9 = next(r for r in table if r["requirement_id"] == "FR-GOV-009")
    assert gov9["verified_by"].startswith("TEST-GOV-TRACELINT INSP-GOV-ACCEPT")
    assert gov9["class"] == "F1" and gov9["owner"] == "Yavuz"


def test_verification_view_is_the_backward_trace(registry: dict[str, Any]) -> None:
    table = {
        r["asset"]: r for r in rows(generate(registry)["verification_coverage.csv"])
    }
    tracelint = table["TEST-GOV-TRACELINT"]
    assert tracelint["kind"] == "TEST"
    assert "FR-GOV-004" in tracelint["requirements"].split()
    assert int(tracelint["requirement_count"]) == len(tracelint["requirements"].split())
    assert table["BENCH-E2E-001"]["kind"] == "BENCH"


def test_claim_view_is_empty_until_claims_exist(registry: dict[str, Any]) -> None:
    assert generate(registry)["claim_coverage.csv"] == "claim,requirements\n"


def test_orphan_report_counts(registry: dict[str, Any]) -> None:
    report = json.loads(generate(registry)["orphan_report.json"])
    assert report["requirements"] == 306
    assert all(v == [] for v in report["orphan_requirements"].values())
    changed = copy.deepcopy(registry)
    changed["edges"] = [
        e
        for e in changed["edges"]
        if not (e["from"] == "FR-GOV-004" and e["relation"] == "DERIVED_FROM")
    ]
    report = json.loads(generate(changed)["orphan_report.json"])
    assert report["orphan_requirements"]["DERIVED_FROM"] == ["FR-GOV-004"]


def test_freshness_reports_missing_stale_and_foreign_files(
    tmp_path: Path, registry: dict[str, Any]
) -> None:
    assert {f.message.split(";")[0] for f in freshness(tmp_path, registry)} == {
        "missing"
    }
    write(tmp_path, registry)
    assert freshness(tmp_path, registry) == []
    (tmp_path / GENERATED / "requirements.csv").write_text("edited by hand\n", "utf-8")
    (tmp_path / GENERATED / "notes.txt").write_text("x\n", "utf-8")
    lines = [f.line() for f in freshness(tmp_path, registry)]
    assert (
        f"TL-07 {GENERATED}/requirements.csv: stale; run `mfgctl trace generate`"
        in lines
    )
    assert f"TL-07 {GENERATED}/notes.txt: not a generated view" in lines


def test_committed_views_are_fresh(registry: dict[str, Any]) -> None:
    assert freshness(ROOT, registry) == []


def test_cli_query_commands(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(ROOT)
    assert main(["requirement", "FR-GOV-005"]) == 0
    out = capsys.readouterr().out
    assert "VERIFIED_BY   TEST-GOV-TRACELINT  [PLANNED]" in out
    assert main(["requirement", "FR-NOPE-001"]) == 2
    assert main(["orphans"]) == 0
    assert "without DERIVED_FROM: 0" in capsys.readouterr().out
