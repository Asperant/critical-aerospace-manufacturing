# Evidence — WP-SCH-001 (dispatch baselines and scheduling instance model)

Requirement FR-SCH-010. The package is `services/scheduler-service/`: the five
dispatch rules FIFO/EDD/CR/SPT/SRPT (`SCH-B1`..`SCH-B5`), their BaselineDefinition
records and a seeded synthetic instance generator (its README states the rule
semantics). This directory holds the local verification run and its limits.

## Run

`runs/run-6-committed-394176a/` is the run of record: one local run of `capture_run.py`
on a **clean committed tree** at source commit `394176a60432d75cd3bcdafa5fe88b2bf2b53929`
(branch `wp/WP-SCH-001-dispatch-baselines`, which contains the merge of `origin/main`
`3242d1f`), started 2026-10-27T20:25:05Z, all six commands exit 0:

| Command | Result |
|---|---|
| scheduler suite (pytest, 99 tests incl. Hypothesis properties) | 99 passed |
| collector tests (`evidence/WP-SCH-001/tests`, 6 tests) | 6 passed |
| `ruff check` / `ruff format --check` on the package and the three evidence scripts | clean / 18 files formatted |
| `pyright --project services/scheduler-service/pyrightconfig.json` | 0 errors |
| `replay_comparison.py`: 6 seeds x 4 `PYTHONHASHSEED` values in fresh processes | all equal to the in-process trace |

Per command the run keeps the exact stdout and stderr bytes (`<id>.stdout`,
`<id>.stderr`, marked binary in `runs/.gitattributes`) with byte counts and SHA-256 in
`results.json`; `display_result_line` there is derived for reading only.
`identity.json` has source, tool, lock, workload and host identity, with host load
taken at start and at finish.

- **Tested source versus evidence commit:** `394176a` is the tested source. The commit
  that adds this run and this README has a different SHA; it changes only files under
  `evidence/WP-SCH-001/`, so the tested source files are unchanged (check with
  `git diff 394176a <evidence commit> --stat`). The run records the tested SHA, never
  its own commit.
- **Not checked by this run:** the static ratchet, trace and `ci/tests` ran separately
  (reported in `tasks/WP-SCH-001/FINAL_REPORT.md`), and
  `check-coverage` plus `test_repository_registry_matches_the_repository` are **red**
  for the undecided observability exemption (see below).
- **Earlier local runs** (`run-3`, `run-5`) were taken on the then-uncommitted tree
  and are kept as history. Their identity lists the changed files outside the commits;
  `run-5` used the collector before its clean-tree fix, and `run-3` the collector
  before the review corrections (it stored stdout with trailing whitespace stripped,
  three stderr lines only, left the evidence scripts out of its manifest and read host
  load after the commands). All their commands passed.
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
