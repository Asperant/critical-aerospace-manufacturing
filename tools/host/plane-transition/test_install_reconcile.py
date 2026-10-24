"""Offline installer checks: no root write, no service start, no real sudoers edit."""

import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import yaml

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
    r"\1 WP-[A-Z0-9]+-[0-9]{3} (MERGED|VALIDATING)"
)


def policy_block(cases):
    return {"lifecycle_reconciliation": {"schema_version": "v1", "cases": cases}}


def case(profile="batuhan", wp="WP-TEST-003", targets=("MERGED", "VALIDATING")):
    return {"profile": profile, "wp_id": wp, "targets": list(targets)}


class GrantTests(unittest.TestCase):
    def test_grants_are_exact_argv_lines_for_each_allow_listed_target(self):
        lines = ins.reconcile_grants(policy_block([case()]))
        self.assertEqual(lines[0].startswith("#"), True)
        self.assertEqual(
            lines[1:],
            [
                "batuhan ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I "
                "/usr/local/libexec/cap-plane-reconcile.py batuhan WP-TEST-003 MERGED",
                "batuhan ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I "
                "/usr/local/libexec/cap-plane-reconcile.py batuhan WP-TEST-003 VALIDATING",
            ],
        )

    def test_every_grant_matches_the_strict_shape_and_has_no_wildcards(self):
        lines = ins.reconcile_grants(
            policy_block([case(), case("asrin", "WP-TEST-001", ["MERGED"])])
        )
        for line in lines[1:]:
            with self.subTest(line=line):
                self.assertRegex(line, GRANT)
                self.assertFalse(set("*?[]|;&$`\\") & set(line))
                self.assertFalse(
                    line.startswith("ailab")
                )  # no legacy shared-ailab grant
        self.assertEqual(len(lines) - 1, 3)

    def test_the_repository_allow_list_yields_exactly_the_approved_grants(self):
        block = yaml.safe_load(
            (
                REPO_ROOT / "project_control" / "lifecycle_reconciliation.yaml"
            ).read_text()
        )
        lines = ins.reconcile_grants({"lifecycle_reconciliation": block})[1:]
        self.assertEqual(
            lines,
            [
                "batuhan ALL=(root) NOPASSWD: NOSETENV: /usr/bin/python3 -I "
                f"/usr/local/libexec/cap-plane-reconcile.py batuhan WP-SIM-001 {target}"
                for target in ("MERGED", "VALIDATING")
            ],
        )

    def test_invalid_identities_or_targets_never_become_privileged_text(self):
        for bad in (
            case(profile="root"),
            case(profile="batuhan ALL"),
            case(wp="WP-X"),
            case(wp="WP-TEST-003; rm"),
            case(targets=["DONE"]),
            case(targets=["MERGED", "VALIDATING\n"]),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                ins.reconcile_grants(policy_block([bad]))

    def test_the_launcher_command_line_matches_the_granted_argv(self):
        text = LAUNCHER.read_text()
        match = re.search(r"exec /usr/bin/sudo -n (.+)$", text, re.M)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(
            match[1],
            '/usr/bin/python3 -I /usr/local/libexec/cap-plane-reconcile.py "$CAP_PROFILE" "$1" "$2"',
        )
        granted = ins.reconcile_grants(policy_block([case()]))[1].split("NOSETENV: ")[1]
        self.assertTrue(
            granted.startswith(
                "/usr/bin/python3 -I /usr/local/libexec/cap-plane-reconcile.py "
            )
        )


class MappingTests(unittest.TestCase):
    def test_reconcile_artifacts_are_deployed_from_reviewed_sources_only(self):
        mapping = ins.deployment_mapping()
        self.assertEqual(
            mapping["/usr/local/libexec/cap-plane-reconcile.py"],
            "tools/host/plane-transition/reconcile.py",
        )
        self.assertEqual(
            mapping["/usr/local/bin/cap-plane-reconcile"],
            "tools/host/plane-transition/cap-plane-reconcile",
        )
        for dest, source in mapping.items():
            with self.subTest(dest=dest):
                self.assertTrue(
                    dest.startswith(("/usr/local/", "/etc/systemd/system/"))
                )
                self.assertTrue((REPO_ROOT / source).is_file(), source)
                self.assertNotIn("..", source.split("/"))

    def test_existing_deployments_are_preserved(self):
        mapping = ins.deployment_mapping()
        for dest in (
            "/usr/local/libexec/cap-plane-transition",
            "/usr/local/libexec/cap-plane-queue",
            "/usr/local/libexec/cap-auto-next.py",
            "/usr/local/libexec/cap-plane-prepare.py",
            "/etc/systemd/system/cap-plane-health.timer",
        ):
            self.assertIn(dest, mapping)

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

    def test_installer_keeps_the_modern_source_and_account_guards(self):
        text = (HERE / "install_auto_next.py").read_text()
        self.assertIn('SOURCE = Path("/srv/ailab/project")', text)
        self.assertNotIn("/srv/ailab/workspaces", text)  # never a developer checkout
        self.assertNotIn("ailab ALL=", text)  # no legacy shared-ailab grant
        for required in (
            "Clean merged reference source required",
            "Stale generated source policy",
            "Symlink deployment target",
            "Installed source hash mismatch",
            "Installed policy implementation mismatch",
            "rollback.py",
        ):
            self.assertIn(required, text)
        self.assertIn('"/usr/sbin/visudo", "-cf", str(reconcile_draft)', text)
        self.assertEqual(text.count("def main"), 1)

    def test_building_the_installer_never_touches_the_host(self):
        # The pure helpers must not run commands or open files for writing.
        def forbidden(*args, **kwargs):
            raise AssertionError("installer helper touched the host")

        with (
            mock.patch.object(ins.subprocess, "run", forbidden),
            mock.patch.object(ins.os, "open", forbidden),
            mock.patch.object(ins.shutil, "copy2", forbidden),
        ):
            ins.reconcile_grants(policy_block([case()]))
            ins.restore_targets(ins.deployment_mapping())


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

    def test_launcher_accepts_only_the_two_reconciliation_targets(self):
        block = LAUNCHER.read_text().split('case "$2" in')[1].split("esac")[0]
        self.assertIn("MERGED|VALIDATING) ;;", block)
        for other in ("DONE", "READY", "IN_PROGRESS", "BLOCKED", "CANCELED"):
            self.assertNotIn(other, block.replace("INVALID_TARGET_STATE", ""))


if __name__ == "__main__":
    unittest.main()
