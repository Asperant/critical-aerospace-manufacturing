"""CTRL-HOST-009: real shared classification, offline proof-adapter fixtures only."""

import importlib.util
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

from test_transition import fixture, t

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auto = load("wip_auto_fixture", HERE / "auto_next.py")
resolver = load(
    "wip_resolver_fixture",
    HERE.parents[1] / "projectctl/src/projectctl/execution_queue.py",
)


class DeferredWipTests(unittest.TestCase):
    def setup_case(self, *, profile="asrin", count=1, blocked=True, heavy=True):
        wp, policy, plane, gh, envelope = fixture(profile=profile)
        if profile == "asrin":
            policy["contexts"][wp]["work_package"]["size_band"] = "L"
        # Distinct fixture IDs deliberately avoid the production incident WPs.
        for index in range(count):
            identity = f"WP-{'CORE' if heavy else 'TEST'}-{910 + index}"
            other = deepcopy(plane.item)
            other.update(
                id=f"active-{index}",
                external_id=identity,
                name=f"[{identity}] Other active WP",
                description_html=json.dumps(
                    {
                        "canonical_wp_id": identity,
                        "canonical_owner": t.q.PEOPLE[profile][0],
                    }
                ),
                state="IN_PROGRESS",
                labels=[plane.blocked] if blocked else [],
            )
            plane.items.append(other)
            policy["contexts"][identity] = deepcopy(policy["contexts"][wp])
            policy["contexts"][identity]["work_package"]["id"] = identity
        policy["external_wait_schema"] = "cap-external-integration-wait-v1"
        return wp, policy, plane, gh, envelope

    def proof(self, identity, profile):
        return {
            "schema": "cap-external-integration-wait-v1",
            "classification": "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
            "wp_id": identity,
            "owner": t.q.PEOPLE[profile][0],
            "owner_work_remaining": False,
            "audit_id": "verified-audit",
            "assessment_digest": "verified-assessment",
            "comment_id": "1234",
            "dependency_nodes": ["DN-FIXTURE"],
        }

    def evaluate(self, case, *, profile="asrin", proof=None, proof_error=None):
        wp, policy, plane, gh, envelope = case
        verifier = Mock(return_value=proof, side_effect=proof_error)
        with (
            patch.dict(sys.modules, {t.__name__: t}),
            patch.object(t, "auto_next_support", return_value=auto),
            patch.object(auto, "load_resolver", return_value=resolver),
            patch.object(auto, "external_wait_proof", verifier),
            patch.object(
                auto, "advance_owner", side_effect=AssertionError("no writer")
            ),
            patch.object(auto, "live_view", wraps=auto.live_view) as live,
        ):
            try:
                t.evaluate(
                    profile,
                    wp,
                    "READY",
                    "IN_PROGRESS",
                    plane.item,
                    plane,
                    policy,
                    gh,
                    envelope,
                )
            finally:
                live.assert_called_once_with(t, plane, policy, profile, gh)
                self.assertEqual(plane.patches, [])
        return verifier

    def test_verified_deferred_heavy_core_does_not_consume_wip(self):
        case = self.setup_case()
        identity = case[2].items[1]["external_id"]
        verifier = self.evaluate(case, proof=self.proof(identity, "asrin"))
        verifier.assert_called_once_with(t, identity, "asrin", case[1], case[3])

    def test_unknown_invalid_or_unavailable_proof_still_consumes_heavy_wip(self):
        for kind in ("missing", "UNKNOWN", "invalid", "foreign", "owner-work", "stale"):
            with self.subTest(kind=kind):
                case = self.setup_case()
                identity = case[2].items[1]["external_id"]
                proof = self.proof(identity, "asrin")
                error = None
                if kind == "missing":
                    proof = None
                elif kind == "UNKNOWN":
                    proof["classification"] = "UNKNOWN"
                elif kind == "invalid":
                    proof.pop("assessment_digest")
                elif kind == "foreign":
                    proof["wp_id"] = "WP-CORE-999"
                elif kind == "owner-work":
                    proof["owner_work_remaining"] = True
                else:
                    error = t.Denied("STALE_ASSESSMENT")
                with self.assertRaises(t.Denied) as raised:
                    self.evaluate(case, proof=proof, proof_error=error)
                self.assertEqual(raised.exception.code, "HEAVY_CORE_WIP_LIMIT")

    def test_ordinary_active_core_still_consumes_heavy_wip(self):
        for blocked in (False, True):
            with self.subTest(blocked=blocked):
                with self.assertRaises(t.Denied) as raised:
                    self.evaluate(self.setup_case(blocked=blocked))
                self.assertEqual(raised.exception.code, "HEAVY_CORE_WIP_LIMIT")

    def test_nonheavy_general_limits_unchanged(self):
        # Yavuz's fixture target is a non-Core M package.
        self.evaluate(self.setup_case(profile="yavuz", heavy=False), profile="yavuz")
        self.evaluate(self.setup_case(profile="yavuz", heavy=True), profile="yavuz")
        with self.assertRaises(t.Denied) as raised:
            self.evaluate(
                self.setup_case(profile="yavuz", count=2, heavy=False), profile="yavuz"
            )
        self.assertEqual(raised.exception.code, "IMPLEMENTATION_WIP_LIMIT")

    def test_general_limit_excludes_only_verified_wait(self):
        case = self.setup_case(profile="yavuz", count=2, heavy=False)
        identity = case[2].items[1]["external_id"]
        # Only the first WP can match this identity-bound proof; the other
        # remains counted by the actual shared classifier.
        self.evaluate(case, profile="yavuz", proof=self.proof(identity, "yavuz"))

    def test_missing_live_item_cannot_partially_filter_active_set(self):
        case = self.setup_case(count=2)
        wp, policy, plane, gh, envelope = case
        identity = plane.items[1]["external_id"]
        live = {
            "complete": True,
            "items": {
                identity: {
                    "state": "IN_PROGRESS",
                    "blocked": True,
                    "owner": t.q.PEOPLE["asrin"][0],
                    "external_integration_wait": self.proof(identity, "asrin"),
                }
            },
        }
        with (
            patch.dict(sys.modules, {t.__name__: t}),
            patch.object(t, "auto_next_support", return_value=auto),
            patch.object(auto, "load_resolver", return_value=resolver),
            patch.object(auto, "live_view", return_value=live),
        ):
            with self.assertRaises(t.Denied) as raised:
                t.evaluate(
                    "asrin",
                    wp,
                    "READY",
                    "IN_PROGRESS",
                    plane.item,
                    plane,
                    policy,
                    gh,
                    envelope,
                )
            self.assertEqual(raised.exception.code, "IMPLEMENTATION_WIP_LIMIT")
            self.assertEqual(plane.patches, [])

    def test_incomplete_live_view_never_releases_wip(self):
        case = self.setup_case()
        wp, policy, plane, gh, envelope = case
        with (
            patch.dict(sys.modules, {t.__name__: t}),
            patch.object(t, "auto_next_support", return_value=auto),
            patch.object(auto, "load_resolver", return_value=resolver),
            patch.object(auto, "live_view", return_value={"complete": False}),
        ):
            with self.assertRaises(t.Denied) as raised:
                t.evaluate(
                    "asrin",
                    wp,
                    "READY",
                    "IN_PROGRESS",
                    plane.item,
                    plane,
                    policy,
                    gh,
                    envelope,
                )
            self.assertEqual(raised.exception.code, "HEAVY_CORE_WIP_LIMIT")


if __name__ == "__main__":
    unittest.main()
