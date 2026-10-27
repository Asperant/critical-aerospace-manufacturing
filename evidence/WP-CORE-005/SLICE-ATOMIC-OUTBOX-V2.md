# WP-CORE-005 — LotHeld.v2 transactional outbox owner-local slice

Date: 2026-10-27

Owner: Asrın Dündar

Canonical WP: `WP-CORE-005`

Change control: `CHG-071 / CTRL-HOST-045`
Branch: `wp/WP-CORE-005-lot-held-v2-outbox`

## Scope completed in this slice

- `LotHeld.v1` schema, fixture, registry declaration and Python payload remain
  unchanged and hash-pinned.
- `LotHeld.v2` preserves the same hold fact and envelope identity while its
  `reason` follows `PlaceLotOnHold.hold_reason` (`minLength: 1`), including
  `NDT anomaly`.
- Core accepted hold and dispatch mutations allocate opaque per-lot event
  versions and insert the corresponding event intent with the command outcome
  in the same PostgreSQL transaction.
- Duplicate command replay returns the existing durable outcome; a conflicting
  idempotency fingerprint does not execute a second mutation.
- Event identity/constraint failure rolls back the material hold, event
  sequence increment and command outcome together.
- The outbox remains transport-neutral. This evidence does not claim NATS,
  relay delivery, consumer projection or effect verification.

## Verification actually run

```text
146 passed — contract registry, compatibility and Core event boundary tests
323 passed, 38 deselected — Core non-integration tests
Ruff: PASS
Pyright: 0 errors
contract gate against origin/main: PASS after staged candidate materialization
projectctl startability WP-CORE-005: STARTABLE
```

The real PostgreSQL 18 suite is required and will be executed by the exact
current-main integration lane. This host has no `CI_PG_DSN` and therefore no
local real-database result is claimed in this artifact.

## Readiness disposition

`DEP-022` remains `NOT_READY` until the merged revision has fresh real
PostgreSQL 18 migration, atomicity, replay, rollback and negative-path
evidence. `DEP-023`/`DEP-024` and NATS publication remain separate downstream
contract/integration gates. A later current-main evidence update may promote
only the exact edge predicate supported by actual evidence.
