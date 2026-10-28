# Scheduler dispatch baselines — WP-SCH-001

Offline Python library (`manufacturing_scheduler`) with the five mandatory dispatch
rules, their `BaselineDefinition` records and a seeded synthetic instance
generator. It selects a job for a caller-built context; it has no server, store,
broker or Core access, performs no production constraint validation and executes
nothing. It is not the optimized scheduler (CP-SAT, rolling horizon) and not the
Priority-Based Dispatch rule named in docs/02, which are other work.

| ID | Rule | Primary key, smallest first |
|---|---|---|
| `SCH-B1` | FIFO | `queue_entry_tick` |
| `SCH-B2` | EDD | `due_tick` |
| `SCH-B3` | CR | `(due_tick - now) / remaining_route_ticks`, an exact `Fraction`; an overdue job keeps its negative ratio |
| `SCH-B4` | SPT | `operation_ticks`, the **next operation** only |
| `SCH-B5` | SRPT | `remaining_route_ticks`, the **whole remaining route** |

- Ties break by `queue_entry_tick`, then `job_id`, so the input order never matters.
- Only jobs that are `ELIGIBLE` and released (`queue_entry_tick <= now`) are ranked.
  Eligibility is a caller-supplied fixture input. `INELIGIBLE` and `COMPLETED` jobs
  never win; an empty result is `NO_CANDIDATES`, a normal outcome.
- SRPT ranks at the supplied decision epoch. Nothing is preempted.
- Time is a local integer count of a declared `tick_unit`; no wall clock is read.
  Jobs and context must declare the same unit.
- The CR formula and the SPT variant are documented implementation choices
  (docs/01 leaves the exact versioned formula to the implementation).

`generate(OfflineInstanceConfig, seed)` draws from its own `PCG64` stream
(`SeedSequence(seed, spawn_key=(1,))`). The result depends on the configuration and
seed alone, never on global state, the hash seed or the clock; replay guarantees hold
for the pinned NumPy version only. Instances are synthetic fixtures: not real
factory data, not a canonical ScenarioDefinition and not research evidence.

`BASELINES` holds the five records (docs/01 Item 14 metadata). Each is
`IMPLEMENTED` and `NOT_FROZEN`; none is VERIFIED, TUNED, FROZEN or EVALUATED. The Git
SHA is bound when a run is captured, never stored in the record. Comparator class
and strength cite the canonical text where it exists; elsewhere they are a proposal
for owner review.

Run from the repository root (`ci/README.md` T0 section):

    uv run --project ci --locked python -m pytest -c services/scheduler-service/pyproject.toml \
      services/scheduler-service/tests -q -p pytest_quarantine
    uv run --project ci --locked pyright --project services/scheduler-service/pyrightconfig.json

The tests use hand-calculated cases and synthetic instances. They are not
BENCH-SCH-001 or BENCH-RQ2-001 evidence.
