"""AUTO_NEXT integration tests; fixture-only, never production mutations."""

import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from test_transition import SECRET, fixture, t

HERE = Path(__file__).resolve().parent


def load(name, path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auto = load("auto_fixture", HERE / "auto_next.py")
resolver = load(
    "resolver_fixture", HERE.parents[1] / "projectctl/src/projectctl/execution_queue.py"
)
auto.resolver = resolver


class AutoNextTests(unittest.TestCase):
    def test_actual_engine_ready_timeout_readback_and_idempotent(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        plane.response_lost = True
        logs = []
        result = t.execute(
            "asrin",
            wp,
            "READY",
            envelope,
            policy,
            plane,
            gh,
            lambda r, k: logs.append(deepcopy(r)),
            SECRET,
        )
        self.assertEqual(result["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "READY"}])
        self.assertEqual(
            t.execute(
                "asrin",
                wp,
                "READY",
                envelope,
                policy,
                plane,
                gh,
                lambda *_: None,
                SECRET,
            )["result"],
            "UNCHANGED",
        )
        self.assertEqual(len(plane.patches), 1)
        self.assertEqual([r["result"] for r in logs], ["INTENT", "VERIFIED"])

    def test_audit_failure_has_zero_patches(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        with self.assertRaises(OSError):
            t.execute(
                "asrin",
                wp,
                "READY",
                envelope,
                policy,
                plane,
                gh,
                Mock(side_effect=OSError()),
                SECRET,
            )
        self.assertEqual(plane.patches, [])

    def test_readback_failure_no_blind_retry(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        plane.fail_readback = True
        with self.assertRaises(t.Denied):
            t.execute(
                "asrin",
                wp,
                "READY",
                envelope,
                policy,
                plane,
                gh,
                lambda *_: None,
                SECRET,
            )
        self.assertEqual(len(plane.patches), 1)

    def test_final_inventory_recheck_stops_external_writer(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        with self.assertRaises(t.Denied):
            t.execute(
                "asrin",
                wp,
                "READY",
                envelope,
                policy,
                plane,
                gh,
                lambda *_: None,
                SECRET,
                prewrite=Mock(side_effect=t.Denied("CONCURRENT_CHANGE")),
            )
        self.assertEqual(plane.patches, [])

    def test_automatic_path_never_sets_done_or_other_fields(self):
        import ast

        tree = ast.parse((HERE / "auto_next.py").read_text())
        targets = [
            node.args[2].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
            and len(node.args) > 2
            and isinstance(node.args[2], ast.Constant)
        ]
        self.assertEqual(targets, ["READY"])
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        before = deepcopy(plane.item)
        t.execute(
            "asrin", wp, "READY", envelope, policy, plane, gh, lambda *_: None, SECRET
        )
        self.assertEqual(
            {k: v for k, v in plane.item.items() if k != "state"},
            {k: v for k, v in before.items() if k != "state"},
        )

    def test_uid_mismatch_denied(self):
        with (
            patch.object(auto.os, "environ", {"SUDO_UID": "1999"}),
            patch.object(
                auto.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=1001)
            ),
            self.assertRaises(PermissionError),
        ):
            auto.require_caller("asrin")

    def test_uid_correct_allowed(self):
        for uid in (0, 1001):
            with (
                self.subTest(uid=uid),
                patch.object(auto.os, "environ", {"SUDO_UID": str(uid)}),
                patch.object(
                    auto.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=1001)
                ),
            ):
                auto.require_caller("asrin")

    def test_per_user_github_drop(self):
        source = (HERE / "transition.py").read_text()
        self.assertIn("pwd.getpwnam(profile)", source)
        self.assertNotIn("pwd.getpwnam('ailab')", source)
        self.assertIn("user=self.uid, group=self.gid", source)

    def test_discovery_pagination_bounded(self):
        gh = SimpleNamespace(_get=Mock(return_value=[{}] * 100))
        with self.assertRaises(t.Denied):
            auto.discover(gh, t)
        self.assertEqual(gh._get.call_count, 20)

    def test_discovery_schema_denied(self):
        with self.assertRaises(t.Denied):
            auto.discover(SimpleNamespace(_get=lambda _: {}), t)

    def test_completed_owner_and_only_affected_consumers(self):
        project = {
            "cards": {
                "WP-A-001": {
                    "owner": resolver.OWNERS["asrin"],
                    "nodes": ["DN-A"],
                    "edges": [],
                },
                "WP-B-001": {
                    "owner": resolver.OWNERS["batuhan"],
                    "nodes": [],
                    "edges": [{"predecessor": {"node": "DN-A"}}],
                },
                "WP-Y-001": {
                    "owner": resolver.OWNERS["yavuz"],
                    "nodes": [],
                    "edges": [],
                },
            }
        }
        with patch.object(
            auto, "advance_owner", return_value={"status": "NO_TASK"}
        ) as advance:
            result = auto.after_done(
                t, "WP-A-001", {"execution_project": project}, None, None, None, SECRET
            )
        self.assertEqual(set(result), {"asrin", "batuhan"})
        self.assertEqual(advance.call_count, 2)

    def test_hook_only_after_verified_done(self):
        source = (HERE / "transition.py").read_text()
        self.assertIn("target=='DONE' and result.get('result')=='VERIFIED'", source)
        self.assertIn("auto.after_done", source)

    def test_global_lock_covers_decision_apply_and_done_hook(self):
        source = (HERE / "auto_next.py").read_text()
        source = source[source.index("def main():") :]
        self.assertLess(
            source.index("flock(lock"), source.index("results[profile] = advance_owner")
        )
        transition = (HERE / "transition.py").read_text()
        self.assertLess(
            transition.index("flock(lock"), transition.index("result=execute(")
        )

    def test_preview_no_execute(self):
        # Verify actual orchestration branch with injected resolver/live adapters.
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        policy.update(execution_project={}, execution_preferences={})
        fake = SimpleNamespace(
            compute_next_eligible=Mock(
                side_effect=[
                    {"status": "NO_TASK", "reasons": ["NO_VERIFIED_ELIGIBLE_WORK"]},
                    {"status": "PROPOSED_NEXT", "wp_id": wp},
                ]
            )
        )
        gh.main_sha = lambda: "a" * 40
        with (
            patch.object(auto, "resolver", fake),
            patch.object(auto, "live_view", return_value={}),
            patch.object(auto, "discover", return_value=[]),
            patch.object(auto, "candidate_evidence", return_value=({}, {wp: envelope})),
            patch.object(t, "execute") as execute,
        ):
            self.assertEqual(
                auto.advance_owner(
                    t,
                    "asrin",
                    policy,
                    lambda: plane,
                    lambda _: gh,
                    lambda *_: None,
                    SECRET,
                    preview=True,
                )["status"],
                "PROPOSED_NEXT",
            )
            execute.assert_not_called()

    def test_no_task_does_not_mutate(self):
        policy = {
            "execution_project": {},
            "execution_preferences": {},
            "source_manifest": {},
        }
        fake = SimpleNamespace(
            compute_next_eligible=lambda *_: {
                "status": "NO_TASK",
                "reasons": ["NO_REMAINING_SCHEDULED_WORK"],
            }
        )
        with (
            patch.object(auto, "resolver", fake),
            patch.object(auto, "live_view", return_value={}),
            patch.object(t, "execute") as execute,
        ):
            auto.advance_owner(t, "asrin", policy, lambda: None, None, None, SECRET)
            execute.assert_not_called()

    def test_two_concurrent_advances_create_only_one_ready(self):
        import fcntl
        import tempfile
        import threading

        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        policy.update(execution_project={}, execution_preferences={})
        gh.__dict__["cache"] = {}
        errors = []
        barrier = threading.Barrier(2)

        def compute(project, live, evidence, owner, planning):
            if live["state"] == "READY":
                return {"status": "READY", "wp_id": wp}
            if evidence.get("candidates"):
                return {"status": "PROPOSED_NEXT", "wp_id": wp}
            return {"status": "NO_TASK", "reasons": ["NO_VERIFIED_ELIGIBLE_WORK"]}

        def work(path):
            try:
                barrier.wait(timeout=5)
                with open(path, "r+") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    auto.advance_owner(
                        t,
                        "asrin",
                        policy,
                        lambda: plane,
                        lambda _: gh,
                        lambda *_: None,
                        SECRET,
                    )
            except Exception as exc:
                errors.append(type(exc).__name__)

        with (
            tempfile.NamedTemporaryFile() as lockfile,
            patch.object(
                auto, "resolver", SimpleNamespace(compute_next_eligible=compute)
            ),
            patch.object(
                auto, "live_view", side_effect=lambda *_: {"state": plane.item["state"]}
            ),
            patch.object(auto, "discover", return_value=[]),
            patch.object(
                auto,
                "candidate_evidence",
                return_value=({"candidates": {wp: {}}}, {wp: envelope}),
            ),
            patch.object(t, "verify_policy_sources"),
        ):
            threads = [
                threading.Thread(target=work, args=(lockfile.name,), daemon=True)
                for _ in range(2)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(plane.patches, [{"state": "READY"}])

    def test_external_inventory_change_rejects_stale_decision(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        policy.update(execution_project={}, execution_preferences={})
        gh.__dict__["cache"] = {}
        fake = SimpleNamespace(
            compute_next_eligible=Mock(
                side_effect=[
                    {"status": "NO_TASK", "reasons": ["NO_VERIFIED_ELIGIBLE_WORK"]},
                    {"status": "PROPOSED_NEXT", "wp_id": wp},
                ]
            )
        )
        with (
            patch.object(auto, "resolver", fake),
            patch.object(
                auto,
                "live_view",
                side_effect=[{"state": "BACKLOG"}, {"state": "READY"}],
            ),
            patch.object(auto, "discover", return_value=[]),
            patch.object(auto, "candidate_evidence", return_value=({}, {wp: envelope})),
            patch.object(t, "execute") as execute,
        ):
            result = auto.advance_owner(
                t, "asrin", policy, lambda: plane, lambda _: gh, lambda *_: None, SECRET
            )
        self.assertEqual(result["status"], "UNAVAILABLE")
        execute.assert_not_called()

    def test_required_aggregate_ci_never_bypassed(self):
        wp, policy, plane, gh, envelope = fixture(
            source="IN_PROGRESS", target="IN_REVIEW"
        )
        policy["required_aggregate_ci"] = ["ci-gate"]
        with self.assertRaises(t.Denied):
            t.execute(
                "asrin",
                wp,
                "IN_REVIEW",
                envelope,
                policy,
                plane,
                gh,
                lambda *_: None,
                SECRET,
            )
        self.assertEqual(plane.patches, [])

    def test_ambiguous_evidence_candidate_does_not_hide_later_candidate(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        second = "WP-TEST-999"
        policy["execution_preferences"] = {
            "sequences": {t.q.PEOPLE["asrin"][0]: [wp, second]}
        }
        policy["contexts"][second] = deepcopy(policy["contexts"][wp])
        live = {
            "items": {w: {"state": "BACKLOG", "blocked": False} for w in [wp, second]}
        }
        sha = gh.main_sha()
        comments = [{"id": n + 1, "body": f"{wp} {sha} DOR-TASK-01"} for n in range(17)]
        comments.append({"id": 99, "body": f"{second} {sha} DOR-TASK-01"})
        with (
            patch.object(t, "find", return_value=plane.item),
            patch.object(t, "evaluate"),
            patch.object(t, "records", return_value=[]),
        ):
            result, envelopes = auto.candidate_evidence(
                t, plane, policy, "asrin", gh, comments, live
            )
        self.assertEqual(
            result["candidates"][wp]["reason"], "AMBIGUOUS_EVIDENCE_DISCOVERY"
        )
        self.assertEqual(result["candidates"][second]["result"], "PASS")
        self.assertEqual(envelopes[second]["evidence_refs"], ["comment:99"])


if __name__ == "__main__":
    unittest.main()
