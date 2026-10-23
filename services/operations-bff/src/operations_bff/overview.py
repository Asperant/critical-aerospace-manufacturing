"""Manufacturing Overview query path: read ports and deterministic composition.

The BFF only composes what backend Query APIs report. Every item keeps its own
epistemic class, source revision and freshness; nothing is derived into a new
status and nothing is filtered by role. Real adapters for the backend services
are integration work: their Query APIs are not yet canonically bound, so the
ports below are deliberately abstract.
"""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from .actor import ActorContext
from .errors import BadRequest, BffError, Unavailable
from .session import format_timestamp

FRESHNESS_ORDER = {"FRESH": 0, "DEGRADED": 1, "STALE": 2}
ATTENTION_KINDS = (
    "QUALITY_EXCURSION",
    "DEGRADED_EQUIPMENT_RISK",
    "BATCH_TARDINESS",
    "PENDING_APPROVAL",
    "STUCK_WORKFLOW",
    "STALE_TWIN_STATE",
)
EPISTEMIC_CLASSES = frozenset(
    {
        "ACTUAL",
        "OBSERVED",
        "INFERRED",
        "PREDICTED",
        "PLANNED",
        "COUNTERFACTUAL",
        "STALE",
    }
)
MAX_LIMIT = 100


class SourceUnavailable(Exception):
    """A backend Query API could not answer."""


class StaleCursor(BffError):
    """The view changed since the cursor was issued: 400, start again."""

    status = 400
    category = "STALE_STATE"
    error_code = "CURSOR_STALE"


@dataclass(frozen=True)
class OverviewQuery:
    """What a backend needs: world binding, as_of, the session actor, correlation id."""

    world_id: str
    simulation_run_id: str | None
    branch_id: str | None
    as_of: datetime | None
    actor: ActorContext
    correlation_id: str


@dataclass(frozen=True)
class AttentionFact:
    """One attention item exactly as a backend reports it."""

    item_id: str
    kind: str
    epistemic_class: str
    subject_type: str
    subject_id: str
    summary: str


@dataclass(frozen=True)
class SourceSnapshot:
    source: str
    revision: str
    as_of: datetime
    freshness: str
    items: tuple[AttentionFact, ...]


class AttentionReader(Protocol):
    """Read port for one backend Query API, Snapshot or read model."""

    @property
    def name(self) -> str: ...

    def read(self, query: OverviewQuery) -> SourceSnapshot:
        """Raise SourceUnavailable when the backend cannot answer."""
        ...


def _valid(snapshot: SourceSnapshot, name: str) -> bool:
    return (
        snapshot.source == name
        and bool(snapshot.revision.strip())
        and snapshot.as_of.tzinfo is not None
        and snapshot.freshness in FRESHNESS_ORDER
        and all(
            f.kind in ATTENTION_KINDS
            and f.epistemic_class in EPISTEMIC_CLASSES
            and f.item_id.strip()
            and f.subject_type.strip()
            and f.subject_id.strip()
            and f.summary.strip()
            for f in snapshot.items
        )
    )


def _encode_cursor(offset: int, revision: str) -> str:
    raw = json.dumps({"o": offset, "v": revision}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_cursor(cursor: str) -> tuple[int, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        offset, revision = data["o"], data["v"]
    except (ValueError, KeyError, TypeError):
        raise BadRequest("Cursor is not valid") from None
    if not isinstance(offset, int) or offset < 0 or not isinstance(revision, str):
        raise BadRequest("Cursor is not valid")
    return offset, revision


class OverviewService:
    def __init__(
        self, required: AttentionReader, degradable: Sequence[AttentionReader] = ()
    ) -> None:
        readers = [required, *degradable]
        if len({r.name for r in readers}) != len(readers):
            raise ValueError("reader names must be unique")
        self._required = required
        self._degradable = tuple(degradable)

    def get(
        self,
        query: OverviewQuery,
        *,
        limit: int,
        cursor: str | None,
        now: datetime,
        correlation_id: str,
    ) -> dict[str, Any]:
        if not 1 <= limit <= MAX_LIMIT:
            raise BadRequest(f"limit must be between 1 and {MAX_LIMIT}")
        snapshots = self._read_all(query)
        # Order never depends on registration order or backend response order.
        snapshots.sort(key=lambda s: s.source)
        revision = _view_revision(query, snapshots)
        entries = sorted(
            (
                (ATTENTION_KINDS.index(f.kind), f.item_id, s.source, f, s)
                for s in snapshots
                for f in s.items
            ),
            key=lambda e: e[:3],
        )
        offset = 0
        if cursor is not None:
            offset, issued_for = _decode_cursor(cursor)
            if issued_for != revision:
                raise StaleCursor("The overview changed; restart from the first page")
            if offset > len(entries):
                raise BadRequest("Cursor is not valid")
        window = entries[offset : offset + limit]
        more = offset + limit < len(entries)
        least_fresh = max((s.freshness for s in snapshots), key=FRESHNESS_ORDER.get)  # type: ignore[arg-type]
        return {
            "contract_version": "bff.overview-query.v1",
            "meta": {
                "revision": revision,
                "as_of": format_timestamp(min(s.as_of for s in snapshots)),
                "generated_at": format_timestamp(now),
                "freshness": least_fresh,
                "world": _world(query),
                "sources": [
                    {
                        "source": s.source,
                        "revision": s.revision,
                        "as_of": format_timestamp(s.as_of),
                        "freshness": s.freshness,
                    }
                    for s in snapshots
                ],
                "correlation_id": correlation_id,
            },
            "needs_attention": [
                {
                    "item_id": f.item_id,
                    "kind": f.kind,
                    "epistemic_class": f.epistemic_class,
                    "subject": {
                        "entity_type": f.subject_type,
                        "entity_id": f.subject_id,
                    },
                    "summary": f.summary,
                    "source": s.source,
                    "source_revision": s.revision,
                    "freshness": s.freshness,
                }
                for _, _, _, f, s in window
            ],
            "page": {
                "limit": limit,
                "next_cursor": _encode_cursor(offset + limit, revision)
                if more
                else None,
            },
        }

    def _read_all(self, query: OverviewQuery) -> list[SourceSnapshot]:
        # The contract has no way to show a missing source, and a missing source
        # must never look like "nothing needs attention", so any outage is a 503
        # naming the sources. Partial results need a contract extension first.
        results: list[SourceSnapshot] = []
        down: list[str] = []
        required_down = False
        for reader in (self._required, *self._degradable):
            try:
                snapshot = reader.read(query)
            except SourceUnavailable:
                down.append(reader.name)
                required_down = required_down or reader is self._required
                continue
            if not _valid(snapshot, reader.name):
                down.append(reader.name)
                required_down = required_down or reader is self._required
                continue
            results.append(snapshot)
        if down:
            raise Unavailable(
                "A backend needed for the overview is unavailable",
                details={
                    "unavailable_sources": sorted(down),
                    "required": required_down,
                },
            )
        return results


def _world(query: OverviewQuery) -> dict[str, str]:
    world = {"world_id": query.world_id}
    if query.simulation_run_id:
        world["simulation_run_id"] = query.simulation_run_id
    if query.branch_id:
        world["branch_id"] = query.branch_id
    return world


def _view_revision(query: OverviewQuery, snapshots: list[SourceSnapshot]) -> str:
    canonical = json.dumps(
        {
            "world": _world(query),
            "sources": [[s.source, s.revision] for s in snapshots],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "view-" + hashlib.sha256(canonical.encode()).hexdigest()[:16]
