"""Structure of the ADR scaffold and the ADR-0003 pilot (WP-DOC-002, FR-GOV-004)."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest

ADR_DIR = Path(__file__).resolve().parents[2] / "docs" / "adr"
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
    meta = metadata(text)
    adr_id = f"ADR-{path.name[:4]}"
    assert list(meta) == METADATA_FIELDS
    assert all(value.strip() for value in meta.values())
    assert meta["ADR-ID"] == adr_id
    assert text.startswith(f"# {adr_id}: {meta['Title']}\n")
    assert meta["Status"] in STATUSES
    assert meta["DecisionLevel"] in LEVELS
    assert meta["ValidationState"] in VALIDATION_STATES
    assert meta["Supersedes"] == "None"
    assert meta["SupersededBy"] == "None"
    dt.date.fromisoformat(meta["Date"])
    assert sections(text) == BODY_SECTIONS
    mapped = {row[0]: row for row in backfill_rows()}[adr_id]
    assert meta["Title"] == mapped[2]
    assert mapped[4] == meta["Status"]
    assert path.name in mapped[5]


@pytest.mark.parametrize("path", [README, TEMPLATE, *records()], ids=lambda p: p.name)
def test_local_links_resolve(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    targets = [t for t in LINK.findall(text) if not re.match(r"[a-z]+:|#", t)]
    for target in targets:
        assert (path.parent / target.split("#")[0]).resolve().exists(), target
