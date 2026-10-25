"""TL-13 PR Requirement-Impact (WP-GOV-002, TEST-GOV-002-005, family
TEST-GOV-TRACELINT).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from cap_trace import Index
from cap_trace.__main__ import main
from cap_trace.impact import behavior_changing, check, declared, owners

ROOT = Path(__file__).resolve().parents[3]
INDEX = Index(requirements={"FR-GOV-004", "FR-GOV-005", "NFR-GOV-009"})
OWNERS = {"FR-GOV-004": "Asrın (@Asperant)", "FR-GOV-005": "Yavuz (@Yavuzgmus)"}
CODE = ["tools/trace/src/cap_trace/lint.py"]


def body(value: str, extra: str = "") -> str:
    return (
        "## Identity and scope\n\nWP/control ID: WP-GOV-002\n"
        f"Requirements (stable IDs, or NONE — reason / control-only scope): {value}\n"
        f"{extra}Architecture surfaces and authority boundaries: ARCH-PLAT-CICD\n"
    )


def lines(text: str, files: list[str] = CODE) -> list[str]:
    findings, _ = check(text, files, INDEX, OWNERS)
    return [f.line() for f in findings]


def test_only_behavior_changing_files_need_a_declaration() -> None:
    assert (
        behavior_changing(["docs/03_x.md", "evidence/WP-X-001/a.json", "README.md"])
        == []
    )
    assert behavior_changing(["09_change/CHG-040.yaml", "project_control/x.yaml"]) == []
    assert behavior_changing(["tools/a.py", "docs/b.md"]) == ["tools/a.py"]
    assert lines("", ["docs/04_Work_Breakdown_Structure.md"]) == []


def test_field_value_includes_continuation_lines_and_stops_at_the_next_field() -> None:
    text = body("FR-GOV-004,", extra="  FR-GOV-005 (completeness rule)\n")
    assert declared(text) == "FR-GOV-004, FR-GOV-005 (completeness rule)"
    assert declared("## Summary\nNothing here\n") is None


def test_declared_ids_pass_and_name_their_owners() -> None:
    findings, notes = check(body("FR-GOV-004, FR-GOV-005"), CODE, INDEX, OWNERS)
    assert findings == []
    assert "impacted requirements: FR-GOV-004, FR-GOV-005" in notes
    assert "owner Asrın (@Asperant): FR-GOV-004" in notes


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "FR-GOV-999",
            "TL-13 FR-GOV-999: declared requirement is not an active catalog ID",
        ),
        ("", "TL-13 PR body: behavior-changing PR without a Requirements field"),
        ("NONE", "TL-13 PR body: Requirements names no requirement ID"),
        (
            "see the summary below",
            "TL-13 PR body: Requirements names no requirement ID",
        ),
        ("XFR-GOV-004 only", "TL-13 PR body: Requirements names no requirement ID"),
    ],
)
def test_invalid_declarations_fail(value: str, expected: str) -> None:
    assert any(line.startswith(expected) for line in lines(body(value)))


def test_missing_field_fails() -> None:
    assert lines("## Summary\n\nchanges the linter\n") == [
        "TL-13 PR body: behavior-changing PR without a Requirements field "
        "(stable IDs, or NONE — reason)"
    ]


@pytest.mark.parametrize(
    "value",
    [
        "NONE — host control helper only, no product behavior",
        "control-only scope: Plane transition policy (CTRL-HOST-015)",
        "Not applicable: CI cache key change, no product requirement",
    ],
)
def test_explained_no_impact_passes(value: str) -> None:
    assert lines(body(value)) == []


def test_owners_come_from_the_team_table() -> None:
    table = owners(ROOT)
    assert table["Asrın"] == "Asperant"
    assert table["Yavuz"] == "Yavuzgmus"


def test_template_keeps_the_field_the_plane_helper_reads() -> None:
    template = (ROOT / ".github/pull_request_template.md").read_text("utf-8")
    assert declared(template) == ""
    assert any(line.startswith("Requirements (") for line in template.splitlines())


def test_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(ROOT)
    pr = tmp_path / "pr.md"
    files = tmp_path / "files.txt"
    files.write_text("tools/trace/src/cap_trace/impact.py\n", "utf-8")
    pr.write_text(body("FR-GOV-009, NFR-GOV-009"), "utf-8")
    assert main(["impact", "--body-file", str(pr), "--files-from", str(files)]) == 0
    assert (
        "owner Yavuz (@Yavuzgmus): FR-GOV-009, NFR-GOV-009" in capsys.readouterr().out
    )
    pr.write_text(body("FR-NOPE-001"), "utf-8")
    assert main(["impact", "--body-file", str(pr), "--files-from", str(files)]) == 1
    assert main(["impact", "--body-file", str(pr)]) == 2
