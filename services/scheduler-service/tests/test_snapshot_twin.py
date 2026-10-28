"""Interface check against the real TwinQueryAPI (fixture provider, FIXTURE_ALLOWED).

Not a live authenticated service and not operational state: the provider returns the
published normal fixture.
"""

from __future__ import annotations

from typing import Any

import pytest
from manufacturing_scheduler.errors import SnapshotError
from manufacturing_scheduler.snapshot import TwinSnapshotReader, read_planning_input
from operational_twin.scheduling_snapshot import (
    SCHEDULING_SNAPSHOT_READ,
    ReadScopeDenied,
    SnapshotQueryError,
    TwinQueryAPI,
    TwinReadContext,
)
from plan_helpers import mutated, policy, snapshot_doc

CONSUMER = "scheduler-service"
GRANTED = TwinReadContext(CONSUMER, frozenset({SCHEDULING_SNAPSHOT_READ}))


def _api(calls: list[str], doc: dict[str, Any] | None = None) -> TwinQueryAPI:
    def provider(world_id: str) -> dict[str, Any]:
        calls.append(world_id)
        return doc if doc is not None else snapshot_doc()

    return TwinQueryAPI(provider, {CONSUMER: frozenset({SCHEDULING_SNAPSHOT_READ})})


def test_scheduler_consumes_what_the_twin_serves_with_one_provider_call() -> None:
    calls: list[str] = []
    reader = TwinSnapshotReader(_api(calls), GRANTED)
    planning_input = read_planning_input(reader, world_id="PRIMARY", policy=policy())
    assert calls == ["PRIMARY"]
    assert planning_input.snapshot.snapshot_revision == "twin-rev-184202"
    assert [lot.lot_id for lot in planning_input.snapshot.lots] == [
        "LOT-001",
        "LOT-002",
    ]


@pytest.mark.parametrize(
    "context",
    [
        TwinReadContext("unknown-consumer", frozenset({SCHEDULING_SNAPSHOT_READ})),
        TwinReadContext(CONSUMER, frozenset()),
    ],
)
def test_twin_scope_denial_propagates_unchanged_without_a_provider_call(
    context: TwinReadContext,
) -> None:
    calls: list[str] = []
    with pytest.raises(ReadScopeDenied):
        read_planning_input(
            TwinSnapshotReader(_api(calls), context),
            world_id="PRIMARY",
            policy=policy(),
        )
    assert calls == []


def test_twin_world_mismatch_is_raised_by_the_twin_not_masked() -> None:
    other = mutated(snapshot_doc(), lambda doc: doc.update(world_id="OTHER"))
    with pytest.raises(SnapshotQueryError):
        read_planning_input(
            TwinSnapshotReader(_api([], other), GRANTED),
            world_id="PRIMARY",
            policy=policy(),
        )


def test_consumer_is_stricter_than_the_twin_where_the_published_schema_is() -> None:
    # The Twin only requires nonblank strings, so it serves an id with an inner space
    # (the published schema pattern forbids whitespace); this consumer rejects it.
    doc = mutated(snapshot_doc(), lambda d: d["lots"][0].update(id="LOT 001"))
    reader = TwinSnapshotReader(_api([], doc), GRANTED)
    with pytest.raises(SnapshotError) as caught:
        read_planning_input(reader, world_id="PRIMARY", policy=policy())
    assert caught.value.code == "IDENTIFIER_INVALID"
