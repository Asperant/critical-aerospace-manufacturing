"""Offline: reconciliation through the REAL GitHub adapter and its cache.

Only the ``gh`` subprocess is replaced by a recording transport whose answers can change
between reads, so the cache behaviour that the fakes in ``test_reconcile`` hide is exercised.
No network, credential, Plane or host access is involved.
"""

import json
import subprocess
import unittest
from collections import Counter
from copy import deepcopy
from typing import Any
from unittest import mock

import test_reconcile as base

t, r = base.t, base.r
REPO = t.REPO
WP, PROFILE = base.WP, base.PROFILE
HEAD, MERGE, PARENT, MAIN = base.HEAD, base.MERGE, base.PARENT, base.MAIN
OTHER_MAIN, NEW_MAIN = "5" * 40, "6" * 40
BRANCH = f"wp/{WP}-slice"
PR_ROUTE = f"{REPO}/pulls/52"
MAIN_ROUTE = f"{REPO}/commits/main"
COMMIT_ROUTE = f"{REPO}/commits/{MERGE}"
BRANCH_ROUTE = f"{REPO}/git/matching-refs/heads/{BRANCH}"
PARENT_COMPARE = f"{REPO}/compare/{PARENT}...{MERGE}"
MAIN_COMPARE = f"{REPO}/compare/{MERGE}...{MAIN}"
FILES_1 = f"{REPO}/pulls/52/files?per_page=100&page=1"
FILES_2 = f"{REPO}/pulls/52/files?per_page=100&page=2"
FILES_3 = f"{REPO}/pulls/52/files?per_page=100&page=3"
CI_ROUTE = f"{REPO}/actions/runs/{base.CI_RUN}"
PC_ROUTE = f"{REPO}/actions/runs/{base.PC_RUN}"
AHEAD = {"status": "ahead", "behind_by": 0}


def pr_payload(**changes):
    payload = {
        "number": 52,
        "base": {"repo": {"full_name": base.REPOSITORY}, "ref": "main"},
        "user": {"login": t.GITHUB[PROFILE]},
        "head": {"ref": BRANCH, "sha": HEAD},
        "title": f"[{WP}] Implement slice",
        "body": "Body",
        "changed_files": 3,
        "state": "closed",
        "merged": True,
        "merge_commit_sha": MERGE,
    }
    payload.update(changes)
    return payload


def run_payload(path):
    return {
        "id": 0,
        "head_sha": MERGE,
        "head_branch": "main",
        "event": "push",
        "path": path,
        "status": "completed",
        "conclusion": "success",
        "run_started_at": base.STARTED,
        "updated_at": base.FINISHED,
        "repository": {"full_name": base.REPOSITORY},
    }


def default_routes():
    return {
        PR_ROUTE: pr_payload(),
        FILES_1: [
            {"filename": "services/sim/a.py", "status": "added"},
            {"filename": "services/sim/b.py", "status": "added"},
            {"filename": "evidence/sim/README.md", "status": "added"},
        ],
        FILES_2: [],
        COMMIT_ROUTE: {"sha": MERGE, "parents": [{"sha": PARENT}, {"sha": HEAD}]},
        PARENT_COMPARE: AHEAD,
        MAIN_COMPARE: AHEAD,
        MAIN_ROUTE: {"sha": MAIN},
        BRANCH_ROUTE: [],
        CI_ROUTE: dict(run_payload(".github/workflows/ci.yml"), id=base.CI_RUN),
        PC_ROUTE: dict(run_payload(".github/workflows/projectctl.yml"), id=base.PC_RUN),
    }


class Transport:
    """Stands in for ``gh api``: answers each GET per route and counts every call."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = Counter()
        self.order = []

    def __call__(self, argv, **kwargs):
        route = argv[-1]
        self.order.append(route)
        self.calls[route] += 1
        handler = self.routes[route]
        payload = handler(self.calls[route]) if callable(handler) else handler
        return subprocess.CompletedProcess(
            argv, 0, stdout=json.dumps(payload).encode(), stderr=b""
        )


def real_adapter() -> Any:
    gh = object.__new__(t.GitHub)
    gh.profile, gh.cache, gh.uid, gh.gid, gh.env = PROFILE, {}, 0, 0, {}
    return gh


def run_through_adapter(overrides=None, source="READY", case=None):
    case = case or base.make_case(changed_files=3)
    routes = default_routes()
    routes.update(overrides or {})
    transport = Transport(routes)
    plane, logs = base.FakePlane(source), []
    outcome: Any
    with mock.patch.object(t.subprocess, "run", transport):
        try:
            outcome = r.reconcile(
                PROFILE,
                WP,
                "VALIDATING",
                base.envelope_for(case, "VALIDATING"),
                base.make_policy(case),
                plane,
                real_adapter(),
                lambda rec, key: logs.append(deepcopy(rec)),
                base.SECRET,
                now=lambda: base.NOW,
            )
        except t.Denied as exc:
            outcome = exc
    return outcome, plane, logs, transport


def second_gather_only(normal, changed, first_gather_reads):
    return lambda n: normal if n <= first_gather_reads else changed


class AdapterCacheTests(unittest.TestCase):
    def test_the_cache_serves_stale_mutable_reads_until_invalidated(self):
        answers = iter([{"sha": MAIN}, {"sha": OTHER_MAIN}])
        transport = Transport({MAIN_ROUTE: lambda n: next(answers)})
        gh = real_adapter()
        with mock.patch.object(t.subprocess, "run", transport):
            self.assertEqual(gh.main_sha(), MAIN)
            self.assertEqual(
                gh.main_sha(), MAIN
            )  # served from cache: one transport call
            self.assertEqual(transport.calls[MAIN_ROUTE], 1)
            gh.invalidate()
            self.assertEqual(gh.main_sha(), OTHER_MAIN)
            self.assertEqual(transport.calls[MAIN_ROUTE], 2)


class FreshRecheckThroughRealAdapterTests(unittest.TestCase):
    def assertBlocked(self, overrides, code):
        outcome, plane, logs, _ = run_through_adapter(overrides)
        self.assertIsInstance(outcome, t.Denied)
        self.assertEqual(outcome.code, code)
        self.assertEqual((plane.patches, logs), ([], []))  # no PATCH, no INTENT row

    def test_unchanged_evidence_verifies_and_rereads_every_mutable_input(self):
        outcome, plane, _, transport = run_through_adapter()
        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertEqual(plane.patches, [{"state": "VALIDATING"}])
        self.assertEqual(
            transport.calls[COMMIT_ROUTE], 1
        )  # immutable: cached across gathers
        for route in (
            PR_ROUTE,
            MAIN_ROUTE,
            BRANCH_ROUTE,
            PARENT_COMPARE,
            MAIN_COMPARE,
            FILES_1,
            FILES_2,
            CI_ROUTE,
            PC_ROUTE,
        ):
            with self.subTest(route=route):
                self.assertGreaterEqual(transport.calls[route], 2)

    def test_main_that_loses_the_merge_before_the_write_blocks_it(self):
        self.assertBlocked(
            {
                MAIN_ROUTE: lambda n: {"sha": MAIN if n == 1 else OTHER_MAIN},
                f"{REPO}/compare/{MERGE}...{OTHER_MAIN}": {
                    "status": "diverged",
                    "behind_by": 1,
                },
            },
            "PRODUCER_MERGE_NOT_IN_MAIN_ANCESTRY",
        )

    def test_legitimate_main_advancement_is_proved_against_the_new_main(self):
        outcome, plane, logs, _ = run_through_adapter(
            {
                MAIN_ROUTE: lambda n: {"sha": MAIN if n == 1 else NEW_MAIN},
                f"{REPO}/compare/{MERGE}...{NEW_MAIN}": AHEAD,
            }
        )
        self.assertEqual(outcome["result"], "VERIFIED")
        self.assertEqual(logs[-1]["facts"]["merge"]["main_sha_observed"], NEW_MAIN)
        self.assertEqual(len(plane.patches), 1)

    def test_the_fresh_pr_is_held_to_every_binding_predicate(self):
        cases = {
            "author": (
                pr_payload(user={"login": "someone-else"}),
                "PR_AUTHOR_PROFILE_MISMATCH",
            ),
            "head": (
                pr_payload(head={"ref": BRANCH, "sha": "7" * 40}),
                "RECONCILIATION_PR_BINDING_MISMATCH",
            ),
            "merge commit": (
                pr_payload(merge_commit_sha="7" * 40),
                "RECONCILIATION_PR_BINDING_MISMATCH",
            ),
            "title": (pr_payload(title="Unrelated"), "PR_WP_BINDING_MISSING"),
            "base": (
                pr_payload(base={"repo": {"full_name": base.REPOSITORY}, "ref": "dev"}),
                "WRONG_PR_REPOSITORY_OR_BASE",
            ),
            "reopened": (
                pr_payload(state="open", merged=False),
                "RECONCILIATION_PR_BINDING_MISMATCH",
            ),
        }
        for name, (changed, code) in cases.items():
            with self.subTest(name=name):
                # PR reads in the first gather: pr_fact and the file-count recheck.
                self.assertBlocked(
                    {PR_ROUTE: second_gather_only(pr_payload(), changed, 2)}, code
                )

    def test_a_run_that_changes_before_the_write_blocks_it(self):
        normal = dict(run_payload(".github/workflows/ci.yml"), id=base.CI_RUN)
        self.assertBlocked(
            {
                CI_ROUTE: lambda n: normal
                if n == 1
                else dict(normal, updated_at="2026-10-24T11:00:00Z")
            },
            "CONCURRENT_GITHUB_CHANGE",
        )
        self.assertBlocked(
            {
                CI_ROUTE: lambda n: normal
                if n == 1
                else dict(normal, conclusion="cancelled")
            },
            "RUN_NO_QUALIFYING_CONCLUSION",
        )


if __name__ == "__main__":
    unittest.main()
