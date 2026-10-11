import re

import pytest

from projectctl.parsers.markdown import headings, table_cells
from projectctl.parsers.wbs import parse_wbs
from projectctl.validators.wbs import validate


def codes(catalog):
    return {d.code for d in validate(catalog)}


def test_extraction_and_provenance(sample):
    catalog = parse_wbs(sample)
    assert not catalog.diagnostics
    wp, = catalog.work_packages
    assert wp.id == "WP-SIM-001"
    assert wp.capability_area == "WP-SIM"
    assert wp.title == "Kernel"
    assert wp.purpose == "Deterministic execution."
    assert wp.primary_owner.canonical_name == "Batuhan Kaya"
    assert wp.primary_owner.source_spelling == "Batu"
    assert wp.supporting_reviewers[0].canonical_name == "Asrın Dündar"
    assert wp.requirement_refs == ["FR-SIM-001", "NFR-REP-001"]
    assert wp.architecture_refs == ["ARCH-SIM-ENGINE"]
    assert wp.readiness_refs == ["DN-SIM-KERNEL"]
    assert wp.dependency_refs == ["DEP-001"]
    assert wp.deliverables == ["kernel", "RNG registry"]
    assert wp.major_tasks == ["implement clock"]
    assert wp.verification_expectations == "TEST-SIM-KERNEL"
    assert wp.evidence_expectations == "CI evidence; NOT_YET_EXECUTED"
    assert wp.milestone == "M1" and wp.sprint_window == "S2"
    assert wp.dor_refs == ["DOR-WP-01", "DOR-WP-02"]
    assert wp.dod_refs == ["DOD-WP-01", "DOD-WP-02"]
    assert wp.cut_fallback == "No cut."
    assert wp.raw_planning_status == "NOT_STARTED"
    assert wp.provenance.path == "docs/04_Work_Breakdown_Structure.md"
    lines = sample.splitlines()
    assert lines[wp.provenance.line_start - 1] == "#### WP-SIM-001 — Kernel"
    assert "\n".join(lines[wp.provenance.line_start - 1:wp.provenance.line_end]) == wp.provenance.raw_context
    assert wp.repository_reference is None
    assert "AREA_INDEX_CONFLICT" not in codes(catalog)


def test_duplicate_wp_detection(sample):
    card = sample[sample.index("#### WP-SIM-001"):sample.index("## 7.")]
    catalog = parse_wbs(sample.replace("## 7.", card + "## 7."))
    assert len(catalog.work_packages) == 2
    assert "DUPLICATE_WP" in codes(catalog)


@pytest.mark.parametrize("bad", ["WP-SIM-01", "WP-SIM-0001", "WP-sim-001", "WP-SIM-001-extra", "WP-NORMAL"])
def test_malformed_id_rejection(sample, bad):
    catalog = parse_wbs(sample.replace("#### WP-SIM-001", f"#### {bad}"))
    assert not catalog.work_packages
    assert "WP_ID_SYNTAX" in codes(catalog)


def test_unknown_owner(sample):
    catalog = parse_wbs(sample.replace("| PrimaryOwner | Batu |", "| PrimaryOwner | Team |"))
    owner = catalog.work_packages[0].primary_owner
    assert owner.source_spelling == "Team" and owner.canonical_name is None
    assert "OWNER_UNRESOLVED" in codes(catalog)


def test_missing_owner_stays_missing(sample):
    catalog = parse_wbs(sample.replace("| PrimaryOwner | Batu |\n", ""))
    assert catalog.work_packages[0].primary_owner is None
    assert "OWNER_UNRESOLVED" in codes(catalog)


def test_capability_membership(sample):
    catalog = parse_wbs(sample.replace("WP-SIM-*", "WP-OTHER-*"))
    assert "AREA_MEMBERSHIP" in codes(catalog)


def test_area_index_conflict(sample):
    catalog = parse_wbs(sample.replace("| WP-SIM-001 | Kernel |", "| WP-SIM-001 | Wrong |"))
    assert "AREA_INDEX_CONFLICT" in codes(catalog)


def test_unknown_local_criterion(sample):
    catalog = parse_wbs(sample.replace("DoD: DOD-WP-01…02", "DoD: DOD-WP-99"))
    assert "DOD_REFERENCE" in codes(catalog)


def test_unsupported_field_is_not_silently_discarded(sample):
    catalog = parse_wbs(sample.replace("**Purpose.**", "| Extra field | value |\n**Purpose.**"))
    assert "UNSUPPORTED_FIELD" in codes(catalog)


def test_composite_scope_index_comparison(sample):
    sample = sample.replace("| F0 | M1 |", "| F1 / H0 | M1 |")
    sample = sample.replace("| ScopeClass | F0 |", "| ScopeClass | F1 (NFR class H0) |")
    catalog = parse_wbs(sample)
    assert "AREA_INDEX_CONFLICT" not in codes(catalog)
    assert catalog.work_packages[0].nfr_class == "H0"


def test_malformed_requirement_reference(sample):
    catalog = parse_wbs(sample.replace("FR-SIM-001", "FR-SIM-01"))
    assert "REQUIREMENT_SYNTAX" in codes(catalog)


def test_fenced_headings_and_workload_mentions(sample):
    sample = sample.replace("## 7.", "```markdown\n#### WP-SIM-999 — Fake\n```\nWP-SMALL WP-NORMAL WP-STRESS\n## 7.")
    assert [wp.id for wp in parse_wbs(sample).work_packages] == ["WP-SIM-001"]


def test_scanner_table_escaping():
    assert table_cells(r"| a\|b | `c|d` |") == ["a|b", "`c|d`"]
    assert table_cells("not a table") is None
    assert [h.title for h in headings("~~~md\n# Fake\n~~~\n# Real\n")] == ["Real"]


def test_full_corpus(corpus):
    catalog = parse_wbs(corpus)
    assert len(catalog.work_packages) == len({wp.id for wp in catalog.work_packages}) == 179
    assert len(catalog.capability_areas) == 29
    assert validate(catalog) == []
    assert all(re.fullmatch(r"WP-[A-Z0-9]+-[0-9]{3}", wp.id) for wp in catalog.work_packages)
    assert all(wp.purpose and wp.deliverables and wp.major_tasks for wp in catalog.work_packages)
    assert all(wp.dor_refs and wp.dod_refs for wp in catalog.work_packages)


def test_owner_distribution(corpus):
    from collections import Counter
    assert Counter(wp.primary_owner.canonical_name for wp in parse_wbs(corpus).work_packages) == {
        "Asrın Dündar": 73, "Selman Özdemir": 17, "Batuhan Kaya": 32, "Yavuz Gümüş": 57,
    }


def test_deterministic_ordering(corpus):
    catalog = parse_wbs(corpus)
    assert [wp.id for wp in catalog.work_packages] == sorted(wp.id for wp in catalog.work_packages)
    assert [a.id for a in catalog.capability_areas] == sorted(a.id for a in catalog.capability_areas)
    assert [wp.model_dump() for wp in catalog.work_packages] == [wp.model_dump() for wp in parse_wbs(corpus).work_packages]


def test_composite_scope_and_guardrail(corpus):
    packages = {wp.id: wp for wp in parse_wbs(corpus).work_packages}
    assert any(wp.nfr_class == "H0" and wp.scope_class == "F1" for wp in packages.values())
    assert packages["WP-X-001"].scope_class == "S"
    assert packages["WP-X-001"].milestone is None
    assert packages["WP-X-001"].sprint_window == "unscheduled"
