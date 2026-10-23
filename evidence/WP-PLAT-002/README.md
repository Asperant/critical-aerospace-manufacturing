# WP-PLAT-002 — mfgctl developer and operator CLI: evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın (advisory, CHG-018) · F1 · M1/S2 ·
readiness node DN-PLAT-TOOLING · requirements FR-PLAT-003, NFR-DX-001…004.

DoR: owner assessment on issue #12 (READY verified 2026-10-22); implementation
start on the same issue (IN_PROGRESS verified 2026-10-23, DEP-001 re-confirmed).

## Deliverables (04 card)

| Deliverable | Where |
|---|---|
| mfgctl command surface | `tools/mfgctl/src/mfgctl/cli.py`; contract `tools/mfgctl/schemas/capabilities.schema.json` |
| doctor checks | `tools/mfgctl/src/mfgctl/doctor.py`, `venv.py` (git, python, uv, venv, docker, compose, disk, ports, lock) |
| smoke commands per capability | `smoke`, `up`/`down`/`status`, `scenario` in `runtime.py` over `registry.py` |
| timing instrumentation for DX targets | `timing.py`, `mfgctl timings` |

Also delivered: idempotent `bootstrap` (never deletes), `check --fast/--pr` reading
its commands from `.github/workflows/ci.yml`, and a redacted `diagnose bundle`
hook (NFR-DX-008 groundwork). Operator documentation: `tools/mfgctl/README.md`.

## Slices

| Slice | Commit | Content |
|---|---|---|
| A | `e6bd2e8` | package skeleton, root discovery, read-only doctor, CI wiring, CODEOWNERS |
| B | `c8d3425` | bootstrap, check, timings, venv health |
| C | `b19c8ef` | capability registry contract, profile/smoke/scenario, diagnose bundle |
| D | this pull request | timing summary counts successful runs only, trace (03/04), evidence |

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `tools/mfgctl/tests/` (TEST-PLAT-002-001…004 in 03 §19.3) | TEST-PLAT-FABCTL | FIXTURE_ALLOWED (fake runners; one test reads the real ci.yml) | CI t1-unit, step "mfgctl tests" |
| `capabilities.schema.json` + example | contract | — | CI t1-contract |
| RUN-PLAT-002-DEV-001 | BENCH-DX-001 instrumentation | REAL commands on the shared host | DEV |

Negative paths covered by the tests: missing tools, unreachable Docker daemon,
wrong Python, unusable or foreign-owned environment, stale lock, timeouts, low
disk, busy ports, workflow drift, unwritable timing storage, missing or
contract-violating registry, unknown names, secret redaction, failed runs
excluded from DX targets.

## Development run RUN-PLAT-002-DEV-001

Produced by `collect_run.py` on the shared host at the revision recorded in
`RUN-PLAT-002-DEV-001/record.json`; host paths and names are replaced with
placeholders. Files: `record.json` (steps, exit codes, explanations),
`doctor.json`, `timings.json`, and the logs of bootstrap (twice), check --fast,
the mfgctl tests, `up core` and `diagnose bundle`.

Read it as a development observation, not acceptance evidence:

- the host is not a documented HardwareProfile (Item 82 still open), so
  NFR-DX-001/002 timings are DEV observations with `observed: null` in 03;
- a non-zero exit is recorded as observed and explained in `record.json`.

## Limitations and follow-ups

- **Registry and Compose profiles:** `profile`, `up`, `down`, `status`, `smoke`
  and `scenario` stop with exit 2 until WP-PLAT-001 delivers
  `infra/mfgctl/capabilities.json` (DEP-003). NFR-DX-003 (smoke ≤ 2 min) and
  NFR-DX-004 (profile ≤ 5 min) stay VERIFY_PLANNED until then.
- **Docker access on the shared host:** the per-person Linux accounts introduced
  on 2026-10-22 are not in the `docker` group; doctor reports it with the
  remediation. Host administration item, reported to the host owner.
- **Integration tier locally:** `check --pr` reports t1-integration as NOT RUN;
  CI runs it.
- **HardwareProfile and BENCH-DX-001 suite:** measurement on documented hardware
  belongs to the M4/M5 benchmark work, not to this package.
- No sealed EvidenceID, accepted measurement or VERIFIED state is claimed.
