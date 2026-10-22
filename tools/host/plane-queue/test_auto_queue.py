"""Pending-work and real-user scope regressions; no credentials/network."""

import importlib.util
import io
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("auto_queue_fixture", HERE / "queue.py")
assert spec is not None and spec.loader is not None
q: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)


class AutomaticQueueTests(unittest.TestCase):
    def test_pending_states_surface_current_and_never_backlog(self):
        for state in ("IN_REVIEW", "MERGE_READY", "MERGED", "VALIDATING"):
            with self.subTest(state=state):
                row = {
                    "wp_id": "WP-GOV-001",
                    "title": "Current",
                    "plane_state": state,
                    "blocked": False,
                    "cycle": "S1",
                    "_profile": "asrin",
                    "_id": "private",
                }
                result = q.select("asrin", {"WP-GOV-001": row})
                self.assertEqual(result["display_status"], "CURRENT")
                self.assertEqual(result["current_task"]["plane_state"], state)

    def test_no_task_explains_no_arbitrary_backlog(self):
        result = q.select("selman", {})
        self.assertEqual(result["display_status"], "NO_TASK")
        self.assertIn("never choose BACKLOG", result["reason"])

    def test_cross_user_uid_refused_before_credentials(self):
        with (
            patch.object(q.sys, "argv", ["helper", "asrin"]),
            patch.object(q.os, "geteuid", return_value=0),
            patch.dict(q.os.environ, {"SUDO_UID": "1002"}),
            patch.object(q.os.environ, "clear"),
            patch.object(q.pwd, "getpwnam", return_value=SimpleNamespace(pw_uid=1001)),
            patch.object(q.Path, "read_text") as read,
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(q.main(), 2)
        read.assert_not_called()
        self.assertNotIn("credential", output.getvalue())


if __name__ == "__main__":
    unittest.main()
