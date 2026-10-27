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
The versioned runner uses the selected Alembic migration tool with the Psycopg
3 driver; it applies migrations atomically, with an advisory lock and a
checksum/runtime-role ledger. Status is
inspectable without mutation:

```text
CORE_MIGRATION_DSN='postgresql://...' python -m manufacturing_core.migrate --status
```

The service package also publishes `role_matrix.json`. It contains only the
canonical schema and environment-variable bindings; it contains no credentials
and never creates roles. A deployment must provide explicit restricted roles for
`core`, `twin`, `automation` and `ai` before applying the matrix. Missing,
administrative, duplicate or cross-schema bindings fail closed.

The runner does not provision the platform or claim shared-host/integration
readiness. CD must execute the migration command and retain the status output.

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

The migration grants runtime only schema USAGE and SELECT/INSERT on the domain,
lifecycle-state and material-hold tables. `0004_material_hold` adds narrowly
scoped UPDATE privileges: only the revision/state columns used by the Core
transition surface and the release fields of `material_hold` are writable;
identity, ownership, command-ledger, DDL, DELETE and cross-schema access remain
protected. The repository inserts and reads domain entities together with their
initial lifecycle state; transition mutation is exposed only through the
explicit `CoreTransitionService` command handlers. Caller transactions can
group inserts; a single route plus its visits is atomic. Query/API contracts,
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

## Authorization policy (slice 1) — WP-SEC-003

`manufacturing_core.authz` is a pure, deny-by-default decision:
`evaluate(principal_permissions, action)` returns `Decision.ALLOW` only when
`action` is in the closed `PROTECTED_ACTIONS` catalog and the caller's
permissions contain that action's exact, case-sensitive `required_permission`.
Unknown or non-string actions, missing or malformed permission collections
(including a bare string), and any inexact or wildcard permission return
`Decision.DENY`.

The catalog lists the candidate Action Catalog members from the architecture
specification, each with an action identifier, a required permission and a
reserved `core_entrypoint` reference. The permission names are provisional,
because the exact RBAC matrix is still an open question, and the entrypoints
are not bound to code: action-specific Core transition handlers remain separate
from this acceptance surface. The module reads no
identity, token, configuration or secret and is not wired to HTTP, an identity
provider or Automation. It is unit-level evidence only; it does not claim
AV-SCEN-04, BENCH-RQ3-001 or the integrated TEST-SEC-AUTHZ-NEG suite.

### Enforcement mechanism (slice 2) — WP-SEC-003

`manufacturing_core.enforcement` puts the slice 1 policy in front of a protected
handler. `authorize(permissions, action)` returns only on ALLOW and otherwise raises
`AuthorizationDenied`; `enforce(permissions, action, handler, *args, **kwargs)`
authorizes first and then calls the handler exactly once, never on DENY. Any fault
while evaluating also denies. `EnforcementRegistry.bind(action)` decorates a handler
(the guarded callable takes the permissions as its first argument), and
`unbound_actions()` / `assert_fully_bound()` report catalogued protected actions that
have no binding.

No action-specific transition handler is bound here; those handlers bind themselves
when written. There is no role-to-permission
mapping, no Automation binding and no HTTP or IdP wiring, and nothing here claims
API or integration acceptance (TEST-SEC-AUTHZ-NEG at INTEGRATION, AV-SCEN-04 and
BENCH-RQ3-001 remain unexecuted).

## Typed command acceptance — WP-CORE-003

`manufacturing_core.commands` publishes the v1 typed operational command
contract for `PlaceLotOnHold`, `ReleaseMaterialHold`, `DispatchLot` and
`CreateMaintenanceWorkOrder`. Every command carries immutable command/version
identity, idempotency key, explicit World/Correlation/Causation IDs, target and
revision/freshness preconditions. The published registry declaration and
fixtures live in `packages/contracts/registry/` and
`services/manufacturing-core/contracts/v1/`.

`PostgresCommandLedger` is separate from the event-consumer ledger. It reserves
an idempotency key and writes a durable `CommandOutcome` in the same transaction
as the optional caller-supplied Core mutation. A retry with the same immutable
command returns the original outcome; a different fingerprint returns
`CONFLICT`. Precondition failures are `REJECTED` (`STALE`, `WORLD_MISMATCH`,
etc.); unclassifiable effects are `UNRESOLVED`. `ACCEPTED` is only a durable
acceptance and always has `NOT_VERIFIED` effect status. Operators query the
outcome before retrying unresolved work, and must verify the canonical event or
effect separately. This slice emits no event, so Core outbox relay integration
remains a separate capability; an event-emitting mutation must keep its outbox
write inside this transaction boundary.
## Lifecycle component

`manufacturing_core.lifecycle` provides the immutable `ProductionOrderState`,
`LotState`, and `SerializedComponentState` records. Lifecycle and execution
state are separate dimensions. `manufacturing_core.transitions` owns the
explicit legal matrices, stable rejection codes, terminal-state protection,
dispatch/resource/active-hold guards and the explicit ReworkDirective guard.
It does not execute rework history or split/merge genealogy.

`CoreTransitionService` runs `PlaceLotOnHold`, `ReleaseMaterialHold` and
`DispatchLot` through the existing `PostgresCommandLedger`; the command
reservation, durable outcome and canonical mutation share one transaction.
Same-fingerprint retries return the durable prior outcome, conflicts do not
execute a second effect, and stale revisions are rejected both before and
under the row lock. Hold placement creates a first-class `ACTIVE` row without
changing lot lifecycle or execution. Release is authorized, target-bound and
retains the row as `RELEASED` history. A partial unique index permits one active
hold per lot, and active holds block dispatch.

The forward-only `0004_material_hold` migration creates the hold table, status
invariants, command foreign keys and history index. Outbox/event publication is
not implemented here; it remains WP-CORE-005. Physical execution remains the
Simulator boundary.

## Lifecycle transition verification — WP-CORE-002

Pure negative-first matrix coverage is in
`tests/test_transitions.py`. Disposable PostgreSQL coverage is in
`tests/persistence/test_transitions.py` and extends the migration/role tests
with atomic hold/release, idempotency, retained history, revision preservation,
authorization denial and dispatch rejection. Run the local slice with:

```
uv run --project ci --locked python -m pytest \
  -c services/manufacturing-core/pyproject.toml \
  services/manufacturing-core/tests -m 'not integration' -q
```

Run the real PostgreSQL 18 slice only with an explicitly disposable
`CI_PG_DSN` and `CORE_TEST_DISPOSABLE=1`; missing configuration is not a pass:

```
CORE_TEST_DISPOSABLE=1 CI_PG_DSN='<disposable-admin-dsn>' \
  uv run --project ci --locked python -m pytest \
  -c services/manufacturing-core/pyproject.toml \
  services/manufacturing-core/tests/persistence -m integration -q
```
