# WP-CORE-001 — bounded DEP-030 SchedulingSnapshot producer slice

This slice publishes the minimum versioned `core.scheduling-snapshot.v1`
contract needed by DEP-030. It carries the immutable world/snapshot revision
and freshness envelope, explicit lot route position, current lot revision,
lot-specific equipment eligibility, priority/due date, and equipment
maintenance state. It also names the current schedule version.

The schema is closed and rejects unknown fields, including hidden Simulator
Oracle state. The fixture is a synthetic development example. The registry
declaration and producer-authority entry make the contract discoverable without
granting mutation, approval or execution authority.

## Verification

- `test_scheduling_snapshot_contract.py`: 9 passed.
- Registry, producer-authority and compatibility tests after registration:
  170 passed.
- Core query plus snapshot focused tests: 43 passed.
- Ruff format/check and the manufacturing-core Pyright project: clean; 0
  errors, 0 warnings, 0 informations.
- `git diff --check`: clean on the producer branch before publication.

This is a producer contract slice, not Twin export, Scheduler implementation,
transport, database snapshot assembly, eligibility calculation, maintenance
mutation, integration readiness or WP-CORE-001 final acceptance. DEP-030 is
projected only after the merged/current-main control verification.
