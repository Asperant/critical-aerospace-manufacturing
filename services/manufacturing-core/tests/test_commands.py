from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from manufacturing_core.commands import (
    DispatchLot,
    EffectVerificationStatus,
    InMemoryCommandLedger,
    OutcomeStatus,
    PlaceLotOnHold,
    UnresolvedEffect,
    reconciliation_action,
    validate_command_context,
    validate_preconditions,
)
from pydantic import ValidationError


def command(**changes: object) -> PlaceLotOnHold:
    values: dict[str, object] = {
        "idempotency_key": "key-1",
        "world_id": "primary",
        "correlation_id": "corr-1",
        "target": {"entity_type": "Lot", "entity_id": "LOT-1"},
        "expected": {"expected_revision": "r1"},
        "hold_reason": "inspection",
        "material_hold_id": "hold-1",
    }
    values.update(changes)
    return PlaceLotOnHold.model_validate(values)


def test_all_command_fields_are_typed_and_canonical() -> None:
    assert command().command_type == "PlaceLotOnHold"
    dispatch = DispatchLot.model_validate(
        {
            "idempotency_key": "dispatch-1",
            "world_id": "primary",
            "correlation_id": "corr-2",
            "target": {"entity_type": "Lot", "entity_id": "LOT-1"},
            "expected": {"expected_revision": "r1"},
            "operation_id": "OP-1",
            "resource_id": "CNC-1",
        }
    )
    assert dispatch.command_type == "DispatchLot"
    assert dispatch.command_version == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"world_id": ""},
        {"correlation_id": ""},
        {"target": {"entity_type": "Lot", "entity_id": ""}},
        {"expected": {}},
        {"command_version": 2},
    ],
)
def test_malformed_commands_fail_closed(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        command(**changes)


def test_revision_and_freshness_rejections_are_typed() -> None:
    with pytest.raises(Exception, match="STALE"):
        validate_preconditions(command(), current_revision="r2")
    old = datetime.now(UTC) - timedelta(minutes=10)
    fresh = command(expected={"observed_at": old, "max_age_seconds": 30})
    with pytest.raises(Exception, match="STALE"):
        validate_preconditions(fresh, current_revision="r1", now=datetime.now(UTC))
    unavailable = command(expected={"expected_revision": "r1"})
    with pytest.raises(Exception, match="UNRESOLVED"):
        validate_preconditions(unavailable, current_revision=None)
    with pytest.raises(Exception, match="WORLD_MISMATCH"):
        validate_command_context(command(), expected_world_id="simulation-1")


def test_duplicate_delivery_returns_original_and_effect_runs_once() -> None:
    ledger = InMemoryCommandLedger()
    effects: list[str] = []
    original = command()
    first = ledger.accept(original, current_revision="r1", mutate=lambda: effects.append("effect"))
    retry = ledger.accept(original, current_revision="r1", mutate=lambda: effects.append("bad"))
    assert first == retry
    assert first.status == OutcomeStatus.ACCEPTED
    assert first.effect_verification == EffectVerificationStatus.NOT_VERIFIED
    assert effects == ["effect"]


def test_same_key_different_command_is_conflict_without_effect() -> None:
    ledger = InMemoryCommandLedger()
    first = ledger.accept(command(), current_revision="r1")
    conflict = ledger.accept(
        command(hold_reason="different"), current_revision="r1", mutate=lambda: pytest.fail()
    )
    assert first.status == OutcomeStatus.ACCEPTED
    assert conflict.status == OutcomeStatus.CONFLICT
    assert conflict.error_code == "CONFLICT"


def test_rejected_and_unresolved_outcomes_are_durable_and_queryable() -> None:
    ledger = InMemoryCommandLedger()
    rejected = ledger.accept(command(), current_revision="r2")
    unresolved_command = command(idempotency_key="key-2")
    unresolved = ledger.accept(
        unresolved_command,
        current_revision="r1",
        mutate=lambda: (_ for _ in ()).throw(UnresolvedEffect("lost acknowledgement")),
    )
    assert rejected.status == OutcomeStatus.REJECTED
    assert rejected.error_code == "STALE"
    assert unresolved.status == OutcomeStatus.UNRESOLVED
    assert ledger.get_outcome(rejected.outcome_id) == rejected
    assert ledger.get_by_idempotency("key-2") == unresolved
    assert reconciliation_action(unresolved) == "LOOKUP_CANONICAL_EFFECT_BEFORE_RETRY"


def test_outcome_identity_is_uuid_and_command_id_is_stable() -> None:
    item = command()
    assert isinstance(item.command_id, UUID)
    assert item.fingerprint() == item.fingerprint()
