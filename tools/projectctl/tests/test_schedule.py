from projectctl.loader import load
from projectctl.validators.schedule import validate_schedule


def test_schedule_full_corpus(root):
    catalog = load(root)
    assert not catalog.diagnostics
    assert validate_schedule(catalog, catalog.schedule) == []
    assert [c.id for c in catalog.schedule.cycles] == [f"S{i}" for i in range(1, 14)]
    assert [m.id for m in catalog.schedule.milestones] == [f"M{i}" for i in range(9)]
    assert catalog.schedule.effective_weeks_per_cycle == 2
    assert all(m.raw_planning_status == "NOT_ATTEMPTED" for m in catalog.schedule.milestones)


def test_schedule_duplicate_cycle(root):
    catalog = load(root)
    bad = catalog.schedule.model_copy(update={"cycles": catalog.schedule.cycles + [catalog.schedule.cycles[0]]})
    assert "CYCLE_SET" in {d.code for d in validate_schedule(catalog, bad)}


def test_schedule_unknown_wp_and_owner_conflict(root):
    catalog = load(root)
    cycle = catalog.schedule.cycles[0].model_copy(update={"work_package_ids": ["WP-FAKE-001"]})
    bad = catalog.schedule.model_copy(update={"cycles": [cycle] + catalog.schedule.cycles[1:], "roadmap_owner_ids": {"Asrın Dündar": []}})
    codes = {d.code for d in validate_schedule(catalog, bad)}
    assert {"SCHEDULE_REFERENCE", "UNSCHEDULED_SET", "ROADMAP_OWNER_CONFLICT", "ROADMAP_CYCLE_CONFLICT"} <= codes


def test_cadence_and_milestone_mismatch(root):
    catalog = load(root)
    milestone = catalog.schedule.milestones[0].model_copy(update={"work_package_ids": []})
    bad = catalog.schedule.model_copy(update={"effective_weeks_per_cycle": 3, "milestones": [milestone] + catalog.schedule.milestones[1:]})
    assert {"CADENCE", "WBS_MILESTONE_CONFLICT"} <= {d.code for d in validate_schedule(catalog, bad)}
