from collections import Counter
import re

from ..diagnostics import Diagnostic
from ..enums import Severity

UNSCHEDULED = {"WP-R2-001", "WP-R2-002", "WP-R2-003", "WP-S-001", "WP-X-001"}


def validate_schedule(catalog, schedule):
    diagnostics = []
    def check(condition, code, message, source=None, record=None):
        if not condition:
            diagnostics.append(Diagnostic(code=code, severity=Severity.ERROR, message=message, source=source, record_id=record))
    expected_cycles = {f"S{i}" for i in range(1, 14)}
    expected_milestones = {f"M{i}" for i in range(9)}
    check(len(schedule.cycles) == 13 and {c.id for c in schedule.cycles} == expected_cycles,
          "CYCLE_SET", "Expected exactly S1–S13")
    check(len(schedule.milestones) == 9 and {m.id for m in schedule.milestones} == expected_milestones,
          "MILESTONE_SET", "Expected exactly M0–M8")
    check(schedule.effective_weeks_per_cycle == 2, "CADENCE", "Expected two effective weeks per cycle")
    packages = {wp.id: wp for wp in catalog.work_packages}
    scheduled = set()
    for cycle in schedule.cycles:
        scheduled.update(cycle.work_package_ids)
        check(len(cycle.work_package_ids) == len(set(cycle.work_package_ids)), "CYCLE_DUPLICATE", "Duplicate identity within cycle", cycle.provenance, cycle.id)
        check(cycle.effective_week_end == 2 * int(cycle.id[1:]), "CYCLE_WEEK", "Cycle effective-week target disagrees with cadence", cycle.provenance, cycle.id)
        check(set(cycle.work_package_ids) <= packages.keys(), "SCHEDULE_REFERENCE", "Cycle contains unknown WP", cycle.provenance, cycle.id)
        check(Counter(cycle.work_package_ids) == Counter(schedule.roadmap_cycle_ids.get(cycle.id, [])),
              "ROADMAP_CYCLE_CONFLICT", "06 roadmaps and 07 cycle membership disagree", cycle.provenance, cycle.id)
        for wp_id in cycle.work_package_ids:
            wp = packages.get(wp_id)
            if wp and wp.sprint_window:
                tokens = re.findall(r"S(\d+)", wp.sprint_window)
                allowed = set(range(int(tokens[0]), int(tokens[-1]) + 1)) if tokens else set()
                check(int(cycle.id[1:]) in allowed, "WBS_CYCLE_CONFLICT", "Cycle outside WBS planning window", wp.provenance, wp_id)
    check(len(scheduled) == 175, "SCHEDULED_COUNT", f"Expected 175 scheduled WPs; observed {len(scheduled)}")
    check(packages.keys() - scheduled == UNSCHEDULED, "UNSCHEDULED_SET", "Unscheduled identities disagree with exact five-item baseline")
    all_milestone_wps = []
    for milestone in schedule.milestones:
        all_milestone_wps.extend(milestone.work_package_ids)
        check(milestone.target_cycle in expected_cycles, "MILESTONE_CYCLE", "Milestone target cycle does not resolve", milestone.provenance, milestone.id)
        check(milestone.effective_week_end == 2 * int(milestone.target_cycle[1:]), "MILESTONE_WEEK", "Milestone effective-week target disagrees", milestone.provenance, milestone.id)
        check(set(milestone.work_package_ids) == {wp.id for wp in packages.values() if wp.milestone == milestone.id},
              "WBS_MILESTONE_CONFLICT", "07 milestone membership and WBS disagree", milestone.provenance, milestone.id)
    check(len(all_milestone_wps) == len(set(all_milestone_wps)) == 175, "SCHEDULE_IDENTITY", "Each scheduled WP must belong to one milestone")
    for owner, ids in schedule.roadmap_owner_ids.items():
        check(len(ids) == len(set(ids)) and set(ids) == {wp.id for wp in packages.values() if wp.primary_owner and wp.primary_owner.canonical_name == owner},
              "ROADMAP_OWNER_CONFLICT", f"Roadmap membership disagrees with WBS for {owner}")
    for wp in packages.values():
        check(wp.milestone is None or wp.milestone in expected_milestones, "WBS_MILESTONE_REFERENCE", "WBS milestone does not resolve", wp.provenance, wp.id)
    return diagnostics
