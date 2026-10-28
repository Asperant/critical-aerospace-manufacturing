# Core order-domain query v1

| Registry field | Declaration |
|---|---|
| Contract ID / version | `core.order-query.v1` / v1 |
| Type / semantics | QUERY; synchronous, read only; transport independent |
| Semantic owner / producer | Asrın Dündar / manufacturing-core only |
| Intended consumers | Simulator, Digital Twin, Scheduler |
| Input schema | `order-query-request.schema.json` |
| Output schema | `order-query.schema.json` |
| Implementation | `OrderQueryRequestV1`, `OrderQueryResultV1`, `query_order_v1` |
| Authority | Core domain read; no command, approval or execution authority |
| Status / dependency | `CONTRACT_READY` for DN-CORE-CONTRACTS/DEP-018, mechanically bound by `evidence/readiness/DN-CORE-CONTRACTS.json` to the merged CORE-001 producer artifacts and current-main checks |
| Security | Internal manufacturing-domain metadata; no credentials or Oracle labels |
| Deprecation | None; initial version, no earlier supported wire contract |

The request names exactly one order. The response carries that order, its route
and visits, its lots and serialized components, and the exact equipment references
needed by the route. Nested entities are the existing Core domain models, not
copies maintained in the contract package. The published schemas are generated
from those models and the two envelope types. Fixtures are deterministic
**SYNTHETIC TEST** examples, not factory observations or seed instructions.

`contract_version` is required and must equal `core.order-query.v1`. Every
identity, reference and revision is a required opaque nonblank string. Revisions
are preserved per entity; there is no numeric comparison, aggregate revision,
freshness guarantee, global snapshot, or counterfactual/world binding. The query
reads the connected Core store in the caller's transaction; callers requiring
one repeatable read view must choose the appropriate transaction boundary.
It does not replace the separately governed scheduling/snapshot contract.

Lots, components and equipment are ordered by identity using Unicode code-point
order, independent of insertion order/database collation. Route `visits` retain
their semantic traversal order, never sorted by visit ID or operation class.
Visit IDs are unique within their route. Revisiting an operation class retains
a distinct visit ID and revision. Identity and revision are never rewritten.

The schemas enforce closed structural shapes and field types. Semantic
validation additionally checks duplicate identities, every cross-entity
reference, collection ordering, and exact required equipment closure; JSON
Schema validation alone does not check referential integrity. Empty lots and
components are permitted for an order with no material yet; a route with no
visits needs no equipment references. Unrelated orders/material are excluded.

Invalid request/response structure or semantics raises Pydantic
`ValidationError`. An absent order raises `QueryReferenceError` with
`ORDER_NOT_FOUND`; a broken stored closure raises `MISSING_ROUTE` or
`MISSING_EQUIPMENT`. Database errors propagate; there is no success-shaped
fallback or implied HTTP status mapping. Reads have no effects to replay,
reserve, approve or execute. Repeated reads may reflect later committed state.
No large artifacts, pagination, history API, service transport or deployment
are introduced by this contract.

Fixture `order-query.normal.json` has CNC then metrology.
Fixture `order-query.reentrant.json` has CNC, metrology, then CNC with distinct
visit IDs in deliberately nonlexicographic traversal order. Both include two
lots and cross-referenced serialized components.

## Bounded SchedulingSnapshot v1

`scheduling-snapshot.v1.schema.json` and `scheduling-snapshot.normal.json`
publish the minimum producer contract bound to DEP-030: an immutable
world/revision/freshness envelope; explicit lot route position and current lot
revision; lot-specific eligible equipment; priority and due date; and current
equipment maintenance state. `current_schedule_version` is included as the
snapshot's current schedule reference. The fixture is a **SYNTHETIC TEST**
example, not a factory observation.

This is a contract slice for the later Twin/Scheduler read surface. It does not
implement Twin export, a scheduler, transport, database assembly, eligibility
calculation, maintenance mutation, or execution authority. Hidden Simulator
Oracle state is explicitly outside the schema.

## Lot operational semantics v1

`lot-operational-semantics.v1.schema.json` and the fixtures
`lot-operational-semantics.reentrant-rework.json` and
`lot-operational-semantics.held.json` publish `core.lot-operational-semantics.v1`
(`SNAPSHOT`, read-only, transport independent, declared consumer Simulator),
bound to DEP-038. The schema is generated from `LotOperationalSemanticsV1` and
reuses the merged domain, lifecycle and rework values; fixtures are **SYNTHETIC
TEST** examples, not factory observations.

One view describes one lot and carries three independent dimensions:

- **Re-entrant lifecycle.** `lifecycle_state` and `execution_state` are separate.
  Revisiting an operation class is a new route visit with its own identity and
  revision; each execution cites exactly one visit. After `STEP_COMPLETED` the
  lot returns to `READY` for its next visit and its lifecycle state is unchanged.
  Visits keep traversal order, never identity order.
- **Hold.** Holds are retained history. At most one hold per lot is `ACTIVE`;
  an active hold is independent of lifecycle and execution state and makes
  dispatch fail with `ACTIVE_HOLD`. `RELEASED` holds carry release time and
  reason. Command identities are not exposed.
- **Rework.** Rework is an explicit directive-linked segment appended to the
  component's immutable execution history. The directive cites a prior origin
  execution and a return visit on the original route and names the rework route
  revision. Scrapped material cannot be reworked and completed material needs a
  governed reopen. The view records facts; it executes and authorizes nothing.

Holds are ordered by placement time then identity; component histories by
component identity; executions keep append order. Revisions are opaque. Route
position stays in `core.scheduling-snapshot.v1`; rework execution, transition
commands, world binding and persistence remain outside this contract.
