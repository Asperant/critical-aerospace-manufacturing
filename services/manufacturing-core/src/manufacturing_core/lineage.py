"""WP-CORE-004 internal split/merge facts, not commands or a current-state store.

Explicit lot references define causal order; no global sequence or receipt-time
ordering is inferred. Revisions are opaque. Merge eligibility/policy and real
canonical producer binding remain the caller's responsibilities.
"""

from datetime import UTC
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from manufacturing_core.domain import Entity, Identity


class LotMembershipSnapshot(BaseModel):
    """Historical membership of one lot, without cloning component entities."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    world_id: Identity
    lot_id: Identity
    component_ids: Annotated[tuple[Identity, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def distinct_components(self) -> Self:
        if len(set(self.component_ids)) != len(self.component_ids):
            raise ValueError("duplicate serialized component in lot snapshot")
        return self


class LotLineageEvent(Entity):
    """Snapshot of a source fact; this is not a published event-envelope schema.

    occurred_at is domain occurrence time, effective_from is business effectivity,
    and recorded_at is recording time. None is substituted for another. Links
    remain historical facts after a successor lot is itself split or merged.
    """

    kind: Literal["SPLIT", "MERGE"]
    source_event_id: Identity
    world_id: Identity
    reason: Identity
    occurred_at: AwareDatetime
    effective_from: AwareDatetime
    recorded_at: AwareDatetime
    parent_lot_ids: Annotated[tuple[Identity, ...], Field(min_length=1)]
    children: Annotated[tuple[LotMembershipSnapshot, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def unambiguous_relationship(self) -> Self:
        parents = set(self.parent_lot_ids)
        children = {child.lot_id for child in self.children}
        if len(parents) != len(self.parent_lot_ids) or len(children) != len(
            self.children
        ):
            raise ValueError("duplicate parent or child lot identity")
        if parents & children:
            raise ValueError("a lot cannot be its own successor")
        if self.kind == "SPLIT":
            if len(parents) != 1 or len(children) < 2:
                raise ValueError("split requires one parent and at least two children")
        elif len(parents) < 2 or len(children) != 1:
            raise ValueError("merge requires at least two parents and one child")
        components: set[str] = set()
        for child in self.children:
            if child.world_id != self.world_id:
                raise ValueError("lineage cannot cross worlds")
            if components.intersection(child.component_ids):
                raise ValueError("component cloned into multiple successor lots")
            components.update(child.component_ids)
        return self

    @property
    def parent_child_links(self) -> tuple[tuple[str, str], ...]:
        """Explicit edges; their provenance/times are retained by this event."""
        return tuple(
            (parent, child.lot_id)
            for parent in self.parent_lot_ids
            for child in self.children
        )


class LotLineageHistory(BaseModel):
    """Complete local lineage closure with explicit root membership snapshots.

    Roots declare the boundary of the supplied history, not inferred lot births.
    Events stay in supplied order. Validation follows explicit ancestry
    regardless of delivery order; independent events need no total ordering.
    This is not an eligibility, policy, dispatch or authoritative mutation API.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    world_id: Identity
    roots: tuple[LotMembershipSnapshot, ...]
    events: tuple[LotLineageEvent, ...] = ()

    @model_validator(mode="after")
    def conserved_acyclic_history(self) -> Self:
        memberships: dict[str, LotMembershipSnapshot] = {}
        root_components: set[str] = set()
        for root in self.roots:
            if root.world_id != self.world_id:
                raise ValueError("lineage cannot cross worlds")
            if root.lot_id in memberships:
                raise ValueError("duplicate root lot identity")
            if root_components.intersection(root.component_ids):
                raise ValueError("component belongs to multiple root lots")
            memberships[root.lot_id] = root
            root_components.update(root.component_ids)

        produced_by: dict[str, LotLineageEvent] = {}
        consumed: set[str] = set()
        record_ids: set[str] = set()
        event_ids: set[str] = set()
        for event in self.events:
            if event.world_id != self.world_id:
                raise ValueError("lineage cannot cross worlds")
            if event.id in record_ids or event.source_event_id in event_ids:
                raise ValueError("duplicate lineage record or source event identity")
            record_ids.add(event.id)
            event_ids.add(event.source_event_id)
            for child in event.children:
                if child.lot_id in memberships or child.lot_id in produced_by:
                    raise ValueError("successor lot identity already exists")
                produced_by[child.lot_id] = event
            for parent in event.parent_lot_ids:
                if parent in consumed:
                    raise ValueError("parent lot consumed by multiple lineage events")
                consumed.add(parent)
        if consumed - (memberships.keys() | produced_by.keys()):
            raise ValueError("unknown parent lot; complete lineage closure required")

        pending = list(self.events)
        while pending:
            ready = [
                event
                for event in pending
                if all(parent in memberships for parent in event.parent_lot_ids)
            ]
            if not ready:
                raise ValueError("cyclic or impossible lot ancestry")
            for event in ready:
                parent_components: set[str] = set()
                for parent in event.parent_lot_ids:
                    material = memberships[parent]
                    if parent_components.intersection(material.component_ids):
                        raise ValueError("merge parents contain overlapping components")
                    parent_components.update(material.component_ids)
                    producer = produced_by.get(parent)
                    if producer is not None and (
                        event.occurred_at.astimezone(UTC)
                        < producer.occurred_at.astimezone(UTC)
                        or event.effective_from.astimezone(UTC)
                        < producer.effective_from.astimezone(UTC)
                    ):
                        raise ValueError("successor event precedes its parent ancestry")
                child_components = {
                    component
                    for child in event.children
                    for component in child.component_ids
                }
                if parent_components != child_components:
                    raise ValueError(
                        "split/merge must conserve serialized component identities"
                    )
                memberships.update((child.lot_id, child) for child in event.children)
                pending.remove(event)
        return self

    def append(self, event: LotLineageEvent) -> "LotLineageHistory":
        """Return extended immutable facts; never update earlier links/membership."""
        return LotLineageHistory(
            world_id=self.world_id, roots=self.roots, events=(*self.events, event)
        )
