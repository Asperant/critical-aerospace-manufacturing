"""WP-CORE-001 pure domain values, before persistence and query contracts.

Identity and revision are opaque, nonblank strings, consistent with repository
models. No UUID scheme, numeric revision sequence or revision allocator is
implied. Route tuple order is traversal order; an operation class may recur,
but each visit has its own identity. These models do not execute transitions.
"""

from collections.abc import Sequence
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

Identity = Annotated[str, StringConstraints(strict=True, pattern=r"\S")]
Revision = Annotated[str, StringConstraints(strict=True, pattern=r"\S")]


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Identity
    revision: Revision


class ProductionOrder(Entity):
    route_id: Identity


class Lot(Entity):
    order_id: Identity


class SerializedComponent(Entity):
    lot_id: Identity


class Equipment(Entity):
    """Equipment reference, without simulated physical state."""


class RouteVisit(Entity):
    route_id: Identity
    operation_class_id: Identity
    equipment_id: Identity


class ManufacturingRoute(Entity):
    visits: tuple[RouteVisit, ...]

    @model_validator(mode="after")
    def consistent_visits(self) -> Self:
        if any(visit.route_id != self.id for visit in self.visits):
            raise ValueError("visit references a different route")
        if len({visit.id for visit in self.visits}) != len(self.visits):
            raise ValueError("route visit identities must be distinct")
        return self


def validate_references(
    *,
    orders: Sequence[ProductionOrder],
    lots: Sequence[Lot],
    components: Sequence[SerializedComponent],
    routes: Sequence[ManufacturingRoute],
    equipment: Sequence[Equipment],
) -> None:
    """Check a complete local entity set, never a partial query response.

    IDs are unique per entity kind. This does not check live membership,
    eligibility, revision freshness or authorize canonical state changes.
    """
    for entities in (orders, lots, components, routes, equipment):
        if len({entity.id for entity in entities}) != len(entities):
            raise ValueError("duplicate entity identity")
    route_ids = {route.id for route in routes}
    order_ids = {order.id for order in orders}
    lot_ids = {lot.id for lot in lots}
    equipment_ids = {item.id for item in equipment}
    if any(order.route_id not in route_ids for order in orders):
        raise ValueError("order references an unknown route")
    if any(lot.order_id not in order_ids for lot in lots):
        raise ValueError("lot references an unknown production order")
    if any(component.lot_id not in lot_ids for component in components):
        raise ValueError("component references an unknown lot")
    if any(
        visit.equipment_id not in equipment_ids
        for route in routes
        for visit in route.visits
    ):
        raise ValueError("visit references unknown equipment")
