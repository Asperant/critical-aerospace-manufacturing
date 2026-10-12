import pytest

from projectctl.parsers.requirements import parse_requirements, MASTER, RTM
from projectctl.parsers.wbs import parse_wbs, WBS_PATH
from projectctl.validators.requirements import validate_requirements
from projectctl.enums import Severity


@pytest.fixture
def requirements(root):
    return parse_requirements((root / MASTER).read_text(), (root / RTM).read_text())


def test_canonical_requirement_baseline(root, requirements):
    from collections import Counter
    assert len(requirements.requirements) == 306
    assert Counter(r.kind for r in requirements.requirements) == {"FR": 186, "NFR": 120}
    assert Counter(r.scope_class for r in requirements.requirements if r.scope_class) == {"F0": 17, "F1": 159, "R1": 10}
    assert Counter(r.quality_class for r in requirements.requirements if r.quality_class) == {"H0": 52, "A1": 41, "S2": 23, "C3": 4}
    wbs = parse_wbs((root / WBS_PATH).read_text())
    diagnostics = validate_requirements(wbs, requirements)
    assert not [d for d in diagnostics if d.severity == Severity.ERROR]
    assert sum(d.code == "STALE_CITATION" for d in diagnostics) == 0


def test_missing_fields_and_compound_owners(requirements):
    catalog = {r.id: r for r in requirements.requirements}
    assert all(r.revision is None and r.catalog_status is None for r in catalog.values())
    assert catalog["FR-GOV-001"].title is None
    assert catalog["NFR-DX-003"].primary_owner.canonical_name == "Yavuz Gümüş"
    assert "PrimaryOwner" in catalog["NFR-DX-003"].primary_owner.source_spelling
    assert catalog["NFR-DATA-002"].primary_owner.canonical_name == "Asrın Dündar"
    assert catalog["NFR-GOV-001"].verification_codes is None
    assert "SHALL" in catalog["NFR-GOV-001"].statement
    assert "NFR-GOV-002" not in catalog["NFR-GOV-001"].provenance.raw_context


def test_duplicate_canonical_and_unresolved_wbs_reference(root, requirements):
    wbs = parse_wbs((root / WBS_PATH).read_text())
    wbs.work_packages[0] = wbs.work_packages[0].model_copy(update={"requirement_refs": ["FR-MISSING-001"]})
    requirements.requirements.append(requirements.requirements[0])
    codes = {d.code for d in validate_requirements(wbs, requirements)}
    assert {"DUPLICATE_REQUIREMENT", "WBS_REQUIREMENT_REFERENCE"} <= codes


def test_trace_conflict_fails(root, requirements):
    wbs = parse_wbs((root / WBS_PATH).read_text())
    requirements.traces[0].assertions["meta"]["owner"] = "Team"
    assert "TRACE_META_CONFLICT" in {d.code for d in validate_requirements(wbs, requirements)}


def test_requirement_yaml_unsafe_tags_rejected(root):
    import yaml
    rtm = (root / RTM).read_text().replace("class: F1", "class: !!python/object:builtins.object {}", 1)
    with pytest.raises(yaml.YAMLError):
        parse_requirements((root / MASTER).read_text(), rtm)


def test_stale_citation_still_detected(root, requirements):
    wbs = parse_wbs((root / WBS_PATH).read_text())
    trace = requirements.traces[0]
    trace.assertions["meta"]["anchor"] = "01 Item81 L1"
    stale = [d for d in validate_requirements(wbs, requirements) if d.code == "STALE_CITATION"]
    assert len(stale) == 1
    assert stale[0].record_id == trace.requirement_id
    assert stale[0].severity == Severity.WARNING
