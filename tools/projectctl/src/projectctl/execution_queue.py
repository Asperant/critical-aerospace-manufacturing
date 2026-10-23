"""Canonical AUTO_NEXT selection. Standard library only; no I/O or execution state."""

from __future__ import annotations

from collections import Counter
from typing import Any

OWNERS = {
    "asrin": "Asrın Dündar",
    "selman": "Selman Özdemir",
    "batuhan": "Batuhan Kaya",
    "yavuz": "Yavuz Gümüş",
}
ASSIGNEES = {
    "Asrın Dündar": "0b4a5417-2ed5-4ac2-95ff-e74104c5d601",
    "Selman Özdemir": "a3d25336-e7d0-43f8-bfef-c0b5c2137a60",
    "Batuhan Kaya": "51137169-2989-42bd-9260-997b26e7e6dd",
    "Yavuz Gümüş": "3ccd9ad8-99e9-4b75-ae65-2325503d347f",
}
ACTIVE = {"READY", "IN_PROGRESS", "IN_REVIEW", "MERGE_READY", "MERGED", "VALIDATING"}
STATES = ACTIVE | {"BACKLOG", "DONE", "CANCELED"}
EXCLUDED = {"WP-R2-001", "WP-R2-002", "WP-R2-003", "WP-S-001", "WP-X-001"}
EXPECTED = dict(zip(OWNERS.values(), (69, 17, 32, 56), strict=True))


def project_view(project: Any) -> dict[str, Any]:
    """Accept the parsed project or the identical installed static projection."""
    if isinstance(project, dict):
        return project
    from .queries import context

    cards = {}
    for wp in project.catalog.work_packages:
        data = context(project, wp.id)
        cards[wp.id] = {
            "owner": wp.primary_owner.canonical_name,
            "scheduled": bool(data["cycle_ids"]),
            "nodes": wp.readiness_refs or [],
            "edges": data["dependency_edges"],
        }
    return {
        "cards": cards,
        "node_levels": {
            node.id: [str(level) for level in node.readiness_levels]
            for node in project.catalog.dependencies.nodes
        },
        "source_manifest": project.source_manifest,
        "valid": project.summary()["validation"] == "PASS",
    }


def validate_preferences(project: Any, policy: dict[str, Any]) -> list[str]:
    """No missing, duplicate, foreign, optional or implicit fallback preferences."""
    view = project_view(project)
    cards = view.get("cards", {})
    sequences = policy.get("sequences", {})
    errors = []
    if policy.get("schema_version") != "cap-execution-preferences-v1":
        errors.append("INVALID_PREFERENCE_SCHEMA")
    if set(sequences) != set(OWNERS.values()):
        errors.append("INVALID_PREFERENCE_OWNERS")
    seen = []
    for owner, sequence in sequences.items():
        if not isinstance(sequence, list) or any(
            not isinstance(w, str) for w in sequence
        ):
            errors.append("INVALID_PREFERENCE_SEQUENCE")
            continue
        seen.extend(sequence)
        for wp in sequence:
            card = cards.get(wp)
            if not card:
                errors.append("UNKNOWN_WP:" + wp)
            elif card["owner"] != owner:
                errors.append("OWNER_MISMATCH:" + wp)
            elif not card["scheduled"]:
                errors.append("UNSCHEDULED_WP:" + wp)
    scheduled = {wp for wp, card in cards.items() if card["scheduled"]}
    if set(seen) != scheduled:
        errors.append("PREFERENCE_COVERAGE_MISMATCH")
    if len(seen) != len(set(seen)):
        errors.append("DUPLICATE_PREFERENCE")
    if (
        len(cards) != 179
        or len(scheduled) != 174
        or set(cards) - scheduled != EXCLUDED
        or Counter(card["owner"] for card in cards.values())
        != Counter(dict(zip(OWNERS.values(), (73, 17, 32, 57), strict=True)))
        or {owner: len(sequences.get(owner, [])) for owner in EXPECTED} != EXPECTED
    ):
        errors.append("CANONICAL_COUNTS_MISMATCH")
    if not view.get("valid"):
        errors.append("CANONICAL_VALIDATION_FAILED")
    return sorted(set(errors))


def compute_next_eligible(
    project: Any,
    live_snapshot: dict[str, Any],
    evidence_snapshot: dict[str, Any],
    owner: str,
    planning_policy: dict[str, Any],
) -> dict[str, Any]:
    """First verified eligible preference, preserving every active/pending item.

    Evidence is supplied by the trusted read adapter, never inferred from Plane
    DONE. Offline callers may preview snapshots but cannot authorize a mutation.
    """
    owner = OWNERS.get(owner, owner)
    view = project_view(project)
    result: dict[str, Any] = {
        "owner": owner,
        "status": "NO_TASK",
        "wp_id": None,
        "reasons": [],
    }
    errors = validate_preferences(view, planning_policy)
    if owner not in ASSIGNEES:
        errors.append("UNKNOWN_OWNER")
    if errors:
        return {**result, "status": "INVALID_BASELINE", "reasons": errors}
    cards = view["cards"]
    items = live_snapshot.get("items", {})
    if live_snapshot.get("complete") is not True or set(items) != set(cards):
        return {
            **result,
            "status": "UNAVAILABLE",
            "reasons": ["INCOMPLETE_PLANE_SNAPSHOT"],
        }
    for wp, item in items.items():
        if item.get("state") not in STATES:
            return {
                **result,
                "status": "UNAVAILABLE",
                "reasons": ["UNKNOWN_STATE:" + wp],
            }
        if (
            item.get("owner") != cards[wp]["owner"]
            or item.get("assignees") != [ASSIGNEES[cards[wp]["owner"]]]
            or type(item.get("blocked")) is not bool
        ):
            return {
                **result,
                "status": "INVALID_BASELINE",
                "reasons": ["LIVE_IDENTITY_MISMATCH:" + wp],
            }
    active = [
        wp
        for wp, item in items.items()
        if cards[wp]["owner"] == owner and item["state"] in ACTIVE
    ]
    if active:
        if len(active) != 1:
            return {
                **result,
                "status": "UNAVAILABLE",
                "reasons": ["MULTIPLE_ACTIVE_WORK"],
                "active": sorted(active),
            }
        wp = active[0]
        item = items[wp]
        return {
            **result,
            "status": "BLOCKED"
            if item["blocked"]
            else ("READY" if item["state"] == "READY" else "CURRENT"),
            "wp_id": wp,
            "state": item["state"],
            "reasons": [item.get("blocker_reason") or "ACTIVE_BLOCKER"]
            if item["blocked"]
            else [],
        }
    if (
        evidence_snapshot.get("complete") is not True
        or evidence_snapshot.get("source_manifest") != view["source_manifest"]
    ):
        return {
            **result,
            "status": "UNAVAILABLE",
            "reasons": ["EVIDENCE_OR_SOURCE_INTEGRITY_UNAVAILABLE"],
        }
    considered = []
    for wp in planning_policy["sequences"][owner]:
        item = items[wp]
        if item["state"] in {"DONE", "CANCELED"}:
            continue
        evidence = evidence_snapshot.get("candidates", {}).get(wp, {})
        reason = candidate_reason(view, wp, item, evidence)
        soft = [
            e["id"] for e in cards[wp]["edges"] if e["semantics"]["strength"] == "SOFT"
        ]
        considered.append({"wp_id": wp, "reason": reason, "soft_dependencies": soft})
        if reason is None:
            return {
                **result,
                "status": "PROPOSED_NEXT",
                "wp_id": wp,
                "considered": considered,
            }
    return {
        **result,
        "reasons": ["NO_VERIFIED_ELIGIBLE_WORK"]
        if considered
        else ["NO_REMAINING_SCHEDULED_WORK"],
        "considered": considered,
    }


def affected_owners(project: Any, completed_wp: str) -> list[str]:
    """Node consumers may share/split WPs. Never construct a fake WP predecessor."""
    view = project_view(project)
    card = view["cards"][completed_wp]
    nodes = set(card["nodes"])
    result = {card["owner"]}
    for consumer in view["cards"].values():
        if any(edge["predecessor"]["node"] in nodes for edge in consumer["edges"]):
            result.add(consumer["owner"])
    return [owner for owner in OWNERS.values() if owner in result]


def candidate_reason(view, wp, item, evidence):
    """One eligibility predicate for release and derived preflight; UNKNOWN fails closed."""
    reason = None
    if item["blocked"]:
        reason = "BLOCKED"
    elif (
        evidence.get("result") != "PASS"
        or evidence.get("dor") != "PASS"
        or not evidence.get("evidence_refs")
    ):
        reason = evidence.get("reason") or "DOR_EVIDENCE_UNKNOWN"
    else:
        for edge in view["cards"][wp]["edges"]:
            sem = edge["semantics"]
            if sem["strength"] != "HARD" or sem["blocking_stage"] != "START":
                continue
            proof = evidence.get("dependencies", {}).get(edge["id"], {})
            levels = view["node_levels"].get(edge["predecessor"]["node"], [])
            required = sem["required_readiness"]
            actual = proof.get("readiness")
            if (
                proof.get("result") != "PASS"
                or not proof.get("evidence_refs")
                or not proof.get("precise_consumer_requirement")
                or required not in levels
                or actual not in levels
                or levels.index(actual) < levels.index(required)
            ):
                reason = "HARD_START_READINESS_UNKNOWN:" + edge["id"]
                break
    return reason


def preflight_health(project, live, evidence, owner, preferences):
    """Derived control-plane status only. Never mutates inputs or Plane."""
    owner = OWNERS.get(owner, owner)
    view = project_view(project)
    decision = compute_next_eligible(view, live, evidence, owner, preferences)
    result = {
        "owner": owner,
        "current": None,
        "prepared_next": None,
        "health": "UNAVAILABLE",
        "candidates": [],
        "first_blocker": None,
        "reasons": decision.get("reasons", []),
    }
    if decision["status"] in {"UNAVAILABLE", "INVALID_BASELINE"}:
        return result
    active = [
        w
        for w, item in live["items"].items()
        if view["cards"][w]["owner"] == owner and item["state"] in ACTIVE
    ]
    if active:
        result["current"] = {
            "wp_id": active[0],
            "state": live["items"][active[0]]["state"],
        }
    if (
        evidence.get("complete") is not True
        or evidence.get("source_manifest") != view["source_manifest"]
    ):
        result["reasons"] = ["EVIDENCE_OR_SOURCE_INTEGRITY_UNAVAILABLE"]
        return result
    candidates = []
    for wp in preferences["sequences"][owner]:
        item = live["items"][wp]
        if item["state"] != "BACKLOG":
            continue
        proof = evidence.get("candidates", {}).get(wp, {})
        reason = candidate_reason(view, wp, item, proof)
        gaps = []
        for edge in view["cards"][wp]["edges"]:
            sem = edge["semantics"]
            if sem["strength"] != "HARD" or sem["blocking_stage"] != "START":
                continue
            dep = proof.get("dependencies", {}).get(edge["id"], {})
            levels = view["node_levels"].get(edge["predecessor"]["node"], [])
            actual, required = dep.get("readiness"), sem["required_readiness"]
            if (
                dep.get("result") != "PASS"
                or not dep.get("evidence_refs")
                or not dep.get("precise_consumer_requirement")
                or required not in levels
                or actual not in levels
                or levels.index(actual) < levels.index(required)
            ):
                gaps.append(
                    {
                        "consumer_wp": wp,
                        "dependency_id": edge["id"],
                        "readiness_node": edge["predecessor"]["node"],
                        "required_readiness": required,
                        "consumer_owner": owner,
                        "missing": "VERIFIED_READINESS_ARTIFACT_AND_ACCOUNTABLE_EVIDENCE",
                    }
                )
        status = "PREPARED"
        if reason:
            status = "NEEDS_EVIDENCE"
            if reason == "BLOCKED":
                status = "BLOCKED"
            elif reason.startswith("HARD_START") or "DEPENDENCY" in reason:
                status = "WAITING_DEP"
            elif "DOR" in reason or "CONFIRMATION" in reason or "ASSESSMENT" in reason:
                status = "NEEDS_DOR"
            elif "UNAVAILABLE" in reason and reason != "DOR_EVIDENCE_UNAVAILABLE":
                status = "UNAVAILABLE"
        candidate = {
            "wp_id": wp,
            "status": status,
            "reason": reason,
            "hard_start_blockers": gaps,
            "soft_dependencies": [
                e["id"]
                for e in view["cards"][wp]["edges"]
                if e["semantics"]["strength"] == "SOFT"
            ],
        }
        candidates.append(candidate)
        if status == "PREPARED" and result["prepared_next"] is None:
            result["prepared_next"] = wp
    result["candidates"] = candidates[:3]
    result["backlog_count"] = len(candidates)
    result["first_blocker"] = next((c for c in candidates if c["reason"]), None)
    if any(c["status"] == "UNAVAILABLE" for c in candidates):
        result["health"] = "UNAVAILABLE"
    elif not candidates:
        result["health"] = "HEALTHY"
    elif result["prepared_next"]:
        result["health"] = "HEALTHY" if active else "STALL_RISK"
        if not active:
            result["reasons"] = ["ELIGIBLE_WORK_AWAITS_GUARDED_RELEASE"]
    else:
        result["health"] = "STALL_RISK" if active else "STALLED"
    if active and live["items"][active[0]]["blocked"]:
        result["health"] = "STALL_RISK"
        result["reasons"] = ["ACTIVE_BLOCKER"]
    return result
