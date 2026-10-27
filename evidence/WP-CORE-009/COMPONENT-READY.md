# WP-CORE-009 — COMPONENT_READY

Status: `COMPONENT_READY`

This artifact is attributable to Asrın Dündar / `Asperant` and binds
`DN-CORE-LIFECYCLE` and `DEP-020` to the merged WP-CORE-009 implementation.
It is not a WP-CORE-009 `DONE` claim and does not certify DEP-019 integration
readiness.

## Exact binding

- Producer: `WP-CORE-009`
- Readiness node: `DN-CORE-LIFECYCLE`
- Readiness level: `COMPONENT_READY`
- Consumer edge: `DEP-020`
- Consumer: `WP-CORE-002` / `DN-CORE-TRANSITIONS`
- Implementation PR: #146
- Implementation merge SHA: `84bebc4d925e0c0c093edeb980195d0b37de4721`
- Final validated current-main SHA: `dda541038d6289b8ed79c0c4c80092c9263847c9`
- Evidence change control: `CHG-059`

## Implemented component

The component provides immutable `ProductionOrderState`, `LotState`, and
`SerializedComponentState` records using the current CORE-001 identity and
revision contract. Order, lot, and serialized-component lifecycle values are
canonical and validated. Lot/component execution state is a separate
dimension with the re-entrant-safe `READY`, `QUEUED`, `RESERVED`,
`DISPATCHED`, `PROCESSING`, and `STEP_COMPLETED` values.

Persistence is provided by forward-only migration `0003_lifecycle.sql` and
the repository state mapping. The v1 CORE-001 order-query contract shape is
unchanged. No transition operation, transition legality, hold/release,
rework, split/merge, or CORE-002 transition-engine behavior is implemented.

## Executed evidence

- `TEST-CORE-LIFECYCLE`: `services/manufacturing-core/tests/test_lifecycle.py` (blob `b712c6978cfd3241ec4f0c66269a7badae3f351c`)
- Persistence state round-trip: `services/manufacturing-core/tests/persistence/test_persistence.py` (blob `44dc7e66480576d9b87bff63e402c08587664693`)
- Local non-integration suite: `270 passed, 34 deselected`
- Local pyright, Ruff and format checks: PASS
- Product PR push CI: run `40474885983`, exact head `16b2184d9f7e8f2bf294214d6faad4b3e829f5a5`, including real PostgreSQL 18 migration/persistence: PASS
- Product merge-main CI: run `40475355234`, exact head `84bebc4d925e0c0c093edeb980195d0b37de4721`, T1 and real PostgreSQL/browser/integration jobs: PASS
- Final current-main T1 CI: run `40476475004`, exact head `dda541038d6289b8ed79c0c4c80092c9263847c9`: PASS
- Final current-main project-control regression: run `40476474980`, exact head `dda541038d6289b8ed79c0c4c80092c9263847c9`: PASS

## Remaining boundary

`DEP-019` remains `HARD / INTEGRATION / SKELETON_READY` and its canonical
`DN-RT-PG` readiness is still `NOT_READY`; this does not invalidate the local
component. WP-CORE-009 remains separate from WP-CORE-002 transition legality
and is not marked `DONE` by this artifact.
