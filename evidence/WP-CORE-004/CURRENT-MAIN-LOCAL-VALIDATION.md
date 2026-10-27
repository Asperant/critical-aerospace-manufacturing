# WP-CORE-004 current-main local validation

Owner: Asrın Dündar. Validation date: 27 October 2026.
Base: `origin/main` at `3ab912deaeadf478b7f535470fcfedfb9c8e96da`.
Status: owner-local implementation batch merged and current-main verified;
integrated acceptance remains pending. This evidence does not claim DONE.
Merged PR: #178. Merge commit: `d2753de2d6f142fca822c055a6ff6d3a809a40bf`.

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

## Post-merge verification

- `origin/main` is at merge commit
  `d2753de2d6f142fca822c055a6ff6d3a809a40bf`.
- The merged PR head `811d74f0aaa450a3ccf580d4cdcaa030c5296fe6` is an exact
  ancestor of `origin/main`, with no tree difference.
- The focused current-main rework/lineage suite passed again: 61 tests.
- Required PR CI passed on the merged head: CI run `40573889658`, push CI run
  `40573880325`, and projectctl run `40573889906`.
- `projectctl check-done` remains `UNKNOWN` and `transition_authorized=false`;
  the merge and local verification do not certify DONE.

The first PR CI rerun (`40573152080`) classified the implementation, static,
contract and scope jobs successfully. Its TL-13 step failed before executing
tests because the rerun event carried the pre-update PR body without the
required `Requirements` field. The current PR body contains the canonical
requirements field; a fresh synchronize event is required for that metadata
check to evaluate the current body.

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
