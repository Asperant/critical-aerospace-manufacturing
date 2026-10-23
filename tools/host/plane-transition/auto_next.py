"""CTRL-HOST-004: root-owned AUTO_NEXT orchestration; existing transition guards."""

import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import pwd
import re
import sys
from copy import copy
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


def load_preparation():
    spec = importlib.util.spec_from_file_location(
        "cap_preparation_read", "/usr/local/libexec/cap-preparation.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
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


def live_view(t, plane, policy, profile=None, gh=None):
    requested_profile = profile
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
        if (
            requested_profile == profile
            and policy.get("deferred_acceptance_schema") == "cap-deferred-acceptance-v1"
            and items[wp]["state"] == "VALIDATING"
            and items[wp]["blocked"]
        ):
            proof = deferred_proof(t, wp, profile, policy, gh or t.GitHub(profile))
            if proof:
                items[wp]["deferred_acceptance"] = proof
        if (
            requested_profile == profile
            and policy.get("external_wait_schema") == "cap-external-integration-wait-v1"
            and items[wp]["state"] == "IN_PROGRESS"
            and items[wp]["blocked"]
        ):
            proof = external_wait_proof(t, wp, profile, policy, gh or t.GitHub(profile))
            if proof:
                items[wp]["external_integration_wait"] = proof
    return {"complete": True, "items": items}


def check_scope_projection(t, gh, wp, blobs, policy):
    """Merge-time WBS/RTM content for this WP must equal the pinned current content.

    Blob bytes are verified against their Git SHA; any missing, oversized, ambiguous
    or unparsable input denies the proof (UNKNOWN never frees the slot).
    """
    expected = policy.get("scope_projections", {}).get(wp)
    refs = policy["contexts"][wp]["work_package"].get("requirement_refs")
    t.need(
        policy.get("scope_projection_schema") == "cap-scope-projection-v1"
        and isinstance(expected, str)
        and isinstance(refs, list),
        "DEFERRED_SCOPE_PROJECTION_UNAVAILABLE",
    )
    texts = {}
    for path in (resolver.WBS_PATH, resolver.RTM_PATH):
        blob_sha = blobs.get(path)
        t.need(
            isinstance(blob_sha, str) and re.fullmatch(r"[a-f0-9]{40}", blob_sha),
            "DEFERRED_SCOPE_PROJECTION_UNAVAILABLE",
        )
        blob = gh._get(f"{t.REPO}/git/blobs/{blob_sha}")
        size = blob.get("size")
        t.need(
            blob.get("encoding") == "base64"
            and type(size) is int
            and 0 < size <= 4_000_000,
            "DEFERRED_SCOPE_PROJECTION_UNAVAILABLE",
        )
        try:
            raw = base64.b64decode(blob.get("content", ""), validate=False)
            text = raw.decode("utf-8")
        except (ValueError, TypeError):
            raise t.Denied("DEFERRED_SCOPE_PROJECTION_UNAVAILABLE") from None
        t.need(
            len(raw) == size
            and hashlib.sha1(
                b"blob " + str(size).encode() + b"\0" + raw, usedforsecurity=False
            ).hexdigest()
            == blob_sha,
            "DEFERRED_SCOPE_PROJECTION_UNAVAILABLE",
        )
        texts[path] = text
    try:
        actual = resolver.scope_projection(
            wp, refs, texts[resolver.WBS_PATH], texts[resolver.RTM_PATH]
        )
    except ValueError:
        raise t.Denied("DEFERRED_SCOPE_PROJECTION_UNAVAILABLE") from None
    t.need(actual == expected, "DEFERRED_CANONICAL_SCOPE_CHANGED")


def check_canonical_scope(t, gh, wp, sha, policy):
    """The WP's canonical inputs at revision `sha` must equal the pinned policy."""
    tree = gh._get(f"{t.REPO}/git/trees/{sha}?recursive=1")
    t.need(tree.get("truncated") is False, "DEFERRED_SOURCE_TREE_INCOMPLETE")
    blobs = {r["path"]: r.get("sha") for r in tree["tree"]}
    sources = (
        set(policy["contexts"][wp]["source_manifest"])
        | {"docs/02_System_Architecture_Specification.md"}
    ) - resolver.PROJECTED_SOURCES
    t.need(
        all(
            blobs.get(p) == policy["source_git_blobs"].get(p) and blobs.get(p)
            for p in sources
        ),
        "DEFERRED_CANONICAL_SCOPE_CHANGED",
    )
    # Shared WBS/RTM files are compared by this WP's own projection only.
    check_scope_projection(t, gh, wp, blobs, policy)


def exact_field(text, label):
    """Single-line `Label: value`; missing or repeated labels are ambiguous."""
    values = re.findall(r"(?im)^" + re.escape(label) + r": ([^\r\n]+)$", text)
    return values[0].strip() if len(values) == 1 else None


AMBIGUOUS = object()


def reassertion(t, wp, profile, verified):
    """Latest UNCHANGED BLOCKED re-assertion of the same verified active blocker.

    The VERIFIED record stays the only authority that the blocker is active; a
    re-assertion may merely carry fresh assessment evidence for that same blocker.
    Returns None when there is none, AMBIGUOUS for any broken, edited or
    contradictory chain, otherwise the re-assertion row.
    """
    rows = t.blocker_rows(wp)
    if not rows:
        return None
    known = [
        i
        for i, r in enumerate(rows)
        if r.get("audit_id") == verified.get("audit_id")
        and r.get("result") == "VERIFIED"
    ]
    if len(known) != 1:
        return AMBIGUOUS
    later = rows[known[0] + 1 :]
    if not later:
        return None
    if t.audit_identity(verified) != verified.get("audit_id"):
        return AMBIGUOUS
    for row in later:
        if not (
            row.get("result") == "UNCHANGED"
            and row.get("operation") == "BLOCKED"
            and row.get("wp_id") == wp
            and row.get("profile") == profile
            and row.get("from_state") == "IN_PROGRESS"
            and row.get("to_state") == "IN_PROGRESS"
            and row.get("active_blocker_audit_id") == verified["audit_id"]
            and row.get("reason") == verified.get("reason")
            and "blocker" not in row
            and t.audit_identity(row) == row.get("audit_id")
        ):
            return AMBIGUOUS
    return later[-1]


def external_wait_proof(t, wp, profile, policy, gh):
    """Owner assessment, verified blocker audit and canonical dependency binding.

    The slot is freed only for an unedited owner-authored comment, referenced by
    the root verified BLOCKED audit or by a later UNCHANGED re-assertion of that
    same verified blocker, that states an approved external wait class and
    `Owner-executable implementation work: NONE`, cites a canonical readiness node
    of this WP's own dependency edges at an explicit level, and was assessed
    against canonical inputs that still match. Absence, ambiguity, UNKNOWN or any
    mismatch leaves the slot occupied; no Plane field or reason text alone suffices,
    and UNCHANGED is never equivalent to VERIFIED.
    """
    global resolver
    if resolver is None:
        resolver = load_resolver()
    verified = t.last_blocker(wp)
    reason = verified.get("reason", "") if verified else ""
    classification = next(
        (
            c
            for c in sorted(resolver.EXTERNAL_WAIT_CLASSES)
            if re.match(re.escape(c) + r"(?::|\s|$)", reason)
        ),
        None,
    )
    if not (
        verified
        and classification
        and verified.get("result") == "VERIFIED"
        and verified.get("operation") == "BLOCKED"
        and verified.get("from_state") == "IN_PROGRESS"
        and verified.get("to_state") == "IN_PROGRESS"
        and verified.get("profile") == profile
    ):
        return None
    try:
        again = reassertion(t, wp, profile, verified)
        if again is AMBIGUOUS:
            return None
        # Fresh re-assertion evidence first; the original assessment remains valid.
        for source in ([again] if again else []) + [verified]:
            proof = assess_external_wait(
                t, wp, profile, policy, gh, verified, source, classification
            )
            if proof:
                return proof
    except t.Denied:
        pass  # UNKNOWN never frees the slot.
    return None


def assess_external_wait(t, wp, profile, policy, gh, verified, source, classification):
    try:
        ids = [
            r[8:]
            for r in source.get("evidence_refs", [])
            if re.fullmatch(r"comment:[1-9][0-9]{0,15}", r)
        ]
        t.need(len(ids) == 1, "EXTERNAL_WAIT_ASSESSMENT_REQUIRED")
        comment = gh._get(f"{t.REPO}/issues/comments/{ids[0]}")
        text = comment.get("body")
        t.need(
            isinstance(text, str)
            and str((comment.get("user") or {}).get("login", "")).casefold()
            == t.GITHUB[profile].casefold()
            and comment.get("created_at")
            and comment.get("created_at") == comment.get("updated_at"),
            "EXTERNAL_WAIT_ASSESSMENT_NOT_OWNER_UNEDITED",
        )
        sha = exact_field(text, "Canonical main revision")
        t.need(
            exact_field(text, "External integration wait class") == classification
            and exact_field(text, "Owner-executable implementation work") == "NONE"
            and sha is not None
            and re.fullmatch(r"[0-9a-f]{40}", sha),
            "EXTERNAL_WAIT_ASSESSMENT_INCOMPLETE",
        )
        record = t.native_record(text, wp, sha)
        t.need(
            record.get("blocker") == verified.get("blocker"),
            "EXTERNAL_WAIT_BLOCKER_ASSESSMENT_CHANGED",
        )
        dependency = (record.get("blocker") or {}).get("external_dependency") or ""
        edges = {
            e["predecessor"]["node"]
            for e in policy["contexts"][wp]["dependency_edges"]
            if isinstance((e.get("predecessor") or {}).get("node"), str)
        }
        nodes = sorted(
            n
            for n in set(re.findall(r"DN-[A-Z0-9]+(?:-[A-Z0-9]+)*", dependency))
            if n in edges
            and any(
                re.search(re.escape(n) + r"\s+" + re.escape(level) + r"\b", dependency)
                for level in policy["node_levels"].get(n, [])
            )
        )
        t.need(nodes, "EXTERNAL_WAIT_CANONICAL_DEPENDENCY_MISSING")
        # The assessment must still describe today's canonical inputs and evidence.
        check_canonical_scope(t, gh, wp, sha, policy)
        t.blocker_evidence(gh, record, "BLOCKER-OBSERVED", gh.main_sha())
        proof = {
            "schema": "cap-external-integration-wait-v1",
            "wp_id": wp,
            "owner": t.q.PEOPLE[profile][0],
            "classification": classification,
            "owner_work_remaining": False,
            "audit_id": verified["audit_id"],
            "comment_id": ids[0],
            "assessment_digest": hashlib.sha256(text.encode()).hexdigest(),
            "dependency_nodes": nodes,
        }
        if source is not verified:
            proof["reassertion_audit_id"] = source["audit_id"]
        return proof
    except t.Denied:
        return None


def deferred_proof(t, wp, profile, policy, gh):
    """Existing attributable owner assessment plus real merged/CI/audit facts.

    Absence, ambiguity or stale canonical scope leaves the slot occupied. No
    Plane field or free-text reason alone authorizes deferred release.
    """
    global resolver
    if resolver is None:
        resolver = load_resolver()
    previous = t.last_blocker(wp)
    if not (
        previous
        and previous.get("result") == "VERIFIED"
        and previous.get("operation") == "BLOCKED"
        and previous.get("from_state") == "VALIDATING"
        and previous.get("to_state") == "VALIDATING"
        and previous.get("profile") == profile
    ):
        return None
    refs = previous.get("evidence_refs", [])
    try:
        pr = t.pr_fact(gh, refs, wp, profile)
        text = pr.get("body") or ""

        def field(label):
            values = re.findall(r"(?im)^" + re.escape(label) + r": ([^\r\n]+)$", text)
            return values[0] if len(values) == 1 else None

        classification = "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE"
        if (
            field("Deferred acceptance class") != classification
            or field("Owner-executable implementation work") != "NONE"
            or not previous.get("reason", "").startswith(classification)
        ):
            return None
        t.need(pr.get("merged") is True, "DEFERRED_PR_NOT_MERGED")
        sha = pr["merge_commit_sha"]
        gh.merged_shape(pr)
        # Scope, readiness, architecture and final acceptance must still match.
        check_canonical_scope(t, gh, wp, sha, policy)
        record = t.native_record(text, wp, sha)
        t.need(
            record.get("blocker") == previous.get("blocker"),
            "DEFERRED_BLOCKER_ASSESSMENT_CHANGED",
        )
        t.need(record["_artifact_refs"], "DEFERRED_EVIDENCE_MISSING")
        for ref in record["_artifact_refs"]:
            gh.artifact(ref, sha)
        runs = [gh.run(int(r.split(":")[1])) for r in refs if r.startswith("run:")]
        t.need(
            any(
                r.get("head_sha") == sha
                and r.get("head_branch") == "main"
                and r.get("event") != "pull_request"
                and r.get("status") == "completed"
                and r.get("conclusion") == "success"
                for r in runs
            ),
            "DEFERRED_POST_MERGE_CI_UNVERIFIED",
        )
        t.ci(gh, sha, policy)
        return {
            "schema": "cap-deferred-acceptance-v1",
            "wp_id": wp,
            "owner": t.q.PEOPLE[profile][0],
            "classification": classification,
            "implementation_complete": True,
            "owner_work_remaining": False,
            "merge_sha": sha,
            "audit_id": previous["audit_id"],
            "assessment_digest": hashlib.sha256(text.encode()).hexdigest(),
        }
    except t.Denied:
        return None  # UNKNOWN never frees the slot.


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


def candidate_evidence(t, plane, policy, profile, gh, comments, live, future=False):
    if future:
        plane = copy(plane)
        plane.items = [
            dict(item, state=plane.states["DONE"])
            if item.get("assignees") == [t.q.PEOPLE[profile][1]]
            and resolver.occupies_implementation_slot(
                item.get("external_id"), live["items"].get(item.get("external_id"), {})
            )
            else item
            for item in plane.items
        ]
    sha = gh.main_sha()
    result = {
        "complete": True,
        "source_manifest": policy["source_manifest"],
        "candidates": {},
    }
    envelopes = {}
    generated = set()
    if policy.get("preparation_schema"):
        tree = gh._get(f"{t.REPO}/git/trees/{sha}?recursive=1")
        t.need(tree.get("truncated") is False, "REPOSITORY_TREE_INCOMPLETE")
        generated = {row["path"] for row in tree["tree"]}
        load_preparation().verify_remote_sources(t, gh, sha, policy)
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
        ids = policy["dor_task"] + policy["contexts"][wp]["work_package"]["dor_refs"]
        entry["deficits"] = [
            {
                "canonical_id": identity,
                "reason": "ACCOUNTABLE_ASSESSMENT_UNVERIFIED",
                "criterion": policy.get("criteria_definitions", {}).get(identity, []),
            }
            for identity in ids
        ]
        if not refs and f"evidence/{wp}/AUTO_PREPARATION.md" not in generated:
            continue
        if not refs:
            refs = [f"repo:evidence/{wp}/AUTO_PREPARATION.md"]
        if len(refs) > 16:
            entry["reason"] = "AMBIGUOUS_EVIDENCE_DISCOVERY"
            continue
        envelope = {
            "reason": "AUTO_NEXT canonical first verified eligible preference",
            "evidence_refs": refs,
        }
        try:
            try:
                records = t.records(gh, refs, wp, sha)
                record = t.confirmation(
                    records, [t.GITHUB[profile]], wp, "BACKLOG", "READY", sha, policy
                )
                entry["deficits"] = []
                for identity in ids:
                    try:
                        t.criteria(gh, record, [identity], sha)
                    except t.Denied as exc:
                        entry["deficits"].append(
                            {
                                "canonical_id": identity,
                                "reason": exc.code,
                                "criterion": policy.get("criteria_definitions", {}).get(
                                    identity, []
                                ),
                            }
                        )
            except t.Denied:
                pass  # Diagnostic detail never replaces the authoritative evaluator.
            item = t.find(plane, profile, wp, policy)
            t.evaluate(
                profile, wp, "BACKLOG", "READY", item, plane, policy, gh, envelope
            )
            records = t.records(gh, refs, wp, sha)
            proofs = {}
            edges = {
                edge["id"]: edge for edge in policy["contexts"][wp]["dependency_edges"]
            }
            for author, record in records:
                for identity, data in record.get("dependency_readiness", {}).items():
                    edge = edges.get(identity)
                    if edge is None:
                        continue
                    producer = policy["node_owners"].get(edge["predecessor"]["node"])
                    if (
                        producer in t.GITHUB
                        and author.casefold() == t.GITHUB[producer].casefold()
                    ):
                        proofs[identity] = dict(data, result="PASS")
            entry.update(
                result="PASS",
                dor="PASS",
                reason=None,
                evidence_refs=refs,
                dependencies=proofs,
                deficits=[],
            )
            envelopes[wp] = envelope
        except t.Denied as exc:
            entry["reason"] = exc.code
    return result, envelopes


def owner_health(t, profile, policy, plane, gh_factory):
    """Fresh read-only preflight, including GitHub auth even when work is active."""
    global resolver
    if resolver is None:
        resolver = load_resolver()
    live = live_view(
        t,
        plane,
        policy,
        profile,
        gh_factory(profile) if policy.get("deferred_acceptance_schema") else None,
    )
    evidence = {
        "complete": True,
        "source_manifest": policy["source_manifest"],
        "candidates": {},
    }
    try:
        gh = gh_factory(profile)
        evidence, _ = candidate_evidence(
            t, plane, policy, profile, gh, discover(gh, t), live, future=True
        )
    except Exception as exc:
        result = resolver.preflight_health(
            policy["execution_project"],
            live,
            evidence,
            profile,
            policy["execution_preferences"],
        )
        result.update(
            health="UNAVAILABLE",
            prepared_next=None,
            reasons=[
                getattr(exc, "code", "GITHUB_AUTH_OR_EVIDENCE_SOURCE_UNAVAILABLE")
                if isinstance(exc, t.Denied)
                else "GITHUB_AUTH_OR_EVIDENCE_SOURCE_UNAVAILABLE"
            ],
            candidates=[],
            first_blocker=None,
        )
        return result
    result = resolver.preflight_health(
        policy["execution_project"],
        live,
        evidence,
        profile,
        policy["execution_preferences"],
    )
    for candidate in result["candidates"]:
        candidate["deficits"] = (
            evidence.get("candidates", {})
            .get(candidate["wp_id"], {})
            .get("deficits", [])
        )
        for blocker in candidate["hard_start_blockers"]:
            producer = policy.get("node_owners", {}).get(blocker["readiness_node"])
            if producer:
                blocker["producer_owner"] = producer
    if policy.get("preparation_schema"):
        spec = importlib.util.spec_from_file_location(
            "cap_preparation_health", "/usr/local/libexec/cap-preparation.py"
        )
        assert spec is not None and spec.loader is not None
        prep = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prep)
        prs = gh._get(f"{t.REPO}/pulls?state=open&per_page=100")
        t.need(
            isinstance(prs, list) and len(prs) < 100,
            "PREPARATION_PR_DISCOVERY_INCOMPLETE",
        )
        for candidate in result["candidates"]:
            plan = prep.derive(
                policy["contexts"][candidate["wp_id"]], policy, gh.main_sha()
            )
            candidate["preparation"] = prep.classify(candidate, plan)
            if candidate["preparation"] == "AUTO_PREPARABLE" and any(
                pr["head"]["ref"].startswith(
                    "wp/" + candidate["wp_id"] + "-auto-prepare-"
                )
                for pr in prs
            ):
                candidate["preparation"] = "IN_PROGRESS"
            candidate["unknown_criteria"] = [
                k for k, v in plan["checks"].items() if v["result"] == "UNKNOWN"
            ]
        result["preparation"] = (
            "VERIFIED_PREPARED"
            if result.get("prepared_next")
            else (
                result["candidates"][0]["preparation"]
                if result["candidates"]
                else "NO_BACKLOG"
            )
        )
    return result


def after_transition(t, wp, policy, plane_factory, gh_factory):
    global resolver
    if resolver is None:
        resolver = load_resolver()
    results = {}
    plane = plane_factory()
    for owner in resolver.affected_owners(policy["execution_project"], wp):
        profile = next(p for p, data in t.q.PEOPLE.items() if data[0] == owner)
        try:
            results[profile] = owner_health(t, profile, policy, plane, gh_factory)
        except Exception:
            results[profile] = {
                "health": "UNAVAILABLE",
                "reasons": ["PREFLIGHT_SOURCE_UNAVAILABLE"],
            }
    return results


def advance_owner(
    t, profile, policy, plane_factory, gh_factory, audit, key, preview=False
):
    """Caller holds the shared pacing lock for the entire resolve/recheck/apply."""
    global resolver
    if resolver is None:
        resolver = load_resolver()
    plane = plane_factory()
    live = live_view(
        t,
        plane,
        policy,
        profile,
        gh_factory(profile) if policy.get("deferred_acceptance_schema") else None,
    )
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
    gh.cache.clear()
    fresh_live = live_view(t, fresh, policy, profile, gh)
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
        gh.cache.clear()
        t.need(
            live_view(t, plane_factory(), policy, profile, gh) == fresh_live,
            "CONCURRENT_CHANGE_RECOMPUTE_REQUIRED",
        )
        gh.cache.clear()
        t.need(gh.main_sha() == observed_sha, "CONCURRENT_CHANGE_RECOMPUTE_REQUIRED")

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
