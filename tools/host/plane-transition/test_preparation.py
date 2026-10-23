"""Bounded preparation safety and actual transition integration; offline fixtures."""

import base64
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_auto_next import HERE, auto, load
from test_transition import SECRET, fixture, t

resolver = load(
    "window_resolver", HERE.parents[1] / "projectctl/src/projectctl/execution_queue.py"
)
p = load("preparation_test", HERE / "preparation.py")
c = load("prepare_test", HERE / "prepare.py")
SHA = "a" * 40


def canonical():
    w = {
        "id": "WP-SIM-001",
        "primary_owner": {"canonical_name": "Batuhan Kaya"},
        "supporting_reviewers": [{"canonical_name": "Asrın Dündar"}],
        "inputs_required_contracts": "no inbound dependency edges in 05 — early unlocker",
        "scope_class": "F0",
        "purpose": "Deterministic simulator kernel",
        "readiness_refs": ["DN-SIM-KERNEL"],
        "requirement_refs": ["FR-SIM-001"],
        "architecture_refs": ["ARCH-SIM-ENGINE"],
        "major_tasks": [
            "implement event queue and clock advance",
            "property tests for event ordering",
        ],
        "deliverables": ["DES kernel module", "kernel unit/property test suite"],
        "verification_expectations": "TEST-SIM-KERNEL, TEST-SIM-DETERMINISM",
    }
    context = {
        "work_package": w,
        "dependency_edges": [],
        "requirements": [
            {
                "id": "FR-SIM-001",
                "statement": "Provide DES simulator",
                "scope_class": "F0",
            }
        ],
        "milestone_id": "M1",
    }
    policy = {
        "contexts": {w["id"]: context},
        "source_manifest": {"docs/04_Work_Breakdown_Structure.md": "b" * 64},
        "preparation_schema": p.SCHEMA,
        "source_git_blobs": {"docs/04_Work_Breakdown_Structure.md": "b" * 40},
    }
    return context, policy


def candidate():
    return {
        "wp_id": "WP-SIM-001",
        "status": "NEEDS_DOR",
        "hard_start_blockers": [],
        "deficits": [{"canonical_id": "DOR-TASK-01"}],
        "reason": "DOR_EVIDENCE_UNAVAILABLE",
    }


def source_tree(policy):
    return {
        "truncated": False,
        "tree": [
            {"path": name, "sha": value, "type": "blob"}
            for name, value in policy["source_git_blobs"].items()
        ],
    }


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.context, self.policy = canonical()
        self.plan = p.derive(self.context, self.policy, SHA)

    def test_mechanical_dor_auto_preparable(self):
        self.assertEqual(p.classify(candidate(), self.plan), "AUTO_PREPARABLE")

    def test_real_implementation_is_never_governance(self):
        item = candidate()
        item["deficits"] = [{"canonical_id": "IMPLEMENTATION-STARTED"}]
        self.assertEqual(p.classify(item, self.plan), "REAL_WORK_REQUIRED")

    def test_hard_start_and_cross_owner_readiness_waits(self):
        item = candidate()
        item["hard_start_blockers"] = [
            {"dependency_id": "DEP-006", "producer_owner": "yavuz"}
        ]
        self.assertEqual(p.classify(item, self.plan), "WAITING_DEP")

    def test_unavailable_never_becomes_prepared(self):
        item = candidate()
        item["status"] = "UNAVAILABLE"
        self.assertEqual(p.classify(item, self.plan), "UNAVAILABLE")

    def test_unknown_is_not_pass(self):
        self.context["work_package"]["major_tasks"] = []
        plan = p.derive(self.context, self.policy, SHA)
        item = candidate()
        item["deficits"] = [{"canonical_id": "DOR-TASK-10"}]
        self.assertEqual(plan["checks"]["DOR-TASK-10"]["result"], "UNKNOWN")
        self.assertEqual(p.classify(item, plan), "REAL_WORK_REQUIRED")

    def test_canonical_source_sha_and_acceptance_retained(self):
        self.assertEqual(self.plan["source_sha"], SHA)
        self.assertEqual(
            self.plan["start_slice"], self.context["work_package"]["major_tasks"][0]
        )
        self.assertEqual(
            self.plan["planned_acceptance"],
            self.context["work_package"]["deliverables"],
        )

    def test_no_fabricated_readiness_or_test_evidence(self):
        self.assertEqual(self.plan["test_results"], "NOT_EXECUTED")
        self.assertEqual(self.plan["readiness_artifacts"], "NOT_PRODUCED")
        self.assertEqual(self.plan["product_implementation"], "NOT_YET_EXECUTED")
        self.assertNotIn("dependency_readiness", self.plan)

    def test_research_never_gets_unjustified_na(self):
        self.context["requirements"][0]["scope_class"] = "R1"
        plan = p.derive(self.context, self.policy, SHA)
        self.assertEqual(plan["checks"]["DOR-TASK-12"]["result"], "UNKNOWN")

    def test_even_later_stage_dependencies_not_invented(self):
        self.context["dependency_edges"] = [
            {"id": "DEP-022", "semantics": {"blocking_stage": "INTEGRATION"}}
        ]
        plan = p.derive(self.context, self.policy, SHA)
        self.assertEqual(plan["checks"]["DOR-TASK-05"]["result"], "UNKNOWN")

    def gh(self, plan=None):
        names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
        route = p.routing_line(self.context, names)
        gh = SimpleNamespace(
            evidence_text=Mock(return_value=p.encode(plan or self.plan))
        )
        gh._get = Mock(
            side_effect=lambda route_: {"status": "ahead"}
            if "/compare/" in route_
            else source_tree(self.policy)
            if "/git/trees/" in route_
            else {"content": base64.b64encode(route.encode()).decode()}
        )
        return gh

    def test_fresh_recompute_binds_record_to_actual_current_sha(self):
        gh = self.gh()
        record = p.verified_record(t, gh, "WP-SIM-001", "c" * 40, self.policy)
        self.assertEqual(record["head_sha"], "c" * 40)
        t.criteria(
            SimpleNamespace(artifact=Mock()), record, list(record["checks"]), "c" * 40
        )
        self.assertTrue(record["_derived"])

    def test_forged_pass_and_product_result_rejected(self):
        for field, value in [
            ("test_results", "PASS"),
            ("accountable_owner", "Asrın Dündar"),
            ("planned_acceptance", ["fake implementation"]),
        ]:
            bad = deepcopy(self.plan)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(t.Denied):
                p.verified_record(t, self.gh(bad), "WP-SIM-001", SHA, self.policy)

    def test_changed_canonical_source_rejected(self):
        self.context["work_package"]["purpose"] = "changed"
        with self.assertRaises(t.Denied):
            p.verified_record(t, self.gh(), "WP-SIM-001", SHA, self.policy)

    def test_nonancestor_source_rejected(self):
        gh = self.gh()
        gh._get = Mock(
            side_effect=lambda route: {"status": "diverged"}
            if "/compare/" in route
            else source_tree(self.policy)
        )
        with self.assertRaises(t.Denied):
            p.verified_record(t, gh, "WP-SIM-001", SHA, self.policy)

    def test_idempotent_existing_artifact_creates_no_pr(self):
        writer = SimpleNamespace(
            gh=SimpleNamespace(
                main_sha=lambda: SHA, evidence_text=lambda *_: p.encode(self.plan)
            )
        )
        writer.call = Mock(
            return_value={
                "truncated": False,
                "tree": [{"path": p.path_for("WP-SIM-001")}],
            }
        )
        result = c.prepare_pr(t, p, writer, candidate(), self.plan, self.policy, Mock())
        self.assertEqual(result["state"], "ALREADY_PRESENT")
        self.assertEqual([x.args[0] for x in writer.call.call_args_list], ["GET"])

    def test_existing_closed_pr_not_recreated(self):
        writer = SimpleNamespace(gh=SimpleNamespace(main_sha=lambda: SHA))
        writer.call = Mock(
            side_effect=[{"truncated": False, "tree": []}, [], [{"number": 31}]]
        )
        result = c.prepare_pr(t, p, writer, candidate(), self.plan, self.policy, Mock())
        self.assertEqual(result["reason"], "PREVIOUS_PREPARATION_CLOSED_NO_BLIND_RETRY")
        self.assertTrue(all(x.args[0] == "GET" for x in writer.call.call_args_list))

    def test_existing_active_pr_failed_ci_has_no_write_or_duplicate(self):
        branch = "wp/WP-SIM-001-auto-prepare-" + self.plan["input_digest"][:12]
        pr = {
            "number": 32,
            "state": "open",
            "head": {"ref": branch, "sha": "c" * 40},
            "base": {"ref": "main"},
            "user": {"login": "Asperant"},
            "draft": False,
        }
        names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
        line = p.routing_line(self.context, names)

        def respond(method, route):
            if "/compare/" in route:
                return {"status": "identical", "behind_by": 0}
            if "/git/trees/" in route:
                return {"truncated": False, "tree": []}
            if "/files?" in route:
                return [
                    {"filename": p.path_for("WP-SIM-001")},
                    {"filename": ".github/CODEOWNERS"},
                ]
            if "CODEOWNERS" in route:
                text = "# original\n" + (line + "\n" if "c" * 40 in route else "")
                return {"content": base64.b64encode(text.encode()).decode()}
            return [pr] if "state=open" in route else pr

        gh = SimpleNamespace(
            main_sha=lambda: SHA,
            evidence_text=lambda *_: p.encode(self.plan),
            cache={},
            _get=Mock(return_value=source_tree(self.policy)),
        )
        writer = SimpleNamespace(gh=gh, call=Mock(side_effect=respond))
        with patch.object(t, "ci", side_effect=t.Denied("CI_NOT_GREEN")):
            result = c.prepare_pr(
                t, p, writer, candidate(), self.plan, self.policy, Mock()
            )
        self.assertEqual(result["state"], "IN_PROGRESS")
        self.assertTrue(all(x.args[0] == "GET" for x in writer.call.call_args_list))

    def supersession_writer(self, *, routed=True):
        old = deepcopy(self.plan)
        old["source_sha"] = "b" * 40
        old["input_digest"] = "d" * 64
        self.old_preparation = old
        self.pr_preparation = deepcopy(self.plan)
        self.pr_preparation["source_sha"] = "e" * 40
        self.prs = [
            {
                "number": 45,
                "state": "open",
                "head": {
                    "ref": "wp/WP-SIM-001-auto-prepare-"
                    + self.plan["input_digest"][:12],
                    "sha": "c" * 40,
                },
                "base": {"ref": "main"},
                "user": {"login": "Asperant"},
                "draft": False,
                "mergeable": True,
                "mergeable_state": "clean",
            }
        ]
        names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
        line = p.routing_line(self.context, names)
        self.main_route = "# original\n" + (line + "\n" if routed else "")
        self.head_route = self.main_route if routed else self.main_route + line + "\n"
        self.pr_files = [{"filename": p.path_for("WP-SIM-001")}]
        if not routed:
            self.pr_files.append({"filename": ".github/CODEOWNERS"})
        self.source_status = "ahead"

        def respond(method, route, body=None):
            if method == "PUT" and route.endswith("/merge"):
                return {"merged": True, "sha": "f" * 40}
            self.assertEqual(method, "GET")
            if "/git/trees/" in route:
                return {
                    "truncated": False,
                    "tree": [{"path": p.path_for("WP-SIM-001")}],
                }
            if "state=open" in route:
                return self.prs
            if "/files?" in route:
                return self.pr_files
            if "CODEOWNERS" in route:
                text = self.main_route if route.endswith(SHA) else self.head_route
                return {"content": base64.encodebytes(text.encode()).decode()}
            if "/compare/" in route:
                return {"status": self.source_status, "behind_by": 0}
            return self.prs[0]

        gh = SimpleNamespace(
            main_sha=lambda: SHA,
            evidence_text=lambda _path, sha: p.encode(
                self.old_preparation if sha == SHA else self.pr_preparation
            ),
            cache={},
            _get=Mock(return_value=source_tree(self.policy)),
        )
        return SimpleNamespace(gh=gh, call=Mock(side_effect=respond))

    def supersede(self, writer):
        with patch.object(t, "ci"):
            return c.prepare_pr(
                t, p, writer, candidate(), self.plan, self.policy, Mock()
            )

    def assert_rejected_without_write(self, writer, reason):
        with self.assertRaises(t.Denied) as error:
            self.supersede(writer)
        self.assertEqual(error.exception.code, reason)
        self.assertTrue(all(x.args[0] == "GET" for x in writer.call.call_args_list))

    def test_stale_merged_artifact_current_pr_is_superseded_without_duplicate_route(
        self,
    ):
        writer = self.supersession_writer()
        result = self.supersede(writer)
        self.assertEqual(result["state"], "MERGED")
        self.assertEqual(result["pr"], 45)
        writes = [x for x in writer.call.call_args_list if x.args[0] != "GET"]
        self.assertEqual(len(writes), 1)
        self.assertTrue(writes[0].args[1].endswith("/pulls/45/merge"))

    def test_supersession_requires_actual_routing_change_when_missing(self):
        writer = self.supersession_writer(routed=False)
        self.pr_files = [{"filename": p.path_for("WP-SIM-001")}]
        self.head_route = self.main_route
        self.assert_rejected_without_write(writer, "PREPARATION_PR_DIFF_INVALID")

    def test_supersession_correct_routing_append_is_valid(self):
        self.assertEqual(
            self.supersede(self.supersession_writer(routed=False))["state"], "MERGED"
        )

    def test_supersession_wrong_routing_and_shadowed_routing_rejected(self):
        for suffix in ["/evidence/WP-SIM-001/ @wrong\n", "* @wrong\n"]:
            writer = self.supersession_writer(routed=False)
            self.head_route += suffix
            with self.subTest(suffix=suffix):
                self.assert_rejected_without_write(
                    writer, "PREPARATION_ROUTING_DIFF_INVALID"
                )

    def test_semantic_preparation_changes_still_require_review(self):
        for key, value in [
            ("start_slice", "broadened scope"),
            ("accountable_owner", "wrong"),
            ("checks", {}),
        ]:
            writer = self.supersession_writer()
            self.old_preparation[key] = value
            result = self.supersede(writer)
            with self.subTest(key=key):
                self.assertEqual(
                    result["reason"],
                    "EXISTING_PREPARATION_INPUT_CHANGED_REVIEW_REQUIRED",
                )
                self.assertTrue(
                    all(x.args[0] == "GET" for x in writer.call.call_args_list)
                )

    def test_supersession_multiple_prs_rejected(self):
        writer = self.supersession_writer()
        self.prs.append(deepcopy(self.prs[0]))
        self.assert_rejected_without_write(writer, "DUPLICATE_PREPARATION_PRS")

    def test_supersession_stale_input_pr_rejected(self):
        writer = self.supersession_writer()
        self.pr_preparation["input_digest"] = "d" * 64
        self.assert_rejected_without_write(writer, "PREPARATION_PR_CONTENT_CHANGED")

    def test_supersession_stale_canonical_source_rejected(self):
        writer = self.supersession_writer()
        tree = source_tree(self.policy)
        tree["tree"][0]["sha"] = "f" * 40
        writer.gh._get.return_value = tree
        self.assert_rejected_without_write(
            writer, "REMOTE_CANONICAL_SOURCE_UNAVAILABLE_POLICY_REFRESH_REQUIRED"
        )

    def test_supersession_nonancestor_source_rejected(self):
        writer = self.supersession_writer()
        self.source_status = "diverged"
        self.assert_rejected_without_write(writer, "PREPARATION_SOURCE_NOT_ANCESTOR")

    def test_supersession_product_files_rejected(self):
        writer = self.supersession_writer()
        self.pr_files.append({"filename": "services/core/product.py"})
        self.assert_rejected_without_write(writer, "PREPARATION_PR_DIFF_INVALID")

    def test_supersession_broadened_pr_and_wrong_wp_rejected(self):
        for key, value in [
            ("start_slice", "implementation"),
            ("wp_id", "WP-OTHER-001"),
            ("checks", {}),
        ]:
            writer = self.supersession_writer()
            self.pr_preparation[key] = value
            with self.subTest(key=key):
                self.assert_rejected_without_write(
                    writer, "PREPARATION_PR_CONTENT_CHANGED"
                )

    def test_supersession_malformed_merged_evidence_requires_review(self):
        writer = self.supersession_writer()
        self.old_preparation["input_digest"] = "not-a-digest"
        self.assertEqual(
            self.supersede(writer)["reason"],
            "EXISTING_PREPARATION_INPUT_CHANGED_REVIEW_REQUIRED",
        )

    def test_supersession_malformed_pr_json_rejected_without_write(self):
        writer = self.supersession_writer()
        original = writer.gh.evidence_text
        for bad in [
            "{invalid",
            p.encode(self.pr_preparation).replace(
                '"wp_id":', '"wp_id": "duplicate", "wp_id":'
            ),
        ]:
            writer.gh.evidence_text = (
                lambda path, sha, bad=bad: original(path, sha) if sha == SHA else bad
            )
            with self.subTest(bad=bad), self.assertRaises((ValueError, t.q.Unsafe)):
                self.supersede(writer)
            self.assertTrue(all(x.args[0] == "GET" for x in writer.call.call_args_list))

    def test_supersession_stale_branch_and_closed_pr_rejected(self):
        writer = self.supersession_writer()
        self.prs[0]["head"]["ref"] += "-old"
        self.assert_rejected_without_write(
            writer, "EXISTING_PREPARATION_INPUT_CHANGED_REVIEW_REQUIRED"
        )
        writer = self.supersession_writer()
        self.prs[0]["state"] = "closed"
        self.assert_rejected_without_write(writer, "PREPARATION_PR_SCOPE_INVALID")

    def test_supersession_missing_pr_is_read_only(self):
        writer = self.supersession_writer()
        self.prs.clear()
        result = self.supersede(writer)
        self.assertEqual(result["reason"], "PREPARATION_SUPERSESSION_PR_REQUIRED")
        self.assertTrue(all(x.args[0] == "GET" for x in writer.call.call_args_list))

    def test_batuhan_normal_auto_next_uses_transition_boundary(self):
        wp, policy, plane, gh, envelope = fixture(
            profile="batuhan", source="BACKLOG", target="READY"
        )
        owner = "batuhan"
        plane.item["assignees"] = [t.q.PEOPLE[owner][1]]
        policy["contexts"][wp]["work_package"]["primary_owner"]["canonical_name"] = (
            t.q.PEOPLE[owner][0]
        )
        # Exercise the actual resolver/execute/revalidation; evidence adapter stands in for merged preparation.
        from test_auto_next import resolver

        policy["execution_project"] = {
            "cards": {
                wp: {
                    "owner": t.q.PEOPLE[owner][0],
                    "scheduled": True,
                    "nodes": [],
                    "edges": [],
                }
            },
            "source_manifest": policy["source_manifest"],
            "valid": True,
        }
        policy["execution_preferences"] = {"sequences": {t.q.PEOPLE[owner][0]: [wp]}}
        gh.main_sha = lambda: SHA
        gh.__dict__["cache"] = {}
        evidence = {
            "complete": True,
            "source_manifest": policy["source_manifest"],
            "candidates": {
                wp: {
                    "result": "PASS",
                    "dor": "PASS",
                    "evidence_refs": ["comment:2"],
                    "dependencies": {},
                }
            },
        }
        with (
            patch.object(resolver, "validate_preferences", return_value=[]),
            patch.object(auto, "resolver", resolver),
            patch.object(auto, "discover", return_value=[]),
            patch.object(
                auto, "candidate_evidence", return_value=(evidence, {wp: envelope})
            ),
            patch.object(t, "verify_policy_sources"),
            patch.object(t, "evaluate", return_value=None),
        ):
            result = auto.advance_owner(
                t, owner, policy, lambda: plane, lambda _: gh, lambda *_: None, SECRET
            )
        self.assertEqual(result["status"], "READY")
        self.assertEqual(plane.patches, [{"state": "READY"}])

    def test_generated_record_through_actual_transition_evaluator(self):
        import sys

        wp, policy, plane, _, _ = fixture(
            profile="batuhan", source="BACKLOG", target="READY"
        )
        context = deepcopy(self.context)
        context["work_package"]["id"] = wp
        context["work_package"]["dor_refs"] = list(self.plan["checks"])[12:]
        context["cycle_ids"] = ["S2"]
        policy["contexts"][wp] = context
        policy["preparation_schema"] = p.SCHEMA
        policy["source_git_blobs"] = {
            name: "b" * 40 for name in policy["source_manifest"]
        }
        plan = p.derive(context, policy, SHA)
        names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
        line = p.routing_line(context, names)
        gh = SimpleNamespace(
            main_sha=lambda: SHA,
            evidence_text=lambda *_: p.encode(plan),
            artifact=Mock(),
        )
        gh._get = Mock(
            side_effect=lambda route: {"status": "identical"}
            if "/compare/" in route
            else source_tree(policy)
            if "/git/trees/" in route
            else {"content": base64.b64encode(line.encode()).decode()}
        )
        original = t.importlib.util.spec_from_file_location

        def local_spec(name, path):
            return original(
                name,
                HERE / "preparation.py"
                if str(path).endswith("cap-preparation.py")
                else path,
            )

        with (
            patch.object(
                t.importlib.util, "spec_from_file_location", side_effect=local_spec
            ),
            patch.dict(sys.modules, {t.__name__: t}),
        ):
            result = t.execute(
                "batuhan",
                wp,
                "READY",
                {"reason": "Derived canonical preparation", "evidence_refs": []},
                policy,
                plane,
                gh,
                lambda *_: None,
                SECRET,
            )
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "READY"}])

    def test_later_stage_evidence_is_deferred_not_promoted_to_start_gate(self):
        self.context["dependency_edges"] = [
            {
                "id": "DEP-022",
                "semantics": {
                    "blocking_stage": "INTEGRATION",
                    "strength": "HARD",
                    "required_readiness": "COMPONENT_READY",
                },
                "precise_requirement": None,
                "unblock_evidence": "atomic mutation+outbox test on real PostgreSQL",
            }
        ]
        plan = p.derive(self.context, self.policy, SHA)
        self.assertEqual(plan["checks"]["DOR-TASK-04"]["result"], "PASS")
        self.assertEqual(plan["deferred_dependencies"][0]["readiness"], "NOT_CERTIFIED")
        self.assertNotIn("dependency_readiness", plan)

    def test_current_canonical_blobs_are_read_only_verified(self):
        gh = SimpleNamespace(_get=Mock(return_value=source_tree(self.policy)))
        p.verify_remote_sources(t, gh, SHA, self.policy)
        gh._get.assert_called_once()

    def test_remote_canonical_change_is_unavailable_not_pass(self):
        tree = source_tree(self.policy)
        tree["tree"][0]["sha"] = "c" * 40
        gh = SimpleNamespace(_get=Mock(return_value=tree))
        with self.assertRaises(t.Denied) as error:
            p.verify_remote_sources(t, gh, SHA, self.policy)
        self.assertIn("UNAVAILABLE_POLICY_REFRESH_REQUIRED", error.exception.code)

    def test_missing_source_projection_is_unavailable(self):
        self.policy.pop("source_git_blobs")
        with self.assertRaises(t.Denied):
            p.verify_remote_sources(t, SimpleNamespace(_get=Mock()), SHA, self.policy)

    def test_truncated_remote_source_tree_is_unavailable(self):
        gh = SimpleNamespace(_get=Mock(return_value={"truncated": True, "tree": []}))
        with self.assertRaises(t.Denied):
            p.verify_remote_sources(t, gh, SHA, self.policy)

    def test_verified_buffer_prevents_unnecessary_preparation_pr(self):
        health = {
            "health": "HEALTHY",
            "prepared_next": "WP-SCH-001",
            "current": {"wp_id": "WP-SIM-001"},
            "candidates": [candidate()],
        }
        adapter = SimpleNamespace(
            owner_health=Mock(return_value=health),
            advance_owner=Mock(return_value={"status": "CURRENT"}),
        )
        support = SimpleNamespace(
            Plane=Mock(return_value=object()),
            GitHub=Mock(),
            append_audit=Mock(),
            now=lambda: "timestamp",
        )
        engine = SimpleNamespace(
            derive=Mock(side_effect=AssertionError("buffer already verified"))
        )
        with (
            patch.object(c, "persist"),
            patch.object(c, "snapshot", return_value={}),
            patch.object(c, "Writer") as writer,
        ):
            result = c.run(adapter, support, engine, {}, "sentinel")
        engine.derive.assert_not_called()
        writer.assert_not_called()
        self.assertEqual(len(result["profiles"]), 4)
        self.assertEqual(result["production_diff"], {})

    def controller_run(self, states, health_for_asrin):
        """Run the real controller loop; only Asrin has candidates to prepare."""
        others = {"health": "HEALTHY", "prepared_next": "WP-OK-001", "candidates": []}

        def owner_health(_t, profile, *_args):
            return deepcopy(health_for_asrin if profile == "asrin" else others)

        adapter = SimpleNamespace(
            owner_health=Mock(side_effect=owner_health),
            advance_owner=Mock(return_value={"status": "NO_TASK"}),
            live_view=Mock(return_value={}),
        )
        support = SimpleNamespace(
            Plane=Mock(return_value=object()),
            GitHub=Mock(),
            append_audit=Mock(),
            now=lambda: "timestamp",
        )
        engine = SimpleNamespace(
            derive=Mock(return_value={"checks": {}}),
            classify=Mock(side_effect=lambda cand, _plan: states[cand["wp_id"]]),
        )
        with (
            tempfile.TemporaryDirectory() as state,
            patch.object(c, "STATE", Path(state)),
            patch.object(c, "persist"),
            patch.object(c, "snapshot", return_value={}),
            patch.object(c, "Writer"),
            patch.object(
                c,
                "prepare_pr",
                return_value={"state": "IN_PROGRESS", "wp_id": "WP-PREP-004"},
            ) as prepare,
        ):
            policy = {"contexts": {wp: {} for wp in states}}
            result = c.run(adapter, support, engine, policy, "sentinel")
        return result, engine, prepare, support

    def head_of_line(self):
        rows = [
            dict(
                candidate(),
                wp_id=f"WP-BLK-00{n}",
                status="WAITING_DEP",
                reason="HARD_START_BLOCKED",
                hard_start_blockers=[{"dependency_id": f"DEP-{n}"}],
            )
            for n in (1, 2, 3)
        ]
        rows += [
            dict(candidate(), wp_id="WP-PREP-004"),
            dict(candidate(), wp_id="WP-PREP-005"),
        ]
        health = {
            "health": "STALLED",
            "prepared_next": None,
            "current": None,
            "candidates": rows,
        }
        return rows, health

    def test_controller_scans_past_blocked_candidates_to_first_preparable(self):
        rows, health = self.head_of_line()
        states = {
            "WP-BLK-001": "WAITING_DEP",
            "WP-BLK-002": "REAL_WORK_REQUIRED",
            "WP-BLK-003": "UNAVAILABLE",
            "WP-PREP-004": "AUTO_PREPARABLE",
            "WP-PREP-005": "AUTO_PREPARABLE",
        }
        result, engine, prepare, support = self.controller_run(states, health)
        self.assertEqual(engine.derive.call_count, 4)  # stops after the first action
        prepare.assert_called_once()
        self.assertEqual(prepare.call_args.args[3]["wp_id"], "WP-PREP-004")
        actions = result["profiles"]["asrin"]["actions"]
        self.assertEqual(
            [(a["wp_id"], a["state"]) for a in actions],
            [
                ("WP-BLK-001", "WAITING_DEP"),
                ("WP-BLK-002", "REAL_WORK_REQUIRED"),
                ("WP-BLK-003", "UNAVAILABLE"),
                ("WP-PREP-004", "IN_PROGRESS"),
            ],
        )
        support.GitHub.assert_called_once_with("asrin")  # one client per profile

    def test_controller_with_no_preparable_candidate_changes_nothing(self):
        rows, health = self.head_of_line()
        states = {row["wp_id"]: "WAITING_DEP" for row in rows}
        result, engine, prepare, _ = self.controller_run(states, health)
        prepare.assert_not_called()
        self.assertEqual(engine.derive.call_count, len(rows))
        actions = result["profiles"]["asrin"]["actions"]
        self.assertEqual([a["wp_id"] for a in actions], [r["wp_id"] for r in rows])
        self.assertTrue(all(a["state"] == "WAITING_DEP" for a in actions))
        self.assertEqual(result["production_diff"], {})

    def test_controller_and_resolver_window_share_the_same_order(self):
        rows, health = self.head_of_line()
        states = {r["wp_id"]: "WAITING_DEP" for r in rows}
        states["WP-PREP-004"] = "AUTO_PREPARABLE"
        window, chosen = resolver.candidate_window(
            rows, lambda cand: states[cand["wp_id"]] == "AUTO_PREPARABLE"
        )
        _, engine, prepare, _ = self.controller_run(states, health)
        self.assertEqual(chosen, "WP-PREP-004")
        self.assertEqual(
            [r["wp_id"] for r in window],
            [r["wp_id"] for r in rows[:4]],
        )
        self.assertEqual(prepare.call_args.args[3]["wp_id"], chosen)

    def test_controller_uid_rejected_before_loading(self):
        with (
            patch.object(c.os, "geteuid", return_value=1001),
            patch.object(c.signal, "alarm"),
            patch.object(c, "load") as loader,
        ):
            self.assertEqual(c.main(), 2)
        loader.assert_not_called()

    def test_timer_bounded_and_health_read_only(self):
        self.assertIn(
            "OnUnitActiveSec=15min", (HERE / "cap-plane-prepare.timer").read_text()
        )
        self.assertIn(
            "TimeoutStartSec=750", (HERE / "cap-plane-prepare.service").read_text()
        )
        self.assertIn("signal.alarm(720)", (HERE / "prepare.py").read_text())
        self.assertNotIn("prepare_pr", (HERE / "health.py").read_text())


if __name__ == "__main__":
    unittest.main()
