# CTRL-HOST-035 — DEP-006 current-main verification

This control records a status projection only. It does not produce a new
PostgreSQL runtime run and does not claim shared-host or full Integration
readiness.

## Bound identity

- Dependency: `DEP-006`
- Producer node: `DN-PLAT-COMPOSE`
- Required level: `SKELETON_READY`
- Consumer: `WP-CORE-007` / `DN-RT-PG`
- Producer WP: `WP-PLAT-001`
- Producer PR: `#53`
- Producer merge: `932edbaf87dd0d06b0984c25b4b75497a265e607`
- Current main at verification: `d5d72e01fc0f1d8480d20b7538b59b7b4f0f9b46`
- Producer merge is an ancestor of current main: PASS
- Required producer CI on PR #53: PASS; post-merge main validation is recorded in the producer evidence

## Evidence checks

`evidence/readiness/DN-PLAT-COMPOSE.json` binds exactly one consumer edge,
`DEP-006`, to `WP-CORE-007` and declares the producer-authored runtime checks.
The following paths were checked against the Git blobs declared by that basis:

- `evidence/WP-PLAT-001/README.md`
- `evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/record.json`
- `evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/status.log.txt`
- `evidence/WP-PLAT-001/RUN-PLAT-001-DEV-001/smoke.log.txt`

All declared blobs matched. The record is `REAL`, the status log contains a
healthy PostgreSQL 18.6 container, and the smoke log contains
`smoke platform-infra: PASS`.

The local Docker socket was not accessible to this developer UID during this
verification, so no replacement runtime run is claimed. Existing producer
evidence remains the runtime observation; this control verifies its exact
current-main attribution and binding.

## Disposition

`DEP-006` may be projected `READY` at `SKELETON_READY`. This does not change
`DEP-007`, does not establish Integration readiness, and does not make
`WP-CORE-007` DONE.
