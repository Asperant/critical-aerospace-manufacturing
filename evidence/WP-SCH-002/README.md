# Evidence — WP-SCH-002 (snapshot consumption and RecoveryPlan contract)

Requirements FR-SCH-001, FR-SCH-007, FR-SCH-008, FR-SCH-015. Code and contract:
`services/scheduler-service/` (`src/`, `contracts/v1/README.md`, `README.md`) and
`packages/contracts/registry/scheduler.recovery-plan.v1.json`. This directory holds local
verification runs and what they do not establish.

## Run of record

`runs/run-4-committed/` — one local run of `capture_run.py` on a **clean committed tree**: tested source
commit `5478ec4fea2b8d201882cde0bfcaea21d4326114` (tree `b7ebe5f70d9d996f56eb67c8ee0a9046518d3616`,
`tree_clean` true, empty changed-file manifest), started 2026-10-28T08:50:07Z, finished 08:50:42Z, base
`3242d1f18f1e4f5bbf857d28b21e6b250fb381b8`. The commit that adds this run and this README changes only files
under `evidence/WP-SCH-002/`, so every source, test, contract, CI and trace file the run tested is unchanged
(check with `git diff 5478ec4 <evidence commit> --stat`). The run records the tested SHA, never its own commit.
It is local evidence, not CI.

| Command | Exit | Result |
|---|---|---|
| `scheduler-suite` (all service tests, quarantine plugin) | 0 | 250 passed |
| `contract-job-invocation` (`test_plan_contract.py` as the CI contract job runs it) | 0 | 41 passed |
| `registry-regressions` (registry, producer authority, naming, CI gate, boundaries) | 0 | 207 passed |
| `collector-tests` | 0 | 6 passed |
| `ruff-check`, `ruff-format` | 0, 0 | clean, 13 files formatted |
| `pyright` (service config) | 0 | 0 errors |
| `probe-matrix` | 0 | `ok: true` (below) |
| `check-contracts` | 0 | PASS, includes `recovery-plan.v1.schema.json (+instance)` |
| `contract-ci-gate` (committed blobs vs `origin/main`) | 0 | PASS: 1 added, 7 unchanged, 8 validated |
| `trace-drift`, `trace-validate` | 0, 0 | no drift; lint PASS (306 requirements) |
| `projectctl-validate`, `projectctl-catalog-lint` | 0, 0 | stdout of validate discarded on purpose |
| `policy-pinning-regressions` | 0 | 26 passed (builder pins, merged-binding wait) |
| `check-test-strategy` | 0 | PASS, 147 files, 28 suites |
| `static-ratchet` | 0 | no new findings; baseline untouched |
| `architecture-boundaries` | 0 | PASS |
| `observability-coverage` | **1** | **RED, expected**: `scheduler-service` has no logging/health disposition |

`results.json` has argv, UTC times, exit code and byte counts with SHA-256 for every command; the
exact stdout/stderr bytes are the `<id>.stdout` / `<id>.stderr` files (marked binary in
`runs/.gitattributes`). `identity.json` has source, tool, lock, host load at start and finish,
workload and the identities that are unavailable. The run exits 1 only because of the coverage gate. Python 3.11.16, uv 0.12.13, locked CI toolchain (`lock_sha256`
in `identity.json`), Intel i7-9700K / 8 CPUs / 30978 MiB, shared host, no containers; governed identities are unavailable (below).

`probe-matrix.stdout` (one JSON line, no seeds, no clock) reports separately:

- **Freshness table, 30 rows** (3 statuses × 5 instants × 2 modes): only a `FRESH` snapshot with
  `generated_at <= now < valid_until` is `NORMAL`; `now == valid_until` is expired; one microsecond
  before `generated_at` is rejected in both modes; degraded, stale and expired are `DIAGNOSTIC_ONLY`
  or rejected, never `NORMAL`.
- **Plan leaf mutations:** every scalar of both fixtures (130 and 139 leaves) changed once. All
  269 tampered documents are rejected; after recomputing the digest 124 are still rejected by a
  structural or cross-field rule and 143 decode to a plan with a **different** digest (the rest are
  the digest field itself); **0 re-digested mutations keep the original digest**.
- **Snapshot drift against the cited plan:** 7 of 7 drifted snapshots (revision, instant, schedule
  version, each lot and equipment revision) fail the binding.

Scratch mutation check (not committed): 35 injected defects in `snapshot.py`, `plans.py` and
`wire.py`; all caught except one unreachable defensive flag (`allow_nan` in the canonical
serializer, inputs are already finite).

## Earlier runs kept as history

All three are byte for byte as captured and describe only the tree they ran on.

- `runs/run-1-uncommitted/`: taken before the evidence-collector tests were listed in
  `ci/test-strategy.json`, so `check-test-strategy` failed (147 files, 1 violation). The strategy entry and CI
  line were then added and the collector gained five commands (trace, projectctl and policy-pinning
  checks); its input manifest differs from later runs in `ci.yml`, `ci/test-strategy.json` and
  `capture_run.py`.
- `runs/run-2-uncommitted/`: the candidate Codex reviewed (200 scheduler tests). Review findings R1
  (`propose_recovery_plan` trusted a retained `NORMAL` label and accepted an expired snapshot) and R2
  (a JSON integer such as `10**400` escaped as `OverflowError` instead of `PlanError`) were reproduced against
  its source. Run-3 supersedes it; the fixes add 50 tests and one scratch-mutation round (R1/R2 guards: 5 of 5
  caught after one extra test for the forged-label guard).
- `runs/run-3-uncommitted/`: the tree after the R1/R2 fixes that Codex re-reviewed (250 tests), before the first commit.
  Its input manifest hashes the collector before the `contract-ci-gate` command was added, so it will not match the
  committed `capture_run.py`; the 31 listed hashes describe that dirty tree only.

## What this is not

- Fixture and contract-level evidence only. Not TEST-UI-PLAN, AV-SCEN-01/02, E2E-01,
  BENCH-E2E-001 or BENCH-SCH-001; FR-SCH-007/008/015 are `EVIDENCE_PENDING` (a local asset ran; `EXECUTED_AS` cites run-4; no
  EvidenceID, `VERIFIED` not claimed) and FR-SCH-001 is unchanged because no dispatch or scheduling is realized.
- The generator (DEP-083) and the production validator (DEP-084) do not exist; DEP-083/084 stay
  `NOT_READY` and their precise consumer fields are proposals (`contracts/v1/README.md`).
  `REPORTED_VALID` is an unattested relay, never validity.
- The `TwinQueryAPI` test uses a fixture provider, not a live authenticated Twin.
- GitHub CI and the real Plane helper were not run against this candidate.
- No governed ReleaseManifest, EnvironmentManifest image digest or HardwareProfile exists
  (WP-PLAT-005); the host facts are local labels.
- Observability: adding `services/scheduler-service` makes the platform coverage gate fail
  truthfully. The decision is the platform owner's (Yavuz); no exemption was proposed or copied.
