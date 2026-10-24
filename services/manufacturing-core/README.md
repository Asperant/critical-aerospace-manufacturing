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
