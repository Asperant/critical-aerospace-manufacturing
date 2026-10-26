"""CTRL-HOST-004: root-owned AUTO_NEXT orchestration; existing transition guards."""

import base64
import datetime as dt
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
from typing import Any, cast

resolver: Any = None
reconcile: Any = None


def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "execution_queue", "/usr/local/libexec/execution_queue.py"
    )
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconcile():
    spec = importlib.util.spec_from_file_location(
        "cap_reconcile", "/usr/local/libexec/cap-plane-reconcile.py"
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
MERGED_BINDINGS_PATH = "project_control/merged_external_bindings.yaml"
MERGED_BINDINGS_SCHEMA = "cap-merged-external-bindings-v1"
MERGED_WAIT_SCHEMA = "cap-merged-external-wait-v1"


def validate_merged_bindings(config, policy):
    """Validate reviewed provenance mappings; never infer producer readiness."""

    def require(value):
        if not value:
            raise ValueError("MERGED_BINDING_PROVENANCE_INVALID")

    require(isinstance(config, dict) and set(config) == {"schema", "bindings"})
    require(config["schema"] == MERGED_BINDINGS_SCHEMA)
    require(isinstance(config["bindings"], list))
    seen = set()
    for row in config["bindings"]:
        require(
            isinstance(row, dict)
            and set(row)
            == {
                "id",
                "producer_wp",
                "producer_owner",
                "producer_scope",
                "consumer_wp",
                "consumer_owner",
                "consumer_scope",
                "requirement",
                "provenance",
                "binding_paths",
            }
        )
        identity = row["id"]
        require(
            isinstance(identity, str)
            and re.fullmatch(r"BIND-[A-Z0-9-]{1,80}", identity)
        )
        require(identity not in seen)
        seen.add(identity)
        require(row["producer_wp"] != row["consumer_wp"])
        sources = set()
        for role in ("producer", "consumer"):
            wp, owner = row[role + "_wp"], row[role + "_owner"]
            require(isinstance(wp, str) and isinstance(owner, str))
            context = policy.get("contexts", {}).get(wp)
            require(isinstance(context, dict) and owner in resolver.OWNERS)
            require(
                context["work_package"]["primary_owner"]["canonical_name"]
                == resolver.OWNERS[owner]
            )
            scope = row[role + "_scope"]
            require(isinstance(scope, str) and re.fullmatch(r"[a-f0-9]{64}", scope))
            require(policy.get("scope_projections", {}).get(wp) == scope)
            sources.update(context["source_manifest"])
        requirement = row["requirement"]
        require(isinstance(requirement, str) and 20 <= len(requirement) <= 1000)
        require(not re.search(r"\b(?:UNKNOWN|TBD|TODO|PENDING)\b", requirement, re.I))
        paths = row["binding_paths"]
        require(isinstance(paths, list) and bool(paths))
        require(
            all(
                isinstance(path, str)
                and re.fullmatch(
                    r"(?:services|packages|infra|workflows)/[A-Za-z0-9_./-]+", path
                )
                and all(part not in {"", ".", ".."} for part in path.split("/"))
                for path in paths
            )
        )
        require(len(paths) == len(set(paths)))
        provenance = row["provenance"]
        require(isinstance(provenance, dict) and bool(provenance))
        for path, digest in provenance.items():
            require(
                isinstance(path, str) and path.startswith("docs/") and path in sources
            )
            require(isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest))
            require(policy.get("source_manifest", {}).get(path) == digest)


def merged_external_wait_proof(t, wp, profile, policy, gh):
    """CHG-034: external-only waiting after merge, with separately reviewed bindings."""
    global resolver
    if resolver is None:
        resolver = load_resolver()
    try:
        config = policy.get("merged_external_bindings")
        validate_merged_bindings(config, policy)
        verified = t.last_blocker(wp)
        t.need(
            isinstance(verified, dict)
            and verified.get("result") == "VERIFIED"
            and verified.get("operation") == "BLOCKED"
            and verified.get("wp_id") == wp
            and verified.get("profile") == profile
            and verified.get("from_state") == "VALIDATING"
            and verified.get("to_state") == "VALIDATING"
            and t.audit_identity(verified) == verified.get("audit_id"),
            "MERGED_WAIT_AUDIT_INVALID",
        )
        classification = "WAITING_EXTERNAL_INTEGRATION_BINDINGS"
        t.need(
            re.match(classification + r"(?::|\s|$)", verified.get("reason", "")),
            "MERGED_WAIT_CLASS_INVALID",
        )
        # CHG-036: the active blocker audit remains the semantic anchor. A
        # A reviewed binding-provenance reassertion may replace its explanatory
        # text: the active blocker audit anchor is the semantic identity. The
        # current assessment below still enforces the exact wait class,
        # blocker, owner-work fields, binding IDs and registry provenance.
        again = reassertion(
            t,
            wp,
            profile,
            verified,
            state="VALIDATING",
            reason_prefix=classification,
        )
        t.need(again is not AMBIGUOUS, "MERGED_WAIT_REASSERTION_INVALID")
        source: Any = again or verified
        ids = [
            r[8:]
            for r in source.get("evidence_refs", [])
            if re.fullmatch(r"comment:[1-9][0-9]{0,15}", r)
        ]
        t.need(len(ids) == 1, "MERGED_WAIT_ASSESSMENT_REQUIRED")
        comment = gh.comment(int(ids[0]))
        text = comment.get("body")
        t.need(
            isinstance(text, str)
            and len(text) <= 65536
            and (comment.get("user") or {}).get("login", "").casefold()
            == t.GITHUB[profile].casefold()
            and comment.get("created_at")
            and comment["created_at"] == comment.get("updated_at"),
            "MERGED_WAIT_ASSESSMENT_NOT_OWNER_UNEDITED",
        )
        sha = exact_field(text, "Canonical main revision")
        pr_id = exact_field(text, "Implementation PR")
        binding_ids = exact_field(text, "External bindings")
        t.need(
            exact_field(text, "External integration wait class") == classification
            and exact_field(text, "Owner-executable implementation work") == "NONE"
            and exact_field(text, "Local actionable work") == "NONE"
            and isinstance(sha, str)
            and t.SHA.fullmatch(sha)
            and isinstance(pr_id, str)
            and re.fullmatch(r"[1-9][0-9]{0,9}", pr_id)
            and isinstance(binding_ids, str),
            "MERGED_WAIT_ASSESSMENT_INCOMPLETE",
        )
        sha, pr_id, binding_ids = (
            cast(str, sha),
            cast(str, pr_id),
            cast(str, binding_ids),
        )
        selected = binding_ids.split(", ")
        bindings = [r for r in config["bindings"] if r["consumer_wp"] == wp]
        t.need(
            bindings
            and len(selected) == len(set(selected))
            and set(selected) == {r["id"] for r in bindings}
            and all(r["consumer_owner"] == profile for r in bindings),
            "MERGED_WAIT_BINDINGS_UNPROVEN",
        )
        record = t.native_record(text, wp, sha)
        t.need(
            record.get("blocker") == verified.get("blocker")
            and not record.get("resolves_audit_id"),
            "MERGED_WAIT_BLOCKER_CHANGED",
        )
        pr = t.pr_fact(gh, ["pr:" + pr_id], wp, profile)
        t.need(
            pr.get("merged") is True
            and comment.get("issue_url", "").endswith("/issues/" + pr_id),
            "MERGED_WAIT_PR_NOT_MERGED",
        )
        merge = pr.get("merge_commit_sha")
        t.need(
            isinstance(merge, str) and t.SHA.fullmatch(merge),
            "MERGED_WAIT_INVALID_MERGE",
        )
        merge = cast(str, merge)
        gh.merged_shape(pr)
        main = gh.main_sha()
        t.need(sha == main, "MERGED_WAIT_ASSESSMENT_STALE")
        gh.ancestor(merge, sha)
        gh.ancestor(sha, main)
        for revision in sorted({merge, sha, main}):
            check_canonical_scope(t, gh, wp, revision, policy)
        for binding in bindings:
            for revision in sorted({sha, main}):
                check_canonical_scope(t, gh, binding["producer_wp"], revision, policy)
        tree = gh._get(f"{t.REPO}/git/trees/{main}?recursive=1")
        t.need(
            tree.get("truncated") is False and isinstance(tree.get("tree"), list),
            "MERGED_WAIT_PRODUCER_INVENTORY_UNKNOWN",
        )
        paths = [row["path"] for row in tree["tree"]]
        t.need(
            all(
                not any(
                    path == expected or path.startswith(expected + "/")
                    for path in paths
                )
                for binding in bindings
                for expected in binding["binding_paths"]
            ),
            "MERGED_WAIT_PRODUCER_DELIVERED",
        )
        for revision in sorted({sha, main}):
            raw, _ = gh.repository_file(MERGED_BINDINGS_PATH, revision)
            t.need(
                hashlib.sha256(raw).hexdigest()
                == policy["source_manifest"].get(MERGED_BINDINGS_PATH),
                "MERGED_WAIT_PROVENANCE_CHANGED",
            )
        t.blocker_evidence(gh, record, "BLOCKER-OBSERVED", main)
        runs = [
            gh.run(int(r[4:]))
            for r in source.get("evidence_refs", [])
            if re.fullmatch(r"run:[1-9][0-9]*", r)
        ]
        t.need(
            any(
                r.get("head_sha") == merge
                and r.get("head_branch") == "main"
                and r.get("event") != "pull_request"
                and r.get("status") == "completed"
                and r.get("conclusion") == "success"
                for r in runs
            ),
            "MERGED_WAIT_MAIN_CI_NOT_GREEN",
        )
        t.ci(gh, merge, policy)
        return {
            "schema": MERGED_WAIT_SCHEMA,
            "wp_id": wp,
            "owner": t.q.PEOPLE[profile][0],
            "classification": classification,
            "owner_work_remaining": False,
            "local_actionable_work": False,
            "merge_sha": merge,
            "audit_id": verified["audit_id"],
            "assessment_digest": hashlib.sha256(text.encode()).hexdigest(),
            "provenance_digest": hashlib.sha256(
                json.dumps(bindings, sort_keys=True).encode()
            ).hexdigest(),
            "binding_ids": sorted(selected),
        }
    except (t.Denied, ValueError, TypeError, KeyError):
        return None  # Missing/UNKNOWN proof never frees a slot.


def semantic_slot_release_proof(t, wp, profile, policy, gh, source=None):
    """CHG-037: semantic scheduler accounting; legacy proofs remain auditable.

    A v2 assessment is the current semantic authority.  The historical VERIFIED
    audit remains the blocker anchor, but an owner-authored UNCHANGED reassertion
    may refresh the assessment without making its explanatory prose part of the
    slot identity.  Legacy wait paths retain their stricter chain rules below.
    """
    global resolver
    if resolver is None:
        resolver = load_resolver()
    source = source or semantic_slot_release_source(t, wp, profile, policy, gh)
    if source is None:
        return None
    if source["semantic_blocker_class"] == resolver.DEFERRED_CLASS:
        try:
            pr = (
                t.pr_fact(gh, source["refs"], wp, profile)
                if source["pr_refs"]
                else source["comment"]
            )
            if (
                pr.get("merged") is not True
                or pr.get("merge_commit_sha") != source["canonical_revision"]
            ):
                return None
            try:
                t.ci(gh, source["canonical_revision"], policy)
            except t.Denied:
                if not recorded_historical_technical_acceptance(
                    t, gh, pr, profile, source["canonical_revision"], policy
                ):
                    raise
        except t.Denied:
            return None
    return {
        "schema": resolver.SLOT_RELEASE_SCHEMA,
        "wp_id": wp,
        "owner": t.q.PEOPLE[profile][0],
        "local_actionable_work": "NONE",
        "implementation_persisted": True,
        "semantic_blocker_id": source["semantic_blocker_id"],
        "semantic_blocker_class": source["semantic_blocker_class"],
        "relevant_scope_digest": source["scope"],
        "assessment_digest": source["assessment_digest"],
        "proof_fingerprint": source["proof_fingerprint"],
    }


def recorded_historical_technical_acceptance(t, gh, pr, profile, merge_sha, policy):
    """Accept recorded merge-time CI for PRs predating the CHG-038 cutover.

    Historical runs are evaluated by their immutable run/job result, not by
    today's step names.  Current PRs never enter this path, and missing or
    ambiguous recorded evidence remains fail-closed.
    """
    try:
        cutoff = policy["historical_technical_acceptance"]["cutoff"]
        merged_at = pr.get("merged_at")
        body = pr.get("body")
        if (
            pr.get("merged") is not True
            or pr.get("merge_commit_sha") != merge_sha
            or not isinstance(merged_at, str)
            or not isinstance(body, str)
            or not merged_at < cutoff
        ):
            return False
        texts = [body]
        comments = gh._get(
            f"{t.REPO}/issues/{pr['number']}/comments?per_page=100&page=1"
        )
        if isinstance(comments, list):
            for comment in comments:
                comment_body = comment.get("body")
                user = comment.get("user") or {}
                if (
                    isinstance(comment_body, str)
                    and user.get("login", "").casefold() == t.GITHUB[profile].casefold()
                    and comment.get("created_at") == comment.get("updated_at")
                    and merge_sha in comment_body
                ):
                    texts.append(comment_body)
        run_ids = set()
        for text in texts:
            run_ids.update(
                int(value)
                for value in re.findall(
                    r"(?:actions/runs/|(?:CI|Main CI|projectctl run|run)\D{0,80})"
                    r"([1-9][0-9]{8,})",
                    text,
                    re.IGNORECASE,
                )
            )
        for run_id in sorted(run_ids):
            run = gh.run(run_id)
            if not (
                run.get("head_sha") == merge_sha
                and run.get("status") == "completed"
                and run.get("conclusion") == "success"
            ):
                continue
            jobs = gh._get(
                f"{t.REPO}/actions/runs/{run_id}/jobs?filter=latest&per_page=100"
            )
            rows = jobs.get("jobs", []) if isinstance(jobs, dict) else []
            if jobs.get("total_count") != len(rows) or not rows:
                continue
            successful = [
                job
                for job in rows
                if job.get("head_sha") == merge_sha
                and job.get("status") == "completed"
                and job.get("conclusion") == "success"
            ]
            names = {job.get("name") for job in successful}
            if len(successful) == len(rows) and "ci-gate" in names and len(names) > 1:
                return True
        return False
    except (AttributeError, KeyError, TypeError, ValueError, t.Denied):
        return False


def semantic_slot_release_source(t, wp, profile, policy, gh):
    """Read the current assessment inputs without merge/CI verification."""
    global resolver
    if resolver is None:
        resolver = load_resolver()
    try:
        verified = t.last_blocker(wp)
    except (OSError, PermissionError):
        return None
    if not (
        isinstance(verified, dict)
        and verified.get("result") == "VERIFIED"
        and verified.get("operation") == "BLOCKED"
        and verified.get("profile") == profile
    ):
        return None
    source = verified
    try:
        rows = t.blocker_rows(wp)
    except Exception:
        return None
    for row in rows:
        if (
            row.get("result") == "UNCHANGED"
            and row.get("operation") == "BLOCKED"
            and row.get("wp_id") == wp
            and row.get("profile") == profile
            and (
                (
                    row.get("from_state") == verified.get("from_state")
                    and row.get("to_state") == verified.get("to_state")
                )
                # A lifecycle reconciliation may move the item to VALIDATING
                # before the owner can reassert the unchanged external wait.
                # Preserve the original VERIFIED blocker as the authority and
                # accept only that exact IN_PROGRESS -> VALIDATING shape.
                or (
                    verified.get("from_state") == "IN_PROGRESS"
                    and verified.get("to_state") == "IN_PROGRESS"
                    and row.get("from_state") == "VALIDATING"
                    and row.get("to_state") == "VALIDATING"
                )
            )
            and row.get("active_blocker_audit_id") == verified.get("audit_id")
            and t.audit_identity(row) == row.get("audit_id")
        ):
            source = row
    refs = source.get("evidence_refs", [])
    comment_ids = [
        ref[8:]
        for ref in refs
        if isinstance(ref, str) and re.fullmatch(r"comment:[1-9][0-9]{0,15}", ref)
    ]
    pr_refs = [ref for ref in refs if isinstance(ref, str) and ref.startswith("pr:")]
    if len(comment_ids) != 1 and len(pr_refs) != 1:
        return None
    comment = (
        gh._get(f"{t.REPO}/issues/comments/{comment_ids[0]}")
        if comment_ids
        else t.pr_fact(gh, refs, wp, profile)
    )
    text = comment.get("body") if isinstance(comment, dict) else None
    if not (
        isinstance(text, str)
        and (comment.get("user") or {}).get("login", "").casefold()
        == t.GITHUB[profile].casefold()
        and (pr_refs or comment.get("created_at") == comment.get("updated_at"))
        and exact_field(text, "Local actionable work") == "NONE"
        and exact_field(text, "Implementation persisted") == "YES"
    ):
        return None
    blocker = verified.get("blocker")
    if not isinstance(blocker, dict):
        blocker = {}
    classification = (
        blocker.get("semantic_class")
        or blocker.get("class")
        or exact_field(text, "Semantic blocker class")
        or exact_field(text, "External integration wait class")
        or exact_field(text, "Deferred acceptance class")
    )
    semantic_id = (
        blocker.get("semantic_id")
        or blocker.get("id")
        or exact_field(text, "Semantic blocker ID")
    )
    if (
        not isinstance(semantic_id, str)
        or not semantic_id
        or classification not in resolver.SLOT_RELEASE_CLASSES
    ):
        return None
    scope = exact_field(text, "Relevant scope digest")
    current_scope = policy.get("scope_projections", {}).get(wp)
    scope = current_scope if scope is None else scope
    if not isinstance(scope, str) or not re.fullmatch(r"[a-f0-9]{64}", scope):
        return None
    sha = exact_field(text, "Canonical main revision")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        return None
    assessment_digest = hashlib.sha256(text.encode()).hexdigest()
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "wp_id": wp,
                "owner": t.q.PEOPLE[profile][0],
                "audit_id": source.get("audit_id"),
                "assessment_digest": assessment_digest,
                "semantic_blocker_id": semantic_id,
                "semantic_blocker_class": classification,
                "relevant_scope_digest": scope,
                "canonical_revision": sha,
                "policy_digest": policy.get("policy_digest"),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {
        "wp_id": wp,
        "refs": refs,
        "comment": comment,
        "pr_refs": pr_refs,
        "semantic_blocker_id": semantic_id,
        "semantic_blocker_class": classification,
        "scope": scope,
        "canonical_revision": sha,
        "assessment_digest": assessment_digest,
        "policy_digest": policy.get("policy_digest"),
        "proof_fingerprint": fingerprint,
    }


def semantic_slot_release_diagnose(t, wp, profile, policy, gh):
    """Read-only, redacted Slot Release v2 diagnosis.

    This deliberately calls the same source and proof functions used by AUTO_NEXT;
    it only exposes bounded predicate names and fingerprints for operator diagnosis.
    It never writes the cache, audit, Plane, GitHub, or policy.
    """
    global resolver
    if resolver is None:
        resolver = load_resolver()
    result = {
        "schema": "cap-slot-release-diagnostic-v1",
        "profile": profile,
        "wp_id": wp,
        "slot_release": "FAIL",
        "sources": {
            "installed_policy": "/etc/cap-plane-queue/transition-policy.json",
            "installed_source": "/usr/local/libexec/cap-auto-next.py",
            "cache": "/run/cap-plane-slot-release-v2.json",
            "audit": "/var/log/cap-plane-transition/audit.jsonl",
        },
    }

    def fail(predicate, details=None):
        if "first_failed_predicate" not in result:
            result["first_failed_predicate"] = predicate
            if details:
                result["details"] = details

    try:
        verified = t.last_blocker(wp)
    except Exception:
        verified = None
    result["audit"] = {
        "latest_blocker_audit_id": verified.get("audit_id")
        if isinstance(verified, dict)
        else None,
        "latest_result": verified.get("result") if isinstance(verified, dict) else None,
        "latest_operation": verified.get("operation")
        if isinstance(verified, dict)
        else None,
        "audit_identity_valid": bool(
            isinstance(verified, dict)
            and t.audit_identity(verified) == verified.get("audit_id")
        ),
    }
    if not isinstance(verified, dict):
        fail("AUDIT_LATEST_BLOCKER_MISSING")
    elif verified.get("result") != "VERIFIED" or verified.get("operation") != "BLOCKED":
        fail("AUDIT_LATEST_BLOCKER_NOT_VERIFIED")
    elif verified.get("profile") != profile or verified.get("wp_id") != wp:
        fail("AUDIT_PROFILE_WP_BINDING")
    elif not result["audit"]["audit_identity_valid"]:
        fail("AUDIT_IDENTITY_INVALID")

    try:
        rows = t.blocker_rows(wp)
    except Exception:
        rows = []
    continuity = []
    if isinstance(verified, dict):
        for row in rows:
            if (
                row.get("result") == "UNCHANGED"
                and row.get("operation") == "BLOCKED"
                and row.get("profile") == profile
                and row.get("wp_id") == wp
                and row.get("active_blocker_audit_id") == verified.get("audit_id")
            ):
                continuity.append(row)
    result["audit"]["continuity_rows"] = len(continuity)
    if not continuity:
        fail("AUDIT_CONTINUITY_REASSERTION_MISSING")

    source = semantic_slot_release_source(t, wp, profile, policy, gh)
    if source is None:
        fail("ACCOUNTABLE_ASSESSMENT_OR_BINDING_INVALID")
    else:
        result["assessment"] = {
            "assessment_digest": source["assessment_digest"],
            "semantic_blocker_id": source["semantic_blocker_id"],
            "semantic_blocker_class": source["semantic_blocker_class"],
            "canonical_revision": source["canonical_revision"],
            "relevant_scope_digest": source["scope"],
            "proof_fingerprint": source["proof_fingerprint"],
            "policy_digest": source["policy_digest"],
        }
        if source["semantic_blocker_class"] not in resolver.SLOT_RELEASE_CLASSES:
            fail("BLOCKER_SEMANTIC_CLASS_UNSUPPORTED")
        elif not source["semantic_blocker_id"]:
            fail("BLOCKER_SEMANTIC_ID_MISSING")
        elif source["semantic_blocker_class"] == resolver.DEFERRED_CLASS:
            try:
                pr = (
                    t.pr_fact(gh, source["refs"], wp, profile)
                    if source["pr_refs"]
                    else source["comment"]
                )
                if pr.get("merged") is not True:
                    fail("MERGE_NOT_VERIFIED")
                elif pr.get("merge_commit_sha") != source["canonical_revision"]:
                    fail("MERGE_REVISION_MISMATCH")
                else:
                    try:
                        t.ci(gh, source["canonical_revision"], policy)
                    except t.Denied as exc:
                        if not recorded_historical_technical_acceptance(
                            t, gh, pr, profile, source["canonical_revision"], policy
                        ):
                            fail("CI_NOT_VERIFIED", {"reason": exc.code})
            except t.Denied as exc:
                fail("MERGE_EVIDENCE_UNAVAILABLE", {"reason": exc.code})
        if "first_failed_predicate" not in result:
            proof = semantic_slot_release_proof(
                t, wp, profile, policy, gh, source=source
            )
            if proof is None:
                fail("SLOT_RELEASE_PROOF_DENIED")
            else:
                result["slot_release"] = "PASS"
                result["proof"] = {
                    "schema": proof["schema"],
                    "semantic_blocker_id": proof["semantic_blocker_id"],
                    "semantic_blocker_class": proof["semantic_blocker_class"],
                    "proof_fingerprint": proof["proof_fingerprint"],
                }
    return result


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
            gh = gh or t.GitHub(profile)
            proof = semantic_slot_release_proof(t, wp, profile, policy, gh)
            if proof:
                items[wp]["slot_release_v2"] = proof
            else:
                proof = deferred_proof(t, wp, profile, policy, gh)
                if proof:
                    items[wp]["deferred_acceptance"] = proof
            if (
                not proof
                and policy.get("deferred_recovery_schema") == "cap-deferred-recovery-v1"
            ):
                try:
                    proof = recovery_proof(t, wp, profile, policy, gh)
                except t.Denied as exc:
                    items[wp]["deferred_recovery_denial"] = exc.code  # code only
                else:
                    if proof:
                        items[wp]["deferred_acceptance"] = proof
        if (
            requested_profile == profile
            and policy.get("external_wait_schema") == "cap-external-integration-wait-v1"
            and items[wp]["state"] == "IN_PROGRESS"
            and items[wp]["blocked"]
        ):
            proof = semantic_slot_release_proof(
                t, wp, profile, policy, gh or t.GitHub(profile)
            )
            if proof:
                items[wp]["slot_release_v2"] = proof
            else:
                proof = external_wait_proof(
                    t, wp, profile, policy, gh or t.GitHub(profile)
                )
                if proof:
                    items[wp]["external_integration_wait"] = proof
        if (
            requested_profile == profile
            and items[wp]["state"] == "VALIDATING"
            and items[wp]["blocked"]
            and policy.get("merged_external_wait_schema") == MERGED_WAIT_SCHEMA
        ):
            proof = merged_external_wait_proof(
                t, wp, profile, policy, gh or t.GitHub(profile)
            )
            if proof:
                items[wp]["merged_external_integration_wait"] = proof
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


def reassertion(t, wp, profile, verified, state="IN_PROGRESS", reason_prefix=None):
    """Latest UNCHANGED BLOCKED re-assertion of the same verified active blocker.

    The VERIFIED record stays the only authority that the blocker is active; a
    re-assertion may merely carry fresh assessment evidence for that same blocker.
    ``reason_prefix`` is reserved for reviewed semantic wait classes whose
    explanation is non-semantic; the default remains byte-identical.
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
            and (
                (row.get("from_state") == state and row.get("to_state") == state)
                or (
                    verified.get("from_state") == "IN_PROGRESS"
                    and verified.get("to_state") == "IN_PROGRESS"
                    and state == "IN_PROGRESS"
                    and row.get("from_state") == "VALIDATING"
                    and row.get("to_state") == "VALIDATING"
                )
            )
            and row.get("active_blocker_audit_id") == verified["audit_id"]
            and (
                row.get("reason") == verified.get("reason")
                if reason_prefix is None
                else isinstance(row.get("reason"), str) and bool(row["reason"].strip())
            )
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


def deferred_reassertion(
    t, gh, wp, profile, policy, verified, merge_sha, classification
):
    """CHG-030: continuity of an unchanged VERIFIED deferred wait at current state.

    The latest VERIFIED BLOCKED audit stays the sole authority that the blocker is
    active; a later UNCHANGED BLOCKED row (same reason, no blocker of its own, linked
    through active_blocker_audit_id) only supplies a fresh owner assessment. That
    assessment must restate the identical blocker and `Owner-executable
    implementation work: NONE`, claim no resolution, satisfy the canonical sources at
    its own revision, and the WP's merge-time scope projection must be unchanged.
    Anything missing, ambiguous or UNKNOWN raises: the original proof then fails.
    """
    again = reassertion(t, wp, profile, verified, "VALIDATING")
    if not isinstance(again, dict):  # None (no re-assertion) or AMBIGUOUS chain
        raise t.Denied("DEFERRED_REASSERTION_UNAVAILABLE")
    ids = [
        r[8:]
        for r in again.get("evidence_refs", [])
        if re.fullmatch(r"comment:[1-9][0-9]{0,15}", r)
    ]
    t.need(len(ids) == 1, "DEFERRED_REASSERTION_ASSESSMENT_REQUIRED")
    comment = gh._get(f"{t.REPO}/issues/comments/{ids[0]}")
    text = comment.get("body")
    t.need(
        isinstance(text, str)
        and str((comment.get("user") or {}).get("login", "")).casefold()
        == t.GITHUB[profile].casefold()
        and comment.get("created_at")
        and comment.get("created_at") == comment.get("updated_at"),
        "DEFERRED_REASSERTION_NOT_OWNER_UNEDITED",
    )
    sha = exact_field(text, "Canonical main revision")
    t.need(
        sha is not None
        and re.fullmatch(r"[0-9a-f]{40}", sha)
        and exact_field(text, "Deferred acceptance class") == classification
        and exact_field(text, "Owner-executable implementation work") == "NONE"
        and exact_field(text, "Resolves blocker") is None,
        "DEFERRED_REASSERTION_INCOMPLETE",
    )
    record = t.native_record(text, wp, sha)
    t.need(
        record.get("blocker") == verified.get("blocker")
        and not record.get("resolves_audit_id"),
        "DEFERRED_REASSERTION_BLOCKER_CHANGED",
    )
    t.need(record["_artifact_refs"], "DEFERRED_REASSERTION_EVIDENCE_MISSING")
    for ref in record["_artifact_refs"]:
        gh.artifact(ref, sha)
    # Current canonical sources and this WP's scope at the assessed revision...
    check_canonical_scope(t, gh, wp, sha, policy)
    # ...and the scope projection at the original merge must be semantically unchanged.
    tree = gh._get(f"{t.REPO}/git/trees/{merge_sha}?recursive=1")
    t.need(tree.get("truncated") is False, "DEFERRED_SOURCE_TREE_INCOMPLETE")
    check_scope_projection(
        t, gh, wp, {r["path"]: r.get("sha") for r in tree["tree"]}, policy
    )
    return {
        "audit_id": again["audit_id"],
        "comment_id": ids[0],
        "digest": hashlib.sha256(text.encode()).hexdigest(),
    }


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
        # A changed whole-blob pinned source (never the WP's own scope projection)
        # may be bridged only by a CHG-030 UNCHANGED re-assertion of this blocker.
        again = None
        try:
            check_canonical_scope(t, gh, wp, sha, policy)
        except t.Denied as exc:
            if exc.code != "DEFERRED_CANONICAL_SCOPE_CHANGED":
                raise
            again = deferred_reassertion(
                t, gh, wp, profile, policy, previous, sha, classification
            )
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
        proof = {
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
        if again:
            proof.update(
                reassertion_audit_id=again["audit_id"],
                reassertion_comment_id=again["comment_id"],
                reassertion_digest=again["digest"],
            )
        return proof
    except t.Denied:
        return None  # UNKNOWN never frees the slot.


def registry_entry(t, gh, disposition, revision):
    """The one registry entry for the deployable at `revision`; absent or ambiguous denies."""
    raw, _ = gh.repository_file(disposition["path"], revision)
    try:
        rows = json.loads(raw)["deployables"]
        found = [
            d
            for d in rows
            if isinstance(d, dict) and d.get("name") == disposition["deployable"]
        ]
    except (ValueError, KeyError, TypeError):
        raise t.Denied("RECOVERY_DISPOSITION_UNVERIFIED") from None
    t.need(len(found) == 1, "RECOVERY_DISPOSITION_UNVERIFIED")
    return found[0]


def recovery_proof(t, wp, profile, policy, gh, today=None):
    """CHG-033: deferred-acceptance proof for an allow-listed two-parent merge.

    The legacy proof stays untouched and still decides every other case. This one binds
    the ORIGINAL VERIFIED blocker audit, the exact PR/head/merge/parents/inventory/runs of
    the allow-listed reconciliation case, a later UNCHANGED re-assertion that carries a
    current unedited owner assessment, the pinned canonical scope at the assessed
    revision, the platform disposition and its expiry, and the still-pending producers.
    It yields the implementation-slot exemption only. Returns None when the WP has no
    case; any failed predicate raises a Denied whose code is the redacted diagnosis.
    """
    global resolver, reconcile
    if resolver is None:
        resolver = load_resolver()
    if reconcile is None:
        reconcile = load_reconcile()
    reconcile.t = t
    case = reconcile.find_recovery_case(policy["deferred_recovery"], profile, wp)
    if case is None:
        return None
    previous = t.last_blocker(wp)
    t.need(
        previous
        and previous.get("result") == "VERIFIED"
        and previous.get("operation") == "BLOCKED"
        and previous.get("from_state") == "VALIDATING"
        and previous.get("to_state") == "VALIDATING"
        and previous.get("profile") == profile,
        "RECOVERY_BLOCKER_AUDIT_MISSING",
    )
    t.need(
        previous.get("audit_id") == case["blocker_audit_id"],
        "RECOVERY_BLOCKER_AUDIT_MISMATCH",
    )
    legacy_cases = policy["lifecycle_reconciliation"].get(
        "legacy_recovery_cases",
        policy["lifecycle_reconciliation"].get("cases", []),
    )
    base = next(c for c in legacy_cases if c["case_id"] == case["reconciliation_case"])
    reconcile.gather(gh, base, profile, wp, "VALIDATING")  # PR, merge, scope, runs
    again = reassertion(t, wp, profile, previous, "VALIDATING")
    if not isinstance(again, dict):  # None (no re-assertion) or AMBIGUOUS chain
        raise t.Denied("RECOVERY_ASSESSMENT_REQUIRED")
    ids = [
        r[8:]
        for r in again.get("evidence_refs", [])
        if re.fullmatch(r"comment:[1-9][0-9]{0,15}", r)
    ]
    t.need(len(ids) == 1, "RECOVERY_ASSESSMENT_REQUIRED")
    comment = gh._get(f"{t.REPO}/issues/comments/{ids[0]}")
    text = comment.get("body")
    t.need(
        isinstance(text, str)
        and str((comment.get("user") or {}).get("login", "")).casefold()
        == t.GITHUB[profile].casefold()
        and comment.get("created_at")
        and comment.get("created_at") == comment.get("updated_at"),
        "RECOVERY_ASSESSMENT_NOT_OWNER_UNEDITED",
    )
    sha = exact_field(text, "Canonical main revision")
    pending = exact_field(text, "Pending producers")
    disposition = case["platform_disposition"]
    t.need(
        sha is not None
        and re.fullmatch(r"[0-9a-f]{40}", sha)
        and exact_field(text, "Platform disposition")
        == f"PR {disposition['pr']} {disposition['merge_sha']}"
        and exact_field(text, "Recovery case") == case["case_id"]
        and exact_field(text, "Original blocker audit") == case["blocker_audit_id"]
        and exact_field(text, "Deferred acceptance class") == case["classification"]
        and exact_field(text, "Owner-executable implementation work") == "NONE"
        and exact_field(text, "Resolves blocker") is None
        and pending is not None
        and sorted(p.strip() for p in pending.split(","))
        == sorted(case["pending_producers"]),
        "RECOVERY_ASSESSMENT_INCOMPLETE",
    )
    record = t.native_record(text, wp, sha)
    t.need(
        record.get("blocker") == previous.get("blocker")
        and not record.get("resolves_audit_id"),
        "RECOVERY_BLOCKER_CHANGED",
    )
    t.need(record["_artifact_refs"], "RECOVERY_EVIDENCE_MISSING")
    for ref in record["_artifact_refs"]:
        gh.artifact(ref, sha)
    main = gh.main_sha()
    gh.ancestor(sha, main)  # the assessed revision is on main
    # The scope held when the owner assessed AND holds on the current main; producer
    # deliveries and the registry entry are read at the current main, never the older sha.
    check_canonical_scope(t, gh, wp, sha, policy)
    check_canonical_scope(t, gh, wp, main, policy)
    tree = gh._get(f"{t.REPO}/git/trees/{main}?recursive=1")  # complete: checked above
    t.need(
        not any(
            row["path"].startswith(f"evidence/{producer}/")
            for row in tree["tree"]
            for producer in case["pending_producers"]
        ),
        "RECOVERY_PRODUCER_ALREADY_DELIVERED",
    )
    pr = gh.fresh_pr(disposition["pr"])
    t.need(
        pr.get("merged") is True
        and pr.get("merge_commit_sha") == disposition["merge_sha"]
        and (pr.get("base") or {}).get("ref") == "main"
        and str((pr.get("user") or {}).get("login", "")).casefold()
        == t.GITHUB[disposition["owner"]].casefold(),
        "RECOVERY_DISPOSITION_UNVERIFIED",
    )
    gh.ancestor(disposition["merge_sha"], main)
    # The terms the platform owner confirmed are the registry entry at the pinned PR merge;
    # the current main must carry that exact entry (a changed reason or status is a new decision).
    approved = registry_entry(t, gh, disposition, disposition["merge_sha"])
    exemption = approved.get("exemption")
    t.need(
        isinstance(exemption, dict)
        and exemption.get("owner") == t.q.PEOPLE[disposition["owner"]][0].split()[0]
        and exemption.get("expires_on") == disposition["expires_on"],
        "RECOVERY_DISPOSITION_UNVERIFIED",
    )
    t.need(
        registry_entry(t, gh, disposition, main) == approved,
        "RECOVERY_DISPOSITION_CHANGED",
    )
    today = today or dt.datetime.now(dt.UTC).date()
    t.need(
        today.isoformat() <= disposition["expires_on"], "RECOVERY_DISPOSITION_EXPIRED"
    )
    digest = hashlib.sha256(text.encode()).hexdigest()
    return {
        "schema": "cap-deferred-acceptance-v1",
        "wp_id": wp,
        "owner": t.q.PEOPLE[profile][0],
        "classification": case["classification"],
        "implementation_complete": True,
        "owner_work_remaining": False,
        "merge_sha": base["merge_sha"],
        "audit_id": previous["audit_id"],
        "assessment_digest": digest,
        "reassertion_audit_id": again["audit_id"],
        "reassertion_comment_id": ids[0],
        "reassertion_digest": digest,
        "recovery_case": case["case_id"],
    }


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
    prep = None
    prs: list = []
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

    def actionable(candidate):
        """Same effective selection as the preparation controller (engine.classify)."""
        if prep is None:
            return candidate["status"] == "PREPARED"
        wp = candidate["wp_id"]
        try:
            plan = prep.derive(policy["contexts"][wp], policy, gh.main_sha())
            deficits = evidence.get("candidates", {}).get(wp, {}).get("deficits", [])
            state = prep.classify(dict(candidate, deficits=deficits), plan)
        except Exception:
            return False  # never actionable when it cannot be derived
        return state in {"AUTO_PREPARABLE", "VERIFIED_PREPARED"}

    result = resolver.preflight_health(
        policy["execution_project"],
        live,
        evidence,
        profile,
        policy["execution_preferences"],
        actionable,
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
    if prep is not None:
        for candidate in result["candidates"]:
            try:
                plan = prep.derive(
                    policy["contexts"][candidate["wp_id"]], policy, gh.main_sha()
                )
            except Exception:
                candidate["preparation"] = "UNAVAILABLE"
                candidate["unknown_criteria"] = []
                continue
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
        head = next(
            (
                c
                for c in result["candidates"]
                if c["wp_id"] == result["actionable_next"]
            ),
            result["candidates"][0] if result["candidates"] else None,
        )
        result["preparation"] = (
            "VERIFIED_PREPARED"
            if result.get("prepared_next")
            else (head["preparation"] if head else "NO_BACKLOG")
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
    denials = {
        w: i["deferred_recovery_denial"]
        for w, i in live.get("items", {}).items()
        if "deferred_recovery_denial" in i
    }
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
        return {**first, **({"deferred_recovery_denials": denials} if denials else {})}
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
    if denials:
        result = {**result, "deferred_recovery_denials": denials}
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
            "reconcile": "/usr/local/libexec/cap-plane-reconcile.py",
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
