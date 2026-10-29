# WP-VIS-008 — CPU smoke inference path: evidence

Owner: Selman Özdemir · supporting reviewer: Yavuz (advisory, CHG-018) · F1 · M2/S3–S4 ·
readiness node DN-VIS-SERVING · requirements FR-VIS-014, NFR-PERF-009, NFR-RES-007.
Builds on the WP-VIS-001 pipeline (branch `wp/WP-VIS-001-inspection-pipeline`).

Verification families: TEST-VIS-CPUSMOKE, TEST-RES-CPUONLY.

## Deliverables (04 card)

| Deliverable | Where | State |
|---|---|---|
| CPU smoke model package, distinct from promoted final models | `services/vision-service/model-packages/vision-baseline-local-deviation/1.0.0/package.json` is a non-promoted, CPU-only package manifest loaded and identity-checked by `vision_service.smoke` | done for the bounded smoke package; promoted final ModelPackages remain outside this WP |
| `mfgctl smoke vision` path | `infra/mfgctl/capabilities.json` capability `vision` → `services/vision-service/smoke.sh` → `python -m vision_service.smoke` | done |
| documented CPU baseline timing | `RUN-VIS-008-LOCAL-001.json` (this directory) | recorded on the primary shared host; synthetic sample |

The smoke path needs only the locked CI toolchain (`numpy`, standard library): no GPU
library, accelerator runtime, container or platform service (NFR-RES-007). It reads
every image through the real `ArtifactStore.read` verification path over an
in-memory S3 client and validates every observation against the registered
`vision.inspection-observation.v1` contract. It fails when any image exceeds
15 s or when a planted-defect image and a clean image are not told apart.

## Accepted sample input

`--sample-manifest PATH` accepts an explicit `vision.smoke-sample/v1` manifest
with labelled PNG paths. The loader rejects missing labels, malformed entries,
and paths outside the manifest directory. No accepted sample is checked into
this repository; the default run therefore remains synthetic and cannot satisfy
NFR-PERF-009 acceptance.

## RUN-VIS-008-LOCAL-001

`services/vision-service/smoke.sh --json` on 2026-10-28, branch
`wp/WP-VIS-008-cpu-smoke` (on WP-VIS-001 pipeline `4401f0f`; pipeline code unchanged by later commits), locked CI toolchain (Python 3.11.16,
numpy 2.4.6). Host: Intel Core i7-9700K, 8 logical CPUs, 30.3 GiB, Linux 7.0.0 —
the primary shared-host HardwareProfile pinned in 01 (DEP-GAP-11 RESOLVED). The GPU
of that profile was not used.

| Sample | Result | Max s/image | Mean s/image | Threshold |
|---|---|---|---|---|
| `vision-smoke-synthetic/1`, 8 × 512×512 grayscale | PASS, functional ok | 0.0142 | see JSON | 15 s |

The shared host was not quiesced and other workloads may have been running; this is
a single run, not a benchmark campaign.

## Verification

| Check | Result |
|---|---|
| `uv run --project ci --locked mfgctl smoke vision` | PASS, exit 0 |
| `services/vision-service/tests/test_smoke.py` (TEST-VIS-008-001, TEST-VIS-CPUSMOKE / TEST-RES-CPUONLY) | 8 passed, within 70 vision-service non-integration tests |
| `infra/compose/tests` (registry conforms, smoke script exists) | 32 passed |
| `tools/mfgctl/tests` | 113 passed |
| ruff, pyright strict (vision-service), static ratchet, architecture boundaries, test strategy | clean / PASS |

Negative paths: threshold breach and functional mismatch both make the smoke FAIL
(exit 1); invalid CLI sizes are rejected.

## What this evidence does not claim

Acceptance classification: implementation complete for the bounded CPU smoke
scope; accepted-sample and promoted-model acceptance remain separate.

Verification boundary: the checked-in run proves the runnable CPU package, CLI,
sample handling, contract validation and negative paths on the shared host; it
does not substitute a governed accepted inspection sample or promoted model.

NFR-PERF-009 is **not** accepted: it names "the accepted small inspection sample",
and no accepted sample exists until dataset governance (WP-VDATA-001) selects one;
the sample here is synthetic. The baseline is not a trained model and has no
accuracy claim. BENCH-PERF-VIS (cold/warm CPU/GPU characterization) is WP-VIS-010.
