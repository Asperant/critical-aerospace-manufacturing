# CTRL-HOST-050 — DEP-038 current-main edge binding

## Disposition

`DEP-038` (`DN-CORE-CONTRACTS` → `DN-SIM-OPSEM`, HARD, START, `CONTRACT_READY`)
is `READY` for the Simulator operational-semantics consumer slice. The predicate
is the published `core.lot-operational-semantics.v1` contract: re-entrant route
visits and execution cycle, independent retained material-hold state that blocks
dispatch, and directive-linked append-only rework history, with two fixtures and
green producer contract tests.

This is an edge-specific binding. It does not reuse the DEP-018 or DEP-021
binding, does not certify global `DN-CORE-CONTRACTS`, and does not claim rework
execution, transition commands, route position, persistence or integration.

## Why the existing implementation was not sufficient on its own

PR #178 (WP-CORE-004) and PR #149 (WP-CORE-002) merged the semantics, but:

- `core.order-query.v1` publishes re-entrant route visits only, with no state,
  hold or rework dimension;
- hold had event and command contracts but no lot-level state view;
- rework history is an internal value (`rework.py`: "no public command
  contract"), with no schema, registry declaration or fixture.

The DEP-038 unblock evidence requires a merged contract, green contract tests
and a published example fixture, so the missing consumer-facing surface was added
as the minimum Core artifact. No transition, persistence or rework behaviour
changed.

## Semantics bound to merged guards

Each rule is asserted in
`services/manufacturing-core/tests/test_operational_semantics_contract.py`
against the merged code, not restated:

- `STEP_COMPLETED` → `READY` is the re-entry cycle; lifecycle stays `IN_PRODUCTION`.
- An active hold makes `validate_dispatch` fail with `ACTIVE_HOLD` while lifecycle
  and execution state are unchanged; released holds stay as history.
- `validate_rework` requires a directive, rejects scrapped material and requires
  a governed reopen for completed material.
- The fixture rework directive cites a prior origin execution and a return visit
  on the original route; the model reuses `ComponentExecutionHistory`.

## Verification (this worktree on top of origin/main db5640a)

- `pytest services/manufacturing-core/tests/test_operational_semantics_contract.py`
  — 32 passed.
- Core suite `-m "not integration"` — 416 passed. The 110 persistence errors
  without that filter need a disposable PostgreSQL DSN that this host does not
  provide; they are unrelated to this change.
- Registry, producer-authority, subject-binding, naming and schema-reference tests
  plus command and event contract tests — 268 passed.
- `ruff check`, `ruff format --check`, `pyright` for manufacturing-core,
  `check_contracts.py` (26 schemas / 9 instances) and `check_test_strategy.py`
  — pass.

## Limits

Fixtures are synthetic development fixtures, not factory observations. Review of
the fixtures by the Simulator owner is a consumer step and is not asserted here.
