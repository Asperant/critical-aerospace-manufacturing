"""Bounded preparation safety and actual transition integration; offline fixtures."""

import base64
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_auto_next import HERE, auto, load
from test_transition import SECRET, fixture, t

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
        gh._get = Mock(return_value={"status": "diverged"})
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
            "head": {"ref": branch, "sha": "c" * 40},
            "base": {"ref": "main"},
            "user": {"login": "Asperant"},
            "draft": False,
        }
        names = {v[0]: t.GITHUB[k] for k, v in t.q.PEOPLE.items()}
        line = p.routing_line(self.context, names)

        def respond(method, route):
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
            main_sha=lambda: SHA, evidence_text=lambda *_: p.encode(self.plan), cache={}
        )
        writer = SimpleNamespace(gh=gh, call=Mock(side_effect=respond))
        with patch.object(t, "ci", side_effect=t.Denied("CI_NOT_GREEN")):
            result = c.prepare_pr(
                t, p, writer, candidate(), self.plan, self.policy, Mock()
            )
        self.assertEqual(result["state"], "IN_PROGRESS")
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
