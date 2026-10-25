"""AUTO_NEXT integration tests; fixture-only, never production mutations."""

import base64
import hashlib
import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

from test_transition import MERGE, SECRET, fixture, t

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

    def test_repo_change_at_final_prewrite_has_zero_plane_patches(self):
        wp, policy, plane, gh, envelope = fixture(source="BACKLOG", target="READY")
        policy.update(execution_project={}, execution_preferences={})
        gh.__dict__["cache"] = {}
        gh.main_sha = Mock(side_effect=["a" * 40, "a" * 40, "b" * 40])
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
            patch.object(auto, "live_view", return_value={}),
            patch.object(auto, "discover", return_value=[]),
            patch.object(auto, "candidate_evidence", return_value=({}, {wp: envelope})),
            patch.object(t, "verify_policy_sources"),
            patch.object(t, "evaluate", return_value=None),
            self.assertRaises(t.Denied) as error,
        ):
            auto.advance_owner(
                t, "asrin", policy, lambda: plane, lambda _: gh, lambda *_: None, SECRET
            )
        self.assertEqual(error.exception.code, "CONCURRENT_CHANGE_RECOMPUTE_REQUIRED")
        self.assertEqual(plane.patches, [])

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

    def test_rollback_preserves_rotated_credentials_and_unrelated_sudo_rules(self):
        install = load("installer_fixture", HERE / "install_auto_next.py")
        paths = install.restore_targets(
            {"/usr/local/libexec/cap-auto-next.py": "source"}
        )
        self.assertIn("/etc/cap-plane-queue/transition-policy.json", paths)
        self.assertIn("/usr/local/libexec/cap-auto-next.py", paths)
        self.assertNotIn("/etc/cap-plane-queue/credential.json", paths)
        self.assertNotIn("/etc/sudoers.d/cap-plane-queue", paths)
        self.assertNotIn("/etc/sudoers.d/cap-plane-transition", paths)


def scope_docs(wp, own="own", other="other"):
    wbs = (
        f"| {wp} | Title | Owner |\n| WP-OTHER-001 | {other} | Owner |\n\n"
        f"#### {wp} — Title\n\n{own}\n\n#### WP-OTHER-001 — Other\n\n{other}\n"
    )
    rtm = (
        f"| FR-TEST-001 | F0 | {own} |\n| FR-OTHER-001 | F0 | {other} |\n\n"
        f"FR-TEST-001:\n  meta: {{{own}}}\n\nFR-OTHER-001:\n  meta: {{{other}}}\n"
    )
    return wbs, rtm


def git_blob(store, text):
    raw = text.encode()
    sha = hashlib.sha1(b"blob %d\0" % len(raw) + raw, usedforsecurity=False).hexdigest()
    store[sha] = {
        "encoding": "base64",
        "size": len(raw),
        "content": base64.b64encode(raw).decode(),
    }
    return sha


class DeferredAcceptanceTests(unittest.TestCase):
    def fixture(self):
        wp, policy, plane, fixture_gh, _ = fixture(source="VALIDATING", target="DONE")
        gh: Any = fixture_gh
        plane.items[0]["labels"].append(plane.blocked)
        policy["deferred_acceptance_schema"] = "cap-deferred-acceptance-v1"
        sources = {
            "docs/08": "blob1",
            "docs/02_System_Architecture_Specification.md": "blob2",
        }
        policy["contexts"][wp]["source_manifest"] = {"docs/08": "digest"}
        policy["contexts"][wp]["work_package"]["requirement_refs"] = ["FR-TEST-001"]
        wbs, rtm = scope_docs(wp)
        policy["scope_projection_schema"] = "cap-scope-projection-v1"
        policy["scope_projections"] = {
            wp: resolver.scope_projection(wp, ["FR-TEST-001"], wbs, rtm)
        }
        blobs = {}
        for path, text in ((resolver.WBS_PATH, wbs), (resolver.RTM_PATH, rtm)):
            sources[path] = git_blob(blobs, text)
        policy["source_git_blobs"] = dict(sources)
        gh.tree = {
            "truncated": False,
            "tree": [{"path": p, "sha": sha} for p, sha in sources.items()],
        }
        gh.blobs = blobs

        def route(path):
            if "/git/blobs/" in path:
                return gh.blobs.get(path.rsplit("/", 1)[1], {})
            return gh.tree

        gh._get = Mock(side_effect=route)
        gh.pr_data["body"] += """
Deferred acceptance class: WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE
Owner-executable implementation work: NONE
Blocker owner: asrin
Blocking WP: WP-TEST-002
External dependency: Real consumer acceptance
Blocker evidence: repo:evidence/test.json
"""
        previous = {
            "profile": "asrin",
            "operation": "BLOCKED",
            "result": "VERIFIED",
            "from_state": "VALIDATING",
            "to_state": "VALIDATING",
            "audit_id": "audit",
            "reason": "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE: real acceptance",
            "evidence_refs": ["pr:1", "run:4"],
            "blocker": {
                "owner": "asrin",
                "wp_id": "WP-TEST-002",
                "external_dependency": "Real consumer acceptance",
            },
        }
        return wp, policy, plane, gh, previous

    def test_verified_assessment_proof_and_live_binding(self):
        wp, policy, plane, gh, previous = self.fixture()
        with patch.object(t, "last_blocker", return_value=previous):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        self.assertTrue(resolver.deferred_acceptance(wp, live["items"][wp]))
        self.assertEqual(live["items"][wp]["state"], "VALIDATING")
        self.assertTrue(live["items"][wp]["blocked"])
        self.assertTrue(gh.artifacts)

    def test_proof_fails_closed_for_every_required_fact(self):
        for gap in (
            "audit",
            "unblocked",
            "not_validating",
            "class",
            "unknown_work",
            "duplicate",
            "owner",
            "merge",
            "branch",
            "scope",
            "truncated",
            "blocker",
            "artifact",
            "run_sha",
            "run_status",
            "run_event",
            "ci",
            "technical_ci",
        ):
            with self.subTest(gap=gap):
                wp, policy, plane, gh, previous = self.fixture()
                if gap == "audit":
                    previous["result"] = "INTENT"
                elif gap == "unblocked":
                    previous["operation"] = "UNBLOCKED"
                elif gap == "not_validating":
                    previous["from_state"] = "MERGED"
                elif gap == "class":
                    gh.pr_data["body"] = gh.pr_data["body"].replace(
                        "Deferred acceptance class: WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE",
                        "Deferred acceptance class: UNKNOWN",
                    )
                elif gap == "unknown_work":
                    gh.pr_data["body"] = gh.pr_data["body"].replace(
                        "work: NONE", "work: UNKNOWN"
                    )
                elif gap == "duplicate":
                    gh.pr_data["body"] += "Owner-executable implementation work: NONE\n"
                elif gap == "owner":
                    gh.pr_data["user"]["login"] = "someone-else"
                elif gap == "merge":
                    gh.pr_data["merged"] = False
                elif gap == "branch":
                    gh.undeleted_branch = True
                elif gap == "scope":
                    policy["source_git_blobs"]["docs/08"] = "changed"
                elif gap == "truncated":
                    gh.tree["truncated"] = True
                elif gap == "blocker":
                    previous["blocker"]["wp_id"] = "WP-TEST-003"
                elif gap == "artifact":
                    gh.missing_artifact = True
                elif gap == "run_sha":
                    gh.run_data["head_sha"] = "c" * 40
                elif gap == "run_status":
                    gh.run_data["status"] = "in_progress"
                elif gap == "run_event":
                    gh.run_data["event"] = "pull_request"
                elif gap == "ci":
                    gh.check_data[0][0]["conclusion"] = "failure"
                else:
                    gh.failed_technical_step = True
                with patch.object(t, "last_blocker", return_value=previous):
                    self.assertIsNone(auto.deferred_proof(t, wp, "asrin", policy, gh))

    def merged(self, gh, wbs, rtm):
        """Replace the implementation-merge versions of the shared canonical files."""
        for path, text in ((resolver.WBS_PATH, wbs), (resolver.RTM_PATH, rtm)):
            sha = git_blob(gh.blobs, text)
            for row in gh.tree["tree"]:
                if row["path"] == path:
                    row["sha"] = sha

    def proof(self, wp, policy, gh, previous):
        with patch.object(t, "last_blocker", return_value=previous):
            return auto.deferred_proof(t, wp, "asrin", policy, gh)

    def test_unrelated_shared_file_edits_preserve_deferred_proof(self):
        wp, policy, plane, gh, previous = self.fixture()
        # Merge-time files differ byte-for-byte from the pinned current files...
        self.merged(gh, *scope_docs(wp, other="edited later for another WP"))
        for path in (resolver.WBS_PATH, resolver.RTM_PATH):
            merge_sha = next(r["sha"] for r in gh.tree["tree"] if r["path"] == path)
            self.assertNotEqual(merge_sha, policy["source_git_blobs"][path])
        # ...yet only another WP's content changed, so the proof still holds.
        self.assertIsNotNone(self.proof(wp, policy, gh, previous))
        with patch.object(t, "last_blocker", return_value=previous):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        self.assertTrue(resolver.deferred_acceptance(wp, live["items"][wp]))

    def test_own_scope_edit_invalidates_deferred_proof(self):
        for own in ("wbs", "rtm"):
            with self.subTest(own=own):
                wp, policy, plane, gh, previous = self.fixture()
                wbs, rtm = scope_docs(wp)
                if own == "wbs":
                    wbs = wbs.replace("\nown\n", "\nown changed\n", 1)
                else:
                    rtm = rtm.replace("meta: {own}", "meta: {own changed}")
                self.merged(gh, wbs, rtm)
                self.assertIsNone(self.proof(wp, policy, gh, previous))

    def test_missing_or_ambiguous_scope_projection_fails_closed(self):
        for gap in (
            "no_projection",
            "projection_none",
            "no_schema",
            "no_refs",
            "no_tree_entry",
            "blob_unavailable",
            "blob_size",
            "blob_hash",
            "blob_encoding",
            "duplicate_card",
            "missing_card",
        ):
            with self.subTest(gap=gap):
                wp, policy, plane, gh, previous = self.fixture()
                wbs, rtm = scope_docs(wp)
                path = resolver.WBS_PATH
                row = next(r for r in gh.tree["tree"] if r["path"] == path)
                if gap == "no_projection":
                    policy.pop("scope_projections")
                elif gap == "projection_none":
                    policy["scope_projections"][wp] = None
                elif gap == "no_schema":
                    policy.pop("scope_projection_schema")
                elif gap == "no_refs":
                    del policy["contexts"][wp]["work_package"]["requirement_refs"]
                elif gap == "no_tree_entry":
                    gh.tree["tree"].remove(row)
                elif gap == "blob_unavailable":
                    del gh.blobs[row["sha"]]
                elif gap == "blob_size":
                    gh.blobs[row["sha"]]["size"] += 1
                elif gap == "blob_hash":
                    gh.blobs[row["sha"]]["content"] = base64.b64encode(
                        wbs.replace("Title", "Tampered").encode()
                    ).decode()
                elif gap == "blob_encoding":
                    gh.blobs[row["sha"]]["encoding"] = "utf-8"
                elif gap == "duplicate_card":
                    self.merged(gh, wbs + f"\n#### {wp} — Title\n\ncopy\n", rtm)
                else:
                    self.merged(gh, wbs.replace(f"#### {wp} — ", "#### "), rtm)
                self.assertIsNone(self.proof(wp, policy, gh, previous))

    def test_other_pinned_shared_sources_still_require_exact_blobs(self):
        wp, policy, plane, gh, previous = self.fixture()
        self.assertIsNotNone(self.proof(wp, policy, gh, previous))
        policy["source_git_blobs"]["docs/02_System_Architecture_Specification.md"] = "x"
        self.assertIsNone(self.proof(wp, policy, gh, previous))

    def test_assessment_digest_changes_for_prewrite_comparison(self):
        wp, policy, plane, gh, previous = self.fixture()
        with patch.object(t, "last_blocker", return_value=previous):
            before = auto.live_view(t, plane, policy, "asrin", gh)
            gh.pr_data["body"] += "Assessment clarification\n"
            after = auto.live_view(t, plane, policy, "asrin", gh)
        self.assertNotEqual(before, after)

    def test_done_still_requires_real_final_acceptance(self):
        # A valid deferred proof cannot turn final DoD UNKNOWN into PASS.
        wp, policy, plane, gh, previous = self.fixture()
        for comment in gh.comments.values():
            import json

            record = json.loads(comment["body"])
            record["cap_plane_transition"]["checks"].pop("DOD-WP-01", None)
            comment["body"] = json.dumps(record)
        with patch.object(t, "last_blocker", return_value=previous):
            self.assertIsNotNone(auto.deferred_proof(t, wp, "asrin", policy, gh))
        plane.item["labels"] = [x for x in plane.item["labels"] if x != plane.blocked]
        with self.assertRaises(t.Denied) as denied:
            t.evaluate(
                "asrin",
                wp,
                "VALIDATING",
                "DONE",
                plane.item,
                plane,
                policy,
                gh,
                {
                    "reason": "Real final acceptance",
                    "evidence_refs": ["pr:1", "comment:2", "run:4"],
                },
            )

        self.assertEqual(denied.exception.code, "CRITERION_NOT_CONFIRMED")


class ExternalIntegrationWaitTests(unittest.TestCase):
    DEPENDENCY = "DN-TEST-LIFE COMPONENT_READY and a real broker binding"
    REVISION = "a" * 40

    def body(self, **overrides):
        fields = {
            "Canonical main revision": self.REVISION,
            "External integration wait class": "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
            "Owner-executable implementation work": "NONE",
            "Reason": "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
            "Blocker owner": "asrin",
            "External dependency": self.DEPENDENCY,
        }
        fields.update(overrides)
        return (
            "External integration blocker assessment.\n\n"
            + "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)
            + "Evidence: repo:docs/04_Work_Breakdown_Structure.md\n"
        )

    def fixture(self):
        wp, policy, plane, fixture_gh, _ = fixture(
            source="IN_PROGRESS", target="IN_REVIEW"
        )
        gh: Any = fixture_gh
        plane.items[0]["labels"].append(plane.blocked)
        policy["external_wait_schema"] = "cap-external-integration-wait-v1"
        policy["node_levels"] = {"DN-TEST-LIFE": ["DEFINED", "COMPONENT_READY"]}
        policy["contexts"][wp]["dependency_edges"] = [
            {"id": "DEP-1", "predecessor": {"node": "DN-TEST-LIFE", "owner": "x"}}
        ]
        policy["contexts"][wp]["source_manifest"] = {"docs/08": "digest"}
        policy["contexts"][wp]["work_package"]["requirement_refs"] = ["FR-TEST-001"]
        wbs, rtm = scope_docs(wp)
        policy["scope_projection_schema"] = "cap-scope-projection-v1"
        policy["scope_projections"] = {
            wp: resolver.scope_projection(wp, ["FR-TEST-001"], wbs, rtm)
        }
        blobs = {}
        sources = {
            "docs/08": "blob1",
            "docs/02_System_Architecture_Specification.md": "blob2",
        }
        for path, text in ((resolver.WBS_PATH, wbs), (resolver.RTM_PATH, rtm)):
            sources[path] = git_blob(blobs, text)
        policy["source_git_blobs"] = dict(sources)
        gh.tree = {
            "truncated": False,
            "tree": [{"path": p, "sha": sha} for p, sha in sources.items()],
        }
        gh.blobs = blobs
        gh.comments = {}
        gh.comment = {
            "user": {"login": "Asperant"},
            "created_at": "2026-10-23T14:33:02Z",
            "updated_at": "2026-10-23T14:33:02Z",
            "body": self.body(),
        }

        def route(path):
            if "/issues/comments/" in path:
                return gh.comments.get(path.rsplit("/", 1)[1], gh.comment)
            if "/git/blobs/" in path:
                return gh.blobs.get(path.rsplit("/", 1)[1], {})
            return gh.tree

        gh._get = Mock(side_effect=route)
        previous = {
            "profile": "asrin",
            "operation": "BLOCKED",
            "result": "VERIFIED",
            "from_state": "IN_PROGRESS",
            "to_state": "IN_PROGRESS",
            "audit_id": "audit",
            "reason": "WAITING_EXTERNAL_INTEGRATION_BINDINGS: bindings unbound",
            "evidence_refs": ["comment:6367332807"],
            "blocker": {
                "owner": "asrin",
                "wp_id": None,
                "external_dependency": self.DEPENDENCY,
            },
        }
        return wp, policy, plane, gh, previous

    def proof(self, wp, policy, gh, previous):
        with patch.object(t, "last_blocker", return_value=previous):
            return auto.external_wait_proof(t, wp, "asrin", policy, gh)

    def test_verified_external_wait_releases_slot(self):
        wp, policy, plane, gh, previous = self.fixture()
        with patch.object(t, "last_blocker", return_value=previous):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        item = live["items"][wp]
        self.assertEqual(item["state"], "IN_PROGRESS")
        self.assertTrue(item["blocked"])
        self.assertEqual(
            item["external_integration_wait"]["dependency_nodes"], ["DN-TEST-LIFE"]
        )
        self.assertTrue(resolver.external_integration_wait(wp, item))
        self.assertFalse(resolver.occupies_implementation_slot(wp, item))
        self.assertEqual(
            resolver.released_wait(wp, item), "WAITING_EXTERNAL_INTEGRATION_BINDINGS"
        )
        self.assertTrue(gh.artifacts)

    def test_owner_executable_or_incomplete_assessment_keeps_slot(self):
        for name, value in (
            ("Owner-executable implementation work", "REMAINING"),
            ("Owner-executable implementation work", "UNKNOWN"),
            ("Owner-executable implementation work", None),
            ("External integration wait class", None),
            ("External integration wait class", "WAITING_LOCAL_TESTS"),
            ("Canonical main revision", None),
            ("Canonical main revision", "not-a-sha"),
        ):
            with self.subTest(field=name, value=value):
                wp, policy, plane, gh, previous = self.fixture()
                gh.comment["body"] = self.body(**{name: value})
                self.assertIsNone(self.proof(wp, policy, gh, previous))
        wp, policy, plane, gh, previous = self.fixture()
        gh.comment["body"] += "Owner-executable implementation work: NONE\n"
        self.assertIsNone(self.proof(wp, policy, gh, previous))

    def test_unknown_or_ambiguous_blocker_keeps_slot(self):
        def edit(key, value):
            def apply(wp, policy, gh, previous):
                if key == "reason":
                    previous["reason"] = value
                elif key == "blocker":
                    previous["blocker"]["external_dependency"] = value
                elif key == "comment":
                    gh.comment.update(value)
                elif key == "node_levels":
                    policy["node_levels"] = value
                elif key == "edges":
                    policy["contexts"][wp]["dependency_edges"] = value
                elif key == "refs":
                    previous["evidence_refs"] = value
                elif key == "audit":
                    previous.update(value)
                elif key == "projection":
                    policy["scope_projections"][wp] = value
                elif key == "schema":
                    policy.pop("scope_projection_schema")
                elif key == "dependency_text":
                    gh.comment["body"] = self.body(**{"External dependency": value})
                    previous["blocker"]["external_dependency"] = value

            return apply

        cases = {
            "generic_blocked": edit("reason", "BLOCKED: waiting"),
            "unknown_class": edit("reason", "WAITING_UNKNOWN_THING: x"),
            "class_prefix_only": edit(
                "reason", "WAITING_EXTERNAL_INTEGRATION_BINDINGS_X"
            ),
            "audit_not_verified": edit("audit", {"result": "INTENT"}),
            "audit_unblocked": edit("audit", {"operation": "UNBLOCKED"}),
            "audit_wrong_state": edit("audit", {"from_state": "READY"}),
            "audit_other_profile": edit("audit", {"profile": "selman"}),
            "no_comment_ref": edit("refs", ["pr:1"]),
            "two_comment_refs": edit("refs", ["comment:1", "comment:2"]),
            "comment_edited": edit("comment", {"updated_at": "2026-10-24T00:00:00Z"}),
            "other_author": edit("comment", {"user": {"login": "someone-else"}}),
            "blocker_changed": edit("blocker", "something else entirely"),
            "no_canonical_node": edit("dependency_text", "a real broker binding"),
            "node_without_level": edit("dependency_text", "DN-TEST-LIFE only"),
            "unknown_node": edit("dependency_text", "DN-OTHER-NODE COMPONENT_READY"),
            "node_not_an_edge": edit("edges", []),
            "level_not_canonical": edit("node_levels", {"DN-TEST-LIFE": ["DEFINED"]}),
            "scope_changed": edit("projection", "0" * 64),
            "projection_unavailable": edit("projection", None),
            "projection_schema_missing": edit("schema", None),
        }
        for name, apply in cases.items():
            with self.subTest(case=name):
                wp, policy, plane, gh, previous = self.fixture()
                apply(wp, policy, gh, previous)
                self.assertIsNone(self.proof(wp, policy, gh, previous))
        wp, policy, plane, gh, previous = self.fixture()
        with patch.object(t, "last_blocker", return_value=None):
            self.assertIsNone(auto.external_wait_proof(t, wp, "asrin", policy, gh))

    # --- UNCHANGED re-assertion of the same verified blocker (CHG-025) ---

    def chain(self, wp, previous, reassert_ref="222"):
        """VERIFIED blocker (prose-only comment 111) + UNCHANGED re-assertion (222)."""
        base = {
            "timestamp": "2026-10-23T14:33:22+00:00",
            "profile": "asrin",
            "wp_id": wp,
            "from_state": "IN_PROGRESS",
            "to_state": "IN_PROGRESS",
            "operation": "BLOCKED",
            "reason": previous["reason"],
            "evidence_refs": ["comment:111"],
            "policy_digest": "digest",
        }
        verified = dict(base, result="VERIFIED", blocker=previous["blocker"])
        verified["audit_id"] = t.audit_identity(verified)
        again = dict(
            base,
            timestamp="2026-10-23T15:32:54+00:00",
            evidence_refs=[f"comment:{reassert_ref}"],
            result="UNCHANGED",
        )
        again["audit_id"] = t.audit_identity(again)
        again["active_blocker_audit_id"] = verified["audit_id"]
        return verified, again

    def chain_fixture(self):
        wp, policy, plane, gh, previous = self.fixture()
        gh.comments["111"] = dict(
            gh.comment, body="Prose only: no exact fields, nothing remains."
        )
        gh.comments["222"] = gh.comment
        verified, again = self.chain(wp, previous)
        return wp, policy, plane, gh, verified, again

    def chain_proof(self, wp, policy, gh, verified, rows):
        with (
            patch.object(t, "last_blocker", return_value=verified),
            patch.object(t, "blocker_rows", return_value=rows),
        ):
            return auto.external_wait_proof(t, wp, "asrin", policy, gh)

    def test_verified_then_unchanged_reassertion_chain_passes(self):
        wp, policy, plane, gh, verified, again = self.chain_fixture()
        # The VERIFIED record alone is backed only by the prose-only comment.
        self.assertIsNone(self.chain_proof(wp, policy, gh, verified, [verified]))
        proof = self.chain_proof(wp, policy, gh, verified, [verified, again])
        assert proof is not None
        self.assertEqual(proof["comment_id"], "222")
        self.assertEqual(proof["audit_id"], verified["audit_id"])
        self.assertEqual(proof["reassertion_audit_id"], again["audit_id"])
        item = {
            "owner": proof["owner"],
            "state": "IN_PROGRESS",
            "blocked": True,
            "external_integration_wait": proof,
        }
        self.assertFalse(resolver.occupies_implementation_slot(wp, item))
        # UNCHANGED is never equivalent to VERIFIED: alone it proves nothing.
        self.assertIsNone(self.chain_proof(wp, policy, gh, None, [again]))
        # Same through the live view.
        with (
            patch.object(t, "last_blocker", return_value=verified),
            patch.object(t, "blocker_rows", return_value=[verified, again]),
        ):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        self.assertTrue(resolver.external_integration_wait(wp, live["items"][wp]))

    def test_direct_verified_proof_still_passes_with_chain_reader(self):
        wp, policy, plane, gh, previous = self.fixture()
        self.assertIsNotNone(self.chain_proof(wp, policy, gh, previous, []))
        wp, policy, plane, gh, verified, again = self.chain_fixture()
        # A good original assessment survives an unusable re-assertion comment.
        gh.comments["111"] = gh.comment
        gh.comments["222"] = dict(gh.comment, updated_at="2026-10-24T00:00:00Z")
        proof = self.chain_proof(wp, policy, gh, verified, [verified, again])
        assert proof is not None
        self.assertEqual(proof["comment_id"], "111")
        self.assertNotIn("reassertion_audit_id", proof)

    def test_reassertion_chain_fails_closed(self):
        def tamper_reason(verified, again, gh, policy):
            again["reason"] = "WAITING_EXTERNAL_INTEGRATION_BINDINGS: edited"

        def other_wp(verified, again, gh, policy):
            again["wp_id"] = "WP-OTHER-999"
            again["audit_id"] = t.audit_identity(again)

        def unknown_predecessor(verified, again, gh, policy):
            again["active_blocker_audit_id"] = "f" * 64

        def not_verified(verified, again, gh, policy):
            verified["result"] = "INTENT"

        def two_verified(verified, again, gh, policy):
            rows.insert(1, dict(verified))

        def later_intent(verified, again, gh, policy):
            rows.append(dict(again, result="INTENT"))

        def unblocked_row(verified, again, gh, policy):
            again["operation"] = "UNBLOCKED"
            again["audit_id"] = t.audit_identity(again)
            again["active_blocker_audit_id"] = verified["audit_id"]

        def other_state(verified, again, gh, policy):
            again["from_state"] = "VALIDATING"
            again["audit_id"] = t.audit_identity(again)
            again["active_blocker_audit_id"] = verified["audit_id"]

        def reason_changed(verified, again, gh, policy):
            again["reason"] = "WAITING_EXTERNAL_INTEGRATION_BINDINGS: different"
            again["audit_id"] = t.audit_identity(again)
            again["active_blocker_audit_id"] = verified["audit_id"]

        def generic_reason(verified, again, gh, policy):
            for row in (verified, again):
                row["reason"] = "BLOCKED: waiting"
                row["audit_id"] = t.audit_identity(row)
            again["active_blocker_audit_id"] = verified["audit_id"]

        def carries_blocker(verified, again, gh, policy):
            again["blocker"] = verified["blocker"]

        def tampered_verified(verified, again, gh, policy):
            verified["evidence_refs"] = ["comment:999"]

        def comment_edited(verified, again, gh, policy):
            gh.comments["222"] = dict(gh.comment, updated_at="2026-10-24T00:00:00Z")

        def comment_foreign(verified, again, gh, policy):
            gh.comments["222"] = dict(gh.comment, user={"login": "someone-else"})

        def comment_fields(verified, again, gh, policy):
            gh.comments["222"] = dict(
                gh.comment,
                body=self.body(**{"Owner-executable implementation work": "REMAINING"}),
            )

        def blocker_changed(verified, again, gh, policy):
            gh.comments["222"] = dict(
                gh.comment,
                body=self.body(
                    **{"External dependency": "DN-TEST-LIFE COMPONENT_READY changed"}
                ),
            )

        def no_comment(verified, again, gh, policy):
            again["evidence_refs"] = ["pr:1"]
            again["audit_id"] = t.audit_identity(again)
            again["active_blocker_audit_id"] = verified["audit_id"]

        def two_comments(verified, again, gh, policy):
            again["evidence_refs"] = ["comment:222", "comment:333"]
            again["audit_id"] = t.audit_identity(again)
            again["active_blocker_audit_id"] = verified["audit_id"]

        def scope_changed(verified, again, gh, policy):
            policy["scope_projections"][verified["wp_id"]] = "0" * 64

        cases = (
            tamper_reason,
            other_wp,
            unknown_predecessor,
            not_verified,
            two_verified,
            later_intent,
            unblocked_row,
            other_state,
            reason_changed,
            generic_reason,
            carries_blocker,
            tampered_verified,
            comment_edited,
            comment_foreign,
            comment_fields,
            blocker_changed,
            no_comment,
            two_comments,
            scope_changed,
        )
        for case in cases:
            with self.subTest(case=case.__name__):
                wp, policy, plane, gh, verified, again = self.chain_fixture()
                rows = [verified, again]
                case(verified, again, gh, policy)
                self.assertIsNone(self.chain_proof(wp, policy, gh, verified, rows))
        # Missing predecessor entirely.
        wp, policy, plane, gh, verified, again = self.chain_fixture()
        self.assertIsNone(self.chain_proof(wp, policy, gh, None, [again]))

    def test_ordinary_in_progress_consumes_slot(self):
        wp, policy, plane, gh, previous = self.fixture()
        plane.items[0]["labels"].remove(plane.blocked)
        with patch.object(t, "last_blocker", return_value=previous):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        item = live["items"][wp]
        self.assertNotIn("external_integration_wait", item)
        self.assertTrue(resolver.occupies_implementation_slot(wp, item))
        # A blocked item without any verified audit also keeps the slot.
        wp, policy, plane, gh, previous = self.fixture()
        with patch.object(t, "last_blocker", return_value=None):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        self.assertTrue(resolver.occupies_implementation_slot(wp, live["items"][wp]))
        # Unsupported schema never even asks for the proof.
        wp, policy, plane, gh, previous = self.fixture()
        del policy["external_wait_schema"]
        with patch.object(t, "last_blocker", return_value=previous):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        self.assertTrue(resolver.occupies_implementation_slot(wp, live["items"][wp]))

    def test_resolver_rejects_incomplete_or_misapplied_proofs(self):
        wp, policy, plane, gh, previous = self.fixture()
        with patch.object(t, "last_blocker", return_value=previous):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        valid = live["items"][wp]
        self.assertFalse(resolver.occupies_implementation_slot(wp, valid))
        for state in ("READY", "IN_REVIEW", "MERGE_READY", "MERGED", "VALIDATING"):
            self.assertTrue(
                resolver.occupies_implementation_slot(wp, dict(valid, state=state)),
                state,
            )
        self.assertTrue(
            resolver.occupies_implementation_slot(wp, dict(valid, blocked=False))
        )
        self.assertTrue(resolver.occupies_implementation_slot("WP-OTHER-999", valid))
        self.assertTrue(
            resolver.occupies_implementation_slot(wp, dict(valid, owner="someone"))
        )
        for key, value in (
            ("schema", "other"),
            ("classification", "WAITING_UNKNOWN"),
            ("owner_work_remaining", True),
            ("owner_work_remaining", None),
            ("audit_id", ""),
            ("comment_id", None),
            ("assessment_digest", 5),
            ("dependency_nodes", []),
            ("dependency_nodes", [""]),
            ("dependency_nodes", "DN-TEST-LIFE"),
        ):
            with self.subTest(key=key, value=value):
                proof = dict(valid["external_integration_wait"], **{key: value})
                self.assertTrue(
                    resolver.occupies_implementation_slot(
                        wp, dict(valid, external_integration_wait=proof)
                    )
                )

    def test_deferred_acceptance_behavior_is_unchanged(self):
        wp, policy, plane, gh, previous = self.fixture()
        with patch.object(t, "last_blocker", return_value=previous):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        wait = live["items"][wp]["external_integration_wait"]
        # An external wait proof never releases a VALIDATING item...
        validating = {
            "owner": "Asrın Dündar",
            "state": "VALIDATING",
            "blocked": True,
            "external_integration_wait": wait,
        }
        self.assertTrue(resolver.occupies_implementation_slot(wp, validating))
        # ...a deferred proof never releases IN_PROGRESS, and still releases VALIDATING.
        deferred = {
            "schema": "cap-deferred-acceptance-v1",
            "classification": resolver.DEFERRED_CLASS,
            "wp_id": wp,
            "owner": "Asrın Dündar",
            "implementation_complete": True,
            "owner_work_remaining": False,
            "merge_sha": "m",
            "audit_id": "a",
            "assessment_digest": "d",
        }
        in_progress = dict(
            validating, state="IN_PROGRESS", deferred_acceptance=deferred
        )
        in_progress.pop("external_integration_wait")
        self.assertTrue(resolver.occupies_implementation_slot(wp, in_progress))
        released = dict(validating, deferred_acceptance=deferred)
        released.pop("external_integration_wait")
        self.assertFalse(resolver.occupies_implementation_slot(wp, released))
        self.assertEqual(resolver.released_wait(wp, released), resolver.DEFERRED_CLASS)


class SlotReleaseV2Tests(unittest.TestCase):
    def proof(self, classification="WAITING_EXTERNAL_INTEGRATION_BINDINGS"):
        return {
            "schema": "cap-slot-release-v2",
            "wp_id": "WP-TEST-002",
            "owner": "Asrın Dündar",
            "local_actionable_work": "NONE",
            "implementation_persisted": True,
            "semantic_blocker_id": "BLOCKER-EXT-001",
            "semantic_blocker_class": classification,
            "relevant_scope_digest": "a" * 64,
        }

    def item(self, state="IN_PROGRESS", **changes):
        item = {
            "owner": "Asrın Dündar",
            "state": state,
            "blocked": True,
            "current_scope_digest": "a" * 64,
            "slot_release_v2": self.proof(),
        }
        item.update(changes)
        return item

    def test_external_wait_with_none_releases_slot(self):
        item = self.item()
        self.assertFalse(resolver.occupies_implementation_slot("WP-TEST-002", item))

    def test_validating_downstream_wait_with_none_releases_slot(self):
        item = self.item(
            "VALIDATING",
            slot_release_v2=self.proof(
                "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE"
            ),
        )
        self.assertFalse(resolver.occupies_implementation_slot("WP-TEST-002", item))

    def test_actionable_yes_or_unknown_keeps_slot(self):
        for value in ("YES", "UNKNOWN"):
            item = self.item(
                slot_release_v2=dict(self.proof(), local_actionable_work=value)
            )
            self.assertTrue(resolver.occupies_implementation_slot("WP-TEST-002", item))

    def test_unrelated_governance_change_does_not_break_release(self):
        item = self.item()
        item["unrelated_governance_digest"] = "b" * 64
        self.assertFalse(resolver.occupies_implementation_slot("WP-TEST-002", item))

    def test_relevant_scope_change_re_evaluates(self):
        item = self.item(current_scope_digest="b" * 64)
        self.assertTrue(resolver.occupies_implementation_slot("WP-TEST-002", item))

    def test_blocker_prose_is_not_a_release_identity(self):
        item = self.item()
        item["blocker_reason"] = "new explanatory prose"
        self.assertFalse(resolver.occupies_implementation_slot("WP-TEST-002", item))

    def test_deferred_core_items_do_not_create_actionable_ambiguity(self):
        rows = {
            "a": dict(
                self.item(
                    "VALIDATING",
                    slot_release_v2=self.proof(
                        "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE"
                    ),
                ),
                wp_id="WP-CORE-004",
            ),
            "b": dict(self.item("IN_PROGRESS"), wp_id="WP-CORE-005"),
            "c": {
                "owner": "Asrın Dündar",
                "state": "READY",
                "blocked": False,
                "wp_id": "WP-CORE-006",
            },
        }
        rows["a"]["slot_release_v2"]["wp_id"] = "WP-CORE-004"
        rows["b"]["slot_release_v2"]["wp_id"] = "WP-CORE-005"
        self.assertEqual(
            resolver.released_wait("WP-CORE-004", rows["a"]),
            resolver.DEFERRED_CLASS,
        )
        self.assertEqual(
            resolver.released_wait("WP-CORE-005", rows["b"]),
            "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
        )


class DeferredReassertionTests(unittest.TestCase):
    """CHG-030: UNCHANGED re-assertion of a VERIFIED deferred wait (generic)."""

    REVISION = "c" * 40
    CLASS = "WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE"

    def comment(self, **overrides):
        fields = {
            "Canonical main revision": self.REVISION,
            "Deferred acceptance class": self.CLASS,
            "Owner-executable implementation work": "NONE",
            "Reason": self.CLASS + ": real acceptance",
            "Blocker owner": "asrin",
            "Blocking WP": "WP-TEST-002",
            "External dependency": "Real consumer acceptance",
        }
        fields.update(overrides)
        return (
            "Deferred wait re-assertion.\n\n"
            + "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)
            + "Evidence: repo:evidence/test.json\n"
        )

    def fixture(self):
        wp, policy, plane, gh, previous = DeferredAcceptanceTests().fixture()
        current_tree = deepcopy(gh.tree)
        merge_tree = deepcopy(gh.tree)
        # A whole-blob pinned source drifted after the merge; the WP scope did not.
        for row in merge_tree["tree"]:
            if row["path"] == "docs/08":
                row["sha"] = "blob-at-merge"
        gh.trees = {MERGE: merge_tree}
        gh.current_tree = current_tree
        gh.comments = {}
        gh.comment = {
            "user": {"login": "Asperant"},
            "created_at": "2026-10-24T17:00:00Z",
            "updated_at": "2026-10-24T17:00:00Z",
            "body": self.comment(),
        }
        blobs = gh.blobs

        def route(path):
            if "/issues/comments/" in path:
                return gh.comments.get(path.rsplit("/", 1)[1], gh.comment)
            if "/git/blobs/" in path:
                return blobs.get(path.rsplit("/", 1)[1], {})
            for sha, tree in gh.trees.items():
                if f"/git/trees/{sha}" in path:
                    return tree
            return gh.current_tree

        gh._get = Mock(side_effect=route)
        base = {
            "timestamp": "2026-10-24T16:50:25+00:00",
            "profile": "asrin",
            "wp_id": wp,
            "from_state": "VALIDATING",
            "to_state": "VALIDATING",
            "operation": "BLOCKED",
            "reason": previous["reason"],
            "evidence_refs": previous["evidence_refs"],
            "policy_digest": "digest",
        }
        verified = dict(base, result="VERIFIED", blocker=previous["blocker"])
        verified["audit_id"] = t.audit_identity(verified)
        again = dict(
            base,
            timestamp="2026-10-24T18:00:00+00:00",
            evidence_refs=["comment:222"],
            result="UNCHANGED",
        )
        again["audit_id"] = t.audit_identity(again)
        again["active_blocker_audit_id"] = verified["audit_id"]
        return wp, policy, plane, gh, verified, again

    def proof(self, wp, policy, gh, verified, rows):
        with (
            patch.object(t, "last_blocker", return_value=verified),
            patch.object(t, "blocker_rows", return_value=rows),
        ):
            return auto.deferred_proof(t, wp, "asrin", policy, gh)

    def test_changed_source_is_bridged_only_by_a_reassertion(self):
        wp, policy, plane, gh, verified, again = self.fixture()
        # The original anchor alone no longer matches the pinned canonical source.
        self.assertIsNone(self.proof(wp, policy, gh, verified, [verified]))
        # UNCHANGED alone proves nothing.
        self.assertIsNone(self.proof(wp, policy, gh, None, [again]))
        proof = self.proof(wp, policy, gh, verified, [verified, again])
        assert proof is not None
        self.assertEqual(proof["audit_id"], verified["audit_id"])
        self.assertEqual(proof["reassertion_audit_id"], again["audit_id"])
        self.assertEqual(proof["reassertion_comment_id"], "222")
        item = {
            "owner": proof["owner"],
            "state": "VALIDATING",
            "blocked": True,
            "deferred_acceptance": proof,
        }
        self.assertTrue(resolver.deferred_acceptance(wp, item))
        self.assertFalse(resolver.occupies_implementation_slot(wp, item))
        with (
            patch.object(t, "last_blocker", return_value=verified),
            patch.object(t, "blocker_rows", return_value=[verified, again]),
        ):
            live = auto.live_view(t, plane, policy, "asrin", gh)
        self.assertTrue(resolver.deferred_acceptance(wp, live["items"][wp]))
        self.assertEqual(live["items"][wp]["state"], "VALIDATING")
        self.assertTrue(live["items"][wp]["blocked"])

    def test_unchanged_original_anchor_needs_no_reassertion(self):
        wp, policy, plane, gh, verified, again = self.fixture()
        gh.trees = {}  # merge-time tree equals the pinned current tree
        proof = self.proof(wp, policy, gh, verified, [verified])
        assert proof is not None
        self.assertNotIn("reassertion_audit_id", proof)

    def test_resolver_rejects_incomplete_reassertion_proof(self):
        wp, policy, plane, gh, verified, again = self.fixture()
        proof = self.proof(wp, policy, gh, verified, [verified, again])
        assert proof is not None
        for key in (
            "reassertion_audit_id",
            "reassertion_comment_id",
            "reassertion_digest",
        ):
            broken = dict(proof, **{key: ""})
            item = {
                "owner": proof["owner"],
                "state": "VALIDATING",
                "blocked": True,
                "deferred_acceptance": broken,
            }
            with self.subTest(key=key):
                self.assertFalse(resolver.deferred_acceptance(wp, item))
                self.assertTrue(resolver.occupies_implementation_slot(wp, item))

    def test_reassertion_fails_closed(self):
        def blocker_code_changed(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment,
                body=self.comment(**{"Deferred acceptance class": "OTHER_WAIT"}),
            )

        def reason_changed(verified, again, gh, policy):
            again["reason"] = self.CLASS + ": edited"

        def dependency_changed(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment,
                body=self.comment(**{"External dependency": "Something new"}),
            )

        def blocking_wp_changed(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment, body=self.comment(**{"Blocking WP": "WP-TEST-003"})
            )

        def own_scope_changed_now(verified, again, gh, policy):
            policy["scope_projections"][verified["wp_id"]] = "0" * 64

        def own_scope_changed_at_merge(verified, again, gh, policy):
            wbs, rtm = scope_docs(verified["wp_id"], own="own changed")
            gh.trees[MERGE] = deepcopy(gh.trees[MERGE])
            for row in gh.trees[MERGE]["tree"]:
                if row["path"] == resolver.WBS_PATH:
                    row["sha"] = git_blob(gh.blobs, wbs)

        def current_source_invalid(verified, again, gh, policy):
            policy["source_git_blobs"]["docs/08"] = "not-the-assessed-blob"

        def owner_work_executable(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment,
                body=self.comment(**{"Owner-executable implementation work": "ANY"}),
            )

        def unknown_work(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment,
                body=self.comment(
                    **{"Owner-executable implementation work": "UNKNOWN"}
                ),
            )

        def unknown_revision(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment, body=self.comment(**{"Canonical main revision": "UNKNOWN"})
            )

        def resolution_claimed(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment,
                body=self.comment(**{"Resolves blocker": verified["audit_id"]}),
            )

        def comment_edited(verified, again, gh, policy):
            gh.comment = dict(gh.comment, updated_at="2026-10-25T00:00:00Z")

        def comment_foreign(verified, again, gh, policy):
            gh.comment = dict(gh.comment, user={"login": "someone-else"})

        def evidence_missing(verified, again, gh, policy):
            gh.comment = dict(
                gh.comment,
                body=self.comment().replace("Evidence: repo:evidence/test.json\n", ""),
            )

        def artifact_missing(verified, again, gh, policy):
            gh.missing_artifact = True

        def no_comment(verified, again, gh, policy):
            again["evidence_refs"] = ["pr:1"]

        def two_comments(verified, again, gh, policy):
            again["evidence_refs"] = ["comment:222", "comment:223"]

        def carries_blocker(verified, again, gh, policy):
            again["blocker"] = verified["blocker"]

        def wrong_link(verified, again, gh, policy):
            again["active_blocker_audit_id"] = "someone-elses"

        def unblocked_row(verified, again, gh, policy):
            again["operation"] = "UNBLOCKED"

        def other_state(verified, again, gh, policy):
            again["from_state"] = "IN_PROGRESS"
            again["to_state"] = "IN_PROGRESS"

        def other_wp(verified, again, gh, policy):
            again["wp_id"] = "WP-OTHER-999"

        def tree_truncated(verified, again, gh, policy):
            gh.trees[MERGE] = dict(gh.trees[MERGE], truncated=True)

        for case in (
            blocker_code_changed,
            reason_changed,
            dependency_changed,
            blocking_wp_changed,
            own_scope_changed_now,
            own_scope_changed_at_merge,
            current_source_invalid,
            owner_work_executable,
            unknown_work,
            unknown_revision,
            resolution_claimed,
            comment_edited,
            comment_foreign,
            evidence_missing,
            artifact_missing,
            no_comment,
            two_comments,
            carries_blocker,
            wrong_link,
            unblocked_row,
            other_state,
            other_wp,
            tree_truncated,
        ):
            with self.subTest(case=case.__name__):
                wp, policy, plane, gh, verified, again = self.fixture()
                case(verified, again, gh, policy)
                self.assertIsNone(
                    self.proof(wp, policy, gh, verified, [verified, again])
                )

    def test_missing_or_unverified_previous_proof_fails_closed(self):
        for gap in ("missing", "intent", "unblocked", "other_state"):
            with self.subTest(gap=gap):
                wp, policy, plane, gh, verified, again = self.fixture()
                rows = [verified, again]
                previous = verified
                if gap == "missing":
                    previous = None
                elif gap == "intent":
                    previous = dict(verified, result="INTENT")
                elif gap == "unblocked":
                    previous = dict(verified, operation="UNBLOCKED")
                else:
                    previous = dict(verified, from_state="MERGED")
                self.assertIsNone(self.proof(wp, policy, gh, previous, rows))

    def test_pr_body_assessment_still_governs_the_original_wait(self):
        wp, policy, plane, gh, verified, again = self.fixture()
        self.assertIsNotNone(self.proof(wp, policy, gh, verified, [verified, again]))
        # A re-assertion cannot repair an owner-executable or unknown original wait.
        for old, new in (("work: NONE", "work: UNKNOWN"),):
            with self.subTest(new=new):
                wp, policy, plane, gh, verified, again = self.fixture()
                gh.pr_data["body"] = gh.pr_data["body"].replace(old, new)
                self.assertIsNone(
                    self.proof(wp, policy, gh, verified, [verified, again])
                )


if __name__ == "__main__":
    unittest.main()
