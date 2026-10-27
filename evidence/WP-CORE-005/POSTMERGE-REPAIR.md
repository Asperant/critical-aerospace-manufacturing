# WP-CORE-005 — post-merge integration repair

Date: 2026-10-27
Owner: Asrın Dündar
Repair branch: `wp/WP-CORE-005-postmerge-fix`
Canonical WP: `WP-CORE-005`
Pre-repair current main: `ba92b07c01972aef5767bf5a611a6cf3cad1963e`

## Observed failure

Main CI run `40545464553` executed the real PostgreSQL 18 lane and exposed two
regressions from the merged outbox slice:

- the existing query-round-trip cleanup did not include the new
  `core.lot_event_sequence` foreign-key table;
- existing accepted `PlaceLotOnHold` commands allow nonblank human-readable
  reasons containing spaces, while the new `LotHeld.v1` payload model/schema
  incorrectly treated `reason` as an opaque identity.

## Repair

- include `core.outbox` and `core.lot_event_sequence` in isolated integration
  cleanup;
- define `reason` as nonblank text while retaining strict nonblank identity
  validation for IDs and revisions;
- update the registered schema digest and add unit coverage for spaced and
  whitespace-only reasons.

This is a C1 compatible correction within the approved WP-CORE-005 contract
scope: existing valid domain command values are preserved and no requirement,
authority boundary or architecture meaning is changed.

## Local verification

- Core non-integration tests: `322 passed, 38 deselected`;
- Core domain-event contract tests: `7 passed`;
- Ruff: PASS;
- Pyright: `0 errors, 0 warnings, 0 informations`;
- `git diff --check`: PASS.

The disposable PostgreSQL integration rerun and current-main post-merge
verification are intentionally pending this repair PR; no readiness promotion
is claimed here.
