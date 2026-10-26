"""Offline installer checks: no root write, no service start, no real sudoers edit."""

import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "install_auto_next_under_test", HERE / "install_auto_next.py"
)
assert spec is not None and spec.loader is not None
ins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ins)

LAUNCHER = HERE / "cap-plane-reconcile"
GRANT = re.compile(
    r"(asrin|selman|batuhan|yavuz) ALL=\(root\) NOPASSWD: NOSETENV: "
    r"/usr/bin/python3 -I /usr/local/libexec/cap-plane-reconcile\.py "
    r"\1$"
)


def policy_block(targets=("MERGED", "VALIDATING")):
    return {
        "lifecycle_reconciliation": {
            "schema_version": "cap-lifecycle-reconciliation-v2",
            "targets": list(targets),
        }
    }


class GrantTests(unittest.TestCase):
    def test_grants_are_profile_scoped_generic_lines_for_each_target(self):
        lines = ins.reconcile_grants(policy_block())
        self.assertEqual(lines[0].startswith("#"), True)
        self.assertEqual(len(lines[1:]), 4)
        self.assertTrue(all("WP-*" not in line for line in lines[1:]))
        self.assertTrue(all("WP-TWIN-001" not in line for line in lines[1:]))

    def test_invalid_identities_or_targets_never_become_privileged_text(self):
        for bad in (("DONE",), ("MERGED", "VALIDATING\n"), ("MERGED",)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ins.reconcile_grants(policy_block(bad))

    def test_the_launcher_command_line_matches_the_granted_argv(self):
        text = LAUNCHER.read_text()
        match = re.search(r"exec /usr/bin/sudo -n (.+)$", text, re.M)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(
            match[1],
            '/usr/bin/python3 -I /usr/local/libexec/cap-plane-reconcile.py "$CAP_PROFILE" "$1" "$2"',
        )
        granted = ins.reconcile_grants(policy_block())[1].split("NOSETENV: ")[1]
        self.assertTrue(
            granted.startswith(
                "/usr/bin/python3 -I /usr/local/libexec/cap-plane-reconcile.py "
            )
        )
        self.assertTrue(GRANT.fullmatch(ins.reconcile_grants(policy_block())[1]))


class MappingTests(unittest.TestCase):
    def test_policy_pinned_implementations_are_all_deployed_files(self):
        deployed = set(ins.deployment_mapping())
        self.assertIn("reconcile", ins.IMPLEMENTATION_TARGETS)
        for kind, dest in ins.IMPLEMENTATION_TARGETS.items():
            with self.subTest(kind=kind):
                self.assertIn(dest, deployed)

    def test_rollback_restores_the_new_files_and_grant(self):
        restore = ins.restore_targets(ins.deployment_mapping())
        self.assertIn("/etc/sudoers.d/cap-plane-reconcile", restore)
        self.assertIn("/usr/local/libexec/cap-plane-reconcile.py", restore)
        self.assertIn("/usr/local/bin/cap-plane-reconcile", restore)


class LauncherTests(unittest.TestCase):
    def run_launcher(self, args, profile="batuhan"):
        env = {"PATH": "/usr/bin:/bin"}
        if profile is not None:
            env["CAP_PROFILE"] = profile
        done = subprocess.run(
            ["/bin/sh", str(LAUNCHER), *args],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        return done.returncode, done.stdout.strip()

    def test_malformed_invocations_are_denied_before_sudo(self):
        cases = [
            ([], "batuhan", "EXPECTED_WP_ID_AND_TARGET_STATE"),
            (["WP-SIM-001"], "batuhan", "EXPECTED_WP_ID_AND_TARGET_STATE"),
            (
                ["WP-SIM-001", "MERGED", "x"],
                "batuhan",
                "EXPECTED_WP_ID_AND_TARGET_STATE",
            ),
            (["WP-SIM-001", "MERGED"], None, "INVALID_CAP_PROFILE"),
            (["WP-SIM-001", "MERGED"], "root", "INVALID_CAP_PROFILE"),
            (["not-a-wp", "MERGED"], "batuhan", "INVALID_CANONICAL_WP_ID"),
            (["WP-SIM-001", "DONE"], "batuhan", "INVALID_TARGET_STATE"),
            (["WP-SIM-001", "READY"], "batuhan", "INVALID_TARGET_STATE"),
            (["WP-SIM-001", "BLOCKED"], "batuhan", "INVALID_TARGET_STATE"),
            (["WP-SIM-001", "merged"], "batuhan", "INVALID_TARGET_STATE"),
        ]
        for args, profile, code in cases:
            with self.subTest(args=args, profile=profile):
                status, out = self.run_launcher(args, profile)
                self.assertEqual(status, 2)
                self.assertEqual(
                    json.loads(out), {"result": "DENIED", "reason_code": code}
                )


if __name__ == "__main__":
    unittest.main()
