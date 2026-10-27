# Evidence — WP-SCH-001 (dispatch baselines and scheduling instance model)

Requirement FR-SCH-010. The package is `services/scheduler-service/`: the five
dispatch rules FIFO/EDD/CR/SPT/SRPT (`SCH-B1`..`SCH-B5`), their BaselineDefinition
records and a seeded synthetic instance generator (its README states the rule
semantics). This directory holds the local verification run and its limits.

## Run

`runs/run-5-uncommitted-2026-10-27/` is the run of record: one local run of
`capture_run.py` (corrected after review), started 2026-10-27T20:11:23Z, all six
commands exit 0:

| Command | Result |
|---|---|
| scheduler suite (pytest, 99 tests incl. Hypothesis properties) | 99 passed |
| collector tests (`evidence/WP-SCH-001/tests`, 5 tests) | 5 passed |
| `ruff check` / `ruff format --check` on the package and the three evidence scripts | clean / 18 files formatted |
| `pyright --project services/scheduler-service/pyrightconfig.json` | 0 errors |
| `replay_comparison.py`: 6 seeds x 4 `PYTHONHASHSEED` values in fresh processes | all equal to the in-process trace |

Per command the run keeps the exact stdout and stderr bytes (`<id>.stdout`,
`<id>.stderr`, marked binary in `runs/.gitattributes`) with byte counts and SHA-256 in
`results.json`; `display_result_line` there is derived for reading only.
`identity.json` has source, tool, lock, workload and host identity, with host load
taken at start and at finish.

- **Source state:** the tree was **not clean**. Commit was not authorized, so
  `identity.json` lists the base commit `3ab912de…` and the SHA-256 of each of the 32
  changed or untracked files, including the capture, replay and collector-test
  scripts, `docs/` and `traceability/`; only `runs/` and this README are excluded. A
  later commit can be checked against them. A run on committed source will be a new
  run, never a replacement of this one.
- **Run-3 is kept unchanged** (`runs/run-3-uncommitted-2026-10-27/`), with its
  limits: its collector stored stdout with trailing whitespace stripped, kept only
  three stderr lines, left the evidence scripts out of its 24-file manifest and read
  host load after the commands. It contains no failure; all its commands passed.
- **Not available, so not claimed:** a governed ReleaseManifest, EnvironmentManifest
  image digest or HardwareProfile. The host facts are local labels. Their canonical
  producer is WP-PLAT-005 (docs/04), not started; DOD-WP-11 stays open for this WP.
- **Earlier attempts** are archived outside the repository with SHA-256
  (`tasks/WP-SCH-001/backups/superseded-1`, `-2` and `-3`). `run-0` crashed in the capture
  script (`uv` not on `PATH`) before writing `results.json`. `run-1` and `run-2`
  passed with the same results; `run-1` stored trailing whitespace and a Pyright
  upgrade notice as its result line, and `run-2` was superseded because two test
  files were edited afterwards (type suppressions removed), which made its source
  digests stale. `run-4` (first run of the corrected collector) was superseded because
  two `noqa` suppressions were removed from evidence scripts afterwards and the
  recorded Ruff scope was widened to those scripts.
- Scratch mutation runs (not committed): 33 injected defects in the package, and 10 in
  the collector, all caught after gaps were closed (the recorded stream output in
  `test_instances.py`; a strict start/finish ordering check in the collector tests).

## What this is not

- Not BENCH-SCH-001 (8 families x 30 paired seeds) or BENCH-RQ2-001 (4 families x 20
  paired seeds, realized closed-loop outcome). Neither has run. Their producers
  besides this WP are WP-SCH-002/003/004/006/007, WP-RES-006/008 and WP-R2-002; they
  need the optimized scheduler, simulator decision interface, metrics and a
  governed EVALUATION environment. FR-SCH-010 stays `NOT_YET_EXECUTED`; its coverage
  state moves only to `IMPLEMENTED` in docs/03.
- Not a production constraint check, not a Core integration, not real factory data.
  The generated instances are synthetic fixtures.
- The baseline records are `IMPLEMENTED` and `NOT_FROZEN`. Their comparator class
  and strength are canonical only for SCH-B1 and SCH-B5; the others are a proposal
  for owner review. BestHeuristic selection and tuning are out of this WP.
- Platform observability is **undecided**: `infra/observability/coverage.json` is
  unchanged and `check-coverage` fails for the existing `scheduler-service` directory
  until the platform owner decides. See `OBSERVABILITY-DECISION-PENDING.md` for the
  verbatim failure and the request. No exemption is proposed or applied.
