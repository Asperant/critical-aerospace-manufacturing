"""WP-CORE-004: TEST-CORE-GENEALOGY split/merge model subset, synthetic values."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from manufacturing_core.lineage import (
    LotLineageEvent,
    LotLineageHistory,
    LotMembershipSnapshot,
)
from pydantic import ValidationError

BASE = datetime(2026, 10, 24, 10, tzinfo=UTC)


def material(lot: str, *components: str) -> LotMembershipSnapshot:
    return LotMembershipSnapshot(
        world_id="WORLD-1", lot_id=lot, component_ids=components
    )


def event(
    kind: str,
    parents: tuple[str, ...],
    children: tuple[LotMembershipSnapshot, ...],
    n: int,
) -> LotLineageEvent:
    return LotLineageEvent.model_validate(
        {
            "id": f"REL-{n}",
            "revision": "opaque-revision",
            "kind": kind,
            "source_event_id": f"EVENT-{n}",
            "world_id": "WORLD-1",
            "reason": "Core-recorded material relationship",
            "occurred_at": BASE + timedelta(minutes=n),
            "effective_from": BASE + timedelta(minutes=n, seconds=1),
            "recorded_at": BASE + timedelta(days=1, minutes=n),
            "parent_lot_ids": parents,
            "children": children,
        }
    )


def split() -> LotLineageEvent:
    return event("SPLIT", ("ROOT",), (material("A", "C1"), material("B", "C2")), 1)


def merge() -> LotLineageEvent:
    return event("MERGE", ("A", "B"), (material("FINAL", "C1", "C2"),), 2)


def history(*events: LotLineageEvent) -> LotLineageHistory:
    return LotLineageHistory(
        world_id="WORLD-1", roots=(material("ROOT", "C1", "C2"),), events=events
    )


def test_valid_split_preserves_parent_and_component_identities() -> None:
    result = history(split())
    assert result.roots == (material("ROOT", "C1", "C2"),)
    assert result.events[0].parent_child_links == (("ROOT", "A"), ("ROOT", "B"))
    assert result.events[0].source_event_id == "EVENT-1"
    assert {c for child in result.events[0].children for c in child.component_ids} == {
        "C1",
        "C2",
    }


def test_valid_merge_retains_both_source_lots() -> None:
    sources = (material("A", "C1"), material("B", "C2"))
    result = LotLineageHistory(world_id="WORLD-1", roots=sources, events=(merge(),))
    assert result.roots == sources
    assert result.events[0].parent_child_links == (("A", "FINAL"), ("B", "FINAL"))
    assert result.events[0].children == (material("FINAL", "C1", "C2"),)


def test_multi_generation_split_merge_diamond_preserves_all_ancestry() -> None:
    first = event(
        "SPLIT", ("ROOT",), (material("A", "C1", "C2"), material("B", "C3")), 1
    )
    second = event("SPLIT", ("A",), (material("A1", "C1"), material("A2", "C2")), 2)
    third = event("MERGE", ("A1", "B"), (material("M", "C1", "C3"),), 3)
    fourth = event("MERGE", ("M", "A2"), (material("FINAL", "C1", "C2", "C3"),), 4)
    # Delayed/out-of-order delivery must not imply different ancestry.
    delivered = (fourth, third, second, first)
    result = LotLineageHistory(
        world_id="WORLD-1",
        roots=(material("ROOT", "C1", "C2", "C3"),),
        events=delivered,
    )
    assert result.events == delivered
    assert {edge for fact in result.events for edge in fact.parent_child_links} == {
        ("ROOT", "A"),
        ("ROOT", "B"),
        ("A", "A1"),
        ("A", "A2"),
        ("A1", "M"),
        ("B", "M"),
        ("M", "FINAL"),
        ("A2", "FINAL"),
    }
    assert LotLineageHistory.model_validate_json(result.model_dump_json()) == result


def test_append_preserves_prior_links_and_nested_immutability() -> None:
    original = history(split())
    before = original.model_dump_json()
    extended = original.append(merge())
    assert original.model_dump_json() == before
    assert extended.events[:-1] == original.events
    for model, field in (
        (original, "events"),
        (original.roots[0], "component_ids"),
        (original.events[0], "parent_lot_ids"),
        (original.events[0], "effective_from"),
    ):
        with pytest.raises(ValidationError, match="frozen"):
            setattr(model, field, "replacement")


def test_recording_time_does_not_order_or_replace_domain_effective_time() -> None:
    data = merge().model_dump()
    data["recorded_at"] = BASE - timedelta(days=1)
    later_fact = LotLineageEvent.model_validate(data)
    result = history(later_fact, split())
    assert result.events[0].recorded_at < result.events[1].recorded_at
    assert result.events[0].occurred_at == BASE + timedelta(minutes=2)
    assert result.events[0].effective_from == BASE + timedelta(minutes=2, seconds=1)


def test_independent_events_need_no_global_timestamp_order() -> None:
    other = event("SPLIT", ("OTHER",), (material("X", "C3"), material("Y", "C4")), 2)
    data = other.model_dump()
    data["occurred_at"] = split().occurred_at
    data["effective_from"] = split().effective_from
    other = LotLineageEvent.model_validate(data)
    result = LotLineageHistory(
        world_id="WORLD-1",
        roots=(material("ROOT", "C1", "C2"), material("OTHER", "C3", "C4")),
        events=(other, split()),
    )
    assert result.events == (other, split())


def test_explicit_ancestry_orders_dependent_events_at_same_timestamp() -> None:
    data = merge().model_dump()
    data["occurred_at"] = split().occurred_at
    data["effective_from"] = split().effective_from
    assert history(LotLineageEvent.model_validate(data), split()).events[1] == split()


@pytest.mark.parametrize("field", ["occurred_at", "effective_from"])
def test_successor_cannot_precede_its_source_ancestry(field: str) -> None:
    data = merge().model_dump()
    data[field] = getattr(split(), field) - timedelta(microseconds=1)
    with pytest.raises(ValidationError, match="precedes its parent"):
        history(split(), LotLineageEvent.model_validate(data))


@pytest.mark.parametrize("field", ["occurred_at", "effective_from"])
def test_repeated_local_hour_cannot_hide_backwards_instant_order(field: str) -> None:
    zone = ZoneInfo("America/New_York")
    parent = split().model_dump()
    child = merge().model_dump()
    parent[field] = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1)
    child[field] = datetime(2026, 11, 1, 1, 45, tzinfo=zone, fold=0)
    # 01:45 in the first local hour is earlier than 01:30 in the repeated hour.
    with pytest.raises(ValidationError, match="precedes its parent"):
        history(
            LotLineageEvent.model_validate(parent),
            LotLineageEvent.model_validate(child),
        )


@pytest.mark.parametrize("field", ["occurred_at", "effective_from", "recorded_at"])
def test_naive_semantic_timestamps_rejected(field: str) -> None:
    data = split().model_dump()
    data[field] = "2026-10-24T10:00:00"
    with pytest.raises(ValidationError):
        LotLineageEvent.model_validate(data)


@pytest.mark.parametrize(
    "kind,parents,children",
    [
        ("SPLIT", ("ROOT",), (material("A", "C1", "C2"),)),
        ("SPLIT", ("ROOT", "OTHER"), (material("A", "C1"), material("B", "C2"))),
        ("MERGE", ("ROOT",), (material("A", "C1", "C2"),)),
        ("MERGE", ("ROOT", "OTHER"), (material("A", "C1"), material("B", "C2"))),
    ],
)
def test_invalid_split_merge_cardinality_rejected(
    kind: str, parents: tuple[str, ...], children: tuple[LotMembershipSnapshot, ...]
) -> None:
    with pytest.raises(ValidationError):
        event(kind, parents, children, 1)


@pytest.mark.parametrize("components", [(), ("C1", "C1")])
def test_empty_or_duplicate_membership_rejected(components: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError):
        material("ROOT", *components)


def test_component_cannot_be_cloned_between_successors() -> None:
    with pytest.raises(ValidationError, match="cloned"):
        event("SPLIT", ("ROOT",), (material("A", "C1"), material("B", "C1", "C2")), 1)


@pytest.mark.parametrize("last_component", ["C3", "UNKNOWN"])
def test_lost_or_invented_components_rejected(last_component: str) -> None:
    fact = event(
        "SPLIT", ("ROOT",), (material("A", "C1"), material("B", last_component)), 1
    )
    with pytest.raises(ValidationError, match="conserve"):
        history(fact)


def test_merge_cannot_discard_a_component() -> None:
    fact = event("MERGE", ("A", "B"), (material("FINAL", "C1"),), 2)
    with pytest.raises(ValidationError, match="conserve"):
        LotLineageHistory(
            world_id="WORLD-1",
            roots=(material("A", "C1"), material("B", "C2")),
            events=(fact,),
        )


def test_ambiguous_initial_membership_rejected() -> None:
    with pytest.raises(ValidationError, match="multiple root lots"):
        LotLineageHistory(
            world_id="WORLD-1", roots=(material("A", "C1"), material("B", "C1"))
        )


def test_duplicate_root_identity_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate root"):
        LotLineageHistory(
            world_id="WORLD-1", roots=(material("A", "C1"), material("A", "C2"))
        )


def test_parent_cannot_be_consumed_by_two_events() -> None:
    second = event("SPLIT", ("ROOT",), (material("X", "C1"), material("Y", "C2")), 2)
    with pytest.raises(ValidationError, match="consumed by multiple"):
        history(split(), second)


def test_unknown_ancestry_is_not_silently_treated_as_a_root() -> None:
    with pytest.raises(ValidationError, match="unknown parent"):
        history(merge())


def test_self_ancestry_rejected() -> None:
    with pytest.raises(ValidationError, match="own successor"):
        event("SPLIT", ("ROOT",), (material("ROOT", "C1"), material("B", "C2")), 1)


def test_cycle_rejected_without_inventing_an_ancestry_order() -> None:
    first = event("SPLIT", ("A",), (material("B", "C1"), material("X", "C2")), 1)
    second = event("SPLIT", ("B",), (material("A", "C1"), material("Y", "C2")), 2)
    with pytest.raises(ValidationError, match="cyclic"):
        LotLineageHistory(world_id="WORLD-1", roots=(), events=(first, second))


def test_successor_identity_cannot_reuse_an_existing_root() -> None:
    fact = event("SPLIT", ("ROOT",), (material("OTHER", "C1"), material("B", "C2")), 1)
    with pytest.raises(ValidationError, match="identity already exists"):
        LotLineageHistory(
            world_id="WORLD-1",
            roots=(material("ROOT", "C1", "C2"), material("OTHER", "C3")),
            events=(fact,),
        )


def test_two_producers_cannot_create_the_same_successor() -> None:
    other = event("SPLIT", ("OTHER",), (material("A", "C3"), material("X", "C4")), 2)
    with pytest.raises(ValidationError, match="identity already exists"):
        LotLineageHistory(
            world_id="WORLD-1",
            roots=(material("ROOT", "C1", "C2"), material("OTHER", "C3", "C4")),
            events=(split(), other),
        )


@pytest.mark.parametrize("field", ["id", "source_event_id"])
def test_duplicate_record_or_source_event_identity_rejected(field: str) -> None:
    data = merge().model_dump()
    data[field] = getattr(split(), field)
    with pytest.raises(
        ValidationError, match="duplicate lineage record or source event"
    ):
        history(split(), LotLineageEvent.model_validate(data))


def test_duplicate_parent_or_child_links_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate parent or child"):
        event("MERGE", ("A", "A"), (material("FINAL", "C1"),), 1)
    with pytest.raises(ValidationError, match="duplicate parent or child"):
        event("SPLIT", ("ROOT",), (material("A", "C1"), material("A", "C2")), 1)


@pytest.mark.parametrize("target", ["root", "event", "child"])
def test_cross_world_history_rejected(target: str) -> None:
    if target == "root":
        data = material("ROOT", "C1", "C2").model_dump()
        data["world_id"] = "OTHER"
        with pytest.raises(ValidationError, match="cross worlds"):
            LotLineageHistory(
                world_id="WORLD-1", roots=(LotMembershipSnapshot.model_validate(data),)
            )
    else:
        data = split().model_dump()
        if target == "child":
            data["children"][0]["world_id"] = "OTHER"
        else:
            data["world_id"] = "OTHER"
            for child in data["children"]:
                child["world_id"] = "OTHER"
        with pytest.raises(ValidationError, match="cross worlds"):
            history(LotLineageEvent.model_validate(data))
