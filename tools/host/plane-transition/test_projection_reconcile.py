"""Offline CTRL-HOST-030 projection reconciliation tests."""

import copy
import importlib.util
import json
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "projection_reconcile", HERE / "projection_reconcile.py"
)
assert SPEC is not None and SPEC.loader is not None
projection = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(projection)


class Denied(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class FakePlane:
    names = {
        "STATE-IN-PROGRESS": "IN_PROGRESS",
        "STATE-VALIDATING": "VALIDATING",
    }

    def __init__(self, item):
        self.items = [copy.deepcopy(item)]
        self.blocked = "BLOCKED-LABEL"
        self.names = dict(self.names)
        self.patches = []

    def issue(self, identity):
        return copy.deepcopy(
            next(item for item in self.items if item["id"] == identity)
        )

    def patch(self, before, target):
        self.patches.append(target)
        item = next(item for item in self.items if item["id"] == before["id"])
        labels = set(item["labels"])
        if target == "BLOCKED":
            labels.add(self.blocked)
        else:
            labels.discard(self.blocked)
        item["labels"] = sorted(labels)


def audit_row(wp, operation, *, audit_id=None, resolves=None):
    row = {
        "timestamp": "2026-10-27T00:00:00+00:00",
        "profile": "asrin",
        "wp_id": wp,
        "from_state": "IN_PROGRESS",
        "to_state": "IN_PROGRESS",
        "operation": operation,
        "reason": "verified blocker",
        "evidence_refs": ["comment:1"],
        "policy_digest": "old-or-current-policy",
        "result": "VERIFIED",
    }
    if resolves:
        row["resolves_audit_id"] = resolves
    fields = {key: row.get(key) for key in projection.t.AUDIT_IDENTITY_FIELDS}
    row["audit_id"] = (
        audit_id
        or __import__("hashlib")
        .sha256(json.dumps(fields, sort_keys=True).encode())
        .hexdigest()
    )
    return row


def fixture(operation="BLOCKED", labels=None):
    wp = "WP-CORE-004"
    blocked = audit_row(wp, "BLOCKED")
    rows = [blocked]
    if operation == "UNBLOCKED":
        rows.append(audit_row(wp, "UNBLOCKED", resolves=blocked["audit_id"]))
    item = {
        "id": "12345678-1234-1234-1234-123456789abc",
        "external_id": wp,
        "external_source": "projectctl",
        "name": f"[{wp}] Test",
        "description_html": json.dumps(
            {"canonical_wp_id": wp, "canonical_owner": "Asrın Dündar"}
        ),
        "state": "STATE-IN-PROGRESS",
        "labels": list(labels or []),
    }
    policy = {
        "policy_digest": "current-policy",
        "contexts": {
            wp: {"work_package": {"primary_owner": {"canonical_name": "Asrın Dündar"}}}
        },
    }
    return wp, rows, item, policy


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.audit_log = []
        fake_q = types.SimpleNamespace(
            PEOPLE={"asrin": ("Asrın Dündar", "owner-id", "asrin@example.test")},
            STATES={"BACKLOG", "READY", "IN_PROGRESS", "VALIDATING", "DONE"},
            metadata=lambda value: json.loads(value),
        )
        projection.__dict__["t"] = types.SimpleNamespace(
            q=fake_q,
            Denied=Denied,
            Plane=FakePlane,
            AUDIT_IDENTITY_FIELDS=(
                "timestamp",
                "profile",
                "wp_id",
                "from_state",
                "to_state",
                "operation",
                "reason",
                "evidence_refs",
                "policy_digest",
            ),
            now=lambda: "2026-10-27T00:01:00+00:00",
            audit_identity=lambda row: __import__("hashlib")
            .sha256(
                json.dumps(
                    {key: row.get(key) for key in projection.t.AUDIT_IDENTITY_FIELDS},
                    sort_keys=True,
                ).encode()
            )
            .hexdigest(),
            blocker_rows=lambda wp: self.rows.get(wp, []),
            last_blocker=lambda wp: next(
                (
                    row
                    for row in reversed(self.rows.get(wp, []))
                    if row.get("result") == "VERIFIED"
                ),
                None,
            ),
            verify_readback=lambda before, after, target, plane: self.assertEqual(
                before["state"], after["state"]
            ),
        )

    def test_verified_blocked_missing_projection_is_repaired_without_lifecycle_change(
        self,
    ):
        wp, rows, item, policy = fixture()
        self.rows[wp] = rows
        plane = FakePlane(item)
        result = projection.reconcile_profile(
            "asrin",
            policy,
            plane,
            lambda record, key: self.audit_log.append(copy.deepcopy(record)),
            "secret",
        )
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["repaired"][0]["action"], "REPAIRED")
        self.assertIn("BLOCKED-LABEL", plane.items[0]["labels"])
        self.assertEqual(plane.items[0]["state"], "STATE-IN-PROGRESS")
        self.assertEqual(
            [row["result"] for row in self.audit_log], ["INTENT", "VERIFIED"]
        )

    def test_verified_unblocked_present_projection_is_removed_without_lifecycle_change(
        self,
    ):
        wp, rows, item, policy = fixture(
            operation="UNBLOCKED", labels=["BLOCKED-LABEL"]
        )
        self.rows[wp] = rows
        plane = FakePlane(item)
        result = projection.reconcile_profile(
            "asrin",
            policy,
            plane,
            lambda record, key: self.audit_log.append(copy.deepcopy(record)),
            "secret",
        )
        self.assertNotIn("BLOCKED-LABEL", plane.items[0]["labels"])
        self.assertEqual(plane.items[0]["state"], "STATE-IN-PROGRESS")
        self.assertEqual(result["repaired"][0]["projection"], "UNBLOCKED")

    def test_projection_repair_keeps_lifecycle_state_separate_from_audit_snapshot(
        self,
    ):
        wp, rows, item, policy = fixture()
        item["state"] = "STATE-VALIDATING"
        self.rows[wp] = rows
        plane = FakePlane(item)
        result = projection.reconcile_profile(
            "asrin",
            policy,
            plane,
            lambda record, key: self.audit_log.append(copy.deepcopy(record)),
            "secret",
        )
        self.assertEqual(result["repaired"][0]["projection"], "BLOCKED")
        self.assertEqual(plane.items[0]["state"], "STATE-VALIDATING")

    def test_missing_audit_with_blocked_projection_fails_closed(self):
        wp, _, item, policy = fixture(labels=["BLOCKED-LABEL"])
        self.rows[wp] = []
        plane = FakePlane(item)
        with self.assertRaisesRegex(Denied, "AUDIT_PROJECTION_SOURCE_UNAVAILABLE"):
            projection.reconcile_profile(
                "asrin",
                policy,
                plane,
                lambda record, key: self.audit_log.append(copy.deepcopy(record)),
                "secret",
            )
        self.assertEqual(plane.patches, [])

    def test_repaired_projection_is_consumed_as_slot_release(self):
        wp, rows, item, policy = fixture()
        self.rows[wp] = rows
        plane = FakePlane(item)
        projection.reconcile_profile(
            "asrin",
            policy,
            plane,
            lambda record, key: self.audit_log.append(copy.deepcopy(record)),
            "secret",
        )
        spec = importlib.util.spec_from_file_location(
            "execution_queue",
            HERE.parents[1]
            / "projectctl"
            / "src"
            / "projectctl"
            / "execution_queue.py",
        )
        assert spec is not None and spec.loader is not None
        queue = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(queue)
        queue_item = {
            "state": "IN_PROGRESS",
            "blocked": "BLOCKED-LABEL" in plane.items[0]["labels"],
            "owner": "Asrın Dündar",
            "slot_release_v2": {
                "schema": "cap-slot-release-v2",
                "wp_id": wp,
                "owner": "Asrın Dündar",
                "local_actionable_work": "NONE",
                "implementation_persisted": True,
                "semantic_blocker_id": "CORE-004-EXECUTE-APPROVED-REWORK-BINDING",
                "semantic_blocker_class": "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
            },
        }
        self.assertEqual(
            queue.semantic_slot_release(wp, queue_item),
            "WAITING_EXTERNAL_INTEGRATION_BINDINGS",
        )


if __name__ == "__main__":
    unittest.main()
