"""Structure of the ADR scaffold and the ADR-0003 pilot (WP-DOC-002, FR-GOV-004)."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest

ADR_DIR = Path(__file__).resolve().parents[2] / "docs" / "adr"
RTM = ADR_DIR.parent / "03_Requirements_Traceability_Matrix.md"
README = ADR_DIR / "README.md"
TEMPLATE = ADR_DIR / "TEMPLATE.md"
PILOT = ADR_DIR / "0003-nats-jetstream-event-backbone.md"

METADATA_FIELDS = [
    "ADR-ID",
    "Title",
    "Status",
    "Date",
    "DecisionOwner",
    "Reviewers",
    "DecisionLevel",
    "AffectedCapabilities",
    "AffectedRequirements",
    "AffectedRisks",
    "AffectedDebt",
    "Supersedes",
    "SupersededBy",
    "ValidationState",
]
BODY_SECTIONS = [
    "Context",
    "Decision Drivers",
    "Constraints/Assumptions",
    "Considered Options",
    "Decision",
    "Rationale",
    "Positive Consequences",
    "Negative Consequences",
    "Risks",
    "Operational Impact",
    "Security/Authority Impact",
    "Research/Evidence Impact",
    "Migration/Rollback",
    "Validation Plan",
    "Revisit Triggers",
    "References",
]
STATUSES = {"PROPOSED", "ACCEPTED", "REJECTED", "SUPERSEDED", "DEPRECATED"}
LEVELS = {"ADR-L1", "ADR-L2", "ADR-L3"}
VALIDATION_STATES = {"PENDING", "VALIDATED"}

MAP_ROW = re.compile(
    r"^\| (ADR-\d{4}) \| (backfill-\d{2}) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$",
    re.MULTILINE,
)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def metadata(text: str) -> dict[str, str]:
    found = re.findall(r"^- \*\*([A-Za-z-]+)\*\*: (.*)$", text, re.MULTILINE)
    keys = [key for key, _ in found]
    assert len(keys) == len(set(keys)), "duplicate metadata field"
    return dict(found)


def sections(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, re.MULTILINE)


def record_errors(text: str, adr_id: str) -> list[str]:
    """Every structural problem of one ADR record (empty when valid)."""
    errors: list[str] = []
    found = re.findall(r"^- \*\*([A-Za-z-]+)\*\*: (.*)$", text, re.MULTILINE)
    keys = [key for key, _ in found]
    meta = dict(found)
    if keys != METADATA_FIELDS:
        errors.append("metadata fields missing, duplicated, extra or out of order")
    if any(not value.strip() for value in meta.values()):
        errors.append("empty metadata value")
    if meta.get("ADR-ID") != adr_id:
        errors.append("ADR-ID does not match the record")
    if not text.startswith(f"# {adr_id}: {meta.get('Title', '')}\n"):
        errors.append("title heading does not match")
    if meta.get("Status") not in STATUSES:
        errors.append("invalid Status")
    if meta.get("DecisionLevel") not in LEVELS:
        errors.append("invalid DecisionLevel")
    if meta.get("ValidationState") not in VALIDATION_STATES:
        errors.append("invalid ValidationState")
    try:
        dt.date.fromisoformat(meta.get("Date", ""))
    except ValueError:
        errors.append("Date is not ISO 8601")
    if sections(text) != BODY_SECTIONS:
        errors.append("body sections missing, extra or out of order")
    return errors


def unresolved_links(text: str, base: Path) -> list[str]:
    targets = [t for t in LINK.findall(text) if not re.match(r"[a-z]+:|#", t)]
    return [t for t in targets if not (base / t.split("#")[0]).resolve().exists()]


def backfill_rows() -> list[tuple[str, ...]]:
    return [m.groups() for m in MAP_ROW.finditer(README.read_text(encoding="utf-8"))]


def test_backfill_map_has_thirteen_unique_ids() -> None:
    rows = backfill_rows()
    ids = [row[0] for row in rows]
    assert len(ids) == 13
    assert len(set(ids)) == 13
    assert len({row[2] for row in rows}) == 13, "decision titles must be unique"


def test_backfill_map_is_the_fixed_position_mapping() -> None:
    rows = backfill_rows()
    for position, row in enumerate(rows, start=1):
        assert row[0] == f"ADR-{position:04d}"
        assert row[1] == f"backfill-{position:02d}"
    assert [row[0] for row in rows] == [f"ADR-{n:04d}" for n in range(1, 14)]


def test_template_has_every_required_field_and_section_in_order() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert list(metadata(text)) == METADATA_FIELDS
    assert sections(text) == BODY_SECTIONS


def records() -> list[Path]:
    return sorted(ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md"))


def test_pilot_adr_0003_exists() -> None:
    assert PILOT in records()


def test_every_record_is_in_the_map_and_every_mapped_record_exists() -> None:
    rows = {row[0]: row for row in backfill_rows()}
    on_disk = {path.name[:4]: path for path in records()}
    for number, path in on_disk.items():
        assert f"ADR-{number}" in rows, f"{path.name} is not in the backfill map"
    for adr_id, row in rows.items():
        if row[4] == "Reserved":
            assert adr_id[4:] not in on_disk, f"{adr_id} has a record but is Reserved"
            assert row[5] == "pending"
        else:
            assert adr_id[4:] in on_disk, f"{adr_id} is mapped but has no record"
            assert on_disk[adr_id[4:]].name in row[5]


@pytest.mark.parametrize("path", records(), ids=lambda p: p.name)
def test_record_metadata_is_valid_and_matches_the_map(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    adr_id = f"ADR-{path.name[:4]}"
    assert record_errors(text, adr_id) == []
    meta = metadata(text)
    assert meta["Supersedes"] == "None"
    assert meta["SupersededBy"] == "None"
    mapped = {row[0]: row for row in backfill_rows()}[adr_id]
    assert meta["Title"] == mapped[2]
    assert mapped[4] == meta["Status"]
    assert path.name in mapped[5]


MUTATIONS = [
    ("- **Status**: ACCEPTED", "- **Status**: DONE"),
    ("- **DecisionLevel**: ADR-L3", "- **DecisionLevel**: ADR-L9"),
    ("- **ValidationState**: PENDING", "- **ValidationState**: MAYBE"),
    ("- **Date**: 2026-10-24", "- **Date**: 24/10/2026"),
    ("- **ADR-ID**: ADR-0003", "- **ADR-ID**: ADR-0004"),
    ("## Rationale\n", "## Reasons\n"),
    ("- **Reviewers**: Yavuz Gümüş\n", ""),
    ("- **AffectedDebt**: None", "- **AffectedDebt**:  "),
    ("## References", "## Decision\n\n## References"),
]


@pytest.mark.parametrize(("old", "new"), MUTATIONS)
def test_a_malformed_record_is_rejected(old: str, new: str) -> None:
    text = PILOT.read_text(encoding="utf-8")
    assert old in text
    assert record_errors(text.replace(old, new, 1), "ADR-0003")


def test_a_duplicated_metadata_field_is_rejected() -> None:
    text = PILOT.read_text(encoding="utf-8")
    duplicated = text.replace(
        "- **Status**: ACCEPTED", "- **Status**: ACCEPTED\n- **Status**: ACCEPTED", 1
    )
    assert record_errors(duplicated, "ADR-0003")


def test_a_broken_local_link_is_reported() -> None:
    assert unresolved_links("[gone](missing-record.md)", ADR_DIR) == [
        "missing-record.md"
    ]
    assert unresolved_links("[ok](README.md#top) [web](https://x.test)", ADR_DIR) == []


@pytest.mark.parametrize("path", [README, TEMPLATE, *records()], ids=lambda p: p.name)
def test_local_links_resolve(path: Path) -> None:
    assert unresolved_links(path.read_text(encoding="utf-8"), path.parent) == []


DECIDED_BY_EDGES = {
    "FR-CORE-012": "ADR-0012",
    "FR-SIM-001": "ADR-0007",
    "FR-SCH-009": "ADR-0008",
    "FR-AUTO-002": "ADR-0004",
    "FR-PLAT-001": "ADR-0011",
}


def test_rtm_has_no_backfill_placeholders_left() -> None:
    text = RTM.read_text(encoding="utf-8")
    assert not re.search(r"ADR:backfill-\d", text)
    assert not re.search(r'DECIDED_BY: \["backfill-', text)


@pytest.mark.parametrize(("requirement", "adr_id"), sorted(DECIDED_BY_EDGES.items()))
def test_rtm_decided_by_edge_points_at_the_minted_adr(
    requirement: str, adr_id: str
) -> None:
    text = RTM.read_text(encoding="utf-8")
    block = re.search(rf"^{requirement}:\n((?:  .*\n)+)", text, re.MULTILINE)
    assert block, f"{requirement} trace block not found"
    assert f'DECIDED_BY: ["{adr_id}"]' in block.group(1)
    rows = [ln for ln in text.splitlines() if ln.startswith(f"| {requirement} |")]
    assert any(adr_id in ln for ln in rows)
    mapped = {row[0]: row for row in backfill_rows()}[adr_id]
    assert mapped[4] == "ACCEPTED"


def test_every_decided_by_target_in_the_rtm_is_minted() -> None:
    text = RTM.read_text(encoding="utf-8")
    targets = set(re.findall(r'DECIDED_BY: \["(ADR-\d{4})"\]', text))
    assert targets == set(DECIDED_BY_EDGES.values())
    assert targets <= {row[0] for row in backfill_rows()}
