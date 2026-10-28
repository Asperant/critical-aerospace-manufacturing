# WP-CORE-007 — current-main owner-scope validation

Date: 2026-10-27
Owner: Asrın Dündar
Canonical WP: `WP-CORE-007`
Evidence refresh control: `CHG-067`
Validated current-main SHA: `3faa5c9997b20ad655a779358d1e9a5579e38622`

## Scope disposition

The owner-executable implementation scope is already present on current main:

- Alembic is the versioned Core migration runner with inspectable migration
  ledger status;
- role bindings are declarative and credential-free;
- explicit restricted migration/runtime roles are validated before same-schema
  grants are applied;
- the Core migration-status artifact is produced by the real PostgreSQL CI lane.

No new product implementation is added by this evidence refresh. No service
credentials or shared-host identities are invented.

## Verification

- focused role/domain tests: `49 passed`;
- Ruff: PASS;
- Pyright: `0 errors, 0 warnings, 0 informations`;
- `projectctl startability WP-CORE-007`: `STARTABLE`;
- current-main T1 CI run `40547115624`, exact head
  `3faa5c9997b20ad655a779358d1e9a5579e38622`: PASS, including the real
  PostgreSQL 18 migration/persistence lane and migration-status artifact.

The current-main full project-control regression is tracked separately and is
not represented as passed by this artifact until its exact run completes.

## Readiness boundary

This validates the owner-local WP-CORE-007 implementation evidence only. It does
not promote `DN-RT-PG` or `DEP-007`: the canonical `HARD / INTEGRATION /
INTEGRATION_READY` shared-host runtime edge remains `NOT_READY` and is owned by
the platform/runtime boundary. WP-CORE-007 is not marked `DONE` by this file.
