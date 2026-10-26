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
The versioned runner uses the selected Psycopg 3 driver; it applies migrations
atomically, with an advisory lock and checksum/runtime-role ledger. Status is
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
are not bound to code: no Core command handler exists yet. The module reads no
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

No Core command handler exists yet, so the registry starts empty and no action is
bound; handlers bind themselves when they are written. There is no role-to-permission
mapping, no Automation binding and no HTTP or IdP wiring, and nothing here claims
API or integration acceptance (TEST-SEC-AUTHZ-NEG at INTEGRATION, AV-SCEN-04 and
BENCH-RQ3-001 remain unexecuted).
