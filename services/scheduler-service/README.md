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


---

# Scheduler snapshot consumer and RecoveryPlan contract — WP-SCH-002

Offline Python library (`manufacturing_scheduler`) with two jobs: consume the published
`core.scheduling-snapshot.v1` strictly, and decode, validate and serialize the
`scheduler.recovery-plan.v1` proposal (IC-SCH-004, see `contracts/v1/README.md`). It has no
server, store, broker or Core access, no solver, no independent validator, and it activates,
approves and executes nothing. The dynamic generator (DEP-083) and the production validator
(DEP-084) are later work and are neither implemented nor certified here.

## Snapshot consumer (`snapshot.py`)

- `parse_snapshot(payload, expected_world_id=…, policy=FreshnessPolicy(now, mode))` returns an
  immutable `PlanningSnapshot`. Consumed fields: `contract_version`, `world_id`,
  `snapshot_revision`, `generated_at`, `freshness.{status,valid_until}`, each lot's `id`,
  `revision`, `route_position.{route_id,visit_id,position,operation_class_id}`, `priority`,
  `due_at`, `eligible_equipment_ids`, each equipment's `id`, `revision`, `maintenance_state`, and
  `current_schedule_version`. Opaque ids and revisions are kept exactly (no trimming, case
  folding or coercion; no implicit primary world).
- Rejected with a stable value-free `SnapshotError.code`: wrong version or world, missing,
  unknown or Oracle-named fields, whitespace in ids, non-integers (bool, `1.0`), naive or
  non-UTC or malformed timestamps, duplicate lot, equipment or eligibility ids, eligibility
  naming absent equipment, an inconsistent freshness window, duplicate JSON fields, `NaN` and
  `Infinity`. Stricter than the Twin's own check where the published schema is.
- **Clock and freshness.** The caller supplies an aware UTC `now`; the package reads no clock and
  invents no maximum age. A snapshot is *expired* when `now >= valid_until` (the end is
  exclusive) and *from the future* when `generated_at > now` (a future snapshot is always
  rejected). `FreshnessMode.NORMAL` accepts only a `FRESH`, unexpired snapshot. In `DIAGNOSTIC`
  mode a degraded, stale or expired snapshot is returned as `DIAGNOSTIC_ONLY` with its reasons;
  it is never promoted to `FRESH`, and `propose_recovery_plan` refuses it. No UTC-to-simulation
  time conversion is attempted.
- **Public boundary only.** `read_planning_input` makes one read through a `SnapshotReader`;
  `TwinSnapshotReader` binds an already-authenticated context to `TwinQueryAPI`
  (`get_scheduling_snapshot_v1`). No private store, no per-entity calls, no retries, no new
  identity system; a denied read raises the Twin's own error.
- **Known incompleteness.** The v1 snapshot has no processing durations, remaining route, holds,
  queues, maintenance windows or simulation time. `PlanningInput.gaps` lists them
  (`InputGap`), `complete` is `False`, and `require_full_instance()` raises
  `IncompleteInputError`. `maintenance_state` `AVAILABLE` and lot eligibility are producer
  labels, not feasibility; the absence of a hold field is not the absence of a hold.

## Plans (`plans.py`)

`RecoveryPlan.from_wire` / `from_json` decode strictly into frozen dataclasses and `to_wire`
serializes them back (stable round trip). `check_snapshot_binding` ties a plan to the snapshot it
cites. `propose_recovery_plan(planning_input, header, candidates, now=…)` is the typed producer port: it
takes candidates from the caller, computes nothing, refuses a candidate that already carries a
validity report, and emits `validation_result: NOT_RUN` only. Construction is a *current* act, so it
rechecks freshness at the caller-supplied aware-UTC `now` (never a hidden clock, and a retained
`NORMAL` label proves nothing): the snapshot must be `FRESH`, already generated and unexpired
(`now < valid_until`), and the plan may not be generated at or after the source's expiry. Decoding a
historical plan with `from_wire` is a separate act and needs no clock.

## Verification

    uv run --project ci --locked python -m pytest -c services/scheduler-service/pyproject.toml \
      services/scheduler-service/tests -q -p pytest_quarantine
    uv run --project ci --locked pyright --project services/scheduler-service/pyrightconfig.json

The tests use the published snapshot fixture, the real `TwinQueryAPI` over a fixture provider
(`FIXTURE_ALLOWED`; not a live authenticated service) and hand-written development plans. They
are not TEST-UI-PLAN, AV-SCEN-01/02, E2E-01, BENCH-E2E-001 or BENCH-SCH-001 evidence.
