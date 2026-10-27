"""Canonical AUTO_NEXT selection. Standard library only; no I/O or execution state."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable
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
EXPECTED = dict(zip(OWNERS.values(), (70, 17, 32, 56), strict=True))


DEFERRED_CLASS = "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE"
WBS_PATH = "docs/04_Work_Breakdown_Structure.md"
RTM_PATH = "docs/03_Requirements_Traceability_Matrix.md"
PROJECTED_SOURCES = frozenset({WBS_PATH, RTM_PATH})
EXTERNAL_WAIT_CLASSES = frozenset({"WAITING_EXTERNAL_INTEGRATION_BINDINGS"})
SLOT_RELEASE_SCHEMA = "cap-slot-release-v2"
SLOT_RELEASE_CLASSES = frozenset(
    {
        DEFERRED_CLASS,
        "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
    }
)


def _lines(text: str) -> list[str]:
    return [line.rstrip("\r") for line in text.split("\n")]


def _first_cell(line: str) -> str | None:
    cells = line.split("|")
    return cells[1].strip() if line.startswith("|") and len(cells) > 2 else None


def scope_projection(
    wp: str, requirement_refs: list[str], wbs_text: str, rtm_text: str
) -> str:
    """Digest of only the canonical content that belongs to one work package.

    Shared WBS/RTM files change for every WP, so whole-file equality would let an
    unrelated edit release or hold another WP's deferred wait. The projection keeps
    the WP's own table rows and card, plus the rows and block of each requirement
    it references. Missing or ambiguous structure raises: the caller fails closed.
    """
    if not re.fullmatch(r"WP-[A-Z0-9]+-[0-9]{3}", wp):
        raise ValueError("INVALID_WP")
    refs = sorted(set(requirement_refs))
    if not refs or any(
        not re.fullmatch(r"[A-Z]+-[A-Z0-9]+-[0-9]{3}", ref) for ref in refs
    ):
        raise ValueError("REQUIREMENT_REFS_UNAVAILABLE")
    wbs, rtm = _lines(wbs_text), _lines(rtm_text)
    rows = [line for line in wbs if _first_cell(line) == wp]
    starts = [i for i, line in enumerate(wbs) if line.startswith(f"#### {wp} — ")]
    if not rows or len(starts) != 1:
        raise ValueError("WBS_PROJECTION_UNAVAILABLE")
    stop = next(
        (i for i in range(starts[0] + 1, len(wbs)) if re.match(r"#{1,4} ", wbs[i])),
        len(wbs),
    )
    projection: dict[str, Any] = {
        "wp": wp,
        "wbs_rows": rows,
        "wbs_card": wbs[starts[0] : stop],
        "requirements": {},
    }
    for ref in refs:
        table = [line for line in rtm if _first_cell(line) == ref]
        blocks = [i for i, line in enumerate(rtm) if line == f"{ref}:"]
        if not table or len(blocks) != 1:
            raise ValueError("RTM_PROJECTION_UNAVAILABLE")
        end = next(
            (
                i
                for i in range(blocks[0] + 1, len(rtm))
                if rtm[i] and not rtm[i][0].isspace()
            ),
            len(rtm),
        )
        projection["requirements"][ref] = {
            "rows": table,
            "block": rtm[blocks[0] : end],
        }
    return hashlib.sha256(
        json.dumps(projection, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def deferred_acceptance(wp: str, item: dict[str, Any]) -> bool:
    """Consume only the root adapter's verified, owner/revision-bound proof.

    Offline snapshots can preview this classification, never authorize writes.
    Lifecycle ACTIVE/STATES and all DONE requirements remain unchanged.
    """
    proof = item.get("deferred_acceptance")
    return (
        item.get("state") == "VALIDATING"
        and item.get("blocked") is True
        and isinstance(proof, dict)
        and proof.get("schema") == "cap-deferred-acceptance-v1"
        and proof.get("classification") == DEFERRED_CLASS
        and proof.get("wp_id") == wp
        and proof.get("owner") == item.get("owner")
        and proof.get("implementation_complete") is True
        and proof.get("owner_work_remaining") is False
        and all(
            isinstance(proof.get(k), str) and proof[k]
            for k in ("merge_sha", "audit_id", "assessment_digest")
        )
        and (
            "reassertion_audit_id" not in proof
            or all(
                isinstance(proof.get(k), str) and proof[k]
                for k in (
                    "reassertion_audit_id",
                    "reassertion_comment_id",
                    "reassertion_digest",
                )
            )
        )
    )


def external_integration_wait(wp: str, item: dict[str, Any]) -> bool:
    """Consume only the root adapter's verified, owner/revision-bound proof.

    An IN_PROGRESS work package whose remaining work is gated solely by explicit
    canonical external dependency/readiness bindings. Offline snapshots can preview
    this classification, never authorize writes. Lifecycle, readiness and every DONE
    requirement remain unchanged; the wait is never completion evidence.
    """
    proof = item.get("external_integration_wait")
    return (
        item.get("state") == "IN_PROGRESS"
        and item.get("blocked") is True
        and isinstance(proof, dict)
        and proof.get("schema") == "cap-external-integration-wait-v1"
        and proof.get("classification") in EXTERNAL_WAIT_CLASSES
        and proof.get("wp_id") == wp
        and proof.get("owner") == item.get("owner")
        and proof.get("owner_work_remaining") is False
        and all(
            isinstance(proof.get(k), str) and proof[k]
            for k in ("audit_id", "assessment_digest", "comment_id")
        )
        and isinstance(proof.get("dependency_nodes"), list)
        and bool(proof["dependency_nodes"])
        and all(isinstance(n, str) and n for n in proof["dependency_nodes"])
    )


def released_wait(wp: str, item: dict[str, Any]) -> str | None:
    """Verified blocked wait that does not occupy the implementation slot."""
    semantic = semantic_slot_release(wp, item)
    if semantic:
        return semantic
    if deferred_acceptance(wp, item):
        return DEFERRED_CLASS
    if external_integration_wait(wp, item):
        return item["external_integration_wait"]["classification"]
    proof = item.get("merged_external_integration_wait")
    if (
        item.get("state") == "VALIDATING"
        and item.get("blocked") is True
        and isinstance(proof, dict)
        and proof.get("schema") == "cap-merged-external-wait-v1"
        and proof.get("classification") == "WAITING_EXTERNAL_INTEGRATION_BINDINGS"
        and proof.get("wp_id") == wp
        and proof.get("owner") == item.get("owner")
        and proof.get("owner_work_remaining") is False
        and proof.get("local_actionable_work") is False
        and all(
            isinstance(proof.get(k), str) and proof[k]
            for k in ("merge_sha", "audit_id", "assessment_digest", "provenance_digest")
        )
        and isinstance(proof.get("binding_ids"), list)
        and bool(proof["binding_ids"])
        and all(isinstance(v, str) and v for v in proof["binding_ids"])
    ):
        return proof["classification"]
    return None


def semantic_slot_release(wp: str, item: dict[str, Any]) -> str | None:
    """Derive scheduler slot release from current semantic owner evidence."""
    proof = item.get("slot_release_v2")
    if not (
        item.get("state") in {"IN_PROGRESS", "VALIDATING"}
        and item.get("blocked") is True
        and isinstance(proof, dict)
        and proof.get("schema") == SLOT_RELEASE_SCHEMA
        and proof.get("wp_id") == wp
        and proof.get("owner") == item.get("owner")
        and proof.get("local_actionable_work") == "NONE"
        and proof.get("implementation_persisted") is True
        and isinstance(proof.get("semantic_blocker_id"), str)
        and bool(proof["semantic_blocker_id"])
        and proof.get("semantic_blocker_class") in SLOT_RELEASE_CLASSES
    ):
        return None
    current_scope = item.get("current_scope_digest")
    if current_scope is not None and current_scope != proof.get(
        "relevant_scope_digest"
    ):
        return None
    if (
        proof["semantic_blocker_class"] == DEFERRED_CLASS
        and item.get("state") != "VALIDATING"
    ):
        return None
    return proof["semantic_blocker_class"]


def occupies_implementation_slot(wp: str, item: dict[str, Any]) -> bool:
    return item.get("state") in ACTIVE and released_wait(wp, item) is None


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
            "scope_known": all(
                bool(getattr(wp, field, None))
                for field in (
                    "id",
                    "scope_class",
                    "dor_refs",
                    "dod_refs",
                )
            ),
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


def startability_from_view(view: dict[str, Any], wp_id: str) -> dict[str, Any]:
    """Evaluate the deliberately small CHG-054 product start rule.

    This is a canonical documentation decision only.  It intentionally does not
    inspect Plane, READY/DoR evidence, queue health, audit continuity, caches or
    Slot Release proofs.  A dependency is a start blocker only when its canonical
    edge is HARD + START and its recorded readiness status is not READY.
    """
    cards = view.get("cards", {}) if isinstance(view, dict) else {}
    result = {
        "schema_version": "cap-startability-v1",
        "wp_id": wp_id,
        "result": "BLOCK",
        "blockers": [],
        "advisories": [],
    }
    card = cards.get(wp_id)
    if not isinstance(card, dict):
        result["blockers"] = ["CANONICAL_WP_UNKNOWN"]
        return result
    owner = card.get("owner")
    if owner not in OWNERS.values():
        result["blockers"].append("CANONICAL_OWNER_AMBIGUOUS")
    if card.get("scope_known", True) is not True:
        result["blockers"].append("CANONICAL_SCOPE_UNKNOWN")
    for edge in card.get("edges", []):
        semantics = edge.get("semantics", {})
        if (
            semantics.get("strength") != "HARD"
            or semantics.get("blocking_stage") != "START"
        ):
            continue
        if edge.get("status") != "READY":
            result["blockers"].append(
                "HARD_START_DEPENDENCY_UNRESOLVED:" + str(edge.get("id", "UNKNOWN"))
            )
    if not result["blockers"]:
        result["result"] = "STARTABLE"
    return result


def evaluate_startability(project: Any, wp_id: str) -> dict[str, Any]:
    """Evaluate startability without any execution-plane or evidence input."""
    return startability_from_view(project_view(project), wp_id)


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
        len(cards) != 180
        or len(scheduled) != 175
        or set(cards) - scheduled != EXCLUDED
        or Counter(card["owner"] for card in cards.values())
        != Counter(dict(zip(OWNERS.values(), (74, 17, 32, 57), strict=True)))
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
        if cards[wp]["owner"] == owner and occupies_implementation_slot(wp, item)
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
        if item["state"] in {"DONE", "CANCELED"} or released_wait(wp, item):
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


CANDIDATE_WINDOW_MINIMUM = 3


def candidate_window(
    candidates: list[dict[str, Any]],
    actionable: Callable[[dict[str, Any]], bool] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Canonical-order prefix through the first actionable candidate.

    Every candidate before the first actionable one stays reported and none of them
    stops the scan, so earlier blocked work cannot starve later executable work. The
    window never reorders, never skips an actionable candidate and is bounded by the
    finite backlog. With no actionable candidate it is the fixed diagnostic head.
    `actionable` classifies one candidate; it defaults to a fully PREPARED status and
    must not weaken any gate (it only selects among already-derived candidates).
    """
    test = actionable or (lambda c: c["status"] == "PREPARED")
    for index, candidate in enumerate(candidates):
        if test(candidate):
            return (
                candidates[: max(CANDIDATE_WINDOW_MINIMUM, index + 1)],
                candidate["wp_id"],
            )
    return candidates[:CANDIDATE_WINDOW_MINIMUM], None


def preflight_health(
    project,
    live,
    evidence,
    owner,
    preferences,
    actionable: Callable[[dict[str, Any]], bool] | None = None,
):
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
        "actionable_next": None,
        "first_blocker": None,
        "reasons": decision.get("reasons", []),
    }
    if decision["status"] in {"UNAVAILABLE", "INVALID_BASELINE"}:
        return result
    active = [
        w
        for w, item in live["items"].items()
        if view["cards"][w]["owner"] == owner and occupies_implementation_slot(w, item)
    ]
    result["deferred_waits"] = [
        {
            "wp_id": w,
            "state": item["state"],
            "blocked": True,
            "reason": released_wait(w, item),
        }
        for w, item in live["items"].items()
        if view["cards"][w]["owner"] == owner and released_wait(w, item)
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
    result["candidates"], result["actionable_next"] = candidate_window(
        candidates, actionable
    )
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
