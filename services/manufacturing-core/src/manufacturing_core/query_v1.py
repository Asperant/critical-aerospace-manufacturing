"""Transport-free Core order-domain query contract v1; no state mutations."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from manufacturing_core.domain import (
    Equipment,
    Identity,
    Lot,
    ManufacturingRoute,
    ProductionOrder,
    SerializedComponent,
    validate_references,
)

if TYPE_CHECKING:
    from manufacturing_core.repository import CoreRepository

CONTRACT_VERSION: Final = "core.order-query.v1"


class OrderQueryRequestV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:cap:core:order-query-request:v1",
        },
    )

    contract_version: Literal["core.order-query.v1"]
    order_id: Identity


class OrderQueryResultV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:cap:core:order-query-result:v1",
        },
    )

    contract_version: Literal["core.order-query.v1"]
    order: ProductionOrder
    route: ManufacturingRoute
    lots: tuple[Lot, ...]
    components: tuple[SerializedComponent, ...]
    equipment: tuple[Equipment, ...]

    @model_validator(mode="after")
    def complete_references(self) -> Self:
        validate_references(
            orders=(self.order,),
            lots=self.lots,
            components=self.components,
            routes=(self.route,),
            equipment=self.equipment,
        )
        for entities in (self.lots, self.components, self.equipment):
            if tuple(item.id for item in entities) != tuple(
                sorted(item.id for item in entities)
            ):
                raise ValueError("entity collections must be ordered by identity")
        if {item.id for item in self.equipment} != {
            visit.equipment_id for visit in self.route.visits
        }:
            raise ValueError("equipment references must exactly match the route")
        return self


class QueryReferenceError(ValueError):
    """Typed query failure; codes have no implied HTTP mapping."""

    def __init__(
        self, code: Literal["ORDER_NOT_FOUND", "MISSING_ROUTE", "MISSING_EQUIPMENT"]
    ):
        self.code = code
        super().__init__(code)


def query_order_v1(
    repository: CoreRepository,
    request: OrderQueryRequestV1,
    *,
    correlation_id: str | None = None,
) -> OrderQueryResultV1:
    from manufacturing_core.observability import correlation, record

    identity = correlation(correlation_id)
    started = perf_counter()
    try:
        result = _query_order_v1(repository, request)
    except Exception:
        record(identity, "order-query.v1", "FAILED", (perf_counter() - started) * 1000)
        raise
    record(identity, "order-query.v1", "SUCCESS", (perf_counter() - started) * 1000)
    return result


def _query_order_v1(
    repository: CoreRepository, request: OrderQueryRequestV1
) -> OrderQueryResultV1:
    """Read the requested order's complete domain closure in caller's transaction.

    No global snapshot revision or freshness guarantee is implied. Only Core
    calls this repository; consumers receive the declared serialized contract.
    """
    order = repository.get(ProductionOrder, request.order_id)
    if order is None:
        raise QueryReferenceError("ORDER_NOT_FOUND")
    route = repository.get(ManufacturingRoute, order.route_id)
    if route is None:
        raise QueryReferenceError("MISSING_ROUTE")
    # Wire order must not depend on the database's locale/collation.
    lots = tuple(sorted(repository.lots_for_order(order.id), key=lambda lot: lot.id))
    components = tuple(
        sorted(
            (
                component
                for lot in lots
                for component in repository.components_for_lot(lot.id)
            ),
            key=lambda component: component.id,
        )
    )
    equipment = []
    for identity in sorted({visit.equipment_id for visit in route.visits}):
        item = repository.get(Equipment, identity)
        if item is None:
            raise QueryReferenceError("MISSING_EQUIPMENT")
        equipment.append(item)
    return OrderQueryResultV1(
        contract_version=CONTRACT_VERSION,
        order=order,
        route=route,
        lots=lots,
        components=components,
        equipment=tuple(equipment),
    )
