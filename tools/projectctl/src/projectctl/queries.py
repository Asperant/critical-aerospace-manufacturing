import re

from .models import OWNER_NAMES


def context(project, wp_id):
    if not re.fullmatch(r"WP-[A-Z0-9]+-\d{3}", wp_id):
        raise ValueError("Invalid complete WP ID")
    c = project.catalog
    matches = [wp for wp in c.work_packages if wp.id == wp_id]
    if len(matches) != 1:
        raise ValueError("WP must resolve to exactly one canonical record")
    wp = matches[0]
    requirements = [r for r in c.requirements.requirements if r.id in (wp.requirement_refs or [])] if c.requirements else []
    edges = [e for e in c.dependencies.edges if e.id in (wp.dependency_refs or []) or e.successor.node in (wp.readiness_refs or [])] if c.dependencies else []
    relevant_ids = {wp.id, *(wp.requirement_refs or []), *(wp.readiness_refs or []), *(e.id for e in edges)}
    cycles = [cycle.id for cycle in c.schedule.cycles if wp_id in cycle.work_package_ids] if c.schedule else []
    return {
        "work_package": wp.model_dump(mode="json"),
        "requirements": [r.model_dump(mode="json") for r in requirements],
        "dependency_edges": [e.model_dump(mode="json") for e in edges],
        "cycle_ids": cycles, "milestone_id": wp.milestone,
        "execution_status": "UNAVAILABLE (documentation only)",
        "diagnostics": [d.model_dump(mode="json") for d in project.diagnostics() if d.record_id in relevant_ids or d.record_id is None],
        "source_manifest": project.source_manifest,
    }


def planning_candidates(project, owner, cycle=None):
    lookup = {key.casefold(): value for key, value in OWNER_NAMES.items()}
    lookup.update({value.casefold(): value for value in OWNER_NAMES.values()})
    canonical = lookup.get(owner.casefold())
    if canonical is None:
        raise ValueError("Unknown canonical owner")
    c = project.catalog
    if c.schedule is None:
        raise ValueError("Schedule unavailable")
    if cycle is not None and cycle not in {item.id for item in c.schedule.cycles}:
        raise ValueError("Unknown cycle")
    membership = {item.id: set(item.work_package_ids) for item in c.schedule.cycles}
    scheduled = set().union(*membership.values())
    items = []
    for wp in c.work_packages:
        if wp.primary_owner and wp.primary_owner.canonical_name == canonical and wp.scope_class in {"F0", "F1", "R1"} and wp.id in scheduled:
            if cycle is None or wp.id in membership[cycle]:
                items.append({"id": wp.id, "title": wp.title, "cycle_ids": [key for key, ids in membership.items() if wp.id in ids], "milestone_id": wp.milestone})
    return {"result_type": "PLANNING_CANDIDATES", "readiness": "NOT_CERTIFIED", "owner": canonical,
            "execution_status": "UNAVAILABLE (documentation only)", "candidates": items}
