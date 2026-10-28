"""Versioned canonical serialization and digests for replay (FR-SIM-008).

Format ``sim-replay-hash/1`` is local to this simulator package, not a cross-service
standard. Each digest is SHA-256 over the UTF-8 bytes of one compact JSON document
made only of lists, strings and integers, so there is no mapping order, ``repr``,
pickle, address, clock or locale in it. The document starts with the format version
and a kind tag (``input``, ``events``, ``state``), which separates the domains.

Values carry an explicit type tag, so ``1``, ``True``, ``1.0`` and ``"1"`` differ:
``["n"]``, ``["b",true]``, ``["i",1]``, ``["f","0x1.0000000000000p+0"]`` (the exact
``float.hex`` of a finite binary64) and ``["s","text"]``. ``-0.0`` and ``0.0`` are
distinct values and hash differently. NaN and infinities are rejected. Payloads and
local state are lists of ``[key, value]`` pairs sorted by key; duplicate keys are
rejected, so construction order never matters.

Event records keep the order of execution and are never sorted. Only these fields are
hashed: ``sequence``, ``time``, ``kind``, ``event_id``, ``payload`` and the outcome
(always ``EXECUTED``). Excluded as provenance: ``correlation_id`` (it is derived from
the scenario identity, which the input digest and the replay identity cover),
``provenance`` (validated to be ``SIMULATION`` but not hashed) and ``error`` (exception
text). A ``FAILED`` record is rejected: it is not evidence of a successful replay.

The final-state digest covers the simulated clock, the local state entries, the next
insertion sequence and every pending event in execution order, not only the queue
depth. It does not cover RNG stream positions, and it is not a snapshot or restore
format.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from manufacturing_simulator.errors import CanonicalizationError
from manufacturing_simulator.events import Payload, PayloadValue
from manufacturing_simulator.kernel import PROVENANCE, ExecutionRecord, RecordOutcome
from manufacturing_simulator.scenario import KernelScenarioConfig, WorldState

FORMAT_VERSION = "sim-replay-hash/1"
OUTCOME = "EXECUTED"


@dataclass(frozen=True)
class EventRecord:
    """The semantic projection of one event: what equality and the hash cover."""

    sequence: int
    time: int
    kind: str
    event_id: str | None
    payload: Payload


@dataclass(frozen=True)
class FinalState:
    """The kernel-local final state: clock, local state and the full pending queue."""

    now: int
    local_state: Payload
    next_sequence: int
    pending: tuple[EventRecord, ...]


def _reject(message: str) -> CanonicalizationError:
    return CanonicalizationError(message)


def _int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _reject(f"{name} must be an int, got {type(value).__name__}")
    if value < 0:
        raise _reject(f"{name} must be >= 0, got {value}")
    return value


def _text(value: object, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        raise _reject(f"{name} must be a non-empty str, got {value!r}")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise _reject(f"{name} is not valid Unicode text") from None
    return value


def encode_value(value: object, name: str = "value") -> list[Any]:
    """The tagged document of one supported scalar; anything else is rejected."""
    if value is None:
        return ["n"]
    if isinstance(value, bool):
        return ["b", value]
    if isinstance(value, int):
        return ["i", value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise _reject(f"{name} is not finite")
        return ["f", value.hex()]
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise _reject(f"{name} is not valid Unicode text") from None
        return ["s", value]
    raise _reject(f"{name} has unsupported type {type(value).__name__}")


def _pairs(raw: object, name: str) -> Payload:
    """Validate a mapping or a sequence of pairs into the sorted, unique form."""
    if isinstance(raw, Mapping):
        items = list(cast(Mapping[Any, Any], raw).items())
    elif isinstance(raw, tuple | list):
        items = []
        for pair in cast(Sequence[Any], raw):
            if (
                not isinstance(pair, tuple | list)
                or len(cast(Sequence[Any], pair)) != 2
            ):
                raise _reject(f"{name} entries must be (key, value) pairs")
            items.append(tuple(cast(Sequence[Any], pair)))
    else:
        raise _reject(f"{name} must be a mapping or a sequence of pairs")
    seen: set[str] = set()
    for key, value in items:
        _text(key, f"{name} key")
        if key in seen:
            raise _reject(f"{name} has a duplicate key {key!r}")
        seen.add(key)
        encode_value(value, f"{name}[{key!r}]")
    return tuple(sorted(items, key=lambda item: item[0]))


def _event(
    sequence: object,
    time: object,
    kind: object,
    event_id: object,
    payload: object,
    name: str,
) -> EventRecord:
    return EventRecord(
        sequence=_int(sequence, f"{name} sequence"),
        time=_int(time, f"{name} time"),
        kind=cast(str, _text(kind, f"{name} kind")),
        event_id=_text(event_id, f"{name} event_id", optional=True),
        payload=_pairs(payload, f"{name} payload"),
    )


def _ordered(events: Sequence[EventRecord], name: str) -> None:
    """Execution order is strictly increasing ``(time, sequence)``; sequences are unique.

    The sequence does not have to increase globally (a later-inserted event with an
    earlier time runs first), so the list is checked, never sorted.
    """
    previous: tuple[int, int] | None = None
    seen: set[int] = set()
    for index, event in enumerate(events):
        position = (event.time, event.sequence)
        if previous is not None and position <= previous:
            raise _reject(f"{name}[{index}] is out of execution order or repeated")
        if event.sequence in seen:
            raise _reject(f"{name}[{index}] repeats sequence {event.sequence}")
        previous = position
        seen.add(event.sequence)


def _canonical_event(event: object, name: str) -> EventRecord:
    """``event`` must be an EventRecord whose fields are already in canonical form."""
    if not isinstance(event, EventRecord):
        raise _reject(f"{name} is not an EventRecord")
    clean = _event(
        event.sequence, event.time, event.kind, event.event_id, event.payload, name
    )
    if canonical_bytes(event_document(clean)) != canonical_bytes(event_document(event)):
        raise _reject(f"{name} is not in canonical form")
    return clean


def check_events(events: object, name: str = "events") -> tuple[EventRecord, ...]:
    """Validate a tuple of executed events: shape, canonical fields, order, uniqueness."""
    if not isinstance(events, tuple):
        raise _reject(f"{name} must be a tuple")
    checked = tuple(
        _canonical_event(e, f"{name}[{i}]")
        for i, e in enumerate(cast(tuple[object, ...], events))
    )
    _ordered(checked, name)
    return checked


def check_state(state: object) -> FinalState:
    """Validate a final state on its own (cross-checks with the run live in replay)."""
    if not isinstance(state, FinalState):
        raise _reject("final state is not a FinalState")
    local = _pairs(state.local_state, "state local state")
    if canonical_bytes(payload_document(local)) != canonical_bytes(
        payload_document(state.local_state)
    ):
        raise _reject("state local state is not in canonical form")
    return FinalState(
        now=_int(state.now, "state clock"),
        local_state=local,
        next_sequence=_int(state.next_sequence, "state next sequence"),
        pending=check_events(state.pending, "pending"),
    )


def project_records(records: Sequence[ExecutionRecord]) -> tuple[EventRecord, ...]:
    """Validate executed records and project them, keeping the execution order."""
    projected: list[EventRecord] = []
    for index, record in enumerate(records):
        name = f"records[{index}]"
        if not isinstance(record, ExecutionRecord):
            raise _reject(f"{name} is not an ExecutionRecord")
        if record.provenance != PROVENANCE:
            raise _reject(f"{name} provenance must be {PROVENANCE!r}")
        if record.outcome is not RecordOutcome.EXECUTED:
            raise _reject(
                f"{name} is not EXECUTED; a failed run is not replay evidence"
            )
        if not isinstance(record.correlation_id, str):
            raise _reject(f"{name} correlation_id must be a str")
        projected.append(
            _event(
                record.sequence,
                record.time,
                record.kind,
                record.event_id,
                record.payload,
                name,
            )
        )
    _ordered(projected, "records")
    return tuple(projected)


def project_world(world: WorldState) -> FinalState:
    """The kernel-local final state of ``world``, validated."""
    return FinalState(
        now=_int(world.clock.now, "clock"),
        local_state=_pairs(world.state, "local state"),
        next_sequence=_int(world.queue.scheduled_total, "next sequence"),
        pending=tuple(
            _event(e.sequence, e.time, e.kind, e.event_id, e.payload, f"pending[{i}]")
            for i, e in enumerate(world.queue.pending())
        ),
    )


def payload_document(payload: Payload) -> list[Any]:
    return [[key, encode_value(value, key)] for key, value in payload]


def event_document(event: EventRecord) -> list[Any]:
    return [
        event.sequence,
        event.time,
        event.kind,
        event.event_id,
        payload_document(event.payload),
    ]


def events_document(events: Sequence[EventRecord]) -> list[Any]:
    return [
        FORMAT_VERSION,
        "events",
        [[*event_document(e), OUTCOME] for e in events],
    ]


def state_document(state: FinalState) -> list[Any]:
    return [
        FORMAT_VERSION,
        "state",
        state.now,
        payload_document(state.local_state),
        state.next_sequence,
        [event_document(e) for e in state.pending],
    ]


def input_document(
    config: KernelScenarioConfig, initial_state: Payload, until: int, max_events: int
) -> list[Any]:
    """Scenario, initial local state and run limits; initial events keep their order."""
    return [
        FORMAT_VERSION,
        "input",
        [
            config.scenario_id,
            config.scenario_version,
            config.seed,
            config.simulator_version,
            config.time_unit.value,
            config.horizon,
            [
                [e.event_id, e.time, e.kind, payload_document(e.payload)]
                for e in config.initial_events
            ],
        ],
        payload_document(initial_state),
        until,
        max_events,
    ]


def canonical_bytes(document: object) -> bytes:
    """Compact UTF-8 JSON of a document made of lists, strings and integers."""
    text = json.dumps(
        document, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        raise _reject("a string is not valid Unicode text") from None


def digest(document: object) -> str:
    return hashlib.sha256(canonical_bytes(document)).hexdigest()


def event_sequence_digest(records: Sequence[ExecutionRecord]) -> str:
    """Digest of the executed events in order (validated at this public boundary)."""
    return digest(events_document(project_records(records)))


def final_state_digest(world: WorldState) -> str:
    """Digest of the clock, local state and the complete pending queue."""
    return digest(state_document(project_world(world)))


def input_digest(
    config: KernelScenarioConfig,
    initial_state: Payload | Mapping[str, PayloadValue],
    until: int,
    max_events: int,
) -> str:
    if not isinstance(config, KernelScenarioConfig):
        raise _reject("config must be a KernelScenarioConfig")
    return digest(
        input_document(
            config,
            _pairs(initial_state, "initial state"),
            _int(until, "until"),
            _int(max_events, "max_events"),
        )
    )


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise _reject(message)


def decode_value(document: object) -> PayloadValue:
    """Inverse of :func:`encode_value`; only the canonical spelling is accepted."""
    _expect(isinstance(document, list) and bool(document), "malformed value")
    items = cast(list[Any], document)
    tag, rest = items[0], items[1:]
    if tag == "n" and not rest:
        return None
    _expect(len(rest) == 1, "malformed value")
    raw = rest[0]
    if tag == "b" and isinstance(raw, bool):
        return raw
    if tag == "i" and isinstance(raw, int) and not isinstance(raw, bool):
        return raw
    if tag == "s" and isinstance(raw, str):
        return raw
    if tag == "f" and isinstance(raw, str):
        try:
            number = float.fromhex(raw)
        except ValueError:
            raise _reject("malformed float") from None
        if math.isfinite(number) and number.hex() == raw:
            return number
    raise _reject(f"malformed value {document!r}")


def _decode_payload(document: object, name: str) -> Payload:
    _expect(isinstance(document, list), f"{name} must be a list")
    pairs: list[tuple[str, PayloadValue]] = []
    for entry in cast(list[Any], document):
        _expect(isinstance(entry, list) and len(cast(list[Any], entry)) == 2, name)
        key, value = cast(list[Any], entry)
        _expect(isinstance(key, str), f"{name} key must be a str")
        pairs.append((key, decode_value(value)))
    return _pairs(pairs, name)


def _decode_event(document: object, name: str, *, outcome: bool) -> EventRecord:
    size = 6 if outcome else 5
    _expect(isinstance(document, list) and len(cast(list[Any], document)) == size, name)
    fields = cast(list[Any], document)
    if outcome:
        _expect(fields[5] == OUTCOME, f"{name} outcome must be {OUTCOME}")
    return _event(
        fields[0],
        fields[1],
        fields[2],
        fields[3],
        _decode_payload(fields[4], f"{name} payload"),
        name,
    )


def decode_events_document(document: object) -> tuple[EventRecord, ...]:
    _expect(
        isinstance(document, list)
        and len(cast(list[Any], document)) == 3
        and cast(list[Any], document)[:2] == [FORMAT_VERSION, "events"]
        and isinstance(cast(list[Any], document)[2], list),
        "malformed events document",
    )
    raw = cast(list[Any], cast(list[Any], document)[2])
    events = tuple(
        _decode_event(item, f"events[{i}]", outcome=True) for i, item in enumerate(raw)
    )
    _expect(
        canonical_bytes(events_document(events)) == canonical_bytes(document),
        "events document is not canonical",
    )
    return check_events(events)


def decode_state_document(document: object) -> FinalState:
    _expect(
        isinstance(document, list)
        and len(cast(list[Any], document)) == 6
        and cast(list[Any], document)[:2] == [FORMAT_VERSION, "state"]
        and isinstance(cast(list[Any], document)[5], list),
        "malformed state document",
    )
    fields = cast(list[Any], document)
    state = FinalState(
        now=_int(fields[2], "state clock"),
        local_state=_decode_payload(fields[3], "state local state"),
        next_sequence=_int(fields[4], "state next sequence"),
        pending=tuple(
            _decode_event(item, f"pending[{i}]", outcome=False)
            for i, item in enumerate(cast(list[Any], fields[5]))
        ),
    )
    _expect(
        canonical_bytes(state_document(state)) == canonical_bytes(document),
        "state document is not canonical",
    )
    return check_state(state)
