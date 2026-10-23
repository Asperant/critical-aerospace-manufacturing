"""Deterministic in-memory read ports built from the contract fixture."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from operations_bff.overview import (
    AttentionFact,
    OverviewQuery,
    SourceSnapshot,
    SourceUnavailable,
)
from test_contract_v1 import load_json


class FakeReader:
    def __init__(self, snapshot: SourceSnapshot) -> None:
        self.snapshot = snapshot
        self._name = snapshot.source
        self.queries: list[OverviewQuery] = []
        self.down = False

    @property
    def name(self) -> str:
        return self._name

    def read(self, query: OverviewQuery) -> SourceSnapshot:
        self.queries.append(query)
        if self.down:
            raise SourceUnavailable
        return self.snapshot

    def with_freshness(self, freshness: str) -> None:
        self.snapshot = replace(self.snapshot, freshness=freshness)


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def from_fixture() -> tuple[FakeReader, FakeReader, dict[str, Any]]:
    """(core reader, twin reader, fixture) with data taken from the fixture."""
    fixture = load_json("overview-query.normal.json")
    readers: dict[str, FakeReader] = {}
    for source in fixture["meta"]["sources"]:
        items = tuple(
            AttentionFact(
                item_id=i["item_id"],
                kind=i["kind"],
                epistemic_class=i["epistemic_class"],
                subject_type=i["subject"]["entity_type"],
                subject_id=i["subject"]["entity_id"],
                summary=i["summary"],
            )
            for i in fixture["needs_attention"]
            if i["source"] == source["source"]
        )
        readers[source["source"]] = FakeReader(
            SourceSnapshot(
                source=source["source"],
                revision=source["revision"],
                as_of=parse(source["as_of"]),
                freshness=source["freshness"],
                items=items,
            )
        )
    return readers["manufacturing-core"], readers["digital-twin-service"], fixture


def many_items(reader: FakeReader, count: int) -> None:
    """Give a reader `count` extra pending approvals (ids sort lexically)."""
    extra = tuple(
        AttentionFact(
            item_id=f"X-{n:03d}",
            kind="PENDING_APPROVAL",
            epistemic_class="ACTUAL",
            subject_type="ApprovalRequest",
            subject_id=f"AR-{n}",
            summary="Approval request awaiting a human decision",
        )
        for n in range(count)
    )
    reader.snapshot = replace(reader.snapshot, items=reader.snapshot.items + extra)
