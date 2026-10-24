# WP-SIM-001 implementation evidence

Local development evidence, 2026-10-24, on `wp/WP-SIM-001-deterministic-des-kernel`
created from `origin/main` = `ff56cfeb3142a41e0eb77b0649e6d8ab0fb7c506`. All runs
were captured on an uncommitted working tree; the file hashes in `run-manifest.json`
bind the content later committed unchanged as the candidate commit (its SHA cannot be
recorded inside the commit itself and is stated in the workflow handoff). This index describes the **post-review revision** (Codex review R1-R3
addressed); runs 1-3 belong to the earlier pre-review revision. This is **not** a sealed EvidenceBundle, a remote CI result, a
`VERIFIED` record or an acceptance record. `AUTO_PREPARATION.md` in this directory
is the earlier mechanical preparation record and is unchanged.

## Authorization and readiness

- `cap-plane-queue` reported WP-SIM-001 as `READY`, not blocked, assigned to the
  canonical owner (Batuhan Kaya). No Plane state was changed.
- `projectctl check-ready WP-SIM-001` returned **UNKNOWN** (transition not
  authorized). It was not converted to PASS. No attributable owner assessment of
  the DoR gap table was supplied to the implementing session; the operator
  directed the start of implementation from the approved plan. That direction is
  not a DoR assessment.
- Review risk estimate kept at the conservative **CR-4** from `AUTO_PREPARATION.md`
  (implementation change class C1); not downgraded to the earlier CR-2.

## Deliverables

| Deliverable (04) | Realization |
|---|---|
| DES kernel module | `services/manufacturing-simulator/src/manufacturing_simulator/` — `events.py` (immutable events, heapq queue), `clock.py`, `kernel.py` (dispatch, run termination, fail-stop), `scenario.py`, `errors.py`, `validation.py` |
| Named RNG stream registry | `rng.py` — arrival, processing, failure, repair, quality, inspection plus architecture-named telemetry and transport; NumPy `PCG64` / `SeedSequence(master_seed, spawn_key=(fixed id,))` |
| Kernel unit/property test suite | `services/manufacturing-simulator/tests/` — 202 tests, Hypothesis profile bounded to 100 derandomized examples |
| Static and CI wiring | root `pyrightconfig.json` (simulator src and tests added), `ci/pyproject.toml` + `ci/uv.lock` (editable simulator source, `numpy==2.4.6`, `hypothesis==6.168.1`), `.github/workflows/ci.yml` step in `t1-unit` |

Exact Core fields consumed: **NONE**. DEP-038 gates the later WP-SIM-003 and is
not claimed satisfied. No Core mutation path, Oracle export, canonical schema,
docs or `09_change/` edit, new infrastructure or external DES framework.

## What was executed

`runs/run-5-post-review/` is the final run: executed once after the last source
edit of the post-review revision (20 commands, all exit 0). `commands-and-results.json`
binds every command, UTC timestamps and exit codes for all runs; `run-manifest.json`
binds the source file hashes of the final revision, base commit, scenario/config
hash, seed, stream-id mapping, tool versions and environment.

| Check | Outcome in the final run (run-5) |
|---|---|
| Simulator pytest (`test-results.xml`) | 202 passed, 0 failed, 0 skipped |
| Simulator Pyright (service config) | 0 errors |
| Simulator Ruff check / format | clean / 16 files formatted |
| `static_ratchet.py check` | PASS; totals unchanged (ruff 307, pyright 189, unformatted 56); `static_baseline.json` not edited |
| flake policy, `ci/tests`, projectctl tests, contracts | pass (26 / 398 tests; 13 schemas, 6 instances) |
| `projectctl validate`, `catalog-lint` | PASS; PASS (306 records) |
| Regression of shared-tooling neighbours | Core pure tests + Pyright, consumer pure, observability pure + coverage, Operations BFF tests + Pyright, mfgctl tests: pass |

Replay: `replay-comparison.json` (regenerated for this revision) — six seeds, each
compared in-process and in fresh processes under `PYTHONHASHSEED` 0, 1, 424242 and
random: all traces equal. `mutation-sanity.txt`: thirteen injected defects (tie
order, clock regression, lookup-order-dependent streams, shared stream id, run
status after failure, consume-before-check, horizon off-by-one, termination
precedence, global RNG, shared queue, and the reverted R2, R1 and typed-pair fixes)
were each caught by the suite. That is a self-assessment of test sensitivity, not a
canonical verification record.

## Run history and source relationship

| Directory | Source revision | Outcome |
|---|---|---|
| `runs/run-1-failed/` | pre-review, before the registry entry existed | `observability-pure-tests` exit 1 (registry rejected the new directory) |
| `runs/run-2-final/` | pre-review (168 tests), registry entry added | 20 commands, exit 0; **superseded** by run-5 |
| `runs/run-3-post-evidence/` | pre-review, repo-wide checks after the first evidence files | exit 0; superseded |
| `runs/run-4-failed-contracts/` | post-review fixes with an over-long registry reason | `contracts` exit 1 (schema maxLength 300) |
| `runs/run-5-post-review/` | post-review, after the last source edit | 20 commands, exit 0 (final) |
| `runs/run-6-post-evidence/` | post-review, after the evidence files were refreshed | validate, catalog-lint (merge base), static ratchet, `git diff --check`: exit 0 |

`run-manifest-pre-review.json`, `replay-comparison-pre-review.json` and
`mutation-sanity-pre-review.txt` are the retained pre-review records. Each failure
exposed a real defect that was fixed before the whole gate was re-run in full; none
was retried until green. Captured output is **normalized** (trailing whitespace
stripped, the session scratch path replaced by `<scratch>`); the original raw bytes
are not retained and cannot be reconstructed. Result lines and exit codes are
unchanged.

## Verification families and obligations

| Family / item | Status |
|---|---|
| TEST-SIM-KERNEL | local property, boundary and negative-path tests executed (toy handlers) |
| TEST-SIM-DETERMINISM | local same-seed, cross-process, hash-seed, lookup-order and stream-isolation tests executed |
| FR-SIM-007 | fixture-based determinism evidence permitted by docs/03; produced locally |
| FR-SIM-001 | requires REAL boundary evidence: **not produced**; toy fixtures do not establish the integrated path |
| AV-SCEN-01, E2E-01, BENCH-SIMVAL-001 | `NOT_YET_EXECUTED`; no commands or thresholds invented |
| Remote CI on the PR head, post-merge validation, DoD, DONE | outstanding |

## Deviations and findings for review

1. **Unplanned shared-file change, decision pending**: `infra/observability/coverage.json`
   (WP-OBS-001 registry) gained a `PENDING` entry for the simulator because the
   registry rejects `NOT_PRESENT` once the directory exists. The exemption owner
   (`Yavuz`) and expiry (2026-11-20) were copied from the neighbouring entries as a
   **proposal**; the record itself says they are not confirmed by an attributable
   platform-owner decision. No agreement with the owner exists. The entry fails the
   coverage check again on 2026-11-20 unless adopted or renewed.
2. **Routing gap**: `.github/CODEOWNERS` routes `evidence/WP-SIM-001/` but has no
   line for `services/manufacturing-simulator/`. Not edited (no invented handles).
3. **Plan wording**: the plan's "Pyright via src import resolution" is realized
   through a root `executionEnvironments` entry for the simulator, preserving every
   existing setting.
4. **Local environment**: tools ran from a `uv` environment kept outside the
   repository (`UV_PROJECT_ENVIRONMENT`); CI uses `ci/.venv` from the same lock.
5. **Known-answer RNG draws** in `test_rng.py` were recorded from NumPy 2.4.6 when the
   tests were written, not derived independently; they detect stream-id or NumPy
   drift. Replay guarantees hold for the pinned NumPy version only.
6. **Limitation**: the local checkout's `AGENTS.md` is a local operator copy
   (skip-worktree) and lacks upstream's newer AUTO_NEXT section; the index entry
   was aligned with `origin/main`.
7. Captured output normalization is described under 'Run history' above; the two
   helper scripts also had trailing whitespace stripped. `test-results.xml` and the
   JSON files are as produced.
8. Hypothesis runs are derandomized and bounded, so CI is reproducible but explores
   a fixed example set.
9. **Review follow-up (Codex R1-R3)**: R1 - the serialized payload reader now
   distinguishes an absent payload (default empty) from a provided one, which must be
   a mapping; falsey scalars, null and arrays are rejected, as are malformed typed
   `(key, value)` pairs, with `InvalidConfigurationError`. R2 - a `BaseException`
   inside a handler (`KeyboardInterrupt`, `SystemExit`, custom) now records one
   FAILED record, marks the run FAILED and is re-raised unchanged; partial handler
   mutation is retained (no rollback claim) and later `step`/`run`/`schedule` are
   refused. R3 - the unsupported "agreed with the owner" assertion was removed from
   the registry record (deviation 1).
10. **Review aids, not verification**: a read-only compliance audit (subagent
    `cap-compliance-auditor`) was run once on the pre-review diff. It reported FAIL
    on judgement points only (the unplanned registry change, nine deliberate
    rule-specific `pyright: ignore` comments in negative-path tests, evidence hygiene
    items fixed afterwards) and found no authority-boundary, determinism, secret or
    evidence-honesty problem. A compliance result is not a test or verification result.
