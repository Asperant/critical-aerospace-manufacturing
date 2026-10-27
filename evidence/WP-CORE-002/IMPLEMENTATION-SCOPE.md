# WP-CORE-002 — implementation scope and gate record

## Implemented

`manufacturing_core.transitions` now owns the explicit order, lot, serialized
component and execution matrices; stable rejection codes; terminal no-
resurrection rules; active-hold and resource dispatch guards; process-start
guards; and explicit ReworkDirective/governed-reopen checks. The existing typed
commands and `PostgresCommandLedger` remain the idempotency, revision,
freshness and durable-outcome authority.

`CoreTransitionService` adds authorized hold placement and release handlers and
the dispatch legality handler. `material_hold` is a separate persisted
dimension. Released rows remain history. No outbox, physical dispatch,
rework-history, split, merge or genealogy implementation is claimed.

## Dependency gates

- `DEP-020`: `READY` at `COMPONENT_READY`; binding artifact is
  `evidence/WP-CORE-009/COMPONENT-READY.md`.
- `DEP-019`: unresolved `HARD + INTEGRATION`; it does not block this WP's
  implementation start under CHG-054.
- `DEP-028`: later `HARD + INTEGRATION` consumer acceptance; not a local start
  blocker.
- `DEP-039`: later `HARD + MILESTONE_EXIT` simulator validity; not a local
  start blocker.
- `DEP-082`: later `HARD + INTEGRATION` scheduler validation; not a local
  start blocker.

Queue, Plane health, Slot Release, READY/DoR and missing downstream acceptance
are advisory or later-stage facts under `START fail-open / DONE fail-closed`.
