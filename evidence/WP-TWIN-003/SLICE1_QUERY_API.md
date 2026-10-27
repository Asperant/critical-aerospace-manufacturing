# WP-TWIN-003 slice 1 — versioned SchedulingSnapshot query API

This slice implements the smallest owner-local contract surface unlocked by
DEP-030: `TwinQueryAPI.get_scheduling_snapshot_v1`. It is a read-only adapter
over an explicitly supplied Twin projection provider. It validates the exact
Core `core.scheduling-snapshot.v1` shape, binds the requested world, requires
the `twin:scheduling-snapshot:read` scope for the configured consumer identity,
and returns a defensive copy.

The canonical schema and fixture remain under
`services/manufacturing-core/contracts/v1/`; this package does not create a
second source of truth. Extra fields, including hidden Simulator Oracle state,
are rejected. No command, mutation, Scheduler activation, database binding or
real event-backbone integration is claimed.

## Verification

- `services/operational-twin/tests/test_scheduling_snapshot.py`: 5 passed
- Existing Twin projection suite: 8 passed
- Negative paths: unknown identity, missing scope, world mismatch, hidden
  Oracle field, missing contract field

Remaining WP-TWIN-003 work is integration with the real Twin read model,
runtime transport/authentication and the required latency/integrated evidence.
