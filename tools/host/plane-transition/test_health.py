"""Health adapters and timer must never execute transitions or fabricate evidence."""

import io
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_auto_next import HERE, auto, load, resolver
from test_transition import fixture, t

h = load("health_fixture", HERE / "health.py")


class HealthTests(unittest.TestCase):
    def test_scan_calls_read_adapter_only_and_auth_failure_is_visible(self):
        adapter = SimpleNamespace(owner_health=Mock(side_effect=RuntimeError("secret")))
        result = h.scan(
            adapter, SimpleNamespace(GitHub=Mock()), {}, object(), ["selman"]
        )
        self.assertEqual(result["selman"]["health"], "UNAVAILABLE")
        self.assertNotIn("secret", str(result))
        self.assertEqual(h.report(result)["project_health"], "PROJECT_STALL_RISK")

    def test_read_only_hypothetical_ready_evaluation(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        other = dict(
            plane.item,
            id="active",
            external_id="WP-ACTIVE-001",
            name="[WP-ACTIVE-001] Current",
            state="READY",
        )
        plane.items.append(other)
        before = deepcopy(plane.items)
        policy["execution_preferences"] = {"sequences": {t.q.PEOPLE["asrin"][0]: [wp]}}
        gh.main_sha = lambda: "a" * 40
        comments = [{"id": 1, "body": wp + " DOR-TASK-01 " + "a" * 40}]
        live = {"items": {wp: {"state": "BACKLOG", "blocked": False}}}
        with (
            patch.object(auto, "resolver", resolver),
            patch.object(t, "records", return_value=[]),
            patch.object(t, "confirmation", return_value={}),
            patch.object(t, "criteria"),
            patch.object(t, "evaluate") as evaluate,
            patch.object(t, "execute") as execute,
        ):
            auto.candidate_evidence(
                t, plane, policy, "asrin", gh, comments, live, future=True
            )
            projected = evaluate.call_args.args[5]
            self.assertEqual(projected.items[-1]["state"], "DONE")
            execute.assert_not_called()
        self.assertEqual(plane.items, before)
        self.assertEqual(plane.patches, [])

    def test_uid_rejected_before_any_read(self):
        with (
            patch.object(h.sys, "argv", ["health", "asrin", "--json"]),
            patch.object(h.os, "geteuid", return_value=0),
            patch.dict(h.os.environ, {"SUDO_UID": "2000"}),
            patch.object(h.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=1001)),
            patch.object(h.signal, "alarm"),
            patch.object(h, "load_auto") as load_auto,
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            self.assertEqual(h.main(), 2)
            load_auto.assert_not_called()

    def test_timer_only_calls_read_only_health(self):
        snapshot = (HERE / "health_snapshot.py").read_text()
        self.assertIn(
            '["/usr/local/bin/cap-plane-health", "--all", "--json"]', snapshot
        )
        for forbidden in (
            "cap-plane-advance",
            "cap-plane-transition",
            "git ",
            "PATCH",
            "credential.json",
        ):
            self.assertNotIn(forbidden, snapshot)
        self.assertIn("timeout=210", snapshot)
        self.assertIn(
            "OnUnitActiveSec=15min", (HERE / "cap-plane-health.timer").read_text()
        )
        self.assertIn(
            "TimeoutStartSec=240", (HERE / "cap-plane-health.service").read_text()
        )

    def test_no_evidence_writer_in_health_path(self):
        import ast

        for filename, names in [
            ("health.py", {"main", "scan"}),
            (
                "auto_next.py",
                {"owner_health", "candidate_evidence", "after_transition"},
            ),
        ]:
            tree = ast.parse((HERE / filename).read_text())
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name in names:
                    calls = [
                        c.func.attr
                        for c in ast.walk(node)
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                    ]
                    self.assertTrue(
                        set(calls).isdisjoint(
                            {"execute", "patch", "append_audit", "write_text"}
                        )
                    )


if __name__ == "__main__":
    unittest.main()
