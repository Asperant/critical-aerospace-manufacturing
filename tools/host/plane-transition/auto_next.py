"""CTRL-HOST-004: root-owned AUTO_NEXT orchestration; existing transition guards."""

import hashlib
import importlib.machinery
import importlib.util
import json
import os
import pwd
import re
import sys
from pathlib import Path
from typing import Any

resolver: Any = None


def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "execution_queue", "/usr/local/libexec/execution_queue.py"
    )
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path("/etc/cap-plane-queue")


def require_caller(profile, caller=None):
    """Only the matching Unix account, or an actual root administrator."""
    caller = (
        int(os.environ.get("SUDO_UID", str(os.getuid()))) if caller is None else caller
    )
    if caller not in {0, pwd.getpwnam(profile).pw_uid}:
        raise PermissionError("PROFILE_UID_MISMATCH")


def live_view(t, plane, policy):
    items = {}
    for item in plane.items:
        wp = item.get("external_id", "")
        if not wp.startswith("WP-"):
            continue
        if wp in items or wp not in policy["contexts"]:
            raise t.Denied("DUPLICATE_OR_UNKNOWN_CANONICAL_WP")
        profile = next(
            p
            for p, data in t.q.PEOPLE.items()
            if data[0]
            == policy["contexts"][wp]["work_package"]["primary_owner"]["canonical_name"]
        )
        t.own(item, profile, wp, policy)
        if item["state"] not in plane.names:
            raise t.Denied("UNKNOWN_PLANE_STATE")
        items[wp] = {
            "owner": t.q.PEOPLE[profile][0],
            "state": plane.names[item["state"]],
            "assignees": item["assignees"],
            "blocked": plane.blocked in item["labels"],
        }
    return {"complete": True, "items": items}


def discover(gh, t):
    """Bounded fresh repository comments; immutable-revision/author checks follow.

    No new confirmation or synthetic assessment is written. Existing attributable
    native/legacy evidence is discovered by WP ID and actual current main SHA.
    """
    result = []
    for page in range(1, 21):
        data = gh._get(f"{t.REPO}/issues/comments?per_page=100&page={page}")
        t.need(isinstance(data, list), "GITHUB_COMMENT_SCHEMA_UNKNOWN")
        result.extend(data)
        if len(data) < 100:
            return result
    raise t.Denied("GITHUB_COMMENT_PAGINATION_INCOMPLETE")


def candidate_evidence(t, plane, policy, profile, gh, comments, live):
    sha = gh.main_sha()
    result = {
        "complete": True,
        "source_manifest": policy["source_manifest"],
        "candidates": {},
    }
    envelopes = {}
    for wp in policy["execution_preferences"]["sequences"][t.q.PEOPLE[profile][0]]:
        if live["items"][wp]["state"] != "BACKLOG" or live["items"][wp]["blocked"]:
            continue
        # Exact ID boundaries; unrelated prose/reviews are not guessed into DoR.
        refs = [
            "comment:" + str(comment["id"])
            for comment in comments
            if re.search(
                r"(?<![A-Z0-9-])" + re.escape(wp) + r"(?![A-Z0-9-])",
                comment.get("body") or "",
            )
            and sha in (comment.get("body") or "")
            and (
                "DOR-" in (comment.get("body") or "")
                or "cap_plane_transition" in (comment.get("body") or "")
            )
        ]
        entry: dict[str, Any] = {
            "result": "UNKNOWN",
            "dor": "UNKNOWN",
            "reason": "DOR_EVIDENCE_UNAVAILABLE",
        }
        result["candidates"][wp] = entry
        if not refs:
            continue
        t.need(len(refs) <= 16, "AMBIGUOUS_EVIDENCE_DISCOVERY")
        envelope = {
            "reason": "AUTO_NEXT canonical first verified eligible preference",
            "evidence_refs": refs,
        }
        try:
            item = t.find(plane, profile, wp, policy)
            t.evaluate(
                profile, wp, "BACKLOG", "READY", item, plane, policy, gh, envelope
            )
            records = t.records(gh, refs, wp, sha)
            proofs = {}
            for _, record in records:
                for identity, data in record.get("dependency_readiness", {}).items():
                    proofs[identity] = dict(data, result="PASS")
            entry.update(
                result="PASS",
                dor="PASS",
                reason=None,
                evidence_refs=refs,
                dependencies=proofs,
            )
            envelopes[wp] = envelope
        except t.Denied as exc:
            entry["reason"] = exc.code
    return result, envelopes


def advance_owner(
    t, profile, policy, plane_factory, gh_factory, audit, key, preview=False
):
    """Caller holds the shared pacing lock for the entire resolve/recheck/apply."""
    global resolver
    if resolver is None:
        resolver = load_resolver()
    plane = plane_factory()
    live = live_view(t, plane, policy)
    project = policy["execution_project"]
    empty = {
        "complete": True,
        "source_manifest": policy["source_manifest"],
        "candidates": {},
    }
    first = resolver.compute_next_eligible(
        project, live, empty, profile, policy["execution_preferences"]
    )
    if first["status"] != "NO_TASK" or first.get("reasons") == [
        "NO_REMAINING_SCHEDULED_WORK"
    ]:
        return first
    try:
        gh = gh_factory(profile)
        observed_sha = gh.main_sha()
        evidence, envelopes = candidate_evidence(
            t, plane, policy, profile, gh, discover(gh, t), live
        )
    except t.Denied as exc:
        return {**first, "status": "UNAVAILABLE", "reasons": [exc.code]}
    result = resolver.compute_next_eligible(
        project, live, evidence, profile, policy["execution_preferences"]
    )
    # Decision audit is not an execution database; queue computes fresh on read.
    audit(
        {
            "timestamp": t.now(),
            "operation": "AUTO_NEXT_PREVIEW" if preview else "AUTO_NEXT",
            "profile": profile,
            "result": result["status"],
            "decision": result,
            "policy_digest": policy["policy_digest"],
        },
        key,
    )
    if preview or result["status"] != "PROPOSED_NEXT":
        return result
    wp = result["wp_id"]
    # External writer may change ANY owned active work, not just selected issue.
    fresh = plane_factory()
    fresh_live = live_view(t, fresh, policy)
    gh.cache.clear()
    if fresh_live != live or gh.main_sha() != observed_sha:
        return {
            **result,
            "status": "UNAVAILABLE",
            "reasons": ["CONCURRENT_CHANGE_RECOMPUTE_REQUIRED"],
        }
    # Re-read attribution/artifacts and all existing transition gates; no stale PASS.
    gh.cache.clear()
    t.verify_policy_sources(policy)

    def prewrite():
        t.need(
            live_view(t, plane_factory(), policy) == fresh_live,
            "CONCURRENT_CHANGE_RECOMPUTE_REQUIRED",
        )

    proof = t.execute(
        profile,
        wp,
        "READY",
        envelopes[wp],
        policy,
        fresh,
        gh,
        audit,
        key,
        prewrite=prewrite,
    )
    if proof["result"] != "VERIFIED":
        return {
            **result,
            "status": "UNAVAILABLE",
            "reasons": ["PROMOTION_NOT_VERIFIED"],
        }
    return {**result, "status": "READY", "transition_result": "VERIFIED"}


def after_done(t, wp, policy, plane_factory, gh_factory, audit, key):
    """Only called after VERIFIED DONE, under the same shared lock."""
    global resolver
    if resolver is None:
        resolver = load_resolver()
    results = {}
    for owner in resolver.affected_owners(policy["execution_project"], wp):
        profile = next(p for p, data in t.q.PEOPLE.items() if data[0] == owner)
        try:
            results[profile] = advance_owner(
                t, profile, policy, plane_factory, gh_factory, audit, key
            )
        except Exception:
            results[profile] = {
                "status": "UNAVAILABLE",
                "reasons": ["ADVANCE_REQUIRES_RECOVERY"],
            }
    return results


def load_transition():
    loader = importlib.machinery.SourceFileLoader(
        "cap_transition", "/usr/local/libexec/cap-plane-transition"
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    module.q = module.load_support()
    return module


def main():
    import fcntl
    import resource

    global resolver
    resolver = load_resolver()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        if os.geteuid() != 0:
            raise PermissionError()
        args = sys.argv[1:]
        preview = args[:1] == ["preview"]
        if preview:
            args = args[1:]
        if len(args) != 1 or args[0] not in {"--all", *resolver.OWNERS}:
            raise ValueError()
        if args[0] == "--all":
            if int(os.environ.get("SUDO_UID", "0")) != 0:
                raise PermissionError("ADMIN_ROOT_REQUIRED")
            profiles = list(resolver.OWNERS)
        else:
            require_caller(args[0])
            profiles = [args[0]]
        os.environ.clear()
        t = load_transition()
        policy = json.loads(
            (ROOT / "transition-policy.json").read_text(), object_pairs_hook=t.q.unique
        )
        t.verify_policy_sources(policy)
        t.policy_checks(policy)
        for name, path in {
            "auto_next": "/usr/local/libexec/cap-auto-next.py",
            "execution_queue": "/usr/local/libexec/execution_queue.py",
        }.items():
            t.need(
                hashlib.sha256(Path(path).read_bytes()).hexdigest()
                == policy["implementation_sha256"][name],
                "AUTO_NEXT_POLICY_REFRESH_REQUIRED",
            )
        key = json.loads((ROOT / "credential.json").read_text())["api_key"]
        fd = os.open(
            "/run/cap-plane-queue.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "r+") as lock:
            t.need(os.fstat(lock.fileno()).st_uid == 0, "UNSAFE_LOCK_OWNER")
            fcntl.flock(lock, fcntl.LOCK_EX)
            results = {}
            for profile in profiles:
                try:
                    results[profile] = advance_owner(
                        t,
                        profile,
                        policy,
                        lambda: t.Plane(key),
                        t.GitHub,
                        (lambda *_: None) if preview else t.append_audit,
                        key,
                        preview,
                    )
                except t.Denied as exc:
                    results[profile] = {"status": "UNAVAILABLE", "reasons": [exc.code]}
                    if exc.code == "MUTATION_UNCONFIRMED_DO_NOT_RETRY_BLINDLY":
                        break
                except Exception:
                    results[profile] = {
                        "status": "UNAVAILABLE",
                        "reasons": ["EVIDENCE_OR_LIVE_READ_UNAVAILABLE"],
                    }
        # Scope-filtered sanitized decisions, not raw GitHub/Plane payloads.
        t.q.emit({"profiles": results}, key)
        return (
            0
            if all(
                r["status"] in {"CURRENT", "READY", "NO_TASK"} for r in results.values()
            )
            else 2
        )
    except Exception:
        print('{"status":"UNAVAILABLE","reason":"AUTO_NEXT_GUARD_OR_LIVE_READ_FAILED"}')
        return 2


if __name__ == "__main__":
    sys.exit(main())
