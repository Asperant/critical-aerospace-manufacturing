"""Offline entry-point guards of the reconcile helper; no service or credential is used."""

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]


def load(name, path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


t = load("transition_for_reconcile_main", HERE / "transition.py")
t.q = load("queue_for_reconcile_main", HERE.parent / "plane-queue" / "queue.py")
r = load("reconcile_for_main", HERE / "reconcile.py")
r.t = t

KEY = "sentinel-plane-secret-do-not-print"
WP = "WP-TEST-003"
HEAD, MERGE, PARENT = "1" * 40, "2" * 40, "3" * 40


class Stdin:
    def __init__(self, payload, tty=False):
        self.buffer = io.BytesIO(payload)
        self._tty = tty

    def isatty(self):
        return self._tty


def policy_for(reconcile_hash):
    names = dict(t.q.PEOPLE)
    case = {
        "case_id": "RECON-TEST-PR52",
        "profile": "batuhan",
        "wp_id": WP,
        "pr": 52,
        "pr_head_sha": HEAD,
        "merge_sha": MERGE,
        "parents": [PARENT, HEAD],
        "changed_files": 3,
        "scope_prefixes": ["services/sim/"],
        "targets": ["MERGED"],
        "validating_runs": [],
        "require_successful_runs": True,
        "approvals": {
            "scope_answer": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "control_id_exception": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "plan_sha256": "c" * 64,
            "plan_approval_turn": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        },
        "change_record": "CHG-031",
    }
    return {
        "contexts": {
            WP: {
                "work_package": {
                    "id": WP,
                    "primary_owner": {"canonical_name": names["batuhan"][0]},
                }
            }
        },
        "review_policy": json.loads(
            (REPO_ROOT / "09_change" / "development_review_policy.json").read_text()
        ),
        "policy_digest": "fixture",
        "implementation_sha256": {"reconcile": reconcile_hash},
        "source_manifest": {},
        "lifecycle_reconciliation": {
            "schema_version": r.POLICY_SCHEMA,
            "cases": [case],
        },
    }


class MainGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        own_hash = hashlib.sha256((HERE / "reconcile.py").read_bytes()).hexdigest()
        self.write(policy_for(own_hash))
        (self.root / "credential.json").write_text(json.dumps({"api_key": KEY}))
        self.plane = mock.Mock(
            side_effect=AssertionError("Plane must not be constructed")
        )
        self.github = mock.Mock(
            side_effect=AssertionError("GitHub must not be constructed")
        )
        self.auto = mock.Mock()

    def write(self, policy):
        (self.root / "transition-policy.json").write_text(json.dumps(policy))

    def invoke(self, argv, stdin=None, euid=0):
        payload = json.dumps(
            {"reason": "Reconcile observed merge facts", "evidence_refs": ["pr:52"]}
        ).encode()
        stdin = stdin or Stdin(payload)
        out = io.StringIO()
        patches = (
            mock.patch.object(sys, "argv", ["reconcile.py", *argv]),
            mock.patch.object(sys, "stdin", stdin),
            mock.patch.object(r.os, "geteuid", return_value=euid),
            mock.patch.object(t, "ROOT", self.root),
            mock.patch.object(t, "verify_policy_sources"),
            mock.patch.object(t, "auto_next_support", return_value=self.auto),
            mock.patch.object(t, "Plane", self.plane),
            mock.patch.object(t, "GitHub", self.github),
            mock.patch.dict(r.os.environ, {"SUDO_UID": "1000"}),
            contextlib.redirect_stdout(out),
        )
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            status = r.main()
        printed = out.getvalue()
        self.assertNotIn(KEY, printed)
        return status, json.loads(printed)

    def assertDenied(self, argv, code, **kwargs):
        status, result = self.invoke(argv, **kwargs)
        self.assertEqual(status, 2)
        self.assertEqual(result, {"result": "DENIED", "reason_code": code})
        self.plane.assert_not_called()
        self.github.assert_not_called()

    def test_requires_root_and_exactly_three_arguments(self):
        self.assertDenied(["batuhan", WP, "MERGED"], "INVALID_INVOCATION", euid=1000)
        self.assertDenied(["batuhan", WP], "INVALID_INVOCATION")
        self.assertDenied(["batuhan", WP, "MERGED", "x"], "INVALID_INVOCATION")

    def test_the_credential_is_never_accepted_in_input_or_echoed(self):
        raw = json.dumps(
            {"reason": f"token {KEY}", "evidence_refs": ["pr:52"]}
        ).encode()
        self.assertDenied(
            ["batuhan", WP, "MERGED"], "SECRET_IN_INPUT", stdin=Stdin(raw)
        )

    def test_a_helper_that_differs_from_the_policy_is_refused(self):
        self.write(policy_for("0" * 64))
        self.assertDenied(["batuhan", WP, "MERGED"], "HELPER_POLICY_REFRESH_REQUIRED")
        policy = policy_for(
            hashlib.sha256((HERE / "reconcile.py").read_bytes()).hexdigest()
        )
        del policy["implementation_sha256"]["reconcile"]
        self.write(policy)
        self.assertDenied(["batuhan", WP, "MERGED"], "HELPER_POLICY_REFRESH_REQUIRED")

    def test_an_unlisted_request_is_denied_before_any_external_lookup(self):
        self.assertDenied(
            ["batuhan", WP, "VALIDATING"], "RECONCILIATION_NOT_AUTHORIZED"
        )
        policy = policy_for(
            hashlib.sha256((HERE / "reconcile.py").read_bytes()).hexdigest()
        )
        del policy["lifecycle_reconciliation"]
        self.write(policy)
        self.assertDenied(["batuhan", WP, "MERGED"], "RECONCILIATION_POLICY_INVALID")


if __name__ == "__main__":
    unittest.main()
