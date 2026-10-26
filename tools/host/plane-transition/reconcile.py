#!/usr/bin/python3 -I
"""Narrow, audited lifecycle reconciliation for an already merged WP.

This is NOT a general transition bypass. It records CURRENT observed GitHub facts
in Plane for exactly the cases allow-listed in the generated policy
(project_control/lifecycle_reconciliation.yaml): a named profile, WP, pull request,
head, merge commit and parents. It never asserts that skipped historical
transitions happened, never marks DONE, never clears BLOCKED and never calls
AUTO_NEXT. CAP_PROFILE is an operational guard, not a security boundary.

Only MERGED or VALIDATING can be requested. The only mutation is the constructed
state PATCH of the existing Plane adapter, preceded by a durable INTENT audit row
and followed by a fresh exact readback. A merged PR may reconcile an already
blocked IN_PROGRESS item directly to VALIDATING; the BLOCKED label is preserved
and the blocker is never cleared. The ordinary cap-plane-transition rules
(adjacent edges, open-PR predicates) are unchanged.
"""

import contextlib
import datetime as dt
import fcntl
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import re
import resource
import sys
import time
from pathlib import Path
from typing import Any

TRANSITION_PATH = "/usr/local/libexec/cap-plane-transition"
POLICY_SCHEMA = "cap-lifecycle-reconciliation-v1"
OPERATION = "LIFECYCLE_RECONCILE"
TARGETS = ("MERGED", "VALIDATING")
# Only these premerge states can be reconciled; nothing terminal, nothing backwards.
SOURCES = ("READY", "IN_PROGRESS", "IN_REVIEW", "MERGE_READY")
# A run only proves validation started if it reached one of these observable states.
STARTED_RUN_STATUSES = ("in_progress", "completed")
TERMINAL_RUN_CONCLUSIONS = ("success", "failure", "timed_out")
PR_EVENTS = ("pull_request", "pull_request_target")
SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
CASE_ID = re.compile(r"RECON-[A-Z0-9][A-Z0-9-]{2,60}")
CHANGE_ID = re.compile(r"CHG-[0-9]{3}")
WORKFLOW_PATH = re.compile(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml")
CASE_KEYS = {
    "case_id",
    "profile",
    "wp_id",
    "pr",
    "pr_head_sha",
    "merge_sha",
    "parents",
    "changed_files",
    "scope_prefixes",
    "targets",
    "validating_runs",
    "require_successful_runs",
    "approvals",
    "change_record",
}
APPROVAL_KEYS = {
    "scope_answer",
    "control_id_exception",
    "plan_sha256",
    "plan_approval_turn",
}
# An owner with another READY or IN_PROGRESS item has an ambiguous queue (AGENTS.md section 20);
# BACKLOG, review, merged and finished work of the same owner is normal and not a conflict.
OWNER_QUEUE_STATES = ("READY", "IN_PROGRESS")
# Always recorded, so a reconciled state is never mistaken for acceptance.
OUTSTANDING = (
    "skipped_state_history_not_asserted",
    "dor_dod_owner_assessment_not_established_by_reconciliation",
    "integrated_acceptance_not_established",
    "done_not_claimed",
)
t: Any = None  # transition module; tests inject it, production loads the root copy


def load_transition() -> Any:
    loader = importlib.machinery.SourceFileLoader("cap_transition", TRANSITION_PATH)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module: Any = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    module.q = module.load_support()
    return module


def need(value: Any, code: str) -> None:
    if not value:
        raise t.Denied(code)


def validate_policy(
    block: Any, contexts: dict[str, Any], people: dict[str, Any]
) -> dict:
    """Strictly validate the allow-list; the same check runs at build and at use time."""
    ok = (
        isinstance(block, dict)
        and set(block) == {"schema_version", "cases"}
        and block["schema_version"] == POLICY_SCHEMA
        and isinstance(block["cases"], list)
        and 1 <= len(block["cases"]) <= 8
    )
    need(ok, "RECONCILIATION_POLICY_INVALID")
    seen: set[Any] = set()
    for case in block["cases"]:
        need(
            isinstance(case, dict) and set(case) == CASE_KEYS,
            "RECONCILIATION_CASE_INVALID",
        )
        need(CASE_ID.fullmatch(str(case["case_id"])), "RECONCILIATION_CASE_INVALID")
        wp = case["wp_id"]
        need(
            case["profile"] in people and wp in contexts, "RECONCILIATION_CASE_INVALID"
        )
        owner = contexts[wp]["work_package"]["primary_owner"]["canonical_name"]
        need(owner == people[case["profile"]][0], "RECONCILIATION_OWNER_MISMATCH")
        need(
            type(case["pr"]) is int and 0 < case["pr"] < 10**10,
            "RECONCILIATION_CASE_INVALID",
        )
        for name in ("pr_head_sha", "merge_sha"):
            need(SHA.fullmatch(str(case[name])), "RECONCILIATION_CASE_INVALID")
        parents = case["parents"]
        need(
            isinstance(parents, list)
            and len(parents) in {1, 2}
            and all(SHA.fullmatch(str(p)) for p in parents)
            and len(set(parents)) == len(parents),
            "RECONCILIATION_CASE_INVALID",
        )
        need(
            len(parents) == 1 or parents[1] == case["pr_head_sha"],
            "RECONCILIATION_CASE_INVALID",
        )
        need(
            type(case["changed_files"]) is int and 0 < case["changed_files"] <= 1000,
            "RECONCILIATION_CASE_INVALID",
        )
        prefixes = case["scope_prefixes"]
        need(
            isinstance(prefixes, list)
            and prefixes
            and all(
                isinstance(p, str)
                and re.fullmatch(r"[A-Za-z0-9_./-]+/", p)
                and ".." not in p.split("/")
                for p in prefixes
            ),
            "RECONCILIATION_CASE_INVALID",
        )
        targets = case["targets"]
        need(
            isinstance(targets, list)
            and targets
            and len(set(targets)) == len(targets)
            and all(x in TARGETS for x in targets),
            "RECONCILIATION_CASE_INVALID",
        )
        runs = case["validating_runs"]
        need(
            isinstance(runs, list)
            and len(runs) <= 4
            and all(
                isinstance(r, dict)
                and set(r) == {"run_id", "workflow_path"}
                and type(r["run_id"]) is int
                and 0 < r["run_id"] < 10**18
                and WORKFLOW_PATH.fullmatch(str(r["workflow_path"]))
                for r in runs
            )
            and len({r["run_id"] for r in runs}) == len(runs),
            "RECONCILIATION_CASE_INVALID",
        )
        need("VALIDATING" not in targets or runs, "RECONCILIATION_RUNS_REQUIRED")
        need(
            type(case["require_successful_runs"]) is bool, "RECONCILIATION_CASE_INVALID"
        )
        approvals = case["approvals"]
        need(
            isinstance(approvals, dict)
            and set(approvals) == APPROVAL_KEYS
            and UUID.fullmatch(str(approvals["scope_answer"]))
            and UUID.fullmatch(str(approvals["control_id_exception"]))
            and UUID.fullmatch(str(approvals["plan_approval_turn"]))
            and SHA256.fullmatch(str(approvals["plan_sha256"])),
            "RECONCILIATION_APPROVAL_INVALID",
        )
        need(
            CHANGE_ID.fullmatch(str(case["change_record"])),
            "RECONCILIATION_CASE_INVALID",
        )
        identity = (case["profile"], wp, case["pr"])
        need(
            identity not in seen and case["case_id"] not in seen,
            "RECONCILIATION_CASE_DUPLICATE",
        )
        seen.update({identity, case["case_id"]})
    return block


def find_case(block: dict, profile: str, wp: str, target: str) -> dict:
    """The one allow-listed case for this exact profile, WP and target, else denied."""
    cases = [
        c
        for c in block["cases"]
        if c["profile"] == profile and c["wp_id"] == wp and target in c["targets"]
    ]
    need(len(cases) == 1, "RECONCILIATION_NOT_AUTHORIZED")
    return cases[0]


RECOVERY_SCHEMA = "cap-deferred-recovery-v1"
RECOVERY_CASE_ID = re.compile(r"DEFER-[A-Z0-9][A-Z0-9-]{2,60}")
RECOVERY_KEYS = {
    "case_id",
    "profile",
    "wp_id",
    "reconciliation_case",
    "blocker_audit_id",
    "classification",
    "platform_disposition",
    "pending_producers",
    "change_record",
}
DISPOSITION_KEYS = {"pr", "merge_sha", "owner", "path", "deployable", "expires_on"}


def validate_recovery_policy(
    block: Any, lifecycle: dict, contexts: dict[str, Any], people: dict[str, Any]
) -> dict:
    """CHG-033: the allow-list of deferred-acceptance recoveries for a two-parent merge.

    Each case names one reconciliation case (the PR, head, merge, parents and runs it
    re-proves), the original VERIFIED blocker audit, the platform disposition and the
    producer WPs whose deliverables are still pending. It authorizes nothing by itself.
    """
    ok = (
        isinstance(block, dict)
        and set(block) == {"schema_version", "cases"}
        and block["schema_version"] == RECOVERY_SCHEMA
        and isinstance(block["cases"], list)
        and 1 <= len(block["cases"]) <= 4
    )
    need(ok, "RECOVERY_POLICY_INVALID")
    seen: set[Any] = set()
    for case in block["cases"]:
        need(
            isinstance(case, dict) and set(case) == RECOVERY_KEYS,
            "RECOVERY_CASE_INVALID",
        )
        wp, profile = case["wp_id"], case["profile"]
        need(
            RECOVERY_CASE_ID.fullmatch(str(case["case_id"]))
            and profile in people
            and wp in contexts
            and CHANGE_ID.fullmatch(str(case["change_record"]))
            and re.fullmatch(r"[0-9a-f]{64}", str(case["blocker_audit_id"]))
            and case["classification"]
            == "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE",
            "RECOVERY_CASE_INVALID",
        )
        owner = contexts[wp]["work_package"]["primary_owner"]["canonical_name"]
        need(owner == people[profile][0], "RECOVERY_OWNER_MISMATCH")
        base = [
            c
            for c in lifecycle["cases"]
            if c["case_id"] == case["reconciliation_case"]
            and c["profile"] == profile
            and c["wp_id"] == wp
            and "VALIDATING" in c["targets"]
        ]
        need(len(base) == 1, "RECOVERY_RECONCILIATION_CASE_UNKNOWN")
        disposition = case["platform_disposition"]
        need(
            isinstance(disposition, dict)
            and set(disposition) == DISPOSITION_KEYS
            and type(disposition["pr"]) is int
            and 0 < disposition["pr"] < 10**10
            and SHA.fullmatch(str(disposition["merge_sha"]))
            and disposition["owner"] in people
            and re.fullmatch(r"[A-Za-z0-9_./-]+", str(disposition["path"]))
            and re.fullmatch(r"[a-z0-9-]+", str(disposition["deployable"]))
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(disposition["expires_on"])),
            "RECOVERY_DISPOSITION_INVALID",
        )
        producers = case["pending_producers"]
        need(
            isinstance(producers, list)
            and 1 <= len(producers) <= 8
            and len(set(producers)) == len(producers)
            and all(p in contexts and p != wp for p in producers),
            "RECOVERY_PRODUCER_UNKNOWN",
        )
        key = (profile, wp)
        need(key not in seen, "RECOVERY_CASE_DUPLICATE")
        seen.add(key)
    return block


def find_recovery_case(block: dict, profile: str, wp: str) -> dict | None:
    cases = [c for c in block["cases"] if c["profile"] == profile and c["wp_id"] == wp]
    return cases[0] if len(cases) == 1 else None


def expected_refs(case: dict, target: str) -> set[str]:
    refs = {f"pr:{case['pr']}"}
    if target == "VALIDATING":
        refs |= {f"run:{r['run_id']}" for r in case["validating_runs"]}
    return refs


def pr_proof(gh: Any, case: dict, profile: str, wp: str) -> dict:
    """PR bindings: identity, author, head, merge and file count on ONE fresh object.

    ``gather`` starts from an invalidated cache, so the read inside ``pr_fact`` is fresh and
    every predicate (repository, base, author, WP binding, head, merge, count) applies to it.
    """
    pr = t.pr_fact(gh, [f"pr:{case['pr']}"], wp, profile)
    ok = (
        pr.get("number") == case["pr"]
        and pr.get("merged") is True
        and pr.get("state") == "closed"
        and pr.get("head", {}).get("sha") == case["pr_head_sha"]
        and pr.get("merge_commit_sha") == case["merge_sha"]
        and pr.get("changed_files") == case["changed_files"]
    )
    need(ok, "RECONCILIATION_PR_BINDING_MISMATCH")
    return pr


def merge_proof(gh: Any, case: dict, pr: dict) -> dict:
    """Merge commit shape and main reachability, without the mutable current PR base.

    Supports the one-parent squash and the two-parent merge. For two parents the
    second must be the PR head and the first must be an ancestor of the merge; the
    exact parents are bound by policy, which also rejects octopus or unrelated parents.
    """
    sha = case["merge_sha"]
    commit = gh.commit(sha)
    parents = [p.get("sha") for p in commit.get("parents", [])]
    need(parents == case["parents"], "MERGE_PARENT_MISMATCH")
    if len(parents) == 2:
        need(parents[1] == pr["head"]["sha"], "MERGE_SECOND_PARENT_NOT_PR_HEAD")
        gh.ancestor(parents[0], sha)
    main = gh.main_sha()
    gh.ancestor(sha, main)  # the merge is reachable from current main
    gh.branch_deleted(pr["head"]["ref"])
    return {
        "merge_sha": sha,
        "parents": parents,
        "shape": "two_parent_merge" if len(parents) == 2 else "squash",
        "branch_deleted": True,
        "main_sha_observed": main,
    }


def scope_proof(gh: Any, case: dict, pr: dict) -> dict:
    files = gh.files(pr)  # complete, bounded, count-reconciled inventory
    need(len(files) == case["changed_files"], "INCOMPLETE_PR_FILE_SCOPE")
    t.pr_scope_paths(files)
    for prefix in case["scope_prefixes"]:
        need(
            any(
                f["filename"].startswith(prefix) and f.get("status") != "removed"
                for f in files
            ),
            "WP_SCOPE_PATH_MISSING",
        )
    inventory = sorted((f["filename"], f["status"]) for f in files)
    digest = hashlib.sha256(json.dumps(inventory).encode()).hexdigest()
    return {"changed_files": len(files), "inventory_sha256": digest}


def parse_time(value: Any) -> dt.datetime:
    need(isinstance(value, str), "RUN_TIMESTAMP_MISSING")
    try:
        moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise t.Denied("RUN_TIMESTAMP_INVALID") from None
    need(moment.tzinfo is not None, "RUN_TIMESTAMP_INVALID")
    return moment


def run_proof(gh: Any, case: dict) -> list[dict]:
    """Actual started main validation runs at the exact merge SHA; observed honestly."""
    observed = []
    for spec in case["validating_runs"]:
        run = gh.fresh_run(spec["run_id"])
        repository = run.get("repository", {}).get("full_name", "")
        need(run.get("id") == spec["run_id"], "RUN_IDENTITY_MISMATCH")
        need(
            repository.casefold()
            == "Asperant/critical-aerospace-manufacturing".casefold(),
            "RUN_WRONG_REPOSITORY",
        )
        need(run.get("head_sha") == case["merge_sha"], "RUN_WRONG_REVISION")
        need(
            run.get("head_branch") == "main" and run.get("event") not in PR_EVENTS,
            "RUN_NOT_A_MAIN_RUN",
        )
        need(
            str(run.get("path", "")).split("@")[0] == spec["workflow_path"],
            "RUN_WRONG_WORKFLOW",
        )
        need(run.get("status") in STARTED_RUN_STATUSES, "RUN_NOT_STARTED")
        started = parse_time(run.get("run_started_at"))
        status, conclusion = run.get("status"), run.get("conclusion")
        if status == "completed":
            need(conclusion in TERMINAL_RUN_CONCLUSIONS, "RUN_NO_QUALIFYING_CONCLUSION")
            need(
                parse_time(run.get("updated_at")) >= started,
                "RUN_TIMESTAMPS_INCONSISTENT",
            )
        else:
            need(conclusion is None, "RUN_TIMESTAMPS_INCONSISTENT")
        if case["require_successful_runs"]:
            need(
                status == "completed" and conclusion == "success",
                "REQUIRED_RUN_NOT_SUCCESSFUL",
            )
        observed.append(
            {
                "run_id": spec["run_id"],
                "workflow_path": spec["workflow_path"],
                "status": status,
                "conclusion": conclusion,
                "run_started_at": run.get("run_started_at"),
                "updated_at": run.get("updated_at"),
                "head_sha": run["head_sha"],
            }
        )
    return observed


def gather(gh: Any, case: dict, profile: str, wp: str, target: str) -> dict:
    """One complete evidence snapshot; every mutable input is read again from GitHub."""
    gh.invalidate()  # only immutable SHA-addressed commits may be served from cache
    pr = pr_proof(gh, case, profile, wp)
    facts: dict[str, Any] = {
        "pr": {
            "number": pr["number"],
            "head": pr["head"]["sha"],
            "branch": pr["head"]["ref"],
            "merge_commit": pr["merge_commit_sha"],
        },
        "merge": merge_proof(gh, case, pr),
        "scope": scope_proof(gh, case, pr),
        "runs": run_proof(gh, case) if target == "VALIDATING" else [],
    }
    return facts


def stable(facts: dict) -> dict:
    """Facts that must not change between proof and write; main may legitimately move."""
    merge = {k: v for k, v in facts["merge"].items() if k != "main_sha_observed"}
    return {**facts, "merge": merge}


def owner_queue_conflicts(
    plane: Any, profile: str, item: dict, released: set[str] | None = None
) -> list[str]:
    """Other READY or IN_PROGRESS items of the same owner; read-only, selects nothing.

    More than one current or next candidate is the ambiguous queue that needs a
    planning-owner decision, so a reconciliation write must not proceed over it.
    """
    member = t.q.PEOPLE[profile][1]
    active = {plane.states[name] for name in OWNER_QUEUE_STATES}
    released = released or set()
    return sorted(
        str(row.get("external_id") or row.get("id"))
        for row in plane.items
        if row.get("id") != item["id"]
        and member in (row.get("assignees") or [])
        and row.get("state") in active
        and str(row.get("external_id") or row.get("id")) not in released
    )


def verified_slot_releases(
    plane: Any, profile: str, item: dict, policy: dict, gh: Any
) -> set[str]:
    """Return only live-proven blocked waits that no longer occupy the slot.

    Slot Release v2 is a derived scheduler property, not a Plane state. Reconciliation
    may use it only for other blocked queue entries and only after the same semantic
    proof used by AUTO_NEXT has been freshly evaluated. Any unavailable proof leaves
    the entry as a conflict.
    """
    member = t.q.PEOPLE[profile][1]
    candidates = [
        row
        for row in plane.items
        if row.get("id") != item["id"]
        and member in (row.get("assignees") or [])
        and row.get("state") == plane.states["IN_PROGRESS"]
        and plane.blocked in (row.get("labels") or [])
        and isinstance(row.get("external_id"), str)
    ]
    if not candidates:
        return set()
    try:
        loader = importlib.machinery.SourceFileLoader(
            "cap_auto_slots", "/usr/local/libexec/cap-auto-next.py"
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec is not None
        auto: Any = importlib.util.module_from_spec(spec)
        loader.exec_module(auto)
        auto.t = t
        auto.resolver = auto.load_resolver()
        released = set()
        for row in candidates:
            proof = auto.semantic_slot_release_proof(
                t, row["external_id"], profile, policy, gh
            )
            if proof:
                released.add(row["external_id"])
        return released
    except Exception:
        return set()


def reconcile(
    profile, wp, target, envelope, policy, plane, gh, audit, key, now=None
) -> dict:
    """Evaluate and apply one allow-listed reconciliation; the sole write is one PATCH."""
    need(
        profile in t.q.PEOPLE and t.q.WP.fullmatch(wp) and target in TARGETS,
        "INVALID_ARGUMENTS",
    )
    t.policy_checks(policy)
    block = validate_policy(
        policy.get("lifecycle_reconciliation"), policy["contexts"], t.q.PEOPLE
    )
    case = find_case(block, profile, wp, target)
    need(
        set(envelope["evidence_refs"]) == expected_refs(case, target),
        "RECONCILIATION_EVIDENCE_REFS_MISMATCH",
    )
    item = t.find(
        plane, profile, wp, policy
    )  # unique canonical mapping, owner, assignee
    source = plane.names[item["state"]]
    blocked = plane.blocked in item["labels"]
    blocked_post_merge = source == "IN_PROGRESS" and target == "VALIDATING" and blocked
    # CHG-018 keeps ordinary transition guards intact. This narrowly scoped recovery
    # path only repairs a missed post-merge lifecycle edge and deliberately retains
    # the active blocker for downstream validation.
    need(not blocked or blocked_post_merge, "ACTIVE_BLOCKER_UNRESOLVED")
    need(source == target or source in SOURCES, "SOURCE_STATE_NOT_RECONCILABLE")
    if source != target:
        # A no-op is exempt: after a reconcile the owner normally has a next READY item.
        conflicts = owner_queue_conflicts(plane, profile, item)
        if conflicts:
            released = verified_slot_releases(plane, profile, item, policy, gh)
            need(
                not owner_queue_conflicts(plane, profile, item, released),
                "OWNER_QUEUE_CONFLICT",
            )
    facts = gather(gh, case, profile, wp, target)
    stamp = (now or t.now)()
    record = {
        "timestamp": stamp,
        "profile": profile,
        "wp_id": wp,
        "from_state": source,
        "to_state": target,
        "operation": OPERATION,
        "reason": envelope["reason"],
        "evidence_refs": envelope["evidence_refs"],
        "policy_digest": policy["policy_digest"],
    }
    record["audit_id"] = hashlib.sha256(
        json.dumps(record, sort_keys=True).encode()
    ).hexdigest()
    record.update(
        case_id=case["case_id"],
        change_record=case["change_record"],
        approvals=case["approvals"],
        facts=facts,
        outstanding=list(OUTSTANDING),
        skipped_state_history_not_asserted=True,
    )
    if blocked_post_merge:
        record["blocked_preserved"] = True
    if source == target:
        # Verified idempotence: facts are re-proved, nothing is written, no PATCH replay.
        need(plane.issue(item["id"]) == item, "CONCURRENT_PLANE_CHANGE")
        record["result"] = "UNCHANGED"
        audit(record, key)
        return record
    again = gather(
        gh, case, profile, wp, target
    )  # recheck GitHub immediately before writing
    need(stable(again) == stable(facts), "CONCURRENT_GITHUB_CHANGE")
    plane.refresh_items()  # fresh queue snapshot immediately before writing
    released = verified_slot_releases(plane, profile, item, policy, gh)
    need(
        not owner_queue_conflicts(plane, profile, item, released),
        "CONCURRENT_OWNER_QUEUE_CHANGE",
    )
    # The final Plane read comes last, after every slower GitHub read, so a change made
    # to the item during the recheck window blocks the write instead of being overwritten.
    fresh = plane.issue(item["id"])
    t.own(fresh, profile, wp, policy)
    need(fresh == item, "CONCURRENT_PLANE_CHANGE")
    record["facts"] = again  # the snapshot closest to the write, incl. latest main
    record["owner_queue_checked"] = ["entry", "pre_write"]
    record["result"] = "INTENT"
    audit(record, key)  # an unwritable durable audit sink blocks the mutation
    try:
        with contextlib.suppress(Exception):
            # exactly one PATCH, never retried; a lost response may still have applied,
            # so only the fresh readback below decides
            plane.patch(fresh, target)
        after = plane.issue(item["id"])
        t.own(after, profile, wp, policy)
        t.verify_readback(fresh, after, target, plane)
        record["result"] = "VERIFIED"
    except Exception:
        record["result"] = "UNCONFIRMED_REQUIRES_READBACK"
        audit(record, key)
        raise t.Denied("MUTATION_UNCONFIRMED_DO_NOT_RETRY_BLINDLY") from None
    audit(record, key)
    return record


def main() -> int:
    global t
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        if t is None:
            t = load_transition()
        need(os.geteuid() == 0 and len(sys.argv) == 4, "INVALID_INVOCATION")
        need(
            t.TARGETS - {"BLOCKED", "UNBLOCKED"} == t.q.STATES,
            "CANONICAL_WORKFLOW_SCHEMA_CHANGED",
        )
        profile, wp, target = sys.argv[1:]
        need(
            profile in t.q.PEOPLE and t.q.WP.fullmatch(wp) and target in TARGETS,
            "INVALID_ARGUMENTS",
        )
        caller_uid = int(os.environ.get("SUDO_UID", str(os.getuid())))
        os.environ.clear()
        need(
            not getattr(sys.stdin, "isatty", lambda: False)(),
            "REASON_AND_EVIDENCE_JSON_REQUIRED_ON_STDIN",
        )
        envelope = t.parse_input(sys.stdin.buffer.read(8193))
        root = t.ROOT
        policy = json.loads(
            (root / "transition-policy.json").read_text(), object_pairs_hook=t.q.unique
        )
        key = json.loads((root / "credential.json").read_text())["api_key"]
        need(
            isinstance(key, str) and key and not any(c in key for c in "\r\n"),
            "INVALID_CREDENTIAL_CONFIG",
        )
        need(
            key not in json.dumps(envelope) and key not in envelope["reason"],
            "SECRET_IN_INPUT",
        )
        t.verify_policy_sources(policy)
        own_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        need(
            own_hash == policy["implementation_sha256"].get("reconcile"),
            "HELPER_POLICY_REFRESH_REQUIRED",
        )
        t.auto_next_support().require_caller(profile, caller_uid)
        block = validate_policy(
            policy.get("lifecycle_reconciliation"), policy["contexts"], t.q.PEOPLE
        )
        find_case(block, profile, wp, target)  # reject before any external lookup
        lockfd = os.open(
            "/run/cap-plane-queue.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(lockfd, "r+") as lock:
            need(os.fstat(lock.fileno()).st_uid == 0, "UNSAFE_LOCK_OWNER")
            fcntl.flock(lock, fcntl.LOCK_EX)
            time.sleep(1.25)
            plane = t.Plane(key)
            gh = t.GitHub(profile)
            result = reconcile(
                profile, wp, target, envelope, policy, plane, gh, t.append_audit, key
            )
        t.q.emit(result, key)  # no AUTO_NEXT, no preparation, no other WP is touched
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
