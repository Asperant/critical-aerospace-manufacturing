"""CHG-033 deferred-acceptance recovery proof; offline fixtures, no Plane/GitHub access."""

import base64
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import test_auto_next as na
import test_reconcile as base
import test_reconcile_adapter as adapter
from test_transition import HEAD, MERGE, FakeGH

HERE = Path(__file__).resolve().parent
t, auto, resolver = na.t, na.auto, na.resolver
rec = na.load("reconcile_recovery", HERE / "reconcile.py")
auto.reconcile = rec  # recovery_proof rebinds rec.t to the transition module it gets
PARENT, REVISION, DISPOSITION_MERGE = "3" * 40, "c" * 40, "d" * 40
CLASS = "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE"
COVERAGE_PATH = "infra/observability/coverage.json"
TODAY = dt.date(2026, 10, 26)
BLOCKER = {"owner": "asrin", "wp_id": None, "external_dependency": "Real acceptance"}


def coverage(**exemption):
    data = {"owner": "Yavuz", "expires_on": "2026-11-20"} | exemption
    entry = {"name": "manufacturing-simulator", "exemption": data}
    return json.dumps({"deployables": [entry]}).encode()


def assessment(audit_id, producers, **overrides):
    fields = {
        "Recovery case": "DEFER-TEST",
        "Original blocker audit": audit_id,
        "Canonical main revision": REVISION,
        "Deferred acceptance class": CLASS,
        "Owner-executable implementation work": "NONE",
        "Pending producers": ", ".join(producers),
        "Platform disposition": f"PR 75 {DISPOSITION_MERGE}",
        "Blocker owner": "asrin",
        "External dependency": "Real acceptance",
        "Reason": "Current owner decision",
        "Evidence": "repo:evidence/test.json",
    }
    fields.update(overrides)
    return "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)


def audit_rows(wp, profile, blocker):
    row: dict[str, Any] = {
        "timestamp": "2026-10-24T16:50:25+00:00",
        "profile": profile,
        "wp_id": wp,
        "from_state": "VALIDATING",
        "to_state": "VALIDATING",
        "operation": "BLOCKED",
        "reason": "Blocked on downstream acceptance",
        "evidence_refs": ["comment:111"],
        "policy_digest": "digest",
    }
    verified = dict(row, result="VERIFIED", blocker=blocker)
    verified["audit_id"] = t.audit_identity(verified)
    again = dict(row, timestamp="2026-10-25T15:01:00+00:00", result="UNCHANGED")
    again["evidence_refs"] = ["comment:222"]
    again["audit_id"] = t.audit_identity(again)
    again["active_blocker_audit_id"] = verified["audit_id"]
    return verified, again


def recovery_block(wp, profile, recon, audit_id, producers):
    disposition = {
        "pr": 75,
        "merge_sha": DISPOSITION_MERGE,
        "owner": "yavuz",
        "path": COVERAGE_PATH,
        "deployable": "manufacturing-simulator",
        "expires_on": "2026-11-20",
    }
    case = {
        "case_id": "DEFER-TEST",
        "profile": profile,
        "wp_id": wp,
        "reconciliation_case": recon,
        "blocker_audit_id": audit_id,
        "classification": CLASS,
        "platform_disposition": disposition,
        "pending_producers": list(producers),
        "change_record": "CHG-033",
    }
    return {"schema_version": rec.RECOVERY_SCHEMA, "cases": [case]}


class GH(FakeGH):
    """The shared fixture fake plus the reads that reconcile primitives use."""

    parents: Any
    runs: Any
    rows: Any
    disposition: Any
    comment_obj: Any
    ancestry_fail: Any
    invalidations: Any
    files_at: Any
    trees: Any
    _get: Any

    def ancestor(self, base, head):
        if (base, head) in getattr(self, "ancestry_fail", set()):
            raise t.Denied("PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY")
        super().ancestor(base, head)

    def invalidate(self):
        self.invalidations = getattr(self, "invalidations", 0) + 1

    def commit(self, sha):
        return {"sha": sha, "parents": [{"sha": p} for p in self.parents]}

    def branch_deleted(self, branch):
        if getattr(self, "undeleted_branch", False):
            raise t.Denied("MERGED_BRANCH_NOT_DELETED")

    def fresh_run(self, number):
        return deepcopy(self.runs[number])

    def files(self, pr):
        return deepcopy(self.rows)

    def repository_file(self, path, sha, limit=65536):
        at = getattr(self, "files_at", {})
        return (
            at[(path, sha)] if (path, sha) in at else super().repository_file(path, sha)
        )

    def fresh_pr(self, number):
        return deepcopy(self.disposition if number == 75 else self.pr_data)


def duplicated():
    one = json.loads(coverage())["deployables"][0]
    return json.dumps({"deployables": [one, dict(one)]}).encode()


def registry(raw=None):
    raw = coverage() if raw is None else raw
    return {
        "type": "file",
        "encoding": "base64",
        "size": len(raw),
        "sha": "a" * 40,
        "content": base64.b64encode(raw).decode(),
    }


def with_rows(gh, extra=None):
    """The shared fixture tree as seen from the current main, plus or changing one row."""
    rows = [dict(r) for r in gh.tree["tree"]]
    if isinstance(extra, str):
        next(r for r in rows if r["path"] == extra)["sha"] = "changed-on-main"
    elif extra:
        rows.append(dict(extra, sha="e"))
    return {"truncated": False, "tree": rows}


class RecoveryBase(unittest.TestCase):
    def fixture(self):
        wp, policy, plane, fake, _ = na.DeferredAcceptanceTests().fixture()
        gh: GH = GH.__new__(GH)
        gh.__dict__.update(fake.__dict__)
        self.producers = sorted(k for k in policy["contexts"] if k != wp)
        self.verified, self.again = audit_rows(wp, "asrin", BLOCKER)
        gh.parents = [PARENT, HEAD]
        gh.pr_data["changed_files"] = 2
        gh.rows = [
            {"filename": "src/project.py", "status": "added"},
            {"filename": "evidence/test.json", "status": "added"},
        ]
        gh.runs = {
            4001: {
                "id": 4001,
                "head_sha": MERGE,
                "head_branch": "main",
                "event": "push",
                "path": ".github/workflows/ci.yml",
                "status": "completed",
                "conclusion": "success",
                "run_started_at": "2026-10-24T10:00:00Z",
                "updated_at": "2026-10-24T10:30:00Z",
                "repository": {"full_name": base.REPOSITORY},
            }
        }
        gh.disposition = {
            "merged": True,
            "merge_commit_sha": DISPOSITION_MERGE,
            "base": {"ref": "main"},
            "user": {"login": t.GITHUB["yavuz"]},
        }
        gh.repo_files = {COVERAGE_PATH: (coverage(), "b")}
        gh.comment_obj = {
            "user": {"login": t.GITHUB["asrin"]},
            "created_at": "2026-10-25T15:00:00Z",
            "updated_at": "2026-10-25T15:00:00Z",
            "body": assessment(self.verified["audit_id"], self.producers),
        }
        gh.trees, gh.files_at = {}, {}
        old = gh._get

        def route(path):
            if "/issues/comments/" in path:
                return gh.comment_obj
            sha = path.split("/git/trees/")[-1].split("?")[0]
            return (
                gh.trees[sha]
                if "/git/trees/" in path and sha in gh.trees
                else old(path)
            )

        gh._get = Mock(side_effect=route)
        recon = {
            "case_id": "RECON-TEST",
            "profile": "asrin",
            "wp_id": wp,
            "pr": 1,
            "pr_head_sha": HEAD,
            "merge_sha": MERGE,
            "parents": [PARENT, HEAD],
            "changed_files": 2,
            "scope_prefixes": ["src/", "evidence/"],
            "targets": ["MERGED", "VALIDATING"],
            "validating_runs": [
                {"run_id": 4001, "workflow_path": ".github/workflows/ci.yml"}
            ],
            "require_successful_runs": True,
        }
        policy["lifecycle_reconciliation"] = {
            "schema_version": rec.POLICY_SCHEMA,
            "cases": [recon],
        }
        policy["deferred_recovery_schema"] = rec.RECOVERY_SCHEMA
        policy["deferred_recovery"] = recovery_block(
            wp, "asrin", "RECON-TEST", self.verified["audit_id"], self.producers
        )
        return wp, policy, plane, gh

    def prove(self, wp, policy, gh, rows=None, previous=None, today=TODAY):
        rows = [self.verified, self.again] if rows is None else rows
        previous = self.verified if previous is None else previous
        with (
            patch.object(t, "last_blocker", return_value=previous),
            patch.object(t, "blocker_rows", return_value=rows),
        ):
            return auto.recovery_proof(t, wp, "asrin", policy, gh, today=today)

    def code(self, wp, policy, gh, **kwargs):
        with self.assertRaises(t.Denied) as caught:
            self.prove(wp, policy, gh, **kwargs)
        return caught.exception.code

    def live(self, wp, policy, plane, gh):
        with (
            patch.object(t, "last_blocker", return_value=self.verified),
            patch.object(t, "blocker_rows", return_value=[self.verified, self.again]),
        ):
            return auto.live_view(t, plane, policy, "asrin", gh)["items"][wp]


class RecoveryProofTests(RecoveryBase):
    def test_valid_case_frees_only_the_slot_and_the_legacy_path_stays_closed(self):
        wp, policy, plane, gh = self.fixture()
        proof = self.prove(wp, policy, gh)
        self.assertEqual(proof["recovery_case"], "DEFER-TEST")
        self.assertEqual(proof["audit_id"], self.verified["audit_id"])
        self.assertEqual(proof["reassertion_comment_id"], "222")
        self.assertTrue(gh.invalidations)  # mutable PR/main/run reads start fresh
        with patch.object(t, "last_blocker", return_value=self.verified):
            self.assertIsNone(auto.deferred_proof(t, wp, "asrin", policy, gh))
        item = self.live(wp, policy, plane, gh)
        self.assertTrue(resolver.deferred_acceptance(wp, item))
        self.assertFalse(resolver.occupies_implementation_slot(wp, item))
        self.assertEqual(plane.patches, [])  # a read-only proof, never a Plane write

    def test_every_missing_or_changed_fact_denies_with_its_own_code(self):
        def comment(**kw):
            return lambda gh, policy: gh.comment_obj.update(
                body=assessment(self.verified["audit_id"], self.producers, **kw)
            )

        def exemption(**kw):
            return lambda gh, policy: gh.repo_files.update(
                {COVERAGE_PATH: (coverage(**kw), "b")}
            )

        def at_main(raw):
            return lambda gh, policy: gh.files_at.update(
                {(COVERAGE_PATH, HEAD): (raw, "b")}
            )

        def put(attr, value):
            return lambda gh, policy: setattr(gh, attr, value)

        def upd(name, **kw):
            return lambda gh, policy: getattr(gh, name).update(kw)

        incomplete = {
            "Owner-executable implementation work": "UNKNOWN",
            "Recovery case": "DEFER-OTHER",
            "Original blocker audit": "0" * 64,
            "Deferred acceptance class": "OTHER",
            "Pending producers": "WP-TEST-002",
            "Resolves blocker": "x",
            "Canonical main revision": "short",
            "Platform disposition": "PR 75 " + "e" * 40,
        }
        cases = {
            "RECOVERY_ASSESSMENT_NOT_OWNER_UNEDITED": [
                upd("comment_obj", updated_at="2026-10-25T16:00:00Z"),
                lambda gh, policy: gh.comment_obj["user"].update(login="other"),
            ],
            "RECOVERY_ASSESSMENT_INCOMPLETE": [
                comment(**{k: v}) for k, v in incomplete.items()
            ]
            + [comment(**{"Platform disposition": None})],
            "RECOVERY_BLOCKER_CHANGED": [comment(**{"External dependency": "Else"})],
            "RECOVERY_EVIDENCE_MISSING": [comment(Evidence=None)],
            "RECOVERY_PRODUCER_ALREADY_DELIVERED": [
                lambda gh, policy: gh.tree["tree"].append(
                    {"path": f"evidence/{self.producers[0]}/x", "sha": "e"}
                ),
                # Delivered after the assessment: only the CURRENT main has it.
                lambda gh, policy: gh.trees.update(
                    {HEAD: with_rows(gh, {"path": f"evidence/{self.producers[1]}/x"})}
                ),
            ],
            "RECOVERY_DISPOSITION_CHANGED": [
                # Same owner and expiry, different terms, only on the current main.
                at_main(coverage(reason="Revoked; implement observability now.")),
                at_main(coverage(expires_on="2026-12-31")),
                at_main(coverage(status="PENDING")),
            ],
            "DEFERRED_SOURCE_TREE_INCOMPLETE": [
                lambda gh, policy: gh.trees.update(
                    {HEAD: dict(with_rows(gh), truncated=True)}
                )
            ],
            "RECOVERY_DISPOSITION_UNVERIFIED": [
                upd("disposition", merged=False),
                upd("disposition", merge_commit_sha="e" * 40),
                upd("disposition", user={"login": "other"}),
                exemption(owner="Other"),
                exemption(expires_on="2026-12-31"),
                put("repo_files", {COVERAGE_PATH: (b"{}", "b")}),
                # Revoked or changed after the assessment: only the CURRENT main shows it.
                lambda gh, policy: gh.files_at.update(
                    {(COVERAGE_PATH, HEAD): (b"{}", "b")}
                ),
                put("files_at", {(COVERAGE_PATH, DISPOSITION_MERGE): (b"{}", "b")}),
                put("repo_files", {COVERAGE_PATH: (duplicated(), "b")}),
            ],
            "RECONCILIATION_PR_BINDING_MISMATCH": [
                upd("pr_data", merged=False),
                upd("pr_data", merge_commit_sha="e" * 40),
            ],
            "MERGE_PARENT_MISMATCH": [put("parents", [HEAD, PARENT])],
            "MERGED_BRANCH_NOT_DELETED": [put("undeleted_branch", True)],
            "PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY": [
                put("stale_ancestry", True),
                put("ancestry_fail", {(REVISION, HEAD)}),
                put("ancestry_fail", {(DISPOSITION_MERGE, HEAD)}),
            ],
            "ARTIFACT_MISSING": [put("missing_artifact", True)],
            "INCOMPLETE_PR_FILE_SCOPE": [lambda gh, policy: gh.rows.pop()],
            "REQUIRED_RUN_NOT_SUCCESSFUL": [
                lambda gh, policy: gh.runs[4001].update(conclusion="failure")
            ],
            "DEFERRED_CANONICAL_SCOPE_CHANGED": [
                lambda gh, policy: policy["source_git_blobs"].update(
                    {"docs/08": "changed"}
                ),
                # Pinned source changed on the current main after the assessment.
                lambda gh, policy: gh.trees.update({HEAD: with_rows(gh, "docs/08")}),
                # Changed at the assessed revision but not on the current main.
                lambda gh, policy: gh.trees.update(
                    {REVISION: with_rows(gh, "docs/08")}
                ),
            ],
        }
        for expected, mutations in cases.items():
            for index, mutate in enumerate(mutations):
                with self.subTest(code=expected, index=index):
                    wp, policy, plane, gh = self.fixture()
                    mutate(gh, policy)
                    self.assertEqual(self.code(wp, policy, gh), expected)

    def test_audit_and_reassertion_chain_must_be_the_original_verified_one(self):
        wp, policy, plane, gh = self.fixture()
        intent = dict(self.verified, result="INTENT")
        other = dict(self.verified, audit_id="f" * 64)
        edited = dict(self.again, reason="x")
        bare = dict(self.again, evidence_refs=["pr:1"])  # a valid row, no comment
        bare["audit_id"] = t.audit_identity(bare)
        self.assertEqual(
            self.code(wp, policy, gh, previous=intent), "RECOVERY_BLOCKER_AUDIT_MISSING"
        )
        self.assertEqual(
            self.code(wp, policy, gh, previous=other, rows=[other]),
            "RECOVERY_BLOCKER_AUDIT_MISMATCH",
        )
        for rows in (
            [self.verified],
            [self.again],
            [self.verified, edited],
            [self.verified, bare],
        ):
            self.assertEqual(
                self.code(wp, policy, gh, rows=rows), "RECOVERY_ASSESSMENT_REQUIRED"
            )

    def test_expiry_denies_and_the_diagnosis_is_a_bare_code(self):
        wp, policy, plane, gh = self.fixture()
        late = dt.date(2026, 11, 21)
        self.assertEqual(
            self.code(wp, policy, gh, today=late), "RECOVERY_DISPOSITION_EXPIRED"
        )
        gh.comment_obj["updated_at"] = "2026-10-25T16:00:00Z"
        item = self.live(wp, policy, plane, gh)
        self.assertEqual(
            item["deferred_recovery_denial"], "RECOVERY_ASSESSMENT_NOT_OWNER_UNEDITED"
        )
        self.assertNotIn("deferred_acceptance", item)

    def test_wp_without_a_case_or_without_the_schema_is_untouched(self):
        wp, policy, plane, gh = self.fixture()
        policy["deferred_recovery"]["cases"][0]["profile"] = "selman"
        self.assertIsNone(self.prove(wp, policy, gh))
        wp, policy, plane, gh = self.fixture()
        del policy["deferred_recovery_schema"]
        item = self.live(wp, policy, plane, gh)
        self.assertNotIn("deferred_acceptance", item)
        self.assertNotIn("deferred_recovery_denial", item)

    def test_advance_owner_reports_denial_codes_only(self):
        live = {"items": {"WP-X": {"deferred_recovery_denial": "RECOVERY_X"}}}
        no_task = {"status": "NO_TASK", "reasons": ["NO_REMAINING_SCHEDULED_WORK"]}
        fake = SimpleNamespace(compute_next_eligible=lambda *_: no_task)
        policy = {"execution_project": {}, "execution_preferences": {}}
        policy["source_manifest"] = {}
        with (
            patch.object(auto, "resolver", fake),
            patch.object(auto, "live_view", return_value=live),
        ):
            result = auto.advance_owner(t, "asrin", policy, Mock(), None, None, "k")
        self.assertEqual(result["deferred_recovery_denials"], {"WP-X": "RECOVERY_X"})


class RecoveryPolicyTests(RecoveryBase):
    def test_valid_policy_is_accepted_and_malformed_ones_are_rejected(self):
        bad = {
            "unknown key": lambda c, b: c.update(extra=1),
            "bad case id": lambda c, b: c.update(case_id="x"),
            "bad audit": lambda c, b: c.update(blocker_audit_id="abc"),
            "bad class": lambda c, b: c.update(classification="OTHER"),
            "bad change": lambda c, b: c.update(change_record="CHG-1"),
            "wrong owner": lambda c, b: c.update(profile="selman"),
            "unknown recon": lambda c, b: c.update(reconciliation_case="RECON-X"),
            "bad merge sha": lambda c, b: c["platform_disposition"].update(
                merge_sha="x"
            ),
            "bad date": lambda c, b: c["platform_disposition"].update(expires_on="s"),
            "unknown producer": lambda c, b: c.update(pending_producers=["WP-NOPE-1"]),
            "self producer": lambda c, b: c.update(pending_producers=[c["wp_id"]]),
            "no producers": lambda c, b: c.update(pending_producers=[]),
            "duplicate case": lambda c, b: b["cases"].append(deepcopy(c)),
            "bad schema": lambda c, b: b.update(schema_version="v0"),
        }
        rec.t = t
        for name, mutate in {"valid": lambda c, b: None, **bad}.items():
            wp, policy, plane, gh = self.fixture()
            block = deepcopy(policy["deferred_recovery"])
            mutate(block["cases"][0], block)
            args = (block, policy["lifecycle_reconciliation"], policy["contexts"])
            args += (dict(t.q.PEOPLE),)
            if name == "valid":
                rec.validate_recovery_policy(*args)
                continue
            with self.subTest(name=name), self.assertRaises(t.Denied):
                rec.validate_recovery_policy(*args)


class RecoveryThroughRealAdapterTests(unittest.TestCase):
    """Mutable inputs are re-read from GitHub on every proof; SHA/main bindings hold."""

    def setUp(self):
        self.t, self.wp = base.t, base.WP
        case = base.make_case(changed_files=3)
        self.policy = base.make_policy(case)
        contexts = self.policy["contexts"]
        producers = ["WP-TEST-001", "WP-TEST-002"]
        self.producer_row = {"path": f"evidence/{producers[0]}/x", "sha": "e" * 40}
        for other in producers:
            contexts[other] = deepcopy(contexts[self.wp])
        work = contexts[self.wp]
        work["source_manifest"] = {"docs/08": "digest"}
        work["work_package"]["requirement_refs"] = ["FR-TEST-001"]
        wbs, rtm = na.scope_docs(self.wp)
        blobs = {}
        sources = {
            "docs/08": "blob1",
            "docs/02_System_Architecture_Specification.md": "b2",
        }
        for path, text in ((resolver.WBS_PATH, wbs), (resolver.RTM_PATH, rtm)):
            sources[path] = na.git_blob(blobs, text)
        projection = resolver.scope_projection(self.wp, ["FR-TEST-001"], wbs, rtm)
        self.policy.update(
            scope_projection_schema="cap-scope-projection-v1",
            scope_projections={self.wp: projection},
            source_git_blobs=dict(sources),
            deferred_recovery_schema=rec.RECOVERY_SCHEMA,
        )
        self.verified, self.again = audit_rows(self.wp, base.PROFILE, BLOCKER)
        audit_id = self.verified["audit_id"]
        self.policy["deferred_recovery"] = recovery_block(
            self.wp, base.PROFILE, case["case_id"], audit_id, producers
        )
        repo, owner = adapter.REPO, self.t.GITHUB[base.PROFILE]
        tree = [{"path": p, "sha": s} for p, s in sources.items()]
        routes = adapter.default_routes()
        routes.update(
            {
                f"{repo}/issues/comments/222": {
                    "user": {"login": owner},
                    "created_at": "2026-10-25T15:00:00Z",
                    "updated_at": "2026-10-25T15:00:00Z",
                    "body": assessment(audit_id, producers),
                },
                f"{repo}/git/trees/{REVISION}?recursive=1": {
                    "truncated": False,
                    "tree": tree,
                },
                f"{repo}/git/trees/{base.MAIN}?recursive=1": {
                    "truncated": False,
                    "tree": tree,
                },
                f"{repo}/contents/evidence/test.json?ref={REVISION}": {
                    "type": "file",
                    "size": 3,
                },
                f"{repo}/contents/{COVERAGE_PATH}?ref={base.MAIN}": registry(),
                f"{repo}/contents/{COVERAGE_PATH}?ref={DISPOSITION_MERGE}": registry(),
                f"{repo}/pulls/75": adapter.pr_payload(
                    number=75,
                    user={"login": self.t.GITHUB["yavuz"]},
                    merge_commit_sha=DISPOSITION_MERGE,
                ),
                f"{repo}/compare/{REVISION}...{base.MAIN}": adapter.AHEAD,
                f"{repo}/compare/{DISPOSITION_MERGE}...{base.MAIN}": adapter.AHEAD,
            }
        )
        routes.update({f"{repo}/git/blobs/{s}": b for s, b in blobs.items()})
        self.routes = routes

    def prove(self, overrides=None, times=1):
        transport = adapter.Transport(dict(self.routes, **(overrides or {})))
        outcome: Any = None
        rows = [self.verified, self.again]
        gh = adapter.real_adapter()  # one adapter, so its cache persists
        with (
            patch.object(self.t.subprocess, "run", transport),
            patch.object(self.t, "last_blocker", return_value=self.verified),
            patch.object(self.t, "blocker_rows", return_value=rows),
        ):
            try:
                for _ in range(times):
                    outcome = auto.recovery_proof(
                        self.t,
                        self.wp,
                        base.PROFILE,
                        self.policy,
                        gh,
                        today=TODAY,
                    )
            except self.t.Denied as exc:
                outcome = exc
        return outcome, transport

    def test_proof_rereads_mutable_inputs_on_every_call(self):
        proof, transport = self.prove(times=2)
        self.assertEqual(proof["recovery_case"], "DEFER-TEST")
        for route in (adapter.PR_ROUTE, adapter.MAIN_ROUTE, adapter.BRANCH_ROUTE):
            with self.subTest(route=route):
                self.assertGreaterEqual(transport.calls[route], 2)
        self.assertEqual(transport.calls[adapter.COMMIT_ROUTE], 1)  # immutable

    def test_main_that_loses_the_merge_or_a_moved_pr_denies(self):
        other = "5" * 40
        lost = {"status": "diverged", "behind_by": 1}
        denied, _ = self.prove(
            {
                adapter.MAIN_ROUTE: {"sha": other},
                f"{adapter.REPO}/compare/{base.MERGE}...{other}": lost,
            }
        )
        self.assertEqual(denied.code, "PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY")
        moved = adapter.pr_payload(head={"ref": adapter.BRANCH, "sha": "7" * 40})
        denied, _ = self.prove({adapter.PR_ROUTE: moved})
        self.assertEqual(denied.code, "RECONCILIATION_PR_BINDING_MISMATCH")

    def test_changes_on_the_current_main_after_the_assessment_deny(self):
        repo, main = adapter.REPO, base.MAIN
        trees = f"{repo}/git/trees/{main}?recursive=1"
        rows = self.routes[trees]["tree"]
        delivered = {"truncated": False, "tree": rows + [self.producer_row]}
        revoked = registry(coverage(reason="Revoked; implement observability now."))
        for code, route, answer in (
            ("RECOVERY_PRODUCER_ALREADY_DELIVERED", trees, delivered),
            (
                "RECOVERY_DISPOSITION_CHANGED",
                f"{repo}/contents/{COVERAGE_PATH}?ref={main}",
                revoked,
            ),
        ):
            with self.subTest(code=code):
                denied, _ = self.prove({route: answer})
                self.assertEqual(denied.code, code)


class PolicyPinningTests(unittest.TestCase):
    def test_generated_policy_pins_the_recovery_sources(self):
        """Runs the real builder on this checkout; a changed or revoked case needs a refresh."""
        root = HERE.parents[2]
        script = (HERE / "build_policy.py").read_text()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "policy.json"
            patched = script.replace(
                "ROOT=Path('/srv/ailab/project')", f"ROOT=Path({str(root)!r})"
            )
            patched = re.sub(
                r"(?m)^output=Path\(.*\)$", f"output=Path({str(out)!r})", patched
            )
            self.assertNotEqual(patched, script)
            done = subprocess.run(
                [sys.executable, "-I", "-c", patched], capture_output=True, text=True
            )
            self.assertEqual(done.returncode, 0, done.stderr[-500:])
            policy = json.loads(out.read_text())
        self.assertEqual(policy["deferred_recovery_schema"], rec.RECOVERY_SCHEMA)
        for name in (
            "project_control/deferred_recovery.yaml",
            "09_change/CHG-033.yaml",
        ):
            raw = (root / name).read_bytes()
            blob = hashlib.sha1(b"blob %d\0" % len(raw) + raw, usedforsecurity=False)
            with self.subTest(name=name):
                digest = hashlib.sha256(raw).hexdigest()
                self.assertEqual(policy["source_manifest"][name], digest)
                self.assertEqual(
                    policy["execution_project"]["source_manifest"][name], digest
                )
                self.assertEqual(policy["source_git_blobs"][name], blob.hexdigest())


if __name__ == "__main__":
    unittest.main()
