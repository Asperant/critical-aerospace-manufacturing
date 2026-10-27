"""Deterministic replay and semantic comparison (FR-SIM-008, NFR-REP-001).

``replay`` runs one scenario in a FRESH kernel: the handler bundle comes from a
caller-supplied factory called once per replay (so no handler state or world is
shared between replays), the world is built by :class:`ScenarioEngine`, and the
declared horizon and event budget bound the run. A new execution is labelled with the
runtime that really ran it: a declared NumPy or RNG identity that this process does
not run is refused, and the input is canonicalized, before any handler is created.
Nothing is retried and a failed run raises :class:`ReplayExecutionError`.

A :class:`ReplayResult` is validated whenever it is constructed, decoded or compared,
independently of its digests: format, field types, execution order, unique sequences,
and the clock, queue and termination relationships of a real run. Digests summarize
the semantic data; a digest over an impossible result never certifies it.

``compare`` checks, in this order: identity and input (``INCOMPATIBLE_INPUT``, not
evidence of nondeterminism), the event sequence (``EVENT_MISMATCH``), the final state
(``STATE_MISMATCH``). Only a complete run (queue empty, or the declared horizon
reached) can be ``MATCH``. Two equal runs that both stopped at their event budget are
``PARTIAL_MATCH``: an equal prefix of an incomplete run, never accepted determinism.

Scope: the kernel is single-threaded, and handlers must not read the wall clock,
global random state, threads or the environment. ``source_id`` and
``handler_bundle_id`` are caller-declared labels, not attested. A passing comparison
is evidence for the supplied handlers, scenario and NumPy version only; it does not
prove that arbitrary handlers, other NumPy versions or other hardware replay
identically.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from itertools import zip_longest
from typing import Any, NoReturn, cast

import numpy as np

from manufacturing_simulator.errors import (
    CanonicalizationError,
    HandlerExecutionError,
    IncompatibleRuntimeError,
    InvalidConfigurationError,
    InvalidTimeError,
    ReplayExecutionError,
)
from manufacturing_simulator.events import Payload, PayloadValue, freeze_payload
from manufacturing_simulator.kernel import EventHandler, Kernel, TerminationReason
from manufacturing_simulator.rng import STREAM_IDS
from manufacturing_simulator.scenario import KernelScenarioConfig, ScenarioEngine
from manufacturing_simulator.serialization import (
    FORMAT_VERSION,
    EventRecord,
    FinalState,
    canonical_bytes,
    check_events,
    check_state,
    decode_events_document,
    decode_state_document,
    digest,
    event_document,
    events_document,
    input_digest,
    payload_document,
    project_records,
    project_world,
    state_document,
)
from manufacturing_simulator.validation import require_int, require_text, require_time

RNG_ALGORITHM = "numpy.PCG64/SeedSequence(master_seed, spawn_key=(stream_id,)); " + (
    ",".join(f"{name.value}={number}" for name, number in STREAM_IDS.items())
)

ReplayHandlers = Callable[[], Mapping[str, EventHandler]]
"""Returns a fresh handler bundle on every call (never a shared, pre-used one)."""


@dataclass(frozen=True)
class ReplayIdentity:
    """What must be equal before two runs may be compared as replays of each other."""

    source_id: str
    handler_bundle_id: str
    numpy_version: str
    rng_algorithm: str

    def __post_init__(self) -> None:
        require_text(self.source_id, "source_id")
        require_text(self.handler_bundle_id, "handler_bundle_id")
        require_text(self.numpy_version, "numpy_version")
        require_text(self.rng_algorithm, "rng_algorithm")

    @classmethod
    def for_current_runtime(
        cls, source_id: str, handler_bundle_id: str
    ) -> ReplayIdentity:
        return cls(source_id, handler_bundle_id, np.__version__, RNG_ALGORITHM)


@dataclass(frozen=True)
class ReplaySpec:
    """A validated, immutable replay request. ``until`` defaults to the horizon."""

    config: KernelScenarioConfig
    identity: ReplayIdentity
    max_events: int
    initial_state: Payload = ()
    until: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.config, KernelScenarioConfig):
            raise InvalidConfigurationError("config must be a KernelScenarioConfig")
        if not isinstance(self.identity, ReplayIdentity):
            raise InvalidConfigurationError("identity must be a ReplayIdentity")
        require_int(
            self.max_events, "max_events", minimum=1, error=InvalidConfigurationError
        )
        object.__setattr__(self, "initial_state", freeze_payload(self.initial_state))
        until = self.config.horizon if self.until is None else self.until
        require_time(until, "until")
        if until > self.config.horizon:
            raise InvalidTimeError(
                f"until {until} is beyond the scenario horizon {self.config.horizon}"
            )
        object.__setattr__(self, "until", until)


_DIGEST = re.compile(r"[0-9a-f]{64}")


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise CanonicalizationError(message)


def validate_result(result: ReplayResult) -> None:
    """Reject any result that no real replay could have produced (digests unused)."""
    _need(isinstance(result, ReplayResult), "not a ReplayResult")
    _need(result.format_version == FORMAT_VERSION, "unsupported replay format")
    _need(isinstance(result.identity, ReplayIdentity), "malformed replay identity")
    _need(
        isinstance(result.input_digest, str)
        and _DIGEST.fullmatch(result.input_digest) is not None,
        "input_digest must be 64 lowercase hex characters",
    )
    _need(isinstance(result.termination, TerminationReason), "malformed termination")
    until = require_int(result.until, "until", minimum=0, error=CanonicalizationError)
    budget = require_int(
        result.max_events, "max_events", minimum=1, error=CanonicalizationError
    )
    events = check_events(result.events)
    state = check_state(result.final_state)
    executed = {e.sequence for e in events}
    waiting = {e.sequence for e in state.pending}
    # Proven from the ACTUAL sequence IDs, in time proportional to the input: n distinct
    # non-negative IDs whose maximum is n-1 are exactly 0..n-1. The claimed next_sequence
    # is compared with n and never used to size or iterate anything.
    issued = executed | waiting
    total = len(events) + len(state.pending)
    _need(
        executed.isdisjoint(waiting)
        and state.next_sequence == total
        and (total == 0 or max(issued) == total - 1),
        "event sequences must be exactly 0..next_sequence-1, each executed or pending",
    )
    _need(
        state.now == (events[-1].time if events else 0),
        "the clock must equal the time of the last executed event",
    )
    _need(state.now <= until, "an event ran beyond the declared horizon")
    _need(len(events) <= budget, "more events ran than the declared budget")
    _need(
        all(e.time >= state.now for e in state.pending),
        "a pending event is in the past",
    )
    waiting_first = state.pending[0] if state.pending else None
    reason = result.termination
    if reason is TerminationReason.QUEUE_EMPTY:
        _need(waiting_first is None, "QUEUE_EMPTY with pending events")
    elif reason is TerminationReason.HORIZON_REACHED:
        _need(
            waiting_first is not None and waiting_first.time > until,
            "HORIZON_REACHED needs a pending event beyond the horizon",
        )
    else:
        _need(
            waiting_first is not None
            and waiting_first.time <= until
            and len(events) == budget,
            "EVENT_LIMIT_REACHED needs the full budget used and work still due",
        )


@dataclass(frozen=True)
class ReplayResult:
    """One completed replay: identities, limits, termination and the semantic data."""

    identity: ReplayIdentity
    input_digest: str
    termination: TerminationReason
    events: tuple[EventRecord, ...]
    final_state: FinalState
    until: int
    max_events: int
    format_version: str = FORMAT_VERSION

    def __post_init__(self) -> None:
        validate_result(self)

    @property
    def event_digest(self) -> str:
        return digest(events_document(self.events))

    @property
    def state_digest(self) -> str:
        return digest(state_document(self.final_state))

    def to_json(self) -> str:
        identity = self.identity
        return json.dumps(
            {
                "format": self.format_version,
                "identity": {
                    "source_id": identity.source_id,
                    "handler_bundle_id": identity.handler_bundle_id,
                    "numpy_version": identity.numpy_version,
                    "rng_algorithm": identity.rng_algorithm,
                },
                "input_digest": self.input_digest,
                "until": self.until,
                "max_events": self.max_events,
                "termination": self.termination.value,
                "events": events_document(self.events),
                "state": state_document(self.final_state),
                "event_digest": self.event_digest,
                "state_digest": self.state_digest,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @classmethod
    def from_json(cls, text: str) -> ReplayResult:
        """Strict inverse of :meth:`to_json`; anything else is rejected, never repaired."""

        def reject_constant(name: str) -> NoReturn:
            raise CanonicalizationError(f"non-finite constant {name} in replay output")

        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            found: dict[str, Any] = {}
            for key, value in pairs:
                if key in found:
                    raise CanonicalizationError(
                        f"duplicate key {key!r} in replay output"
                    )
                found[key] = value
            return found

        try:
            raw = json.loads(
                text,
                parse_constant=reject_constant,
                object_pairs_hook=reject_duplicates,
            )
        except json.JSONDecodeError as exc:
            raise CanonicalizationError(f"malformed replay output: {exc}") from exc
        keys = {
            "format",
            "identity",
            "input_digest",
            "until",
            "max_events",
            "termination",
            "events",
            "state",
            "event_digest",
            "state_digest",
        }
        if not isinstance(raw, dict) or set(cast(dict[str, Any], raw)) != keys:
            raise CanonicalizationError("replay output has missing or unknown keys")
        data = cast(dict[str, Any], raw)
        if data["format"] != FORMAT_VERSION:
            raise CanonicalizationError(f"unsupported replay format {data['format']!r}")
        try:
            identity = ReplayIdentity(**cast(dict[str, Any], data["identity"]))
            termination = TerminationReason(data["termination"])
        except (TypeError, ValueError, InvalidConfigurationError) as exc:
            raise CanonicalizationError(f"malformed replay identity: {exc}") from exc
        result = cls(
            identity=identity,
            input_digest=data["input_digest"],
            termination=termination,
            events=decode_events_document(data["events"]),
            final_state=decode_state_document(data["state"]),
            until=data["until"],
            max_events=data["max_events"],
        )
        if (result.event_digest, result.state_digest) != (
            data["event_digest"],
            data["state_digest"],
        ):
            raise CanonicalizationError("replay output digests do not match its data")
        return result


def _require_current_runtime(identity: ReplayIdentity) -> None:
    if (identity.numpy_version, identity.rng_algorithm) != (
        np.__version__,
        RNG_ALGORITHM,
    ):
        raise IncompatibleRuntimeError(
            f"the spec declares numpy {identity.numpy_version!r} / rng "
            f"{identity.rng_algorithm!r} but this process runs numpy "
            f"{np.__version__!r} / rng {RNG_ALGORITHM!r}"
        )


def replay(spec: ReplaySpec, handlers: ReplayHandlers) -> ReplayResult:
    """Run ``spec`` once in a fresh kernel and return its semantic result."""
    if not isinstance(spec, ReplaySpec):
        raise InvalidConfigurationError("spec must be a ReplaySpec")
    _require_current_runtime(spec.identity)
    until = cast(int, spec.until)
    # Canonicalize the input now: a failure here happens before any handler exists.
    input_hash = input_digest(spec.config, spec.initial_state, until, spec.max_events)
    bundle = handlers()
    if not isinstance(bundle, Mapping):
        raise InvalidConfigurationError("the handler factory must return a mapping")
    bundle = dict(bundle)
    world = ScenarioEngine(bundle.keys()).initialize(spec.config)
    world.state.update(spec.initial_state)
    kernel = Kernel(world, bundle)
    try:
        run = kernel.run(until, spec.max_events)
    except HandlerExecutionError as exc:
        raise ReplayExecutionError(
            f"replay failed at sequence {exc.sequence}, time {exc.time}: {exc}",
            sequence=exc.sequence,
            time=exc.time,
            kind=exc.kind,
        ) from exc
    return ReplayResult(
        identity=spec.identity,
        input_digest=input_hash,
        termination=run.termination,
        events=project_records(kernel.records()),
        final_state=project_world(world),
        until=until,
        max_events=spec.max_events,
    )


class ComparisonOutcome(StrEnum):
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    EVENT_MISMATCH = "EVENT_MISMATCH"
    STATE_MISMATCH = "STATE_MISMATCH"
    INCOMPATIBLE_INPUT = "INCOMPATIBLE_INPUT"


@dataclass(frozen=True)
class ReplayComparison:
    outcome: ComparisonOutcome
    detail: str

    @property
    def accepted(self) -> bool:
        """Only a complete, equal run is accepted determinism evidence."""
        return self.outcome is ComparisonOutcome.MATCH


def _bytes(document: object) -> bytes:
    return canonical_bytes(document)


def compare(left: ReplayResult, right: ReplayResult) -> ReplayComparison:
    """Compare two results; only a complete semantic match is ``MATCH``."""
    if not isinstance(left, ReplayResult) or not isinstance(right, ReplayResult):
        raise InvalidConfigurationError("both arguments must be ReplayResult")
    validate_result(left)
    validate_result(right)

    def differs(outcome: ComparisonOutcome, detail: str) -> ReplayComparison:
        return ReplayComparison(outcome, detail)

    incompatible = ComparisonOutcome.INCOMPATIBLE_INPUT
    pairs: tuple[tuple[str, object, object], ...] = (
        ("format_version", left.format_version, right.format_version),
        ("source_id", left.identity.source_id, right.identity.source_id),
        (
            "handler_bundle_id",
            left.identity.handler_bundle_id,
            right.identity.handler_bundle_id,
        ),
        ("numpy_version", left.identity.numpy_version, right.identity.numpy_version),
        ("rng_algorithm", left.identity.rng_algorithm, right.identity.rng_algorithm),
        ("input_digest", left.input_digest, right.input_digest),
        ("until", left.until, right.until),
        ("max_events", left.max_events, right.max_events),
    )
    for name, a, b in pairs:
        if a != b:
            return differs(incompatible, f"{name} differs: {a!r} vs {b!r}")
    for index, (a, b) in enumerate(zip_longest(left.events, right.events)):
        if (
            a is None
            or b is None
            or _bytes(event_document(a)) != _bytes(event_document(b))
        ):
            return differs(
                ComparisonOutcome.EVENT_MISMATCH,
                f"first differing event is index {index}: {a} vs {b}",
            )
    a_state, b_state = left.final_state, right.final_state
    for name, a, b in (
        ("now", a_state.now, b_state.now),
        ("next_sequence", a_state.next_sequence, b_state.next_sequence),
        (
            "local_state",
            _bytes(payload_document(a_state.local_state)),
            _bytes(payload_document(b_state.local_state)),
        ),
        (
            "pending",
            _bytes([event_document(e) for e in a_state.pending]),
            _bytes([event_document(e) for e in b_state.pending]),
        ),
    ):
        if a != b:
            return differs(
                ComparisonOutcome.STATE_MISMATCH, f"final state {name} differs"
            )
    if left.termination is TerminationReason.EVENT_LIMIT_REACHED:
        return ReplayComparison(
            ComparisonOutcome.PARTIAL_MATCH,
            f"equal prefix of {len(left.events)} events; both runs stopped at their "
            "event budget, so this is not accepted determinism",
        )
    return ReplayComparison(
        ComparisonOutcome.MATCH,
        f"{len(left.events)} events, termination {left.termination.value}",
    )


def check_determinism(spec: ReplaySpec, handlers: ReplayHandlers) -> ReplayComparison:
    """Replay twice, each time in a fresh kernel, and compare the two results."""
    return compare(replay(spec, handlers), replay(spec, handlers))


__all__ = [
    "RNG_ALGORITHM",
    "ComparisonOutcome",
    "PayloadValue",
    "ReplayComparison",
    "ReplayHandlers",
    "ReplayIdentity",
    "ReplayResult",
    "ReplaySpec",
    "check_determinism",
    "compare",
    "replay",
    "validate_result",
]
