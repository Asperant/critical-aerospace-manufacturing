"""Offline fixtures only. Tests never load a Plane/GitHub credential or call either."""

import importlib.util
import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]


def load(name, path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


t = load("transition_for_reconcile", HERE / "transition.py")
t.q = load("queue_for_reconcile", HERE.parent / "plane-queue" / "queue.py")
r = load("reconcile_under_test", HERE / "reconcile.py")
r.t = t

SECRET = "sentinel-plane-secret-do-not-print"
WP = "WP-TEST-003"
PROFILE = "batuhan"
HEAD = "1" * 40
MERGE = "2" * 40
PARENT = "3" * 40
MAIN = "4" * 40
NOW = "2026-10-24T20:00:00+00:00"
STARTED = "2026-10-24T10:00:00Z"
FINISHED = "2026-10-24T10:30:00Z"
FILES = 131
CI_RUN, PC_RUN = 4001, 4002
REPOSITORY = "Asperant/critical-aerospace-manufacturing"


def make_case(**overrides):
    case = {
        "case_id": "RECON-TEST-PR52",
        "profile": PROFILE,
        "wp_id": WP,
        "pr": 52,
        "pr_head_sha": HEAD,
        "merge_sha": MERGE,
        "parents": [PARENT, HEAD],
        "changed_files": FILES,
        "scope_prefixes": ["services/sim/", "evidence/sim/"],
        "targets": ["MERGED", "VALIDATING"],
        "validating_runs": [
            {"run_id": CI_RUN, "workflow_path": ".github/workflows/ci.yml"},
            {"run_id": PC_RUN, "workflow_path": ".github/workflows/projectctl.yml"},
        ],
        "require_successful_runs": True,
        "approvals": {
            "scope_answer": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "control_id_exception": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "plan_sha256": "c" * 64,
            "plan_approval_turn": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        },
        "change_record": "CHG-031",
    }
    case.update(overrides)
    return case


def make_policy(case=None):
    names = dict(t.q.PEOPLE)
    contexts = {
        WP: {
            "work_package": {
                "id": WP,
                "primary_owner": {"canonical_name": names[PROFILE][0]},
            },
            "dependency_edges": [],
            "cycle_ids": ["S1"],
        }
    }
    review = json.loads(
        (REPO_ROOT / "09_change" / "development_review_policy.json").read_text()
    )
    return {
        "contexts": contexts,
        "review_policy": review,
        "policy_digest": "fixture-policy-digest",
        "lifecycle_reconciliation": {
            "schema_version": r.POLICY_SCHEMA,
            "cases": [case or make_case()],
        },
    }


class FakePlane:
    def __init__(self, source, labels=None):
        names = dict(t.q.PEOPLE)
        self.item = {
            "id": "12345678-1234-1234-1234-123456789abc",
            "external_id": WP,
            "external_source": "projectctl",
            "name": f"[{WP}] Test work",
            "description_html": json.dumps(
                {"canonical_wp_id": WP, "canonical_owner": names[PROFILE][0]}
            ),
            "state": source,
            "assignees": [names[PROFILE][1]],
            "labels": list(labels or ["MILESTONE-LABEL"]),
            "priority": "low",
            "cycle": "S1",
        }
        self.items = [deepcopy(self.item)]
        self.states = {s: s for s in t.q.STATES}
        self.names = {s: s for s in t.q.STATES}
        self.members = [{"id": v[1], "email": v[2]} for v in t.q.PEOPLE.values()]
        self.blocked = "BLOCKED-LABEL"
        self.patches = []
        self.apply = True
        self.response_lost = False
        self.corrupt = False
        self.drift_on_read = None  # (read number, changes) simulating a concurrent edit
        self.reads = 0
        self.refreshes = 0
        self.queue_change = None  # row appended on the next refresh (a concurrent edit)

    def issue(self, identity):
        self.reads += 1
        value = deepcopy(self.item)
        if self.drift_on_read and self.reads >= self.drift_on_read[0]:
            value.update(self.drift_on_read[1])
        return value

    def refresh_items(self):
        self.refreshes += 1
        if self.queue_change:
            self.items = [*self.items, deepcopy(self.queue_change)]
        return self.items

    def patch(self, before, target):
        body = t.patch_body(before, target, self.states, self.blocked)
        self.patches.append(deepcopy(body))
        if self.apply:
            self.item.update(body)
        if self.corrupt:
            self.item["assignees"] = ["someone-else"]
        if self.response_lost:
            raise TimeoutError(SECRET)


class FakeGH:
    def __init__(self, case=None):
        case = case or make_case()
        self.case = case
        self.main = MAIN
        self.deleted = True
        self.parents = list(case["parents"])
        self.commit_sha = case["merge_sha"]
        self.ancestry_fail = set()
        self.pr_data = {
            "number": case["pr"],
            "base": {"repo": {"full_name": REPOSITORY}, "ref": "main", "sha": "9" * 40},
            "user": {"login": t.GITHUB[PROFILE]},
            "head": {"ref": f"wp/{WP}-slice", "sha": case["pr_head_sha"]},
            "title": f"[{WP}] Implement slice",
            "body": "Body",
            "changed_files": case["changed_files"],
            "state": "closed",
            "merged": True,
            "merge_commit_sha": case["merge_sha"],
        }
        self.rows = [
            {"filename": f"services/sim/file{i}.py", "status": "added"}
            for i in range(case["changed_files"] - 1)
        ] + [{"filename": "evidence/sim/README.md", "status": "added"}]
        self.runs = {}
        for spec in case["validating_runs"]:
            self.runs[spec["run_id"]] = {
                "id": spec["run_id"],
                "head_sha": case["merge_sha"],
                "head_branch": "main",
                "event": "push",
                "path": spec["workflow_path"],
                "status": "completed",
                "conclusion": "success",
                "run_started_at": STARTED,
                "updated_at": FINISHED,
                "repository": {"full_name": REPOSITORY},
            }
        self.fresh_run_calls = 0
        self.invalidations = 0
        self.on_invalidate = None  # called with the snapshot number, simulating a race
        self.run_drift = None  # (call number, run id, changes)

    def invalidate(self):
        self.invalidations += 1
        if self.on_invalidate:
            self.on_invalidate(self.invalidations)

    def pr(self, number):
        return deepcopy(self.pr_data)

    def fresh_pr(self, number):
        return deepcopy(self.pr_data)

    def commit(self, sha):
        if sha != self.commit_sha:
            raise t.Denied("COMMIT_IDENTITY_MISMATCH")
        return {"sha": sha, "parents": [{"sha": p} for p in self.parents]}

    def ancestor(self, base, head):
        if (base, head) in self.ancestry_fail:
            raise t.Denied("PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY")

    def main_sha(self):
        return self.main

    def branch_deleted(self, branch):
        if not self.deleted:
            raise t.Denied("MERGED_BRANCH_NOT_DELETED")

    def files(self, pr):
        return deepcopy(self.rows)

    def fresh_run(self, number):
        self.fresh_run_calls += 1
        if number not in self.runs:
            raise t.Denied("GITHUB_READ_UNAVAILABLE")
        run = deepcopy(self.runs[number])
        drift = self.run_drift
        if drift and self.fresh_run_calls >= drift[0] and number == drift[1]:
            run.update(drift[2])
        return run


def envelope_for(case, target):
    refs = [f"pr:{case['pr']}"]
    if target == "VALIDATING":
        refs += [f"run:{x['run_id']}" for x in case["validating_runs"]]
    return {"reason": "Reconcile observed merge facts", "evidence_refs": refs}


def run_case(source="READY", target="VALIDATING", mutate=None, case=None):
    case = case or make_case()
    policy = make_policy(case)
    plane, gh = FakePlane(source), FakeGH(case)
    env = envelope_for(case, target)
    if mutate:
        mutate(policy, plane, gh, env)
    logs = []

    def audit(record, key):
        if key in json.dumps(record):
            raise t.Denied("SECRET_IN_AUDIT_INPUT")
        logs.append(deepcopy(record))

    result = r.reconcile(
        PROFILE, WP, target, env, policy, plane, gh, audit, SECRET, now=lambda: NOW
    )
    return result, plane, logs, gh


def denied(test, code, **kwargs):
    with test.assertRaises(t.Denied) as caught:
        run_case(**kwargs)
    test.assertEqual(caught.exception.code, code)


class PolicyTests(unittest.TestCase):
    def check(self, block):
        return r.validate_policy(block, make_policy()["contexts"], dict(t.q.PEOPLE))

    def test_unlisted_profile_wp_or_target_is_not_authorized(self):
        block = make_policy()["lifecycle_reconciliation"]
        for profile, wp, target in [
            ("asrin", WP, "VALIDATING"),
            (PROFILE, "WP-TEST-001", "VALIDATING"),
            (PROFILE, WP, "DONE"),
            (PROFILE, WP, "READY"),
        ]:
            with self.subTest(profile=profile, wp=wp, target=target):
                with self.assertRaises(t.Denied) as caught:
                    r.find_case(block, profile, wp, target)
                self.assertEqual(caught.exception.code, "RECONCILIATION_NOT_AUTHORIZED")

    def test_malformed_policy_cases_are_rejected(self):
        cases = {
            "unknown key": lambda c: c.update(extra=1),
            "missing key": lambda c: c.pop("merge_sha"),
            "bad profile": lambda c: c.update(profile="nobody"),
            "unknown wp": lambda c: c.update(wp_id="WP-NOPE-001"),
            "bad pr": lambda c: c.update(pr=0),
            "bool pr": lambda c: c.update(pr=True),
            "short sha": lambda c: c.update(merge_sha="abc"),
            "uppercase sha": lambda c: c.update(pr_head_sha="A" * 40),
            "second parent not head": lambda c: c.update(parents=[PARENT, "5" * 40]),
            "three parents": lambda c: c.update(parents=[PARENT, HEAD, "5" * 40]),
            "duplicate parents": lambda c: c.update(parents=[HEAD, HEAD]),
            "no files": lambda c: c.update(changed_files=0),
            "too many files": lambda c: c.update(changed_files=1001),
            "bad prefix": lambda c: c.update(scope_prefixes=["services/sim"]),
            "traversal prefix": lambda c: c.update(scope_prefixes=["../x/"]),
            "empty targets": lambda c: c.update(targets=[]),
            "unsupported target": lambda c: c.update(targets=["DONE"]),
            "validating without runs": lambda c: c.update(validating_runs=[]),
            "bad workflow": lambda c: c["validating_runs"][0].update(
                workflow_path="/etc/passwd"
            ),
            "duplicate runs": lambda c: c.update(
                validating_runs=[c["validating_runs"][0]] * 2
            ),
            "non-bool success flag": lambda c: c.update(require_successful_runs="yes"),
            "bad approval id": lambda c: c["approvals"].update(scope_answer="x"),
            "bad plan hash": lambda c: c["approvals"].update(plan_sha256="1"),
            "bad change id": lambda c: c.update(change_record="CHG-1"),
            "bad case id": lambda c: c.update(case_id="x"),
        }
        for name, change in cases.items():
            case = make_case()
            change(case)
            block = {"schema_version": r.POLICY_SCHEMA, "cases": [case]}
            with self.subTest(name=name), self.assertRaises(t.Denied):
                self.check(block)

    def test_owner_mismatch_duplicates_and_shape_are_rejected(self):
        contexts = make_policy()["contexts"]
        contexts[WP]["work_package"]["primary_owner"]["canonical_name"] = "Someone Else"
        block = make_policy()["lifecycle_reconciliation"]
        with self.assertRaises(t.Denied) as caught:
            r.validate_policy(block, contexts, dict(t.q.PEOPLE))
        self.assertEqual(caught.exception.code, "RECONCILIATION_OWNER_MISMATCH")
        twice = {"schema_version": r.POLICY_SCHEMA, "cases": [make_case(), make_case()]}
        for bad in (
            twice,
            {"schema_version": "v0", "cases": [make_case()]},
            {"schema_version": r.POLICY_SCHEMA, "cases": []},
            {"schema_version": r.POLICY_SCHEMA},
            None,
            [],
        ):
            with self.subTest(bad=str(bad)[:40]), self.assertRaises(t.Denied):
                self.check(bad)

    def test_repository_policy_file_matches_the_approved_case(self):
        block = yaml.safe_load(
            (
                REPO_ROOT / "project_control" / "lifecycle_reconciliation.yaml"
            ).read_text()
        )
        contexts = {
            "WP-SIM-001": {
                "work_package": {"primary_owner": {"canonical_name": "Batuhan Kaya"}}
            },
            "WP-CORE-007": {
                "work_package": {"primary_owner": {"canonical_name": "Asrın Dündar"}}
            },
        }
        r.validate_policy(block, contexts, dict(t.q.PEOPLE))
        case = next(
            case
            for case in block["legacy_recovery_cases"]
            if case["wp_id"] == "WP-SIM-001"
        )
        self.assertEqual(
            (case["profile"], case["wp_id"], case["pr"], case["changed_files"]),
            ("batuhan", "WP-SIM-001", 52, 131),
        )
        self.assertEqual(
            case["pr_head_sha"], "9bac44c7285846a5d8e2af0565433fd8f88b602e"
        )
        self.assertEqual(case["merge_sha"], "471a9b19dbd1319727443cee4f50215a371af716")
        self.assertEqual(
            case["parents"],
            ["a2e9760c9ffe3c97d4a2d3af60335cfe552df680", case["pr_head_sha"]],
        )
        self.assertEqual(
            [x["run_id"] for x in case["validating_runs"]], [40099331443, 40099331483]
        )
        self.assertTrue(case["require_successful_runs"])
        core = next(
            case
            for case in block["legacy_recovery_cases"]
            if case["wp_id"] == "WP-CORE-007"
        )
        self.assertEqual(
            (core["profile"], core["pr"], core["merge_sha"]),
            ("asrin", 104, "4058f3268725359d4a8dcfbabb7fca78f5c9ae7f"),
        )


class ReconcileFlowTests(unittest.TestCase):
    def test_ready_to_validating_is_one_audited_patch(self):
        result, plane, logs, gh = run_case()
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "VALIDATING"}])
        self.assertEqual([x["result"] for x in logs], ["INTENT", "VERIFIED"])
        row = logs[-1]
        self.assertEqual(row["operation"], "LIFECYCLE_RECONCILE")
        self.assertEqual((row["from_state"], row["to_state"]), ("READY", "VALIDATING"))
        self.assertEqual(row["timestamp"], NOW)
        self.assertTrue(row["skipped_state_history_not_asserted"])
        self.assertIn("done_not_claimed", row["outstanding"])
        self.assertIn("integrated_acceptance_not_established", row["outstanding"])
        self.assertEqual(row["case_id"], "RECON-TEST-PR52")
        self.assertEqual(row["change_record"], "CHG-031")
        self.assertEqual(row["approvals"], make_case()["approvals"])
        self.assertEqual(row["facts"]["merge"]["shape"], "two_parent_merge")
        self.assertEqual(row["facts"]["merge"]["parents"], [PARENT, HEAD])
        self.assertEqual([x["run_id"] for x in row["facts"]["runs"]], [CI_RUN, PC_RUN])
        self.assertTrue(all(x["conclusion"] == "success" for x in row["facts"]["runs"]))
        self.assertEqual(row["facts"]["scope"]["changed_files"], FILES)
        self.assertEqual(logs[0]["audit_id"], logs[1]["audit_id"])
        self.assertNotIn(SECRET, json.dumps(logs))

    def test_merged_fallback_needs_no_run_and_writes_merged(self):
        result, plane, logs, gh = run_case("READY", "MERGED")
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(logs[-1]["facts"]["runs"], [])
        self.assertEqual(gh.fresh_run_calls, 0)
        self.assertEqual(plane.patches, [{"state": "MERGED"}])

    def test_same_target_is_verified_idempotence_with_no_patch(self):
        for target in ("MERGED", "VALIDATING"):
            with self.subTest(target=target):
                result, plane, logs, gh = run_case(target, target)
                self.assertEqual(result["result"], "UNCHANGED")
                self.assertEqual(plane.patches, [])
                self.assertEqual([x["result"] for x in logs], ["UNCHANGED"])
                self.assertTrue(logs[0]["skipped_state_history_not_asserted"])

    def test_terminal_backwards_and_unlisted_sources_fail_closed(self):
        for source, target in [
            ("BACKLOG", "VALIDATING"),
            ("DONE", "VALIDATING"),
            ("CANCELED", "MERGED"),
            ("VALIDATING", "MERGED"),
            ("MERGED", "VALIDATING"),
            ("DONE", "MERGED"),
        ]:
            with self.subTest(source=source, target=target):
                denied(
                    self, "SOURCE_STATE_NOT_RECONCILABLE", source=source, target=target
                )

    def test_blocked_work_fails_closed_even_when_otherwise_idempotent(self):
        def block(policy, plane, gh, env):
            plane.item["labels"].append(plane.blocked)

        denied(self, "ACTIVE_BLOCKER_UNRESOLVED", mutate=block)
        denied(self, "ACTIVE_BLOCKER_UNRESOLVED", source="VALIDATING", mutate=block)

    def test_blocked_in_progress_reconciles_to_validating_without_clearing_blocker(
        self,
    ):
        result, plane, logs, _ = run_case(
            source="IN_PROGRESS",
            mutate=lambda policy, item, gh, env: item.item["labels"].append(
                item.blocked
            ),
        )
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "VALIDATING"}])
        self.assertIn(plane.blocked, plane.item["labels"])
        self.assertTrue(logs[-1]["blocked_preserved"])
        self.assertEqual(
            (logs[-1]["from_state"], logs[-1]["to_state"]),
            ("IN_PROGRESS", "VALIDATING"),
        )

    def test_unsupported_targets_and_arguments_are_rejected(self):
        policy, plane, gh = make_policy(), FakePlane("READY"), FakeGH()
        for profile, wp, target in [
            (PROFILE, WP, "DONE"),
            (PROFILE, WP, "IN_PROGRESS"),
            (PROFILE, WP, "BLOCKED"),
            ("nobody", WP, "MERGED"),
            (PROFILE, "bad", "MERGED"),
        ]:
            with self.subTest(target=target, profile=profile):
                with self.assertRaises(t.Denied) as caught:
                    r.reconcile(
                        profile,
                        wp,
                        target,
                        envelope_for(make_case(), "MERGED"),
                        policy,
                        plane,
                        gh,
                        lambda *a: None,
                        SECRET,
                    )
                self.assertEqual(caught.exception.code, "INVALID_ARGUMENTS")
        self.assertEqual(plane.patches, [])

    def test_wrong_assignee_owner_or_ambiguous_mapping_is_rejected(self):
        def wrong_assignee(policy, plane, gh, env):
            plane.item["assignees"] = ["someone-else"]
            plane.items = [deepcopy(plane.item)]

        def duplicated(policy, plane, gh, env):
            plane.items = [deepcopy(plane.item), deepcopy(plane.item)]

        def wrong_owner(policy, plane, gh, env):
            owner = policy["contexts"][WP]["work_package"]["primary_owner"]
            owner["canonical_name"] = "Asrın Dündar"

        denied(self, "PLANE_ASSIGNEE_MISMATCH", mutate=wrong_assignee)
        denied(self, "AMBIGUOUS_OR_MISSING_CANONICAL_WP", mutate=duplicated)
        denied(self, "RECONCILIATION_OWNER_MISMATCH", mutate=wrong_owner)

    def test_evidence_refs_must_be_exactly_the_bound_pr_and_runs(self):
        cases = {
            "missing run": lambda e: e["evidence_refs"].pop(),
            "extra comment": lambda e: e["evidence_refs"].append("comment:5"),
            "wrong pr": lambda e: e["evidence_refs"].__setitem__(0, "pr:53"),
            "wrong run": lambda e: e["evidence_refs"].__setitem__(1, "run:9"),
            "no pr": lambda e: e["evidence_refs"].pop(0),
        }
        for name, change in cases.items():
            with self.subTest(name=name):
                denied(
                    self,
                    "RECONCILIATION_EVIDENCE_REFS_MISMATCH",
                    mutate=lambda p, pl, g, e, change=change: change(e),
                )
        denied(
            self,
            "RECONCILIATION_EVIDENCE_REFS_MISMATCH",
            target="MERGED",
            mutate=lambda p, pl, g, e: e["evidence_refs"].append(f"run:{CI_RUN}"),
        )


class MergeProofTests(unittest.TestCase):
    def mutate_gh(self, **changes):
        def apply(policy, plane, gh, env):
            for key, value in changes.items():
                setattr(gh, key, value)

        return apply

    def mutate_pr(self, **changes):
        def apply(policy, plane, gh, env):
            gh.pr_data.update(changes)

        return apply

    def test_two_parent_proof_rejects_forged_or_unrelated_parents(self):
        cases = {
            "unrelated first parent": [("5" * 40), HEAD],
            "second parent not head": [PARENT, "5" * 40],
            "octopus": [PARENT, HEAD, "5" * 40],
            "swapped": [HEAD, PARENT],
            "squash shape": [PARENT],
        }
        for name, parents in cases.items():
            with self.subTest(name=name):
                denied(
                    self,
                    "MERGE_PARENT_MISMATCH",
                    mutate=self.mutate_gh(parents=parents),
                )

    def test_commit_identity_and_branch_and_main_reachability(self):
        denied(
            self, "COMMIT_IDENTITY_MISMATCH", mutate=self.mutate_gh(commit_sha="6" * 40)
        )
        denied(self, "MERGED_BRANCH_NOT_DELETED", mutate=self.mutate_gh(deleted=False))
        denied(
            self,
            "PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY",
            mutate=self.mutate_gh(ancestry_fail={(MERGE, MAIN)}),
        )
        denied(
            self,
            "PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY",
            mutate=self.mutate_gh(ancestry_fail={(PARENT, MERGE)}),
        )

    def test_merge_proof_itself_requires_the_second_parent_to_be_the_pr_head(self):
        # Call the proof directly with an unvalidated case: policy validation and the PR
        # binding normally make this unreachable, so the guard is exercised on its own.
        case = make_case(parents=[PARENT, "5" * 40])
        gh = FakeGH(case)
        with self.assertRaises(t.Denied) as caught:
            r.merge_proof(gh, case, gh.pr_data)
        self.assertEqual(caught.exception.code, "MERGE_SECOND_PARENT_NOT_PR_HEAD")
        good = make_case()
        proof = r.merge_proof(FakeGH(good), good, FakeGH(good).pr_data)
        self.assertEqual(proof["parents"], [PARENT, HEAD])

    def test_historical_first_parent_need_not_equal_the_mutable_pr_base(self):
        def new_base(policy, plane, gh, env):
            gh.pr_data["base"]["sha"] = "a" * 40  # base moved since the merge

        result, _, _, _ = run_case(mutate=new_base)
        self.assertEqual(result["result"], "VERIFIED")

    def test_squash_proof_is_supported_when_the_policy_says_one_parent(self):
        case = make_case(parents=[PARENT])
        result, _, logs, _ = run_case(case=case)
        self.assertEqual(logs[-1]["facts"]["merge"]["shape"], "squash")
        self.assertEqual(result["result"], "VERIFIED")
        denied(
            self,
            "MERGE_PARENT_MISMATCH",
            case=case,
            mutate=self.mutate_gh(parents=[PARENT, HEAD]),
        )

    def test_scope_inventory_must_be_complete_safe_and_in_the_wp(self):
        def short(policy, plane, gh, env):
            gh.rows = gh.rows[:-1]

        def secret_path(policy, plane, gh, env):
            gh.rows[0] = {"filename": "services/sim/.env", "status": "added"}

        def no_evidence(policy, plane, gh, env):
            gh.rows[-1] = {"filename": "docs/other.md", "status": "added"}

        def removed_only(policy, plane, gh, env):
            gh.rows[-1] = {"filename": "evidence/sim/README.md", "status": "removed"}

        denied(self, "INCOMPLETE_PR_FILE_SCOPE", mutate=short)
        denied(self, "PR_SECRET_OR_RUNTIME_PATH", mutate=secret_path)
        denied(self, "WP_SCOPE_PATH_MISSING", mutate=no_evidence)
        denied(self, "WP_SCOPE_PATH_MISSING", mutate=removed_only)


class RunProofTests(unittest.TestCase):
    def change_runs(self, **changes):
        def apply(policy, plane, gh, env):
            for run in gh.runs.values():
                run.update(changes)

        return apply

    def test_runs_that_do_not_prove_started_validation_are_rejected(self):
        cases = {
            "wrong sha": ({"head_sha": "9" * 40}, "RUN_WRONG_REVISION"),
            "wrong branch": ({"head_branch": "wp/x"}, "RUN_NOT_A_MAIN_RUN"),
            "pull request event": ({"event": "pull_request"}, "RUN_NOT_A_MAIN_RUN"),
            "target event": ({"event": "pull_request_target"}, "RUN_NOT_A_MAIN_RUN"),
            "wrong repo": (
                {"repository": {"full_name": "x/y"}},
                "RUN_WRONG_REPOSITORY",
            ),
            "missing repo": ({"repository": {}}, "RUN_WRONG_REPOSITORY"),
            "wrong workflow": (
                {"path": ".github/workflows/other.yml"},
                "RUN_WRONG_WORKFLOW",
            ),
            "wrong id": ({"id": 5}, "RUN_IDENTITY_MISMATCH"),
            "queued": ({"status": "queued", "conclusion": None}, "RUN_NOT_STARTED"),
            "waiting": ({"status": "waiting", "conclusion": None}, "RUN_NOT_STARTED"),
            "no start time": ({"run_started_at": None}, "RUN_TIMESTAMP_MISSING"),
            "bad start time": (
                {"run_started_at": "yesterday"},
                "RUN_TIMESTAMP_INVALID",
            ),
            "naive start time": (
                {"run_started_at": "2026-10-24T10:00:00"},
                "RUN_TIMESTAMP_INVALID",
            ),
            "cancelled": ({"conclusion": "cancelled"}, "RUN_NO_QUALIFYING_CONCLUSION"),
            "skipped": ({"conclusion": "skipped"}, "RUN_NO_QUALIFYING_CONCLUSION"),
            "no conclusion": ({"conclusion": None}, "RUN_NO_QUALIFYING_CONCLUSION"),
            "finished before start": (
                {"updated_at": "2026-10-24T09:00:00Z"},
                "RUN_TIMESTAMPS_INCONSISTENT",
            ),
            "failed first case": (
                {"conclusion": "failure"},
                "REQUIRED_RUN_NOT_SUCCESSFUL",
            ),
            "running first case": (
                {"status": "in_progress", "conclusion": None},
                "REQUIRED_RUN_NOT_SUCCESSFUL",
            ),
        }
        for name, (changes, code) in cases.items():
            with self.subTest(name=name):
                denied(self, code, mutate=self.change_runs(**changes))


class WriteSafetyTests(unittest.TestCase):
    def test_concurrent_plane_change_blocks_the_write(self):
        def drift(policy, plane, gh, env):
            plane.drift_on_read = (2, {"labels": ["MILESTONE-LABEL", "NEW"]})

        denied(self, "CONCURRENT_PLANE_CHANGE", mutate=drift)

    def test_a_plane_change_during_the_github_recheck_window_blocks_the_write(self):
        holder = {}

        def race(policy, plane, gh, env):
            holder["plane"] = plane

            def change(snapshot):
                if snapshot == 2:  # while the pre-write GitHub snapshot is being taken
                    plane.item["labels"] = [*plane.item["labels"], "RACING-EDIT"]

            gh.on_invalidate = change

        denied(self, "CONCURRENT_PLANE_CHANGE", mutate=race)
        self.assertEqual(holder["plane"].patches, [])

    def test_concurrent_github_change_blocks_the_write(self):
        def drift(policy, plane, gh, env):
            gh.run_drift = (3, CI_RUN, {"updated_at": "2026-10-24T11:00:00Z"})

        denied(self, "CONCURRENT_GITHUB_CHANGE", mutate=drift)

    def test_main_moving_forward_is_not_a_concurrent_change(self):
        class MovingMain(FakeGH):
            calls = 0

            def main_sha(self):
                self.calls += 1
                return f"{self.calls}" * 40

        policy, plane, gh = make_policy(), FakePlane("READY"), MovingMain()
        logs = []
        result = r.reconcile(
            PROFILE,
            WP,
            "VALIDATING",
            envelope_for(make_case(), "VALIDATING"),
            policy,
            plane,
            gh,
            lambda rec, key: logs.append(deepcopy(rec)),
            SECRET,
            now=lambda: NOW,
        )
        self.assertEqual(result["result"], "VERIFIED")

    def test_unwritable_audit_blocks_mutation(self):
        policy, plane, gh = make_policy(), FakePlane("READY"), FakeGH()

        def broken(record, key):
            raise OSError("audit sink unavailable")

        with self.assertRaises(OSError):
            r.reconcile(
                PROFILE,
                WP,
                "VALIDATING",
                envelope_for(make_case(), "VALIDATING"),
                policy,
                plane,
                gh,
                broken,
                SECRET,
                now=lambda: NOW,
            )
        self.assertEqual(plane.patches, [])

    def test_lost_response_that_applied_is_verified_by_readback_with_one_patch(self):
        def lost(policy, plane, gh, env):
            plane.response_lost = True

        result, plane, logs, _ = run_case(mutate=lost)
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(len(plane.patches), 1)
        self.assertNotIn(SECRET, json.dumps(logs))

    def test_lost_response_that_did_not_apply_is_unconfirmed_and_never_retried(self):
        policy, plane, gh = make_policy(), FakePlane("READY"), FakeGH()
        plane.response_lost, plane.apply = True, False
        logs = []
        with self.assertRaises(t.Denied) as caught:
            r.reconcile(
                PROFILE,
                WP,
                "VALIDATING",
                envelope_for(make_case(), "VALIDATING"),
                policy,
                plane,
                gh,
                lambda rec, key: logs.append(deepcopy(rec)),
                SECRET,
                now=lambda: NOW,
            )
        self.assertEqual(
            caught.exception.code, "MUTATION_UNCONFIRMED_DO_NOT_RETRY_BLINDLY"
        )
        self.assertEqual(len(plane.patches), 1)
        self.assertEqual(
            [x["result"] for x in logs], ["INTENT", "UNCONFIRMED_REQUIRES_READBACK"]
        )

    def test_protected_field_change_in_readback_is_unconfirmed(self):
        policy, plane, gh = make_policy(), FakePlane("READY"), FakeGH()
        plane.corrupt = True
        logs = []
        with self.assertRaises(t.Denied) as caught:
            r.reconcile(
                PROFILE,
                WP,
                "VALIDATING",
                envelope_for(make_case(), "VALIDATING"),
                policy,
                plane,
                gh,
                lambda rec, key: logs.append(deepcopy(rec)),
                SECRET,
                now=lambda: NOW,
            )
        self.assertEqual(
            caught.exception.code, "MUTATION_UNCONFIRMED_DO_NOT_RETRY_BLINDLY"
        )
        self.assertEqual(len(plane.patches), 1)

    def test_secret_in_audit_input_is_refused(self):
        def reflect(policy, plane, gh, env):
            env["reason"] = f"leaked {SECRET}"

        with self.assertRaises(t.Denied) as caught:
            run_case(mutate=reflect)
        self.assertEqual(caught.exception.code, "SECRET_IN_AUDIT_INPUT")


def other_row(external_id, state, assignees=None):
    owner = dict(t.q.PEOPLE)[PROFILE][1]
    return {
        "id": f"row-{external_id}",
        "external_id": external_id,
        "state": state,
        "assignees": [owner] if assignees is None else assignees,
    }


class OwnerQueueTests(unittest.TestCase):
    def add(self, *rows):
        def apply(policy, plane, gh, env):
            plane.items = [*plane.items, *rows]

        return apply

    def test_another_ready_or_in_progress_item_of_the_owner_blocks_the_write(self):
        for name, rows in {
            "ready": [other_row("WP-OTHER-001", "READY")],
            "in progress": [other_row("WP-OTHER-002", "IN_PROGRESS")],
            "both": [
                other_row("WP-OTHER-001", "READY"),
                other_row("WP-OTHER-002", "IN_PROGRESS"),
            ],
            "multi-assignee": [
                other_row(
                    "WP-OTHER-003", "READY", ["someone", dict(t.q.PEOPLE)[PROFILE][1]]
                )
            ],
        }.items():
            with self.subTest(name=name):
                policy, plane, gh = make_policy(), FakePlane("READY"), FakeGH()
                self.add(*rows)(policy, plane, gh, None)
                with self.assertRaises(t.Denied) as caught:
                    r.reconcile(
                        PROFILE,
                        WP,
                        "VALIDATING",
                        envelope_for(make_case(), "VALIDATING"),
                        policy,
                        plane,
                        gh,
                        lambda *a: None,
                        SECRET,
                        now=lambda: NOW,
                    )
                self.assertEqual(caught.exception.code, "OWNER_QUEUE_CONFLICT")
                self.assertEqual(plane.patches, [])
                self.assertEqual(gh.invalidations, 0)  # denied before any GitHub proof

    def test_normal_neighbouring_work_is_not_a_conflict(self):
        rows = [
            other_row("WP-OTHER-010", "BACKLOG"),
            other_row("WP-OTHER-011", "IN_REVIEW"),
            other_row("WP-OTHER-012", "MERGE_READY"),
            other_row("WP-OTHER-013", "MERGED"),
            other_row("WP-OTHER-014", "VALIDATING"),
            other_row("WP-OTHER-015", "DONE"),
            other_row("WP-OTHER-016", "CANCELED"),
            other_row("WP-OTHER-017", "READY", ["another-member"]),
            other_row("WP-OTHER-018", "IN_PROGRESS", ["another-member"]),
            other_row("WP-OTHER-019", "READY", []),
        ]
        result, plane, _, _ = run_case(mutate=self.add(*rows))
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "VALIDATING"}])

    def test_a_verified_no_op_is_exempt_from_the_queue_check(self):
        result, plane, _, _ = run_case(
            source="VALIDATING",
            mutate=self.add(other_row("WP-OTHER-001", "READY")),
        )
        self.assertEqual(result["result"], "UNCHANGED")
        self.assertEqual((plane.patches, plane.refreshes), ([], 0))

    def test_only_verified_slot_release_can_remove_a_blocked_queue_conflict(self):
        plane = FakePlane("READY")
        blocked = other_row("WP-OTHER-001", "IN_PROGRESS")
        blocked["labels"] = [plane.blocked]
        plane.items.append(blocked)
        self.assertEqual(
            r.owner_queue_conflicts(plane, PROFILE, plane.item), ["WP-OTHER-001"]
        )
        self.assertEqual(
            r.owner_queue_conflicts(plane, PROFILE, plane.item, {"WP-OTHER-001"}),
            [],
        )

    def test_a_conflict_appearing_before_the_write_blocks_it(self):
        def appears(policy, plane, gh, env):
            plane.queue_change = other_row("WP-OTHER-001", "READY")

        policy, plane, gh = make_policy(), FakePlane("READY"), FakeGH()
        appears(policy, plane, gh, None)
        logs = []
        with self.assertRaises(t.Denied) as caught:
            r.reconcile(
                PROFILE,
                WP,
                "VALIDATING",
                envelope_for(make_case(), "VALIDATING"),
                policy,
                plane,
                gh,
                lambda rec, key: logs.append(rec),
                SECRET,
                now=lambda: NOW,
            )
        self.assertEqual(caught.exception.code, "CONCURRENT_OWNER_QUEUE_CHANGE")
        self.assertEqual((plane.patches, logs, plane.refreshes), ([], [], 1))


class FreshSnapshotTests(unittest.TestCase):
    def test_the_audit_records_the_snapshot_closest_to_the_write(self):
        class MovingMain(FakeGH):
            calls = 0

            def main_sha(self):
                self.calls += 1
                return f"{self.calls}" * 40

        policy, plane, gh = make_policy(), FakePlane("READY"), MovingMain()
        logs = []
        r.reconcile(
            PROFILE,
            WP,
            "VALIDATING",
            envelope_for(make_case(), "VALIDATING"),
            policy,
            plane,
            gh,
            lambda rec, key: logs.append(deepcopy(rec)),
            SECRET,
            now=lambda: NOW,
        )
        self.assertEqual(logs[-1]["facts"]["merge"]["main_sha_observed"], "2" * 40)


class OrdinaryTransitionStillStrictTests(unittest.TestCase):
    def test_ordinary_updater_still_rejects_a_state_skip(self):
        import test_transition as tt

        with self.assertRaises(tt.t.Denied) as caught:
            tt.run_case("batuhan", "READY", "VALIDATING")
        self.assertEqual(caught.exception.code, "INVALID_CANONICAL_TRANSITION")

    def test_ordinary_merged_shape_still_rejects_two_parent_merges(self):
        gh = object.__new__(t.GitHub)
        pr = {"head": {"ref": f"wp/{WP}-slice"}, "merge_commit_sha": MERGE}

        def get(route):
            if "matching-refs" in route:
                return []
            return {"parents": [{"sha": PARENT}, {"sha": HEAD}]}

        gh._get = get
        with self.assertRaises(t.Denied) as caught:
            gh.merged_shape(pr)
        self.assertEqual(caught.exception.code, "NON_SQUASH_MERGE_SHAPE")


if __name__ == "__main__":
    unittest.main()
