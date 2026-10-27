"""CHG-054 product-start regression tests; no credentials or network."""

import unittest
from unittest.mock import patch

from test_transition import fixture, t


class AdvisorySchedulingTests(unittest.TestCase):
    def evaluate(self, *, hard_start=False, dependency_status="READY", integration=False):
        wp, policy, plane, gh, envelope = fixture()
        context = policy["contexts"][wp]
        if hard_start:
            context["dependency_edges"] = [
                {
                    "id": "DEP-018",
                    "status": dependency_status,
                    "predecessor": {"node": "DN-TEST", "owner": "Asrın"},
                    "successor": {"node": "DN-CONSUMER", "owner": "Asrın"},
                    "semantics": {
                        "kind": "CONTRACT",
                        "strength": "HARD",
                        "blocking_stage": "INTEGRATION" if integration else "START",
                        "required_readiness": "CONTRACT_READY",
                    },
                }
            ]
        with patch.object(t, "records", side_effect=AssertionError("START must not read evidence")):
            t.evaluate(
                "asrin", wp, "READY", "IN_PROGRESS", plane.item, plane, policy, gh, envelope
            )

    def test_queue_or_slot_proof_is_not_needed_for_start(self):
        self.evaluate()

    def test_external_integration_dependency_does_not_block_start(self):
        self.evaluate(hard_start=True, dependency_status="NOT_READY", integration=True)

    def test_unresolved_hard_start_dependency_blocks(self):
        with self.assertRaises(t.Denied) as raised:
            self.evaluate(hard_start=True, dependency_status="NOT_READY")
        self.assertEqual(raised.exception.code, "HARD_START_DEPENDENCY_UNRESOLVED:DEP-018")

    def test_multiple_active_work_is_not_a_slot_gate(self):
        wp, policy, plane, gh, envelope = fixture()
        other = dict(plane.item)
        other.update(id="active-1", external_id="WP-TEST-910", state=plane.states["IN_PROGRESS"])
        plane.items.append(other)
        policy["contexts"]["WP-TEST-910"] = policy["contexts"][wp]
        policy["contexts"]["WP-TEST-910"]["work_package"] = dict(
            policy["contexts"][wp]["work_package"], id="WP-TEST-910"
        )
        with patch.object(t, "records", side_effect=AssertionError("START must not read evidence")):
            t.evaluate("asrin", wp, "READY", "IN_PROGRESS", plane.item, plane, policy, gh, envelope)


if __name__ == "__main__":
    unittest.main()
