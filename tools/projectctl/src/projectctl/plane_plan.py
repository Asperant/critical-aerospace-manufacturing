"""Pure dry-run projection. No HTTP client and no execution-state store."""
from collections import Counter, defaultdict
from hashlib import sha256
import html
import json
import re
import unicodedata

from .enums import Severity
from .plane import PlaneError
from .project import PARSER_VERSION

STATES = ["BACKLOG", "READY", "IN_PROGRESS", "IN_REVIEW", "MERGE_READY", "MERGED", "VALIDATING", "DONE", "CANCELED"]
WP_ID = re.compile(r"^WP-[A-Z0-9]+-\d{3}$")
VISIBLE_ID = re.compile(r"^\[(WP-[A-Z0-9]+-\d{3})\](?:\s|$)")


def _name(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _description(metadata):
    return '<p>projectctl canonical planning projection; planning is not evidence.</p><pre>' + html.escape(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2)) + '</pre>'


def bootstrap_plan(project, audit):
    if any(d.severity == Severity.ERROR for d in project.diagnostics()):
        raise PlaneError("Canonical validation failed; no bootstrap plan available")
    if (audit.get("schema_version") != "plane-v1-audit-v1" or audit.get("api_version") != "v1"
            or audit.get("mutation_enabled") is not False or audit.get("project", {}).get("name") != "Graduation Project"
            or audit.get("project", {}).get("identifier") != "CAP"):
        raise PlaneError("Invalid or wrong-target API v1 discovery snapshot")
    for key in ["states", "labels", "modules", "cycles", "work_items"]:
        if not isinstance(audit.get(key), list):
            raise PlaneError("Required discovery resource unavailable: " + key)
    from .control_plane import canonical_audit
    audit, control_items = canonical_audit(audit, project.control_items)
    c = project.catalog
    conflicts, ambiguities, missing, operations = [], [], [], []
    prefix = f"/api/v1/workspaces/{audit['workspace']['slug']}/projects/{audit['project']['id']}/"
    def conflict(code, identity, **details):
        conflicts.append({"code": code, "identity": identity, **details})

    state_index = defaultdict(list)
    for state in audit["states"]:
        state_index[state["name"]].append(state)
    for state in STATES:
        if len(state_index[state]) != 1:
            conflict("WORKFLOW_STATE_MISSING_OR_DUPLICATE", state, observed_count=len(state_index[state]))
    for state in sorted(set(state_index) - set(STATES)):
        conflict("NONCANONICAL_WORKFLOW_STATE", state, plane_ids=[s["id"] for s in state_index[state]])
    backlog = state_index["BACKLOG"][0]["id"] if len(state_index["BACKLOG"]) == 1 else None

    owners = sorted({w.primary_owner.canonical_name for w in c.work_packages if w.primary_owner})
    owner_map = {}
    # Only exact normalized full names in the target project qualify. No username guessing.
    for owner in owners:
        matches = [m for m in audit.get("project_members") or []
                   if _name(m.get("first_name", "") + " " + m.get("last_name", "")) == _name(owner)]
        owner_map[owner] = matches[0]["id"] if len(matches) == 1 else None
        if len(matches) > 1:
            conflict("AMBIGUOUS_OWNER", owner, member_ids=[m["id"] for m in matches])
        if not matches:
            missing.append({"owner": owner, "reason": "PROJECT_MEMBERS_UNAVAILABLE" if audit.get("project_members") is None
                            else "NO_EXACT_PROJECT_MEMBER", "affected_wp_ids": sorted(w.id for w in c.work_packages
                                                         if w.primary_owner.canonical_name == owner)})

    def structure(kind, identity, desired):
        rows = [r for r in audit[kind] if r.get("name") == identity]
        if len(rows) > 1:
            conflict("DUPLICATE_STRUCTURE", identity, kind=kind, plane_ids=[r["id"] for r in rows])
            action, existing, changes = "conflict", None, {}
        else:
            existing = rows[0] if rows else None
            changes = {k: v for k, v in desired.items() if existing is None or existing.get(k) != v}
            action = "create" if existing is None else "update" if changes else "unchanged"
        operations.append({"kind": kind, "identity": identity, "action": action,
                           "plane_id": existing["id"] if existing else None, "desired": desired,
                           "request": {"method": "POST" if action == "create" else "PATCH",
                                       "path": prefix + kind + "/" + (existing["id"] + "/" if existing else ""),
                                       "body": changes} if action in {"create", "update"} else None})
        return existing["id"] if existing else f"$ref:{kind}:{identity}"

    module_map = {a.id: structure("modules", a.id, {"name": a.id, "description": a.title}) for a in c.capability_areas}
    cycle_map = {s.id: structure("cycles", s.id, {"name": s.id, "description":
                 f"{s.title}; effective engineering weeks W{s.effective_week_end - 1}–W{s.effective_week_end}. Calendar dates unspecified."})
                 for s in c.schedule.cycles}
    labels = {m.id: structure("labels", "MS:" + m.id, {"name": "MS:" + m.id}) for m in c.schedule.milestones}
    # Preserve the existing orthogonal label exactly; never reclassify as a state.
    structure("labels", "BLOCKED", {"name": "BLOCKED"})

    by_id = defaultdict(list)
    for item in audit["work_items"]:
        external = item.get("external_id")
        match = VISIBLE_ID.match(item.get("name", ""))
        visible = match.group(1) if match else None
        identities = {i for i in [external, visible] if isinstance(i, str) and WP_ID.fullmatch(i)}
        if len(identities) > 1:
            conflict("CONFLICTING_CANONICAL_IDS", item["id"], canonical_ids=sorted(identities))
        for identity in identities:
            by_id[identity].append(item)
    duplicates = {key: sorted(r["id"] for r in rows) for key, rows in sorted(by_id.items()) if len(rows) > 1}
    for key, ids in duplicates.items():
        conflict("DUPLICATE_CANONICAL_ID", key, plane_ids=ids)
    canonical = {w.id for w in c.work_packages}
    for key in sorted(set(by_id) - canonical):
        conflict("UNKNOWN_CANONICAL_ID", key, plane_ids=[r["id"] for r in by_id[key]])

    for wp in c.work_packages:
        cycle_ids = [s.id for s in c.schedule.cycles if wp.id in s.work_package_ids]
        unresolved_cycle = len(cycle_ids) > 1
        if unresolved_cycle:
            ambiguities.append({"code": "SINGLE_PLANE_CYCLE_UNRESOLVED", "identity": wp.id,
                                "canonical_cycle_ids": cycle_ids, "source": wp.provenance.path,
                                "raw_planning_window": wp.raw_planning_window,
                                "reason": "No approved rule chooses one cycle from the canonical multi-cycle window"})
        owner = wp.primary_owner.canonical_name
        metadata = {"canonical_wp_id": wp.id, "canonical_owner": owner, "capability_area": wp.capability_area,
                    "cycle_ids": cycle_ids, "milestone": wp.milestone, "scope_class": wp.scope_class,
                    "requirement_refs": wp.requirement_refs, "architecture_refs": wp.architecture_refs,
                    "readiness_refs": wp.readiness_refs, "dependency_refs": wp.dependency_refs,
                    "dor_refs": wp.dor_refs, "dod_refs": wp.dod_refs,
                    "verification_expectations": wp.verification_expectations, "evidence_expectations": wp.evidence_expectations,
                    "initialization_policy": "BACKLOG on creation only; never infer execution from documentation",
                    "source": {k: v for k, v in wp.provenance.model_dump().items() if k != "raw_context"},
                    "source_sha256": project.source_manifest[wp.provenance.path], "parser_version": PARSER_VERSION}
        desired = {"name": f"[{wp.id}] {wp.title}", "external_source": "projectctl", "external_id": wp.id,
                   "description_html": _description(metadata)}
        if owner_map[owner]:
            desired["assignees"] = [owner_map[owner]]
        existing = by_id[wp.id][0] if len(by_id[wp.id]) == 1 else None
        changes = {k: v for k, v in desired.items() if existing is None or existing.get(k) != v}
        if wp.id in duplicates:
            action = "conflict"
        elif existing is None:
            action = "create"
            changes["state"] = backlog
        elif changes and existing.get("external_source") != "projectctl":
            action = "conflict"
            conflict("UNMANAGED_ITEM_METADATA", wp.id, plane_id=existing["id"],
                     reason="Will not overwrite user-owned descriptions or metadata")
        else:
            action = "update" if changes else "unchanged"
        # Relations are separate v1 operations. References resolve only after structures are re-read.
        module_id = module_map[wp.capability_area]
        cycle_id = cycle_map[cycle_ids[0]] if len(cycle_ids) == 1 else None
        label_ids = [labels[wp.milestone]] if wp.milestone in labels else []
        relations = {"module": module_id, "cycle": cycle_id, "milestone_labels": label_ids,
                     "cycle_resolution": "UNRESOLVED" if unresolved_cycle else "SCHEDULED" if cycle_ids else "UNSCHEDULED"}
        if existing is not None:
            # Issue list responses may omit module/cycle memberships. Do not invent an empty relation.
            ambiguities.append({"code": "RELATION_READ_REQUIRED", "identity": wp.id,
                                "reason": "Re-read module/cycle issue membership before planning relationship mutations"})
        blockers = (["SINGLE_PLANE_CYCLE_UNRESOLVED"] if unresolved_cycle else []) + ([] if backlog else ["BACKLOG_STATE_UNAVAILABLE"])
        operations.append({"kind": "work_items", "identity": wp.id, "action": action,
                           "plane_id": existing["id"] if existing else None, "canonical_metadata": metadata,
                           "desired": desired, "relations": relations, "blockers": blockers,
                           "request": {"method": "POST" if action == "create" else "PATCH",
                                       "path": prefix + "issues/" + (existing["id"] + "/" if existing else ""),
                                       "body": changes} if action in {"create", "update"} else None})
    counts = Counter(o["action"] for o in operations)
    body = {"schema_version": "plane-bootstrap-plan-v1", "api_version": "v1", "dry_run": True,
            "mutation_enabled": False, "ready_for_live_mutation": not conflicts and not ambiguities,
            "control_item_count": len(control_items),
            "source_manifest": project.source_manifest, "parser_version": PARSER_VERSION,
            "workspace": audit["workspace"], "project": audit["project"],
            "audit_sha256": sha256(json.dumps(audit, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            "owner_mapping": owner_map, "missing_owners": missing, "conflicts": conflicts,
            "ambiguous_mappings": ambiguities, "duplicate_canonical_ids": duplicates,
            "unmanaged_work_items": sorted(i["id"] for i in audit["work_items"]
                                           if not any(i in rows for rows in by_id.values())),
            "summary": {"actions": dict(sorted(counts.items())), "modules": len(module_map), "cycles": len(cycle_map),
                        "milestone_labels": len(labels), "work_packages": len(canonical),
                        "scheduled": sum(bool(o["canonical_metadata"]["cycle_ids"]) for o in operations if o["kind"] == "work_items"),
                        "unscheduled_ids": [o["identity"] for o in operations if o["kind"] == "work_items" and not o["canonical_metadata"]["cycle_ids"]]},
            "operations": operations,
            "idempotency": "Re-read before apply; exact structure name and canonical WP ID identity; duplicate/conflicting IDs block; update owned static fields only; never reset existing workflow state; no deletes. Relationship writes require fresh membership reads.",
            "limitations": ["No API mutation is implemented or called", "Symbolic $ref values are not live API IDs",
                            "Relationship entries are intended mappings, not executable request bodies",
                            "Calendar dates absent in canonical sources; API acceptance of undated cycles must be checked before apply",
                            "All canonical diagnostics remain visible through projectctl validate; planning is not evidence"]}
    body["ready_for_live_mutation"] = not conflicts and not ambiguities and not body["unmanaged_work_items"]
    return body
