# WP-CORE-005 — transactional outbox owner-local slice

Date: 2026-10-27
Owner: Asrın Dündar
Branch: `wp/WP-CORE-005-transactional-outbox`
Canonical WP: `WP-CORE-005`

## Implemented

- Added the forward-only `0005_outbox` PostgreSQL migration.
- Added Core-owned `core.outbox` storage with immutable event identity,
  versioned payload/envelope checks, pending/publication state and retry fields.
- Added a per-lot event sequence without changing opaque manufacturing revisions.
- Bound `PlaceLotOnHold` and `DispatchLot` accepted mutations to their existing
  Core-owned `LotHeld.v1` and `LotDispatchAuthorized.v1` contracts in the same
  command transaction.
- Added `execute_with_outbox` as a caller-owned savepoint boundary.
- Added the transport-neutral `OutboxRelay`; NATS subjects, streams and runtime
  ACLs remain the external Yavuz-owned runtime binding.
- Added negative tests for event identity binding and PostgreSQL constraint
  rollback behavior.

## Verification actually run

```text
321 passed, 38 deselected — Core non-integration tests
105 passed — Core event contract and registry tests
Ruff: PASS
Pyright: 0 errors
projectctl startability WP-CORE-005: STARTABLE
```

The real PostgreSQL integration suite was not executed: this host has no
`CI_PG_DSN`/`CORE_TEST_DISPOSABLE` configuration and Docker API access is denied.
No PostgreSQL integration result is claimed here.

## Readiness disposition

This slice does not promote `DEP-022` or `DN-CORE-OUTBOX`. Required real
PostgreSQL atomicity, migration and rollback evidence remains to be executed in
the disposable PostgreSQL 18 environment. NATS publication and integration
readiness remain external runtime work.

