"""CTRL-HOST-031: CHG-054 start transitions and typed GitHub read failures.

Offline fixtures only (the harness of test_transition.py): no credential, network,
Plane or GitHub call. These tests pin the corrected behavior: BACKLOG -> READY and
READY -> IN_PROGRESS share the canonical owner/scope/HARD+START predicate, the obsolete
READY.md, DoR-comment, preparation, cycle and other-READY gates are gone, adjacent
steps and real work facts are kept, and a missing repository file is never an outage.
"""

import json
import subprocess
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

import test_transition as base
from test_transition import HEAD, SECRET, fixture, run_case, t


def hard_start(status, strength="HARD", stage="START", edge="DEP-9"):
    edge = {
        "id": edge,
        "predecessor": {"node": "DN-X"},
        "semantics": {"strength": strength, "blocking_stage": stage},
    }
    if status is not None:
        edge["status"] = status
    return edge


def with_edges(*edges):
    def mutate(policy, plane, gh, envelope):
        policy["contexts"][plane.item["external_id"]]["dependency_edges"] = list(edges)

    return mutate


def ready_refs(*refs):
    def mutate(policy, plane, gh, envelope):
        envelope["evidence_refs"] = list(refs)

    return mutate


class ReadyIsCanonicalStartEligibility(unittest.TestCase):
    def test_ready_needs_no_assessment_file_comment_preparation_slot_or_schedule(self):
        def advisory_only(policy, plane, gh, envelope):
            envelope["evidence_refs"] = ["pr:1"]
            gh.comments = {}  # no owner DoR comment
            policy["contexts"][plane.item["external_id"]][
                "cycle_ids"
            ] = []  # unscheduled
            policy["preparation_schema"] = (
                "cap-preparation-v1"  # stale/absent preparation
            )
            other = deepcopy(plane.item)
            other.update(
                id="other-ready",
                external_id="WP-TEST-099",
                state="READY",
                name="[WP-TEST-099] Other READY work",
            )
            plane.items.append(other)  # another READY item of the same owner

            def forbidden(*args, **kwargs):
                raise AssertionError("READY must not read READY.md or any assessment")

            gh.repository_file = forbidden
            gh.evidence_text = forbidden

        result, plane, logs, gh = run_case(
            source="BACKLOG", target="READY", mutate=advisory_only
        )
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "READY"}])
        self.assertEqual([r["result"] for r in logs], ["INTENT", "VERIFIED"])
        self.assertEqual(gh.artifacts, [])

    def test_ready_is_not_a_dor_pass_and_records_only_the_state_change(self):
        result, plane, logs, _ = run_case(source="BACKLOG", target="READY")
        self.assertEqual(plane.patches, [{"state": "READY"}])
        for record in logs:
            self.assertNotIn("checks", record)
            self.assertNotIn("dor", json.dumps(record).lower())

    def test_ready_evidence_must_name_real_github_objects(self):
        for refs in (
            ["comment:99"],  # absent comment
            ["commit:" + "9" * 40],  # absent revision
            ["pr:1", "comment:99"],
        ):
            with self.subTest(refs=refs), self.assertRaises(t.Denied):
                run_case(source="BACKLOG", target="READY", mutate=ready_refs(*refs))
        for refs in (
            ["commit:" + HEAD],
            ["comment:2"],
            ["run:4"],
            ["pr:1", "comment:2"],
        ):
            with self.subTest(refs=refs):
                result, *_ = run_case(
                    source="BACKLOG", target="READY", mutate=ready_refs(*refs)
                )
                self.assertEqual(result["result"], "VERIFIED")


class OneStartPredicateForBothStartTransitions(unittest.TestCase):
    EDGES = {
        "hard-start-not-ready": (
            (hard_start("NOT_READY"),),
            "HARD_START_DEPENDENCY_UNRESOLVED:DEP-9",
        ),
        "hard-start-status-missing": (
            (hard_start(None),),
            "HARD_START_DEPENDENCY_UNRESOLVED:DEP-9",
        ),
        "hard-start-unknown-status": (
            (hard_start("UNKNOWN"),),
            "HARD_START_DEPENDENCY_UNRESOLVED:DEP-9",
        ),
        "one-of-two-unresolved": (
            (hard_start("READY", edge="DEP-1"), hard_start("NOT_READY")),
            "HARD_START_DEPENDENCY_UNRESOLVED:DEP-9",
        ),
    }

    def test_unresolved_real_hard_start_dependency_stops_both_transitions(self):
        for name, (edges, code) in self.EDGES.items():
            for source, target in (("BACKLOG", "READY"), ("READY", "IN_PROGRESS")):
                with self.subTest(case=name, target=target):
                    with self.assertRaises(t.Denied) as denied:
                        run_case(
                            source=source, target=target, mutate=with_edges(*edges)
                        )
                    self.assertEqual(denied.exception.code, code)

    def test_only_a_resolved_hard_start_dependency_and_later_gates_do_not_block_start(
        self,
    ):
        later = (
            hard_start("NOT_READY", stage="INTEGRATION", edge="DEP-I"),
            hard_start("NOT_READY", stage="MILESTONE_EXIT", edge="DEP-M"),
            hard_start("NOT_READY", stage="FREEZE", edge="DEP-F"),
            hard_start("NOT_READY", strength="SOFT", edge="DEP-S"),
            hard_start(None, stage="INTEGRATION", edge="DEP-N"),
            hard_start("READY", edge="DEP-R"),
        )
        for source, target in (("BACKLOG", "READY"), ("READY", "IN_PROGRESS")):
            with self.subTest(target=target):
                result, plane, *_ = run_case(
                    source=source, target=target, mutate=with_edges(*later)
                )
                self.assertEqual(result["result"], "VERIFIED")
                self.assertEqual(plane.patches, [{"state": target}])

    def test_canonical_owner_and_scope_ambiguity_is_a_start_blocker(self):
        wp, policy, *_ = fixture(source="BACKLOG", target="READY")
        context = policy["contexts"][wp]
        t.product_startability(context)
        owner = deepcopy(context)
        owner["work_package"]["primary_owner"]["canonical_name"] = "Nobody Canonical"
        with self.assertRaises(t.Denied) as denied:
            t.product_startability(owner)
        self.assertEqual(denied.exception.code, "CANONICAL_OWNER_AMBIGUOUS")
        for field in ("id", "scope_class", "dor_refs", "dod_refs"):
            scope = deepcopy(context)
            scope["work_package"][field] = [] if field.endswith("refs") else ""
            with self.subTest(field=field), self.assertRaises(t.Denied) as denied:
                t.product_startability(scope)
            self.assertEqual(denied.exception.code, "CANONICAL_SCOPE_UNKNOWN")

    def test_start_still_requires_the_exact_canonical_owner_and_assignee(self):
        for source, target in (("BACKLOG", "READY"), ("READY", "IN_PROGRESS")):
            wp, policy, plane, gh, envelope = fixture(source=source, target=target)
            other = next(p for p in t.q.PEOPLE if p != "asrin")
            with self.subTest(target=target), self.assertRaises(t.Denied):
                t.execute(
                    other,
                    wp,
                    target,
                    envelope,
                    policy,
                    plane,
                    gh,
                    lambda *a: None,
                    SECRET,
                )
            plane.item["assignees"] = ["foreign-user"]
            plane.items[0]["assignees"] = ["foreign-user"]
            with (
                self.subTest(target=target, assignee="foreign"),
                self.assertRaises(t.Denied),
            ):
                t.execute(
                    "asrin",
                    wp,
                    target,
                    envelope,
                    policy,
                    plane,
                    gh,
                    lambda *a: None,
                    SECRET,
                )
            self.assertEqual(plane.patches, [])

    def test_real_orthogonal_blocker_still_stops_both_transitions(self):
        for source, target in (("BACKLOG", "READY"), ("READY", "IN_PROGRESS")):

            def blocked(policy, plane, gh, envelope):
                plane.item["labels"].append(plane.blocked)
                plane.items[0]["labels"].append(plane.blocked)

            with self.subTest(target=target), self.assertRaises(t.Denied) as denied:
                run_case(source=source, target=target, mutate=blocked)
            self.assertEqual(denied.exception.code, "ACTIVE_BLOCKER_UNRESOLVED")


class AdjacentStepsAndRealWorkFacts(unittest.TestCase):
    def test_backlog_to_in_progress_remains_invalid_with_any_evidence(self):
        for refs in (["pr:1"], ["commit:" + HEAD], ["pr:1", "comment:2", "run:4"]):
            with self.subTest(refs=refs), self.assertRaises(t.Denied) as denied:
                run_case(
                    source="BACKLOG", target="IN_PROGRESS", mutate=ready_refs(*refs)
                )
            self.assertEqual(denied.exception.code, "INVALID_CANONICAL_TRANSITION")

    def test_in_progress_needs_an_actual_wp_commit_or_live_pr(self):
        result, plane, _, gh = run_case(mutate=ready_refs("commit:" + HEAD))
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "IN_PROGRESS"}])
        self.assertEqual(gh.started, (plane.item["external_id"], HEAD, "asrin"))

        def no_change(policy, plane, gh, envelope):
            envelope["evidence_refs"] = ["commit:" + HEAD]
            gh.bad_work_commit = True

        with self.assertRaises(t.Denied) as denied:
            run_case(mutate=no_change)
        self.assertEqual(denied.exception.code, "NO_IMPLEMENTATION_CHANGE_FROM_MAIN")
        with self.assertRaises(t.Denied) as denied:
            run_case(mutate=ready_refs("comment:2", "run:4"))  # planning evidence only
        self.assertEqual(denied.exception.code, "ONE_REAL_WP_PR_REQUIRED")

        def merged_pr(policy, plane, gh, envelope):
            gh.pr_data.update(merged=True, state="closed")

        with self.assertRaises(t.Denied) as denied:
            run_case(mutate=merged_pr)
        self.assertEqual(denied.exception.code, "NO_LIVE_IMPLEMENTATION_PR")

    def test_no_state_is_skipped_or_synthesized(self):
        for source, target in (
            ("BACKLOG", "IN_REVIEW"),
            ("BACKLOG", "DONE"),
            ("READY", "IN_REVIEW"),
            ("IN_PROGRESS", "READY"),
            ("CANCELED", "READY"),
            ("DONE", "READY"),
        ):
            with (
                self.subTest(source=source, target=target),
                self.assertRaises(t.Denied),
            ):
                run_case(source=source, target=target)

    def test_start_correction_leaves_merge_and_done_gates_fail_closed(self):
        def failing_ci(policy, plane, gh, envelope):
            gh.check_data[0][0]["conclusion"] = "failure"

        with self.assertRaises(t.Denied):
            run_case(source="IN_REVIEW", target="MERGE_READY", mutate=failing_ci)

        def no_owner_assessment(policy, plane, gh, envelope):
            envelope["evidence_refs"] = ["pr:1", "run:4"]

        with self.assertRaises(t.Denied):
            run_case(source="VALIDATING", target="DONE", mutate=no_owner_assessment)

        def unresolved_hard_edge(policy, plane, gh, envelope):
            with_edges(hard_start("NOT_READY", stage="INTEGRATION"))(
                policy, plane, gh, envelope
            )

        result, *_ = run_case(
            source="IN_REVIEW", target="MERGE_READY", mutate=unresolved_hard_edge
        )
        self.assertEqual(
            result["result"], "VERIFIED"
        )  # unchanged: not a MERGE_READY gate


class TypedGitHubReadFailures(unittest.TestCase):
    CONTENTS = f"{t.REPO}/contents/evidence/x.md?ref={HEAD}"
    PULL = f"{t.REPO}/pulls/9"

    def client(self):
        client = object.__new__(t.GitHub)
        client.cache, client.env, client.uid, client.gid = {}, {}, 0, 0
        client.request_timeout, client.deadline = 30, None
        return client

    def failed(self, route, stderr, returncode=1):
        result = SimpleNamespace(returncode=returncode, stdout=b"", stderr=stderr)
        with (
            patch.object(t.subprocess, "run", return_value=result),
            self.assertRaises(t.Denied) as denied,
        ):
            self.client()._get(route)
        return denied.exception.code

    def test_missing_repository_file_is_a_missing_artifact_not_an_outage(self):
        self.assertEqual(
            self.failed(self.CONTENTS, b"gh: Not Found (HTTP 404)"),
            "ARTIFACT_NOT_FOUND",
        )
        for call in (
            lambda c: c.artifact("repo:evidence/x.md", HEAD),
            lambda c: c.repository_file("evidence/x.md", HEAD),
            lambda c: c.evidence_text("evidence/x.md", HEAD),
        ):
            result = SimpleNamespace(
                returncode=1, stdout=b"", stderr=b"gh: Not Found (HTTP 404)"
            )
            with (
                patch.object(t.subprocess, "run", return_value=result),
                self.assertRaises(t.Denied) as denied,
            ):
                call(self.client())
            self.assertEqual(denied.exception.code, "ARTIFACT_NOT_FOUND")
        self.assertIn("ARTIFACT_NOT_FOUND", t.MISSING_ARTIFACT)

    def test_other_not_found_routes_are_not_reclassified(self):
        for route in (
            self.PULL,
            f"{t.REPO}/issues/comments/5",
            f"{t.REPO}/actions/runs/7",
        ):
            self.assertEqual(
                self.failed(route, b"gh: Not Found (HTTP 404)"),
                "GITHUB_READ_UNAVAILABLE",
            )

    def test_auth_permission_service_and_unknown_failures_stay_distinct_and_fail_closed(
        self,
    ):
        cases = {
            b"gh: Bad credentials (HTTP 401)": "GITHUB_AUTH_HTTP_401",
            b"gh: Resource not accessible (HTTP 403)": "GITHUB_FORBIDDEN_HTTP_403",
            b"gh: API rate limit exceeded (HTTP 403)": "GITHUB_FORBIDDEN_HTTP_403",
            b"gh: Server Error (HTTP 500)": "GITHUB_SERVICE_ERROR",
            b"gh: Bad Gateway (HTTP 502)": "GITHUB_SERVICE_ERROR",
            b"gh: Service Unavailable (HTTP 503)": "GITHUB_SERVICE_ERROR",
            b"error connecting to api.github.com": "GITHUB_READ_UNAVAILABLE",
            b"": "GITHUB_READ_UNAVAILABLE",
            b"gh: Conflict (HTTP 409)": "GITHUB_READ_UNAVAILABLE",
        }
        for stderr, code in cases.items():
            for route in (
                self.CONTENTS,
                self.PULL,
            ):  # a file route never turns 4xx/5xx into "missing"
                with self.subTest(stderr=stderr, route=route.rsplit("/", 2)[-2]):
                    self.assertEqual(self.failed(route, stderr), code)

    def test_timeout_oversize_and_malformed_responses_are_typed(self):
        with (
            patch.object(
                t.subprocess, "run", side_effect=subprocess.TimeoutExpired("gh", 30)
            ),
            self.assertRaises(t.Denied) as denied,
        ):
            self.client()._get(self.PULL)
        self.assertEqual(denied.exception.code, "GITHUB_READ_TIMEOUT")
        for stdout, code in (
            (b"x" * 8_000_001, "GITHUB_RESPONSE_TOO_LARGE"),
            (b"{not json", "GITHUB_RESPONSE_MALFORMED"),
            (b'{"a": 1, "a": 2}', "GITHUB_RESPONSE_MALFORMED"),
        ):
            result = SimpleNamespace(returncode=0, stdout=stdout, stderr=b"")
            with (
                self.subTest(code=code),
                patch.object(t.subprocess, "run", return_value=result),
            ):
                client = self.client()
                with self.assertRaises(t.Denied) as denied:
                    client._get(self.PULL)
                self.assertEqual(denied.exception.code, code)
                self.assertEqual(client.cache, {})  # nothing malformed is cached

    def test_success_is_unchanged_and_cached_and_errors_never_echo_stderr(self):
        ok = SimpleNamespace(
            returncode=0, stdout=b'{"type": "file", "size": 5}', stderr=b""
        )
        client = self.client()
        with patch.object(t.subprocess, "run", return_value=ok) as run:
            self.assertEqual(client._get(self.CONTENTS), {"type": "file", "size": 5})
            client._get(self.CONTENTS)
        self.assertEqual(run.call_count, 1)
        leak = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"HTTP 404 token=" + SECRET.encode()
        )
        with (
            patch.object(t.subprocess, "run", return_value=leak),
            self.assertRaises(t.Denied) as denied,
        ):
            self.client()._get(self.CONTENTS)
        self.assertNotIn(SECRET, denied.exception.code)
        self.assertNotIn(SECRET, str(denied.exception.args))

    def test_a_missing_basis_file_is_rejected_as_missing_other_failures_are_not_relabelled(
        self,
    ):
        for code, reason in (
            ("ARTIFACT_NOT_FOUND", "RUNTIME_READINESS_BASIS_MISSING"),
            ("ARTIFACT_NOT_A_FILE", "RUNTIME_READINESS_BASIS_MISSING"),
            ("GITHUB_FORBIDDEN_HTTP_403", "GITHUB_FORBIDDEN_HTTP_403"),
            ("GITHUB_SERVICE_ERROR", "GITHUB_SERVICE_ERROR"),
        ):
            helper = base.TransitionTests(
                "test_automatic_runtime_skeleton_readiness_is_accepted"
            )
            context, edge, policy, gh, _ = helper.runtime_fixture()
            real = gh.repository_file

            def read(path, sha, limit=65536, _real=real, _code=code):
                if path == "evidence/readiness/DN-PLAT-COMPOSE.json":
                    raise t.Denied(_code)
                return _real(path, sha, limit)

            gh.repository_file = read
            with self.subTest(code=code):
                result = t.automatic_readiness_attestation(
                    gh, context, edge, HEAD, policy
                )
                self.assertEqual(result["status"], "UNKNOWN")  # never a PASS
                self.assertIn(reason, result["reasons"])
                if reason != "RUNTIME_READINESS_BASIS_MISSING":
                    self.assertNotIn(
                        "RUNTIME_READINESS_BASIS_MISSING", result["reasons"]
                    )


if __name__ == "__main__":
    unittest.main()
