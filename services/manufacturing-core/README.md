# Core initial persistence interface — WP-CORE-001

Internal capability diagnostics: `manufacturing_core.observability.health(dsn,
correlation_id=...)` returns READY/UNAVAILABLE after a real restricted runtime
connection/privilege probe. It does not certify manufacturing/action readiness.
`query_order_v1(..., correlation_id=...)` propagates caller correlation into
structured JSON completion/failure logs with outcome and duration; omitted IDs
are generated. Connection strings, exception text and domain payloads are not
logged. The embedding process configures standard Python log handlers/exporters;
no HTTP endpoint or telemetry platform is introduced.

The first service-owned migration lives in
`src/manufacturing_core/migrations/0001_domain.sql`, included as package data.
The local runner uses the selected Psycopg 3 driver; it applies only this
migration, atomically, with an advisory lock and checksum/runtime-role ledger.
It does not select a shared migration framework, provision the platform,
implement CD wiring, or certify WP-CORE-007 / DN-RT-PG readiness.

## External role and connection contract

An operator supplies an existing PostgreSQL 18+ database and two distinct login
identities. Neither identity may be superuser, CREATEDB, CREATEROLE, REPLICATION
or BYPASSRLS. The runtime identity must not be a member of the migration role.
The migration identity owns `core` and its tables. For initial schema creation
only, it needs CREATE on the target database; alternatively an administrator
precreates an empty `core` schema owned by this migration identity. Revoke
database bootstrap CREATE after initial creation. No role/password provisioning
or shared credentials are embedded in the application or migration.

- `CORE_MIGRATION_DSN`: explicit operator-supplied migration connection string.
- `CORE_RUNTIME_ROLE`: existing runtime role name, quoted as a SQL identifier.
- Run `python -m manufacturing_core.migrate` from an installed service package
  (with the `postgres` extra), or with its `src` on `PYTHONPATH`.
- The application caller supplies its separate runtime DSN to
  `manufacturing_core.database.connect_runtime(dsn)`. There is no fallback DSN.
  The function checks restricted role attributes and refuses Core schema
  ownership, schema CREATE or migration-role membership.

The migration grants runtime only schema USAGE and SELECT/INSERT on the six
domain tables. It grants no ledger, DDL, UPDATE, DELETE, or cross-schema access.
The initial repository inserts and reads domain entities; it does not execute
manufacturing transitions. Caller transactions can group inserts; a single
route plus its visits is atomic. Query/API contracts, lifecycle mutation,
deployment environment/secret binding, broader role provisioning and CD remain
separate later work. This interface does not claim deployment readiness.

## Focused real persistence verification

Use the existing CI PostgreSQL fixture with `CI_POSTGRES_IMAGE=postgres:18-alpine`.
Provide its `CI_PG_DSN` and explicitly set `CORE_TEST_DISPOSABLE=1`, then run:

```
python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence -m integration -q
```

The fixture administrator creates a uniquely named disposable database and two
nonadministrative login roles with generated transient test-only passwords.
Actual schema migration and repository operations connect as those separate
roles, never as administrator. Cleanup affects only fixture-created objects.
The opt-in must never target a shared/production database. Missing configuration
fails the integration tests; it never becomes a passing skip. Pure unit runs
select `-m 'not integration'` and need no database.

## Internal rework history values — WP-CORE-004 slice 1

`manufacturing_core.rework.ComponentExecutionHistory.append_rework(segment)`
returns a new immutable value containing the original route/execution snapshot
and a separate, directive-linked rework segment. Earlier segments are retained.
Each execution has its own identity, component/lot references and aware start/end
timestamps. Duplicate execution/directive identities, an unknown origin/return
visit, a mismatched rework-route revision or a different component are rejected.
Tuple order is append order; timestamps retain occurrence time without asserting
cross-event arrival order. Approval/policy states and rework counts are recorded
from the caller, without choosing numeric limits or treating a stored state as
execution permission.

This is an internal component-scoped domain value API, not the
`ExecuteApprovedReworkDirective` contract or its handler. It does not persist,
dispatch, alter membership/lifecycle, authenticate approval or execute a directive.
Core's canonical lifecycle/authorization caller must supply validated facts before
future integration; DEP-029 remains HARD/INTEGRATION at COMPONENT_READY. The initial
database schema and published order-query contracts are unchanged.

## Append-only rework persistence — WP-CORE-004 slice 2

With the same explicit migration DSN and restricted runtime role as above, run
`python -m manufacturing_core.rework_migrate`. This verifies/applies the unchanged
initial domain migration first, then atomically applies the additive
`0002_rework_history.sql`. A separate checksum/runtime-role ledger preserves the
initial runner's single-migration contract. Replays verify both ledgers; a changed
checksum or runtime-role binding fails closed. No platform roles are provisioned.

`ReworkHistoryRepository(connection)` provides only `create(history)`,
`append_rework(component_id, segment)` and `get(component_id)`. Component, lot and
equipment references use existing Core identities. Route snapshots are stored per
segment with their original identities, revisions and ordered visits; they never
overwrite current route definitions. Directives are linked to their segment and
prior component execution through foreign keys. Execution occurrence times use
PostgreSQL `timestamptz`; caller model values remain unchanged.

Each create/append uses a transaction (a savepoint inside a caller transaction)
and a per-component transaction advisory lock. Append reads and validates the
existing history before inserting the next segment. Duplicate creation is an
error, with no replace/upsert path. Any failure rolls back all rows of that call;
the caller's outer rollback also rolls back successful nested calls. Runtime
grants on the five history tables are SELECT/INSERT only; there is no runtime
UPDATE/DELETE/TRUNCATE or migration-ledger access. Errors propagate to the caller.

This is internal storage of caller-validated history, not protected rework
execution, a lifecycle transition or active membership management. Integration
still requires the actual canonical producer/authorization binding under DEP-029.
No schema deployment is automatic. A code rollback can leave the additive tables
intact; never delete history to roll back an application version.

Focused database verification uses the existing disposable-DB opt-in:

```
python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_rework_persistence.py -m integration -q
```

Provide `CI_PG_DSN` and `CORE_TEST_DISPOSABLE=1` only for a disposable PostgreSQL
18 test administrator, as above. These tests create another isolated database
using the existing test roles and drop it on exit; original-schema fixtures and
shared databases are untouched.

## Split/merge lineage values — WP-CORE-004 slice 3

`manufacturing_core.lineage` contains frozen `LotMembershipSnapshot`,
`LotLineageEvent` and `LotLineageHistory` values. A split records one source lot
and at least two fresh successor lots; a merge records at least two source lots
and one fresh successor. Component identities are references, never copied into
new serialized-component entities. Each operation conserves the exact component
set; successor memberships cannot overlap. Original lot snapshots and events
remain intact, including after later generations split or merge again.

The supplied roots explicitly bound a complete local history closure; no unknown
parent is silently promoted to a root. Lot identities have one producer and at
most one split/merge consumer within that closure. Cycles, reused successor IDs,
duplicate source-event/record IDs and cross-world facts are rejected. These
structural checks do not decide product/route/quality/capacity compatibility or
authorize a merge; a Core caller must supply the already-governed facts.

Each fact retains its source-event identity, opaque revision, reason, world,
`occurred_at`, `effective_from` and `recorded_at`. All three times are aware and
remain separate. A successor cannot occur or become effective before its
explicit producer ancestry (comparing UTC instants, including repeated local
hours); equality is allowed because the lot links already
order dependent facts. Recording time never substitutes for occurrence time.
There is no global sequence assumption: unrelated facts can share timestamps,
and complete out-of-order input is validated by ancestry without reordering or
rewriting the supplied facts. Roots do not invent birth timestamps. Permanent
lineage links are not expiring membership intervals or a generic temporal engine.

`history.append(event)` returns a new validated value, preserving the previous
history. This slice adds no database tables, repository path, command handler,
current-state update, simulation-time conversion or external event/query contract.
Canonical envelope sequencing and producer/eligibility binding remain at their
existing integration boundaries. Run only `tests/test_lineage.py` for the focused
model checks; no database is required.


## Relational lineage snapshots — WP-CORE-004 slice 4

`LotLineageRepository.create(history)`, `append(world_id, event)` and
`get(world_id)` persist the slice 3 values in normalized event, lot snapshot,
component membership and parent relation tables. One stored complete local
closure is keyed by its model's `world_id`; roots are fixed at creation. This is
internal history storage, not a public ingestion/query contract. Canonical lot
and component references must already exist; current component membership is
never reassigned. No protected action or merge-eligibility decision is added.

Apply the additive migration with explicit `CORE_MIGRATION_DSN` and
`CORE_RUNTIME_ROLE`, as for the other scoped migration:

```
python -m manufacturing_core.lineage_migrate
```

The unchanged base migration is verified first. A separate checksum ledger and
the existing migration lock keep this additive migration independently replayable
alongside rework storage. Runtime receives SELECT/INSERT only. Create/append use
per-world transaction locks and savepoints; callers retain outer rollback control.
All inputs are revalidated by the complete lineage model, including ancestry,
world isolation and exact component conservation, before insertion. There is no
update/delete/upsert repository path. Delivery positions retain tuple ordering,
including out-of-order complete ancestry; timestamps remain separate PostgreSQL
`timestamptz` instants (original timezone spelling is not stored). Opaque revisions,
source event IDs, parent/child order and component order round-trip unchanged.

With disposable PostgreSQL 18 `CI_PG_DSN` and `CORE_TEST_DISPOSABLE=1`, run only:

```
python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_lineage_persistence.py -m integration -q
```

The fixture creates/drops its own database and uses separate restricted migrator
and runtime roles. No shared schema or existing migration contract is changed.


## Genealogy exposure reads — WP-CORE-004

`GenealogyQueries(connection)` provides a controlled transport-free read interface
for Core callers. It adds no HTTP endpoints, UI, command execution or database
writes. Callers own authorization and transaction isolation; a result is a read
of stored facts, not certification of producer completeness or current membership.

- `rework_history(component_id)` returns immutable original/rework segments in
  persisted append/visit order, preserving directive linkage, execution IDs,
  equipment references and historical route revisions.
- `lot(LotTraceRequest(world_id=..., lot_id=..., direction="BACKWARD"))` traverses
  complete ancestry; `FORWARD` traces descendant lot impact. Relational recursive
  traversal deduplicates diamonds without a depth cutoff. Full event parent/child
  membership snapshots remain attached, including sibling/merge context.
- `component(ComponentTraceRequest(world_id=..., component_id=...))` starts at
  every recorded membership of that immutable component identity. `focus_lot_ids`
  lists the component's actual stored memberships. Other merge parents in the
  returned facts are context, not evidence of target membership in those lots.
- `equipment_exposure(EquipmentExposureRequest(...))` returns actual execution
  visits overlapping `[started_at, ended_at)`, optionally restricted by historical
  operation class. Zero-duration visits are included as instants at the start and
  excluded at the end. Planned equipment assignments do not count as exposure.
- `common_equipment_exposure(CohortExposureRequest(component_ids=(...)))` groups
  actual execution references by equipment and operation class. Counts/ratios use
  distinct requested components, preserving separate re-entrant execution IDs.
  Missing history is explicit; it never proves no prior exposure. The ratio's
  denominator is the full requested distinct cohort, including missing histories.

Lineage results order facts causally, then by UTC occurrence/effectivity and
identity between ready independent facts. Receipt time never replaces occurrence
or causality. Each fact retains its original persisted `position`, timestamps,
parent/child tuple order and opaque revision. Lot collections sort by identity;
execution exposure sorts by UTC start/end, component, stored segment/visit and
execution identity. Rework retrieval retains its original supplied ordering.
Unknown world/lot/component history returns `None`; empty equipment exposure
returns `()`. Known identities with no history also return `None`, not a fabricated
empty manufacturing history. Invalid typed requests and real database failures
propagate; missing schemas/unavailability are never silently returned as empty.

Lineage is world-scoped. Existing execution persistence uses global canonical
component identity and has no world field; these queries do not invent world
binding for it. RecipeVersion, inspection/hold/maintenance and protected producer
fields are not synthesized. This interface supports stored WP-CORE-004 facts;
it does not certify the broader Item 25 integration families as implemented.
`ExecuteApprovedReworkDirective` command execution remains unimplemented.

`health(correlation_id=...)` checks SELECT access to both storage surfaces and
reports READY/UNAVAILABLE as read-access health only. Query methods accept an
optional validated `correlation_id` and emit existing structured outcome/duration
telemetry without IDs, payloads, DSNs or exception text. Production freshness and
cross-read snapshot guarantees require caller-managed isolation and producer
bindings. Reads capture relevant immutable lineage event IDs before fetching
snapshots so later supported appends cannot rewrite the selected fact set.

After applying both scoped history migrations, use only the focused query checks:

```
python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_genealogy_queries.py -m integration -q -s
```

Use disposable PostgreSQL 18 `CI_PG_DSN` and `CORE_TEST_DISPOSABLE=1`. The module
creates/drops its own database and rolls back its synthetic fixtures. Its bounded
WP-NORMAL sanity case uses 100 equipment identities and 1,000 terminal lots plus
retained ancestors; 30 ancestry/exposure samples report median/p95/max. This is
local query sanity evidence, not integrated workload acceptance or factory data.
