#!/usr/bin/python3 -I
"""CTRL-HOST-030: reconcile orthogonal BLOCKED projection from verified audits.

This helper never changes a Plane lifecycle state.  A verified BLOCKED or
UNBLOCKED transition audit is the authority for the orthogonal label only;
missing, malformed, ambiguous, or state-mismatched audit evidence fails closed.
"""

import contextlib
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import resource
import sys
import time
from pathlib import Path
from typing import Any

TRANSITION_PATH = "/usr/local/libexec/cap-plane-transition"
PROJECTION_OPERATION = "BLOCKED_PROJECTION_RECONCILE"
PROJECTION_REASON = (
    "Reconcile orthogonal BLOCKED projection from verified transition audit"
)

t: Any = None


def load_transition() -> Any:
    loader = importlib.machinery.SourceFileLoader(
        "cap_projection_transition", TRANSITION_PATH
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("TRANSITION_SOURCE_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.__dict__["q"] = module.load_support()
    return module


def need(value: Any, code: str) -> None:
    if not value:
        raise t.Denied(code)


def _canonical_items(plane: Any, profile: str, policy: dict) -> list[dict]:
    owner = t.q.PEOPLE[profile][0]
    by_wp: dict[str, dict] = {}
    for item in plane.items:
        wp = item.get("external_id")
        if not isinstance(wp, str) or not wp.startswith("WP-"):
            continue
        if wp not in policy["contexts"]:
            continue
        context_owner = policy["contexts"][wp]["work_package"]["primary_owner"][
            "canonical_name"
        ]
        if context_owner != owner:
            continue
        need(wp not in by_wp, "DUPLICATE_CANONICAL_WP")
        need(
            item.get("external_source") == "projectctl",
            "PLANE_CANONICAL_IDENTITY_MISMATCH",
        )
        need(
            item.get("name", "").startswith("[" + wp + "] "),
            "PLANE_CANONICAL_IDENTITY_MISMATCH",
        )
        metadata = t.q.metadata(item.get("description_html"))
        need(metadata.get("canonical_wp_id") == wp, "PLANE_METADATA_ID_MISMATCH")
        need(metadata.get("canonical_owner") == owner, "PLANE_METADATA_OWNER_MISMATCH")
        need(item.get("state") in plane.names, "UNKNOWN_PLANE_STATE")
        need(
            isinstance(item.get("labels"), list)
            and all(isinstance(x, str) for x in item["labels"]),
            "INVALID_PLANE_LABELS",
        )
        by_wp[wp] = item
    return [by_wp[wp] for wp in sorted(by_wp)]


def _verified_rows(wp: str) -> list[dict]:
    rows = t.blocker_rows(wp)
    need(isinstance(rows, list), "AUDIT_ROWS_UNAVAILABLE")
    return rows


def authoritative_projection(
    wp: str, profile: str, state: str
) -> tuple[str | None, str | None]:
    """Return the label target and source audit id, or no target for no-op.

    The latest VERIFIED BLOCKED/UNBLOCKED row is authoritative.  A present
    label without any trustworthy audit is intentionally left untouched; it is
    not safe to infer that the blocker was resolved.
    """
    rows = _verified_rows(wp)
    latest = t.last_blocker(wp)
    if latest is None:
        return None, None
    need(
        latest.get("profile") == profile and latest.get("wp_id") == wp,
        "AUDIT_PROFILE_WP_BINDING",
    )
    need(t.audit_identity(latest) == latest.get("audit_id"), "AUDIT_IDENTITY_INVALID")
    need(
        latest.get("from_state") == state and latest.get("to_state") == state,
        "AUDIT_LIFECYCLE_STATE_MISMATCH",
    )
    operation = latest.get("operation")
    if operation == "BLOCKED":
        return "BLOCKED", latest["audit_id"]
    if operation != "UNBLOCKED":
        raise t.Denied("AUDIT_OPERATION_AMBIGUOUS")
    resolved = latest.get("resolves_audit_id")
    need(
        isinstance(resolved, str)
        and any(
            row.get("audit_id") == resolved
            and row.get("result") == "VERIFIED"
            and row.get("operation") == "BLOCKED"
            and t.audit_identity(row) == row.get("audit_id")
            for row in rows
        ),
        "UNBLOCKED_RESOLUTION_AUDIT_INVALID",
    )
    return "UNBLOCKED", latest["audit_id"]


def _record(
    item: dict,
    profile: str,
    target: str,
    source_audit_id: str,
    policy: dict,
    result: str,
    state: str,
) -> dict:
    record = {
        "timestamp": t.now(),
        "profile": profile,
        "wp_id": item["external_id"],
        "from_state": state,
        "to_state": state,
        "operation": PROJECTION_OPERATION,
        "reason": PROJECTION_REASON,
        "evidence_refs": ["audit:" + source_audit_id],
        "policy_digest": policy["policy_digest"],
        "projection_target": target,
        "projection_source_audit_id": source_audit_id,
        "lifecycle_unchanged": True,
        "result": result,
    }
    record["audit_id"] = hashlib.sha256(
        json.dumps(
            {k: record.get(k) for k in t.AUDIT_IDENTITY_FIELDS}, sort_keys=True
        ).encode()
    ).hexdigest()
    return record


def reconcile_item(
    plane: Any, item: dict, profile: str, policy: dict, audit, key: str
) -> dict:
    wp = item["external_id"]
    state = plane.names[item["state"]]
    item = dict(item)
    item["_projection_state"] = state
    target, source_audit_id = authoritative_projection(wp, profile, state)
    has_label = plane.blocked in item["labels"]
    if target is None or (target == "BLOCKED") == has_label:
        return {
            "wp_id": wp,
            "projection": "BLOCKED" if has_label else "UNBLOCKED",
            "action": "UNCHANGED",
            "source_audit_id": source_audit_id,
        }
    fresh = plane.issue(item["id"])
    need(
        fresh == {k: v for k, v in item.items() if k != "_projection_state"},
        "CONCURRENT_PLANE_CHANGE",
    )
    if not isinstance(source_audit_id, str):
        raise t.Denied("AUDIT_SOURCE_ID_MISSING")
    record = _record(item, profile, target, source_audit_id, policy, "INTENT", state)
    audit(record, key)
    try:
        with contextlib.suppress(Exception):
            plane.patch(fresh, target)
        after = plane.issue(item["id"])
        need(
            after.get("state") == fresh.get("state"),
            "WORKFLOW_CHANGED_DURING_PROJECTION_UPDATE",
        )
        t.verify_readback(fresh, after, target, plane)
        record["result"] = "VERIFIED"
    except Exception:
        record["result"] = "UNCONFIRMED_REQUIRES_READBACK"
        audit(record, key)
        raise t.Denied("MUTATION_UNCONFIRMED_DO_NOT_RETRY_BLINDLY") from None
    audit(record, key)
    return {
        "wp_id": wp,
        "projection": target,
        "action": "REPAIRED",
        "source_audit_id": source_audit_id,
    }


def reconcile_profile(profile: str, policy: dict, plane: Any, audit, key: str) -> dict:
    need(profile in t.q.PEOPLE, "INVALID_PROFILE")
    # First evaluate every candidate.  One unknown/ambiguous audit blocks all
    # writes, so a partial projection repair cannot hide an unresolved source.
    items = _canonical_items(plane, profile, policy)
    decisions = []
    for item in items:
        state = plane.names[item["state"]]
        target, source_audit_id = authoritative_projection(
            item["external_id"], profile, state
        )
        has_label = plane.blocked in item["labels"]
        if target is None and has_label:
            raise t.Denied("AUDIT_PROJECTION_SOURCE_UNAVAILABLE")
        action = (
            "UNCHANGED"
            if target is None or (target == "BLOCKED") == has_label
            else "REPAIR"
        )
        decisions.append((item, target, source_audit_id, action))
    repaired = []
    unchanged = []
    for item, _target, source_audit_id, action in decisions:
        if action == "UNCHANGED":
            unchanged.append(
                {
                    "wp_id": item["external_id"],
                    "projection": "BLOCKED"
                    if plane.blocked in item["labels"]
                    else "UNBLOCKED",
                    "source_audit_id": source_audit_id,
                }
            )
            continue
        repaired.append(reconcile_item(plane, item, profile, policy, audit, key))
    return {
        "schema": "cap-blocked-projection-reconcile-v1",
        "result": "PASS",
        "profile": profile,
        "repaired": repaired,
        "unchanged": unchanged,
        "lifecycle_mutations": 0,
    }


def main() -> int:
    global t
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        t = load_transition()
        need(os.geteuid() == 0 and len(sys.argv) == 2, "INVALID_INVOCATION")
        profile = sys.argv[1]
        caller_uid = int(os.environ.get("SUDO_UID", str(os.getuid())))
        os.environ.clear()
        root = t.ROOT
        policy = json.loads(
            (root / "transition-policy.json").read_text(), object_pairs_hook=t.q.unique
        )
        key = json.loads((root / "credential.json").read_text())["api_key"]
        need(
            isinstance(key, str) and key and not any(c in key for c in "\r\n"),
            "INVALID_CREDENTIAL_CONFIG",
        )
        t.verify_policy_sources(policy)
        expected = policy.get("implementation_sha256", {}).get("projection_reconcile")
        need(
            isinstance(expected, str)
            and hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == expected,
            "HELPER_POLICY_REFRESH_REQUIRED",
        )
        t.auto_next_support().require_caller(profile, caller_uid)
        lockfd = os.open(
            "/run/cap-plane-queue.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(lockfd, "r+") as lock:
            need(os.fstat(lock.fileno()).st_uid == 0, "UNSAFE_LOCK_OWNER")
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX)
            time.sleep(1.25)
            plane = t.Plane(key)
            result = reconcile_profile(profile, policy, plane, t.append_audit, key)
        t.q.emit(result, key)
        return 0
    except Exception as exc:
        denied = getattr(t, "Denied", None)
        if denied is not None and isinstance(exc, denied):
            print(
                json.dumps(
                    {"result": "DENIED", "reason_code": getattr(exc, "code", None)},
                    sort_keys=True,
                )
            )
        else:
            print(
                '{"result":"UNAVAILABLE","reason_code":"EVIDENCE_OR_SERVICE_UNAVAILABLE"}'
            )
        return 2


if __name__ == "__main__":
    sys.exit(main())
