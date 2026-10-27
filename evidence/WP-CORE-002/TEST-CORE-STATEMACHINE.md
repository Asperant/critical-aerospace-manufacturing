# TEST-CORE-STATEMACHINE — WP-CORE-002

Evidence status: `PARTIAL_LOCAL_EXECUTION`

This artifact records the executable local evidence available on 2026-10-27.
It does not claim `DN-CORE-TRANSITIONS` `INTEGRATION_READY`, WP `DONE`, or
post-merge acceptance.

## Scope bound

- WP: `WP-CORE-002`
- Readiness node: `DN-CORE-TRANSITIONS`
- Requirements: `FR-CORE-003`, `FR-CORE-007`, `FR-CORE-008`
- Producer readiness consumed: `DEP-020` / `DN-CORE-LIFECYCLE` at `COMPONENT_READY`
- Producer artifact: `evidence/WP-CORE-009/COMPONENT-READY.md`
- Not consumed as a START blocker: `DEP-019` (`INTEGRATION`)

## Executed local evidence

Commands were run from the repository root:

```text
uv run --project ci --locked python -m pytest \
  -c services/manufacturing-core/pyproject.toml \
  services/manufacturing-core/tests -m 'not integration' -q
309 passed, 37 deselected

uv run --project ci --locked ruff check services/manufacturing-core
All checks passed!

uv run --project ci --locked ruff format --check services/manufacturing-core
34 files already formatted

uv run --project ci --locked pyright \
  --project services/manufacturing-core/pyrightconfig.json
0 errors, 0 warnings, 0 informations

uv run --project ci --locked python -m mfgctl trace drift --strict
no drift between traceability/trace_edges.yaml and docs/03_Requirements_Traceability_Matrix.md §17
```

The focused transition suite is included in the 308 passing tests and covers
all declared legal matrix edges plus negative cases for terminal states,
invalid execution jumps, active holds, unavailable resources, missing
dispatch, missing ReworkDirective and governed reopen.

## PostgreSQL evidence

The real PostgreSQL 18 suite is declared in
`services/manufacturing-core/tests/persistence/test_transitions_persistence.py`.
It covers migration creation/replay, role grants, foreign keys, atomic
hold/release, retained history, revision preservation, idempotency, duplicate
hold rejection, target binding and authorization denial.

This workspace had no `CI_PG_DSN` and no `CORE_TEST_DISPOSABLE=1`, so the
disposable PostgreSQL run was **not executed**. The required command is:

```text
CORE_TEST_DISPOSABLE=1 CI_PG_DSN='<disposable-admin-dsn>' \
  uv run --project ci --locked python -m pytest \
  -c services/manufacturing-core/pyproject.toml \
  services/manufacturing-core/tests/persistence -m integration -q
```

No PostgreSQL pass, CI pass, PR, merge SHA, or post-merge main validation is
claimed by this artifact.

## Boundary evidence

- `0004_material_hold` is forward-only and creates a retained hold record with
  a one-active-hold-per-lot partial unique index and command foreign keys.
- Hold placement/release does not overwrite lot lifecycle or execution state.
- Revision tokens remain opaque; transition updates atomically write the base
  lot revision and state-row revision under the existing command ledger.
- Outbox/relay publication is intentionally absent; it remains WP-CORE-005.
- Rework legality is guarded here, while directive execution/history and
  split/merge/genealogy remain outside this WP.
