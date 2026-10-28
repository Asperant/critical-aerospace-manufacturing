"""Dispatch gate: acceptance, revalidation, idempotency, ordering (TEST-SIM-DECISIONIF).

Passing here proves the dispatch interface on a test-only facility, not the
operational model and not integrated acceptance.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from dispatch_fixtures import build, intake_document, lot, rig
from manufacturing_simulator import (
    ExecutionContext,
    OutcomeStatus,
    RejectReason,
)

CORE_EVENT: dict[str, Any] = {
    "event_type": "production.lot-dispatch-authorized",
    "schema_version": 1,
    "aggregate_type": "Lot",
    "aggregate_id": "L1",
    "aggregate_version": 8,
    "lot_id": "L1",
    "lot_revision": "L1-r1",
    "dispatch_id": "DSP-1",
}


def setup(*lots: Any) -> tuple[Any, Any, ExecutionContext]:
    rigged = rig(lots or (lot("L1"), lot("L2")), None)
    kernel = build(rigged)
    return rigged, kernel, ExecutionContext(kernel)


def test_an_accepted_dispatch_executes_only_through_a_kernel_event() -> None:
    rigged, kernel, ctx = setup()
    outcome = rigged.gate.submit(intake_document(), ctx)
    assert outcome.status is OutcomeStatus.ACCEPTED and outcome.reason_code is None
    assert rigged.facility.started == []  # queued, not executed
    kernel.step()
    assert rigged.facility.started == [(0, "L1", "M1")]
    assert rigged.gate.executions == (("DSP-1", None),)
    kinds = [event.kind for event in rigged.publisher.events]
    assert kinds == ["DISPATCH_ACCEPTED", "DISPATCH_STARTED"]


REJECTIONS: list[tuple[str, dict[str, Any], RejectReason]] = [
    ("wrong world", {"world_id": "other"}, RejectReason.WRONG_WORLD),
    ("stale revision", {"base_state_revision": "rev-0"}, RejectReason.STALE_REVISION),
    (
        "time",
        {"decision_time": {"value": 5, "unit": "us"}},
        RejectReason.DECISION_TIME_MISMATCH,
    ),
    ("unknown lot", {"lot_id": "NOPE"}, RejectReason.UNKNOWN_LOT),
    ("lot revision", {"lot_revision": "old"}, RejectReason.LOT_REVISION_MISMATCH),
    ("route step", {"route_step": "OTHER"}, RejectReason.WRONG_ROUTE_STEP),
    ("unknown machine", {"machine_id": "MX"}, RejectReason.UNKNOWN_MACHINE),
    (
        "core without authorization",
        {"source": "CORE_AUTHORIZED"},
        RejectReason.CORE_AUTHORIZATION_MISSING,
    ),
]


@pytest.mark.parametrize(("name", "change", "reason"), REJECTIONS)
def test_revalidation_rejects_without_touching_state(
    name: str, change: dict[str, Any], reason: RejectReason
) -> None:
    rigged, kernel, ctx = setup()
    before = (rigged.facility.state_revision, len(kernel.world.queue))
    outcome = rigged.gate.submit(intake_document(**change), ctx)
    assert outcome.status is OutcomeStatus.REJECTED, name
    assert outcome.reason_code is reason, name
    assert (rigged.facility.state_revision, len(kernel.world.queue)) == before
    assert rigged.facility.started == []


def test_held_ineligible_and_busy_are_rejected() -> None:
    rigged, kernel, ctx = setup(
        lot("L1", held=True), lot("L2", machines=("M2",)), lot("L3")
    )
    held = rigged.gate.submit(intake_document(), ctx)
    assert held.reason_code is RejectReason.LOT_HELD
    ineligible = rigged.gate.submit(
        intake_document(dispatch_id="DSP-2", lot_id="L2", lot_revision="L2-r1"), ctx
    )
    assert ineligible.reason_code is RejectReason.MACHINE_INELIGIBLE
    ok = rigged.gate.submit(
        intake_document(dispatch_id="DSP-3", lot_id="L3", lot_revision="L3-r1"), ctx
    )
    assert ok.status is OutcomeStatus.ACCEPTED
    kernel.step()
    busy = rigged.gate.submit(
        intake_document(
            dispatch_id="DSP-4",
            lot_id="L2",
            lot_revision="L2-r1",
            machine_id="M1",
            base_state_revision=rigged.facility.state_revision,
        ),
        ctx,
    )
    assert busy.reason_code in {
        RejectReason.MACHINE_UNAVAILABLE,
        RejectReason.MACHINE_INELIGIBLE,
    }


def test_two_decisions_for_one_machine_or_lot_cannot_both_be_pending() -> None:
    rigged, _, ctx = setup()
    assert rigged.gate.submit(intake_document(), ctx).status is OutcomeStatus.ACCEPTED
    same_machine = rigged.gate.submit(
        intake_document(dispatch_id="DSP-2", lot_id="L2", lot_revision="L2-r1"), ctx
    )
    assert same_machine.reason_code is RejectReason.MACHINE_UNAVAILABLE
    same_lot = rigged.gate.submit(
        intake_document(dispatch_id="DSP-3", machine_id="M2"), ctx
    )
    assert same_lot.reason_code is RejectReason.LOT_ALREADY_DISPATCHED


def test_resubmitting_the_same_decision_is_idempotent_and_a_changed_one_conflicts() -> (
    None
):
    rigged, kernel, ctx = setup()
    first = rigged.gate.submit(intake_document(), ctx)
    again = rigged.gate.submit(json.dumps(intake_document()), ctx)
    assert again == first
    assert len(kernel.world.queue) == 1  # scheduled once
    changed = rigged.gate.submit(intake_document(machine_id="M2"), ctx)
    assert changed.reason_code is RejectReason.DUPLICATE_CONFLICT
    kernel.step()
    assert rigged.facility.started == [(0, "L1", "M1")]
    # Even after execution the same bytes give the stored answer and run nothing.
    assert rigged.gate.submit(intake_document(), ctx) == first
    assert len(rigged.facility.started) == 1


def test_a_rejected_decision_is_remembered_as_rejected() -> None:
    rigged, _, ctx = setup()
    bad = intake_document(lot_id="NOPE")
    first = rigged.gate.submit(bad, ctx)
    assert first.reason_code is RejectReason.UNKNOWN_LOT
    assert rigged.gate.submit(bad, ctx) == first


def test_the_lot_is_revalidated_when_the_event_runs() -> None:
    rigged, kernel, ctx = setup()
    assert rigged.gate.submit(intake_document(), ctx).status is OutcomeStatus.ACCEPTED
    rigged.facility.update_lot("L1", held=True)  # a hold lands before execution
    kernel.step()
    assert rigged.facility.started == []
    assert rigged.gate.executions == (("DSP-1", RejectReason.LOT_HELD),)
    kinds = [event.kind for event in rigged.publisher.events]
    assert kinds == ["DISPATCH_ACCEPTED", "DISPATCH_START_REJECTED"]
    # The lot and machine are free again: a corrected decision is accepted.
    rigged.facility.update_lot("L1", held=False)
    retry = intake_document(
        dispatch_id="DSP-2",
        lot_revision="L1-r1",
        base_state_revision=rigged.facility.state_revision,
    )
    assert rigged.gate.submit(retry, ctx).status is OutcomeStatus.ACCEPTED


@pytest.mark.parametrize(
    "garbage",
    ["", "not json", "[]", "null", '{"a": 1, "a": 2}', '{"x": NaN}', "{}", 5],
)
def test_malformed_input_is_answered_not_raised(garbage: Any) -> None:
    rigged, kernel, ctx = setup()
    outcome = rigged.gate.submit(garbage, ctx)
    assert outcome.status is OutcomeStatus.REJECTED
    assert outcome.dispatch_id is None
    assert len(kernel.world.queue) == 0


def test_core_authorization_binds_the_dispatch_to_lot_and_revision() -> None:
    rigged, kernel, ctx = setup()
    rigged.gate.authorize(CORE_EVENT)
    document = intake_document(source="CORE_AUTHORIZED")
    assert rigged.gate.submit(document, ctx).status is OutcomeStatus.ACCEPTED
    kernel.step()
    assert rigged.facility.started == [(0, "L1", "M1")]

    other, _, other_ctx = setup()
    other.gate.authorize({**CORE_EVENT, "lot_revision": "L1-r0"})
    mismatch = other.gate.submit(document, other_ctx)
    assert mismatch.reason_code is RejectReason.CORE_AUTHORIZATION_INVALID


@pytest.mark.parametrize(
    "change",
    [
        {"event_type": "production.other"},
        {"schema_version": 2},
        {"schema_version": True},
        {"aggregate_type": "Machine"},
        {"aggregate_version": 0},
        {"lot_id": " L1"},
        {"dispatch_id": ""},
        {"extra": 1},
    ],
)
def test_an_invalid_core_authorization_is_refused(change: dict[str, Any]) -> None:
    rigged, _, _ = setup()
    bad = {**CORE_EVENT, **change}
    with pytest.raises(Exception, match="CORE_AUTHORIZATION_INVALID"):
        rigged.gate.authorize(bad)
    missing = {k: v for k, v in CORE_EVENT.items() if k != "lot_id"}
    with pytest.raises(Exception, match="CORE_AUTHORIZATION_INVALID"):
        rigged.gate.authorize(missing)


def test_conflicting_core_authorizations_for_one_dispatch_are_refused() -> None:
    rigged, _, _ = setup()
    rigged.gate.authorize(CORE_EVENT)
    rigged.gate.authorize(CORE_EVENT)  # identical repeat is fine
    with pytest.raises(Exception, match="CORE_AUTHORIZATION_INVALID"):
        rigged.gate.authorize({**CORE_EVENT, "lot_id": "L2"})
