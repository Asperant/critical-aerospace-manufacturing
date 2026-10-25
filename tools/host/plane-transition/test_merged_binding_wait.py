"""CHG-034 offline proof/slot regressions; no live API, state or deployment."""

import hashlib
import json
import unittest
from copy import deepcopy
from unittest.mock import Mock, patch

import test_auto_next as existing
from test_auto_next import auto, resolver
from test_transition import HEAD, MERGE, t


class MergedBindingWaitTests(unittest.TestCase):
    def setUp(self):
        self.wp, self.policy, self.plane, self.gh, self.audit = (
            existing.ExternalIntegrationWaitTests().fixture()
        )
        self.producer = next(w for w in self.policy["contexts"] if w != self.wp)
        owner = self.policy["contexts"][self.producer]["work_package"]["primary_owner"][
            "canonical_name"
        ]
        producer_profile = next(p for p, v in resolver.OWNERS.items() if v == owner)
        self.policy["contexts"][self.producer]["source_manifest"] = {
            "docs/08": "digest"
        }
        self.policy["scope_projections"][self.wp] = "1" * 64
        self.policy["scope_projections"][self.producer] = "2" * 64
        binding = {
            "id": "BIND-TEST-HTTP",
            "producer_wp": self.producer,
            "producer_owner": producer_profile,
            "producer_scope": "2" * 64,
            "consumer_wp": self.wp,
            "consumer_owner": "asrin",
            "consumer_scope": "1" * 64,
            "requirement": "Bound producer transport context consumed by the envelope guard",
            "provenance": {"docs/08": "3" * 64},
            "binding_paths": ["services/producer/event_binding.py"],
        }
        self.policy["source_manifest"]["docs/08"] = "3" * 64
        config = {"schema": auto.MERGED_BINDINGS_SCHEMA, "bindings": [binding]}
        self.policy["merged_external_bindings"] = config
        self.policy["merged_external_wait_schema"] = auto.MERGED_WAIT_SCHEMA
        raw = json.dumps(config).encode()
        self.policy["source_manifest"][auto.MERGED_BINDINGS_PATH] = hashlib.sha256(
            raw
        ).hexdigest()
        self.gh.repo_files[auto.MERGED_BINDINGS_PATH] = (raw, "b" * 40)
        self.gh.main_sha = Mock(return_value=HEAD)
        self.gh.checks = Mock(wraps=self.gh.checks)
        self.gh.pr_data.update(merged=True, state="closed", merge_commit_sha=MERGE)
        self.gh.run_data.update(
            head_sha=MERGE, status="completed", conclusion="success"
        )
        self.gh.comment["issue_url"] = (
            "https://api.github.com/repos/Asperant/critical-aerospace-manufacturing/issues/1"
        )
        self.gh.comment["body"] = self.body()
        self.gh.comment = Mock(return_value=self.gh.comment)
        self.audit.update(wp_id=self.wp, from_state="VALIDATING", to_state="VALIDATING")
        self.audit["evidence_refs"].append("run:4")
        self.audit["audit_id"] = t.audit_identity(self.audit)
        self.plane.item["labels"].append(self.plane.blocked)
        self.plane.items[0]["state"] = self.plane.states["VALIDATING"]
        self.plane.item["state"] = self.plane.states["VALIDATING"]
        self.scope = patch.object(auto, "check_canonical_scope").start()
        self.addCleanup(patch.stopall)
        patch.object(t, "last_blocker", side_effect=lambda _: self.audit).start()
        patch.object(t, "blocker_rows", side_effect=lambda _: [self.audit]).start()

    def body(self, **changes):
        fields = {
            "Canonical main revision": HEAD,
            "Implementation PR": "1",
            "External integration wait class": "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
            "Owner-executable implementation work": "NONE",
            "Local actionable work": "NONE",
            "External bindings": "BIND-TEST-HTTP",
            "Blocker owner": "asrin",
            "External dependency": existing.ExternalIntegrationWaitTests.DEPENDENCY,
        }
        fields.update(changes)
        return (
            f"{self.wp} external wait\n"
            + "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)
            + "Evidence: repo:docs/04_Work_Breakdown_Structure.md\n"
        )

    def proof(self):
        return auto.merged_external_wait_proof(
            t, self.wp, "asrin", self.policy, self.gh
        )

    def test_real_merge_ci_provenance_releases_only_slot(self):
        before = deepcopy(self.plane.item)
        proof = self.proof()
        self.assertIsNotNone(proof)
        self.gh.checks.assert_called_once_with(MERGE)
        item = {
            "state": "VALIDATING",
            "blocked": True,
            "owner": t.q.PEOPLE["asrin"][0],
            "merged_external_integration_wait": proof,
        }
        self.assertFalse(resolver.occupies_implementation_slot(self.wp, item))
        self.assertEqual(
            resolver.released_wait(self.wp, item),
            "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
        )
        self.assertEqual(self.plane.item, before)
        self.assertFalse(self.plane.patches)
        self.assertNotIn("implementation_complete", proof)
        self.assertIn(
            (self.wp, MERGE),
            [(c.args[2], c.args[3]) for c in self.scope.call_args_list],
        )
        self.assertIn(
            (self.producer, HEAD),
            [(c.args[2], c.args[3]) for c in self.scope.call_args_list],
        )
        for state in resolver.STATES - {"VALIDATING"}:
            self.assertIsNone(resolver.released_wait(self.wp, dict(item, state=state)))
        self.assertIsNone(resolver.released_wait(self.wp, dict(item, blocked=False)))

    def test_live_adapter_attaches_new_proof_without_changing_other_paths(self):
        with patch.object(auto, "deferred_proof", return_value=None):
            live = auto.live_view(t, self.plane, self.policy, "asrin", self.gh)
        self.assertIn("merged_external_integration_wait", live["items"][self.wp])
        self.assertIsNone(
            resolver.released_wait(self.wp, {"state": "VALIDATING", "blocked": True})
        )

    def test_slot_proof_never_bypasses_blocker_or_done_gate(self):
        self.assertIsNotNone(self.proof())
        with self.assertRaises(t.Denied) as denied:
            t.evaluate(
                "asrin",
                self.wp,
                "VALIDATING",
                "DONE",
                self.plane.item,
                self.plane,
                self.policy,
                self.gh,
                {"reason": "No acceptance claim", "evidence_refs": ["pr:1"]},
            )
        self.assertEqual(denied.exception.code, "ACTIVE_BLOCKER_UNRESOLVED")
        self.assertFalse(self.plane.patches)

    def test_unknown_missing_duplicate_or_local_work_keeps_slot(self):
        for field, value in [
            ("Owner-executable implementation work", "UNKNOWN"),
            ("Owner-executable implementation work", "REMAINING"),
            ("Local actionable work", "YES"),
            ("Local actionable work", "UNKNOWN"),
            ("Local actionable work", None),
            ("External bindings", "UNKNOWN"),
            ("External bindings", "BIND-TEST-HTTP, BIND-TEST-HTTP"),
            (
                "External integration wait class",
                "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE",
            ),
            ("Canonical main revision", "bad"),
            ("Implementation PR", None),
        ]:
            with self.subTest(field=field, value=value):
                self.gh.comment.return_value["body"] = self.body(**{field: value})
                self.assertIsNone(self.proof())
        self.gh.comment.return_value["body"] = (
            self.body() + "Owner-executable implementation work: NONE\n"
        )
        self.assertIsNone(self.proof())

    def test_absent_edited_foreign_or_wrong_pr_assessment_denied(self):
        original = deepcopy(self.gh.comment.return_value)
        for field, value in [
            ("updated_at", "2026-10-24T00:00:00Z"),
            ("user", {"login": "selorito"}),
            ("issue_url", "/issues/99"),
        ]:
            with self.subTest(field=field):
                self.gh.comment.return_value = dict(original, **{field: value})
                self.assertIsNone(self.proof())
        self.gh.comment.return_value = original
        self.audit["evidence_refs"] = []
        self.audit["audit_id"] = t.audit_identity(self.audit)
        self.assertIsNone(self.proof())

    def test_audit_mismatch_tamper_or_nonvalidating_state_denied(self):
        original = deepcopy(self.audit)
        for field, value in [
            ("result", "INTENT"),
            ("audit_id", "forged"),
            ("from_state", "IN_PROGRESS"),
            ("profile", "selman"),
            ("blocker", {"owner": "yavuz"}),
        ]:
            with self.subTest(field=field):
                self.audit = dict(original, **{field: value})
                self.assertIsNone(self.proof())

    def test_unmerged_undeleted_or_unreachable_merge_denied(self):
        self.gh.pr_data["merged"] = False
        self.assertIsNone(self.proof())
        self.gh.pr_data["merged"] = True
        self.gh.undeleted_branch = True
        self.assertIsNone(self.proof())
        self.gh.undeleted_branch = False
        self.gh.stale_ancestry = True
        self.assertIsNone(self.proof())

    def test_wrong_sha_failed_or_unstarted_main_ci_denied(self):
        original = deepcopy(self.gh.run_data)
        for field, value in [
            ("head_sha", HEAD),
            ("head_branch", "wp/other"),
            ("event", "pull_request"),
            ("status", "queued"),
            ("conclusion", "failure"),
        ]:
            with self.subTest(field=field):
                self.gh.run_data = dict(original, **{field: value})
                self.assertIsNone(self.proof())
        self.gh.run_data = original
        self.gh.check_data = (
            [{"name": "projectctl", "status": "completed", "conclusion": "failure"}],
            [],
        )
        self.assertIsNone(self.proof())

    def test_missing_stale_or_unknown_provenance_denied(self):
        config = self.policy["merged_external_bindings"]
        original = deepcopy(config["bindings"][0])
        for field, value in [
            ("producer_wp", "WP-MISSING-001"),
            ("producer_owner", "asrin"),
            ("consumer_wp", self.producer),
            ("consumer_owner", "yavuz"),
            ("producer_scope", "0" * 64),
            ("requirement", "UNKNOWN"),
            ("binding_paths", []),
            ("binding_paths", ["services/../fake"]),
            ("provenance", {}),
            ("provenance", {"docs/08": "0" * 64}),
        ]:
            with self.subTest(field=field):
                config["bindings"] = [dict(original, **{field: value})]
                self.assertIsNone(self.proof())
        for rows in [[], [original, original]]:
            config["bindings"] = rows
            self.assertIsNone(self.proof())

    def test_changed_scope_registry_or_missing_artifact_denied(self):
        self.scope.side_effect = t.Denied("DEFERRED_CANONICAL_SCOPE_CHANGED")
        self.assertIsNone(self.proof())
        self.scope.side_effect = None
        raw = self.gh.repo_files[auto.MERGED_BINDINGS_PATH]
        self.gh.repo_files[auto.MERGED_BINDINGS_PATH] = (b"changed", raw[1])
        self.assertIsNone(self.proof())
        self.gh.repo_files[auto.MERGED_BINDINGS_PATH] = raw
        self.gh.missing_artifact = True
        self.assertIsNone(self.proof())

    def test_unchanged_reassertion_preserves_verified_authority(self):
        again = dict(
            self.audit,
            result="UNCHANGED",
            active_blocker_audit_id=self.audit["audit_id"],
        )
        again.pop("blocker")
        again["audit_id"] = t.audit_identity(again)
        with patch.object(t, "blocker_rows", return_value=[self.audit, again]):
            self.assertIsNotNone(self.proof())
            again["reason"] = "different reason"
            self.assertIsNone(self.proof())

    def test_published_producer_binding_or_stale_owner_assessment_keeps_slot(self):
        self.gh.tree["tree"].append(
            {"path": "services/producer/event_binding.py", "sha": "c" * 40}
        )
        self.assertIsNone(self.proof())
        self.gh.tree["tree"].pop()
        self.gh.main_sha.return_value = "d" * 40
        self.assertIsNone(self.proof())

    def test_truncated_producer_inventory_is_unknown(self):
        self.gh.tree["truncated"] = True
        self.assertIsNone(self.proof())

    def test_bad_or_old_proof_cannot_release_validating_slot(self):
        proof = self.proof()
        for field in [
            "schema",
            "merge_sha",
            "audit_id",
            "assessment_digest",
            "provenance_digest",
            "binding_ids",
            "owner_work_remaining",
            "local_actionable_work",
        ]:
            altered = deepcopy(proof)
            altered.pop(field)
            item = {
                "state": "VALIDATING",
                "blocked": True,
                "owner": t.q.PEOPLE["asrin"][0],
                "merged_external_integration_wait": altered,
            }
            self.assertTrue(resolver.occupies_implementation_slot(self.wp, item))


if __name__ == "__main__":
    unittest.main()
