"""Focused tests for generic evidence-based lifecycle reconciliation."""

import importlib.util
import unittest
from pathlib import Path
from typing import Any

import yaml

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


t: Any = load("transition_generic", HERE / "transition.py")
t.q = load("queue_generic", HERE.parent / "plane-queue" / "queue.py")
r: Any = load("reconcile_generic", HERE / "reconcile.py")
r.t = t


class GenericPolicyTests(unittest.TestCase):
    def test_repository_policy_has_no_wp_authorization_cases(self):
        block = yaml.safe_load(
            (
                HERE.parents[2] / "project_control/lifecycle_reconciliation.yaml"
            ).read_text()
        )
        self.assertEqual(block["schema_version"], r.GENERIC_POLICY_SCHEMA)
        self.assertNotIn("cases", block)
        self.assertIn("legacy_recovery_cases", block)

    def test_validation_accepts_generic_policy_without_wp_allow_list(self):
        block = yaml.safe_load(
            (
                HERE.parents[2] / "project_control/lifecycle_reconciliation.yaml"
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

    def test_validating_requires_owner_comment_and_main_run_refs(self):
        valid = {"evidence_refs": ["pr:111", "comment:6418172571", "run:40336487460"]}
        self.assertEqual(
            r.generic_refs(valid, "VALIDATING"), (111, [40336487460], 6418172571)
        )
        for refs in (
            ["pr:111", "run:40336487460"],
            ["pr:111", "comment:6418172571"],
            [
                "pr:111",
                "comment:6418172571",
                "run:40336487460",
                "run:40336487457",
                "x:1",
            ],
        ):
            with self.subTest(refs=refs), self.assertRaises(t.Denied):
                r.generic_refs({"evidence_refs": refs}, "VALIDATING")

    def test_merged_target_rejects_run_evidence_and_requires_comment(self):
        with self.assertRaises(t.Denied):
            r.generic_refs(
                {"evidence_refs": ["pr:111", "comment:6418172571", "run:40336487460"]},
                "MERGED",
            )

    def test_exact_main_aggregate_is_the_merge_revision_ci_proof(self):
        class GitHub:
            def checks(self, sha):
                self.sha = sha
                return (
                    [
                        {
                            "name": "ci-gate",
                            "status": "completed",
                            "conclusion": "success",
                            "details_url": "https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/40336487460/job/1",
                        }
                    ],
                    [],
                )

            def fresh_run(self, run_id):
                return {
                    "head_sha": "a" * 40,
                    "head_branch": "main",
                    "status": "completed",
                    "conclusion": "success",
                }

        self.assertEqual(
            r.generic_required_ci(
                GitHub(),
                "a" * 40,
                {"required_aggregate_ci": ["ci-gate"]},
            )["status"],
            "success",
        )


if __name__ == "__main__":
    unittest.main()
