# Simulator deterministic kernel — WP-SIM-001

Custom Python discrete-event kernel (no external DES framework): a heapq
future-event queue, a monotonic integer clock, named seeded NumPy random streams
and kernel-local scenario initialization. Simulator-owned; output is simulation
data and every record carries `SIMULATION` provenance.

- Time is a local integer count of the declared unit (microseconds) from run
  start. It is not wall-clock time and not a cross-service unit.
- Events order by `(time, insertion sequence)`: equal-time events are FIFO,
  including events a handler inserts at the current time.
- Streams (`arrival`, `processing`, `failure`, `repair`, `quality`, `inspection`,
  plus the architecture-named `telemetry`, `transport`) are `PCG64` generators
  seeded from `SeedSequence(master_seed, spawn_key=(fixed stream id,))`. A stream
  depends only on the master seed and its fixed id, never on lookup order or
  global state. Replay guarantees hold for the pinned NumPy version only.
- A handler exception fails the run (fail-stop). There is no retry, no resume and
  no rollback of the handler's partial mutation.
- `KernelScenarioConfig` is a minimal local fixture shape, **not** the canonical
  ScenarioDefinition. No Core contract field is consumed, and nothing here
  mutates Core state, persists data, or opens an endpoint.

Not in this package: manufacturing operation semantics, scheduling, Core
integration, snapshot/fork/persistence, the replay-hash service and the Oracle.

Run from the repository root (`ci/README.md` T0 section):

    uv run --project ci python -m pytest -c services/manufacturing-simulator/pyproject.toml \
      services/manufacturing-simulator/tests -q -p pytest_quarantine
    uv run --project ci pyright --project services/manufacturing-simulator/pyrightconfig.json

The tests use an opaque toy scenario. They check kernel mechanics only and are
not AV-SCEN-01, E2E-01 or BENCH-SIMVAL-001 evidence.
