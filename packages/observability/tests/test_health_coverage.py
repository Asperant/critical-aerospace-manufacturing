from __future__ import annotations

import copy
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from cap_observability import check_health_report
from cap_observability.__main__ import main
from cap_observability.coverage import MANDATORY, check
from cap_observability.health import Check, aggregate, health_report

REPO = Path(__file__).resolve().parents[3]
SCHEMAS = Path(__file__).resolve().parents[1] / "src/cap_observability/schemas"
TODAY = date(2026, 10, 23)


def chk(cls: str, status: str, kind: str = "dependency", name: str = "db") -> Check:
    return Check(name, kind, cls, status)  # type: ignore[arg-type]


# ------------------------------------------------------------------ health ---


@pytest.mark.parametrize(
    ("checks", "expected"),
    [
        ([("REQUIRED", "READY")], "READY"),
        ([("REQUIRED", "UNAVAILABLE")], "UNAVAILABLE"),
        ([("REQUIRED", "DEGRADED")], "DEGRADED"),
        ([("DEGRADABLE", "UNAVAILABLE")], "DEGRADED"),
        ([("OPTIONAL", "UNAVAILABLE")], "READY"),
        ([("DEGRADABLE", "UNAVAILABLE"), ("REQUIRED", "UNAVAILABLE")], "UNAVAILABLE"),
    ],
)
def test_dependency_classes_decide_the_aggregate(
    checks: list[tuple[str, str]], expected: str
) -> None:
    items = [{"class": c, "status": s} for c, s in checks]
    assert aggregate(items) == expected


def test_report_conforms_and_is_derived() -> None:
    report = health_report(
        "manufacturing-core",
        "local-yavuz",
        [
            chk("REQUIRED", "READY", "readiness", "api"),
            chk("REQUIRED", "READY", "dependency", "postgresql"),
            Check(
                "telemetry",
                "dependency",
                "OPTIONAL",
                "UNAVAILABLE",
                "collector down",
                2.5,
            ),
        ],
        correlation_id="health-1",
        now=datetime(2026, 10, 23, 20, 0, tzinfo=UTC),
    )
    assert check_health_report(report) == []
    assert report["status"] == "READY"
    assert report["checked_at"] == "2026-10-23T20:00:00.000Z"


def test_not_live_is_never_ready() -> None:
    report = health_report(
        "manufacturing-core", "local-yavuz", [chk("REQUIRED", "READY")], live=False
    )
    assert report["status"] == "UNAVAILABLE"
    assert check_health_report(report) == []


def test_published_example_conforms() -> None:
    example = json.loads((SCHEMAS / "health.json").read_text("utf-8"))
    assert check_health_report(example) == []


def test_claimed_status_must_match_the_checks() -> None:
    example = json.loads((SCHEMAS / "health.json").read_text("utf-8"))
    example["status"] = "READY"  # a required-free DEGRADABLE failure says DEGRADED
    assert any("§68" in e for e in check_health_report(example))


def test_empty_checks_are_refused() -> None:
    with pytest.raises(ValueError):
        health_report("manufacturing-core", "local-yavuz", [])


# ---------------------------------------------------------------- coverage ---


def registry(**overrides: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for name in MANDATORY:
        entry: dict[str, Any] = {
            "name": name,
            "owner": "Asrın",
            "runtime": "python",
            "path": f"services/{name}",
            "logging": "NOT_PRESENT",
            "health": "NOT_PRESENT",
        }
        entry.update(overrides.get(name, {}))
        entries.append(entry)
    return {"schema": "cap.telemetry-coverage/v1", "deployables": entries}


def service(root: Path, name: str, *, depends: bool, source: str) -> None:
    path = root / "services" / name
    (path / "src").mkdir(parents=True)
    deps = '["cap-observability[otel]"]' if depends else "[]"
    (path / "pyproject.toml").write_text(f"[project]\ndependencies = {deps}\n")
    (path / "src" / "app.py").write_text(source)


EXEMPT = {
    "reason": "waiting for the owner",
    "owner": "Yavuz",
    "expires_on": "2026-11-06",
}


def test_nothing_present_is_clean(tmp_path: Path) -> None:
    result = check(registry(), tmp_path, TODAY)
    assert result.violations == []
    assert "0/9 mandatory deployables exist" in result.summary()


def test_existing_service_must_be_declared(tmp_path: Path) -> None:
    service(tmp_path, "vision-service", depends=False, source="")
    result = check(registry(), tmp_path, TODAY)
    assert any("vision-service: exists" in v for v in result.violations)


def test_adopted_requires_real_use(tmp_path: Path) -> None:
    service(tmp_path, "vision-service", depends=False, source="print('hi')")
    claim = {"vision-service": {"logging": "ADOPTED", "health": "ADOPTED"}}
    result = check(registry(**claim), tmp_path, TODAY)
    assert len([v for v in result.violations if "ADOPTED but" in v]) == 2


def test_adopted_and_used_counts(tmp_path: Path) -> None:
    service(
        tmp_path,
        "vision-service",
        depends=True,
        source="configure('vision-service', '0.1')\nhealth_report('v', 'e', checks)\n",
    )
    claim = {"vision-service": {"logging": "ADOPTED", "health": "ADOPTED"}}
    result = check(registry(**claim), tmp_path, TODAY)
    assert result.violations == []
    assert "logging 1/1 adopted" in result.summary()


@pytest.mark.parametrize(
    ("exemption", "problem"),
    [
        (None, "needs an exemption"),
        (EXEMPT | {"expires_on": "2026-10-01"}, "expired"),
        (EXEMPT | {"expires_on": "2026-12-31"}, "longer than 30 days"),
        (EXEMPT | {"owner": "Mallory"}, "team owner"),
        (EXEMPT | {"reason": " "}, "reason"),
    ],
)
def test_pending_needs_a_bounded_exemption(
    tmp_path: Path, exemption: dict[str, str] | None, problem: str
) -> None:
    service(tmp_path, "vision-service", depends=False, source="")
    entry: dict[str, Any] = {"logging": "PENDING", "health": "PENDING"}
    if exemption is not None:
        entry["exemption"] = exemption
    result = check(registry(**{"vision-service": entry}), tmp_path, TODAY)
    assert any(problem in v for v in result.violations), result.violations


def test_absent_service_cannot_claim_coverage(tmp_path: Path) -> None:
    result = check(
        registry(**{"scheduler-service": {"logging": "ADOPTED"}}), tmp_path, TODAY
    )
    assert any("must be NOT_PRESENT" in v for v in result.violations)


def test_registry_must_list_the_nine(tmp_path: Path) -> None:
    data = registry()
    data["deployables"] = data["deployables"][:8]
    assert check(data, tmp_path, TODAY).violations


def test_repository_registry_matches_the_repository() -> None:
    data = json.loads((REPO / "infra/observability/coverage.json").read_text("utf-8"))
    result = check(data, REPO, date.today())
    assert result.violations == [], result.violations
    assert "manufacturing-core" in result.present


def test_cli_reports_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(registry()))
    monkeypatch.chdir(tmp_path)
    assert main(["check-coverage", str(path)]) == 0
    assert "telemetry coverage" in capsys.readouterr().out
    bad = copy.deepcopy(registry())
    bad["deployables"][0]["owner"] = "Mallory"
    path.write_text(json.dumps(bad))
    assert main(["check-coverage", str(path)]) == 1
    assert main(["check-coverage", str(tmp_path / "missing.json")]) == 2
