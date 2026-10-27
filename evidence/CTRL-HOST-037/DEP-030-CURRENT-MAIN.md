# CTRL-HOST-037 — DEP-030 current-main readiness

## Disposition

`DEP-030` is `READY` at `CONTRACT_READY` for the bounded
`core.scheduling-snapshot.v1` producer contract. The exact predicate is:
explicit lot route position, current lot revision, lot-specific eligible
equipment, priority and due date, equipment maintenance state, and immutable
snapshot world/revision/freshness metadata.

The contract is a closed, read-only planning input. It does not implement or
claim Twin export, Scheduler consumption, database snapshot assembly,
integration readiness, execution authority or WP-TWIN-003 completion.

## Current-main verification

- Verified main and producer merge: `4ca1e3dc90e8ffbbf17f7ca14470d3e84a336f21`
- Producer: `WP-CORE-001`, PR #152, merged by `Asperant`.
- Required CI for PR #152 passed: `ci-scope`, `t1-contract`, `t1-static`,
  `t1-unit`, and `ci-gate`; integration was correctly skipped for this
  contract-only slice.
- Focused producer contract test: `9 passed`.
- Registry, producer-authority and compatibility tests: `170 passed`.
- Core query plus snapshot focused tests: `43 passed`.
- Ruff and manufacturing-core Pyright: clean.
- Exact artifact hashes and Git blobs are recorded in
  `evidence/readiness/DN-CORE-SNAPCON-DEP-030.json`.

## Limits

The fixture is synthetic development evidence, not factory data. The status
projection does not unlock any later INTEGRATION or MILESTONE_EXIT edge and
does not mark any WP DONE.
