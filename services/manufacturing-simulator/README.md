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
integration, snapshot/fork/persistence, a replay service and the Oracle.

Run from the repository root (`ci/README.md` T0 section):

    uv run --project ci python -m pytest -c services/manufacturing-simulator/pyproject.toml \
      services/manufacturing-simulator/tests -q -p pytest_quarantine
    uv run --project ci pyright --project services/manufacturing-simulator/pyrightconfig.json

The tests use an opaque toy scenario. They check kernel mechanics only and are
not AV-SCEN-01, E2E-01 or BENCH-SIMVAL-001 evidence.

## Replay and event-sequence hash (WP-SIM-002)

`replay(spec, handlers)` runs a `ReplaySpec` (scenario, explicit initial local state,
horizon, positive event budget, and a `ReplayIdentity` of source, handler bundle,
NumPy and RNG) once in a **fresh** kernel. `handlers` is a factory called once per
replay, so no handler state or world is shared. A new execution is labelled with the
runtime that really ran it: a declared NumPy or RNG identity that this process does not
run raises `IncompatibleRuntimeError`, and the input is canonicalized, before the
factory is called. `source_id` and `handler_bundle_id` are caller-declared labels, not
attested. Nothing is retried; a failing handler raises `ReplayExecutionError` and never
yields a result.

A `ReplayResult` is validated whenever it is constructed, decoded from JSON or compared,
independently of its digests: format, field types, execution order (strictly increasing
`(time, sequence)`, unique sequences), and the clock, queue and termination relationships
of a real run. An impossible result raises `CanonicalizationError` and is never compared;
duplicate JSON keys are rejected too.

`compare` returns `INCOMPATIBLE_INPUT` (different identity or input: not evidence of
nondeterminism), `EVENT_MISMATCH`, `STATE_MISMATCH`, `PARTIAL_MATCH` or `MATCH`. Only a
complete run can be `MATCH`: queue empty, or the declared horizon reached. Two equal runs
that both stopped at their event budget are `PARTIAL_MATCH`, an equal prefix of an
incomplete run, and are not accepted (`ReplayComparison.accepted` is false).
`check_determinism` replays twice and compares.

Digests are SHA-256 over canonical, type-tagged, versioned bytes
(`sim-replay-hash/1`, documented in `serialization.py`): finite floats as `float.hex`,
`-0.0` distinct from `0.0`, event order preserved, `correlation_id`, `provenance` and
exception text excluded, `FAILED` records rejected. The final-state digest covers the
clock, local state, next insertion sequence and the complete pending queue. A digest
summarizes the semantic data and never replaces comparing it.

Limits: single-threaded kernel; handlers must not read the wall clock, global random
state, threads or the environment; RNG stream positions are not part of the state
digest; replay holds for the pinned NumPy version only. This is a kernel-local
projection, not a cross-service standard, snapshot or restore format. The tests
(`test_serialization.py`, `test_replay.py`, `test_replay_validation.py`) bound this for
the toy handlers and are not BENCH-SIMVAL-001 or REPRO-NONOWNER-001 evidence.
