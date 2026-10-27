# WP-CORE-004 current-main local validation

Owner: Asrın Dündar. Validation date: 27 October 2026.
Base: `origin/main` at `3ab912deaeadf478b7f535470fcfedfb9c8e96da`.
Status: owner-local implementation batch validated; post-merge and integrated
acceptance remain pending. This evidence does not claim DONE.

## Completed owner-local scope

- immutable component-scoped rework history values and append-only persistence;
- split/merge lineage values, conserved component membership and temporal ancestry;
- relational lineage persistence and genealogy/equipment exposure queries;
- transaction/savepoint rollback, per-component/per-world serialization and
  restricted runtime SELECT/INSERT enforcement;
- migration integration into the current Core Alembic chain as
  `0006_rework_history` and `0007_lot_lineage`;
- current-main Core migration status/table health coverage and structured query
  success/failure observability;
- RTM realization references for FR-CORE-009 through FR-CORE-012.

The implementation deliberately does not add `ExecuteApprovedReworkDirective`.
Its authoritative approval lookup, lifecycle transition binding and frozen
protected-command contract are not defined by current canonical inputs.

## Executed checks

| Check | Result |
|---|---|
| Focused rework/lineage unit tests | 61 passed |
| Full Core non-integration tests | 384 passed, 115 deselected |
| Full Core PostgreSQL integration suite on disposable PostgreSQL 18.6 | 115 passed |
| Ruff check | PASS |
| Ruff format check | PASS |
| Pyright | 0 errors, 0 warnings |
| `projectctl validate --json` | PASS; existing documentation diagnostics retained |
| `projectctl check-done WP-CORE-004` | UNKNOWN; post-merge/owner DoD evidence gate remains fail-closed |
| `git diff --check` | PASS |

The PostgreSQL run used an isolated disposable database and separate restricted
migration/runtime roles. It exercised the complete current-main migration chain,
including rework and lineage revisions, foreign keys, rollback, replay,
runtime privilege denial, history immutability and genealogy query sanity.
Synthetic WP-NORMAL timings are local sanity only and are not integrated
manufacturing acceptance evidence.

## Remaining gates

- `ExecuteApprovedReworkDirective` remains blocked by missing authoritative
  approval/authorization lookup, lifecycle transition producer binding and the
  exact protected command contract (target, actor, WorldID, proposal/plan
  revision, state revision, expiry, policy and idempotency).
- DEP-029 remains a HARD `INTEGRATION@COMPONENT_READY` gate requiring the
  DN-CORE-LIFECYCLE consumer binding and genealogy queries over real lineage.
- AV-SCEN-01, BENCH-E2E-001, BENCH-RQ1-001, required CI, post-merge validation,
  trace dispositions and accountable final DoD evidence remain pending.

Recommended lifecycle after merge: `VALIDATING`, unless the exact strict DONE
criteria are later independently evidenced.
