"""WP-TEST-007: rule catalog, requirement context and the exception process.

TEST-ARCH-BOUNDARY (CI, EV-L2). The exception registry is exercised on temporary
repositories; the real repository must pass with the registry it carries.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import pytest
from check_architecture_boundaries import (
    EXCEPTIONS_PATH,
    MAX_EXCEPTION_DAYS,
    RULES_PATH,
    Violation,
    check,
    check_exceptions,
    check_service_sources,
    describe,
    load_rules,
)

ROOT = Path(__file__).resolve().parents[2]
TODAY = dt.date(2026, 10, 28)
BAD_FILE = "services/operations-bff/src/bad.py"


def test_catalog_matches_the_checker_and_03() -> None:
    """Every rule id the checker emits is cataloged, and `architecture` equals 03 §17."""
    rules = load_rules(ROOT)
    script = (ROOT / "ci/scripts/check_architecture_boundaries.py").read_text("utf-8")
    emitted = set(re.findall(r'"(BR-\d\d)"', script))
    assert emitted <= set(rules), emitted - set(rules)
    assert set(rules) == {"BR-01", "BR-02", "BR-03", "BR-04", "BR-05"}
    rtm = (ROOT / "docs/03_Requirements_Traceability_Matrix.md").read_text("utf-8")
    for rule in rules.values():
        allocated: set[str] = set()
        for requirement in rule["requirements"]:
            block = re.search(rf"^{requirement}:\n((?:  .*\n)+)", rtm, re.M)
            assert block, f"{requirement} has no 03 §17 record"
            line = re.search(r"ALLOCATED_TO: \[([^\]]*)\]", block[1])
            assert line, requirement
            allocated |= {item.strip() for item in line[1].split(",")}
        assert set(rule["architecture"]) == allocated, rule["id"]
        assert isinstance(rule["exception_allowed"], bool)
        if not rule["exception_allowed"]:
            assert rule["why_no_exception"], rule["id"]


def test_rule_requirements_are_active_in_the_catalog() -> None:
    active = {
        item["id"]
        for item in json.loads((ROOT / "requirements/catalog.json").read_text("utf-8"))[
            "requirements"
        ]
    }
    for rule in load_rules(ROOT).values():
        assert set(rule["requirements"]) <= active, rule["id"]


def repo(
    tmp_path: Path, exceptions: list[dict[str, Any]], chg: str = "APPROVED"
) -> Path:
    """A minimal repository: catalog, one violating service file, CHG register, registry."""
    (tmp_path / "ci/architecture").mkdir(parents=True)
    (tmp_path / "09_change").mkdir()
    (tmp_path / RULES_PATH).write_text((ROOT / RULES_PATH).read_text("utf-8"))
    (tmp_path / EXCEPTIONS_PATH).write_text(
        json.dumps(
            {"schema": "cap.architecture-exceptions/v1", "exceptions": exceptions}
        )
    )
    with (tmp_path / "09_change/change_requests.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "id",
                "title",
                "class",
                "review_risk_class",
                "owner",
                "decision",
                "status",
                "control_item",
            ]
        )
        writer.writerow(
            ["CHG-900", "t", "C1", "CR-1", "Yavuz", chg, "APPROVED", "CTRL-X"]
        )
    source = tmp_path / BAD_FILE
    source.parent.mkdir(parents=True)
    source.write_text("import psycopg\n", encoding="utf-8")
    return tmp_path


def entry(**changes: Any) -> dict[str, Any]:
    base = {
        "id": "EX-1",
        "rule": "BR-02",
        "path": BAD_FILE,
        "owner": "Yavuz",
        "reason": "Temporary read-only reporting query until the contract exists",
        "chg": "CHG-900",
        "expires": (TODAY + dt.timedelta(days=30)).isoformat(),
    }
    return base | changes


def run(root: Path) -> tuple[list[str], list[str]]:
    return check_exceptions(root, check_service_sources(root), TODAY)


def test_violations_carry_rule_and_requirement_context(tmp_path: Path) -> None:
    root = repo(tmp_path, [])
    (violation,) = check_service_sources(root)
    assert isinstance(violation, Violation) and violation.rule == "BR-02"
    assert violation.startswith("[BR-02] services/operations-bff/src/bad.py:1:")
    text = "\n".join(describe(root, violation))
    assert "FR-EVT-007" in text and "FR-CORE-013" in text and "ARCH-CORE-DB" in text
    assert "rule owner Asrın" in text and "approved CHG" in text


def test_without_an_exception_the_violation_stands(tmp_path: Path) -> None:
    remaining, applied = run(repo(tmp_path, []))
    assert len(remaining) == 1 and applied == []


def test_a_valid_exception_covers_exactly_its_rule_and_file(tmp_path: Path) -> None:
    root = repo(tmp_path, [entry()])
    other = root / "services/operations-bff/src/other.py"
    other.write_text("import sqlalchemy\n", encoding="utf-8")
    remaining, applied = run(root)
    assert len(applied) == 1 and "EXCEPTED" in applied[0] and "CHG-900" in applied[0]
    assert (
        len(remaining) == 1 and "other.py" in remaining[0]
    ), "another file is not covered"


@pytest.mark.parametrize(
    ("change", "expect"),
    [
        ({"rule": "BR-04"}, "does not allow exceptions"),
        ({"rule": "BR-01"}, "does not allow exceptions"),
        ({"rule": "BR-99"}, "unknown rule"),
        (
            {"path": "services/operations-bff/src/missing.py"},
            "not an existing repository file",
        ),
        ({"path": "../outside.py"}, "not an existing repository file"),
        ({"owner": " "}, "owner is missing"),
        ({"reason": "temporary"}, "reason is missing or too short"),
        ({"chg": "CHG-901"}, "not an approved change"),
        ({"chg": ""}, "not an approved change"),
        ({"expires": "soon"}, "not an ISO date"),
        ({"expires": "2026-10-28"}, "expired on"),
        ({"expires": "2026-01-01"}, "expired on"),
        ({"expires": "2027-12-31"}, "beyond the"),
    ],
)
def test_an_invalid_exception_is_rejected_and_the_violation_stays(
    tmp_path: Path, change: dict[str, Any], expect: str
) -> None:
    remaining, applied = run(repo(tmp_path, [entry(**change)]))
    assert applied == []
    text = "\n".join(remaining)
    assert expect in text and "[BR-05]" in text
    if change.get("rule") not in {"BR-04", "BR-01"} and "path" not in change:
        assert "[BR-02]" in text, "an invalid exception must not hide the violation"


def test_a_draft_change_does_not_approve_an_exception(tmp_path: Path) -> None:
    remaining, applied = run(repo(tmp_path, [entry()], chg="DRAFT"))
    assert applied == [] and any("not an approved change" in item for item in remaining)


def test_an_approved_with_conditions_change_counts(tmp_path: Path) -> None:
    _, applied = run(repo(tmp_path, [entry()], chg="APPROVED_WITH_CONDITIONS"))
    assert len(applied) == 1


def test_a_stale_exception_is_itself_a_violation(tmp_path: Path) -> None:
    root = repo(tmp_path, [entry()])
    (root / BAD_FILE).write_text("print('fixed')\n", encoding="utf-8")
    remaining, applied = run(root)
    assert applied == [] and len(remaining) == 1
    assert "[BR-05]" in remaining[0] and "stale" in remaining[0]


def test_the_expiry_limit_is_enforced_at_the_boundary(tmp_path: Path) -> None:
    last_day = (TODAY + dt.timedelta(days=MAX_EXCEPTION_DAYS)).isoformat()
    _, applied = run(repo(tmp_path, [entry(expires=last_day)]))
    assert len(applied) == 1
    first_bad = (TODAY + dt.timedelta(days=MAX_EXCEPTION_DAYS + 1)).isoformat()
    remaining, _ = run(repo(tmp_path / "b", [entry(expires=first_bad)]))
    assert any("beyond the" in item for item in remaining)


def test_duplicate_exception_ids_are_rejected(tmp_path: Path) -> None:
    remaining, _ = run(repo(tmp_path, [entry(), entry(path="x.py")]))
    assert any("duplicate id" in item for item in remaining)


@pytest.mark.parametrize(
    "registry",
    [
        "{",
        '{"schema": "other", "exceptions": []}',
        '{"schema": "cap.architecture-exceptions/v1"}',
    ],
)
def test_an_unreadable_registry_fails_closed(tmp_path: Path, registry: str) -> None:
    root = repo(tmp_path, [])
    (root / EXCEPTIONS_PATH).write_text(registry, encoding="utf-8")
    remaining, _ = run(root)
    assert any("[BR-05]" in item and "unreadable" in item for item in remaining)
    assert any("[BR-02]" in item for item in remaining)
    (root / EXCEPTIONS_PATH).unlink()
    assert any("unreadable" in item for item in run(root)[0])


def test_the_real_repository_passes_with_the_registry_it_carries() -> None:
    assert check(ROOT, TODAY) == []
    registry = json.loads((ROOT / EXCEPTIONS_PATH).read_text("utf-8"))
    assert (
        registry["exceptions"] == []
    ), "exceptions are temporary: this test is the reminder to remove or re-approve them"
