"""Controlled negative cases for replay results, shared by the tests and the evidence
matrix (``evidence/WP-SIM-002/replay_matrix.py``).

Two kinds of negative, kept apart on purpose:

* behaviour differences: real alternative executions, each a VALID result that must
  never compare as ``MATCH`` (several differ only in type, which Python ``==`` hides);
* structural corruptions: results no real replay could produce, in memory and as JSON
  whose digests were recomputed so that a digest cannot certify them; each must be
  rejected, never compared.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from typing import Any

from manufacturing_simulator import (
    CanonicalizationError,
    ComparisonOutcome,
    ReplayResult,
    TerminationReason,
    compare,
    replay,
)
from manufacturing_simulator.serialization import digest
from replay_fixtures import fresh_handlers, make_spec, variant_handlers

EVENT = ComparisonOutcome.EVENT_MISMATCH
STATE = ComparisonOutcome.STATE_MISMATCH

BEHAVIOR_EXPECTED: dict[str, tuple[dict[str, Any], ComparisonOutcome]] = {
    "event payload 1 -> 1.0": ({"tag": 1.0}, EVENT),
    "event payload 1 -> True": ({"tag": True}, EVENT),
    "event payload 1 -> '1'": ({"tag": "1"}, EVENT),
    "event payload value": ({"tag": 2}, EVENT),
    "same-time insertion order": ({"order": "yx"}, EVENT),
    "state 1 -> 1.0": ({"marker": 1.0}, STATE),
    "state 1 -> True": ({"marker": True}, STATE),
    "pending content, same depth": ({"late_tag": "b"}, STATE),
    "one extra event executed at the end": ({"late_time": 4999}, EVENT),
    "extra stream draws": ({"extra_draws": 3}, STATE),
}


def baseline() -> ReplayResult:
    """A complete run that stopped at its horizon with one event still pending."""
    return replay(make_spec(), variant_handlers)


def behavior_outcomes() -> dict[str, ComparisonOutcome]:
    base = baseline()
    outcomes: dict[str, ComparisonOutcome] = {}
    for name, (options, _) in BEHAVIOR_EXPECTED.items():
        other = replay(make_spec(), lambda o=options: variant_handlers(**o))
        outcomes[name] = compare(base, other).outcome
    return outcomes


def object_corruptions() -> dict[str, Callable[[], ReplayResult]]:
    r, done = baseline(), replay(make_spec(), fresh_handlers)
    partial = replay(make_spec(max_events=25), fresh_handlers)
    ev, st = list(r.events), r.final_state
    multi = next(i for i, e in enumerate(ev) if len(e.payload) > 1)
    replace = dataclasses.replace

    def event(index: int, **change: Any) -> ReplayResult:
        copy = list(ev)
        copy[index] = replace(ev[index], **change)
        return replace(r, events=tuple(copy))

    def state(**change: Any) -> ReplayResult:
        return replace(r, final_state=replace(st, **change))

    def pending(**change: Any) -> ReplayResult:
        first = replace(st.pending[0], **change)
        return state(pending=(first, *st.pending[1:]))

    end = TerminationReason
    as_text: Any = "QUEUE_EMPTY"
    partial_text: Any = "EVENT_LIMIT_REACHED"
    as_list: Any = list(ev)
    cut = partial.final_state
    stale = replace(cut.pending[0], time=cut.now - 1)
    twin = replace(st.pending[0], sequence=ev[0].sequence, time=st.pending[0].time + 1)
    return {
        "unsupported format": lambda: replace(r, format_version="x"),
        "upper-case input digest": lambda: replace(
            r, input_digest=r.input_digest.upper()
        ),
        "short input digest": lambda: replace(r, input_digest="ab"),
        "termination as text": lambda: replace(r, termination=as_text),
        "termination as text, incomplete run": lambda: replace(
            partial, termination=partial_text
        ),
        "negative horizon": lambda: replace(r, until=-1),
        "bool horizon": lambda: replace(r, until=True),
        "zero budget": lambda: replace(r, max_events=0),
        "negative clock": lambda: state(now=-1),
        "negative next sequence": lambda: state(next_sequence=-1),
        "clock ahead of the last event": lambda: state(now=st.now + 1),
        "next sequence too small": lambda: state(next_sequence=st.next_sequence - 1),
        "next sequence too large": lambda: state(next_sequence=st.next_sequence + 1),
        "next sequence astronomically large": lambda: state(next_sequence=10**30),
        "hole with a matching counter": lambda: replace(
            r,
            events=(*ev[:5], *ev[6:]),
            final_state=replace(st, next_sequence=st.next_sequence - 1),
        ),
        "events held in a list": lambda: replace(r, events=as_list),
        "pending duplicates an executed sequence": lambda: state(
            pending=(*st.pending, twin)
        ),
        "local state not sorted": lambda: state(local_state=st.local_state[::-1]),
        "reversed events": lambda: replace(r, events=tuple(reversed(ev))),
        "dropped middle event": lambda: replace(r, events=(*ev[:5], *ev[6:])),
        "repeated last event": lambda: replace(r, events=(*ev, ev[-1])),
        "duplicate sequence id": lambda: event(1, sequence=ev[0].sequence),
        "bool sequence": lambda: event(0, sequence=True),
        "empty kind": lambda: event(0, kind=""),
        "payload not sorted": lambda: event(multi, payload=ev[multi].payload[::-1]),
        "pending reuses an executed sequence": lambda: pending(sequence=ev[0].sequence),
        "pending event in the past": lambda: pending(time=0),
        "pending event in the past, incomplete run": lambda: replace(
            partial, final_state=replace(cut, pending=(stale, *cut.pending[1:]))
        ),
        "QUEUE_EMPTY with work pending": lambda: replace(
            r, termination=end.QUEUE_EMPTY
        ),
        "HORIZON_REACHED with nothing pending": lambda: replace(
            done, termination=end.HORIZON_REACHED
        ),
        "EVENT_LIMIT_REACHED under budget": lambda: replace(
            r, termination=end.EVENT_LIMIT_REACHED
        ),
        "event beyond the horizon": lambda: replace(r, until=ev[-1].time - 1),
        "more events than the budget": lambda: replace(r, max_events=len(ev) - 1),
    }


def json_corruptions() -> dict[str, str]:
    """Corrupted JSON; digests are recomputed so only structure can reject them."""
    text = baseline().to_json()
    data = json.loads(text)
    version, kind, records = data["events"]
    head, tail = data["state"][:5], data["state"][5]

    def doc(**change: Any) -> str:
        out = {**data, **change}
        out["event_digest"] = digest(out["events"])
        out["state_digest"] = digest(out["state"])
        return json.dumps(out)

    def events(items: list[Any]) -> list[Any]:
        return [version, kind, items]

    def state(index: int, value: Any) -> list[Any]:
        changed = list(head)
        changed[index] = value
        return [*changed, tail]

    cloned = [list(r) for r in records]
    cloned[1][0] = cloned[0][0]
    float_spelling = json.dumps(data["state"]).replace(
        "0x1.8000000000000p+0", "0x1.8p+0"
    )
    return {
        "unsupported format": doc(format="sim-replay-hash/0"),
        "upper-case input digest": doc(input_digest=data["input_digest"].upper()),
        "bool horizon": doc(until=True),
        "float budget": doc(max_events=1.5),
        "reversed events": doc(events=events(records[::-1])),
        "dropped middle event": doc(events=events([*records[:5], *records[6:]])),
        "repeated last event": doc(events=events([*records, records[-1]])),
        "duplicate sequence id": doc(events=events(cloned)),
        "clock changed": doc(state=state(2, data["state"][2] + 1)),
        "next sequence changed": doc(state=state(4, data["state"][4] + 1)),
        "next sequence astronomically large": doc(state=state(4, 10**30)),
        "hole with a matching counter": doc(
            events=events([*records[:5], *records[6:]]),
            state=state(4, data["state"][4] - 1),
        ),
        "termination changed": doc(termination="QUEUE_EMPTY"),
        "horizon too small": doc(until=records[-1][1] - 1),
        "non-canonical float spelling": doc(state=json.loads(float_spelling)),
        "duplicate top-level key": text.replace('"until":', '"until":1,"until":', 1),
        "duplicate nested key": text.replace(
            '"source_id":', '"source_id":"x","source_id":', 1
        ),
    }


def rejected(build: Callable[[], object]) -> bool:
    """True if ``build`` raises CanonicalizationError; any other outcome is False."""
    try:
        build()
    except CanonicalizationError:
        return True
    return False
