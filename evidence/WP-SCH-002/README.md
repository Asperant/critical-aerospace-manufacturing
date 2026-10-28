# Evidence — WP-SCH-002 (snapshot consumption and RecoveryPlan contract)

Requirements FR-SCH-001, FR-SCH-007, FR-SCH-008, FR-SCH-015. Code and contract:
`services/scheduler-service/` (`src/`, `contracts/v1/README.md`, `README.md`) and
`packages/contracts/registry/scheduler.recovery-plan.v1.json`. This directory holds local
verification runs and what they do not establish.

## Run of record

`runs/run-3-uncommitted/` — one local run of `capture_run.py` on the **uncommitted** working
tree: base `3242d1f18f1e4f5bbf857d28b21e6b250fb381b8`, 31 changed or untracked files listed with
SHA-256 in `identity.json` (`tree_clean` false, because no commit is authorized yet), started
2026-10-28T08:39:42Z, finished 08:40:17Z, after the Codex review fixes R1 and R2. This is **not** committed-source evidence: a later run on
the committed candidate must be added and cite the exact tested source SHA.

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
workload and the identities that are unavailable. The run exits 1 only because of the coverage gate.

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

Both are byte for byte as captured and describe only the tree they ran on.

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

## What this is not

- Fixture and contract-level evidence only. Not TEST-UI-PLAN, AV-SCEN-01/02, E2E-01,
  BENCH-E2E-001 or BENCH-SCH-001; FR-SCH-001/007/008/015 remain unverified and their RTM states
  unchanged (`VERIFY_PLANNED`) because no committed-source run exists yet.
- The generator (DEP-083) and the production validator (DEP-084) do not exist; DEP-083/084 stay
  `NOT_READY` and their precise consumer fields are proposals (`contracts/v1/README.md`).
  `REPORTED_VALID` is an unattested relay, never validity.
- The `TwinQueryAPI` test uses a fixture provider, not a live authenticated Twin.
- `GitHub CI`, the contract-registry CI gate (it reads committed blobs only) and the real Plane
  helper were not run against this candidate.
- No governed ReleaseManifest, EnvironmentManifest image digest or HardwareProfile exists
  (WP-PLAT-005); the host facts are local labels.
- Observability: adding `services/scheduler-service` makes the platform coverage gate fail
  truthfully. The decision is the platform owner's (Yavuz); no exemption was proposed or copied.
