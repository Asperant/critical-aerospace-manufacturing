# WP-VIS-001 — slice 2: pure inspection pipeline

Owner: Selman Özdemir · supporting reviewer: Asrın (advisory, CHG-018) · F0 · M2/S3–S4 ·
readiness node DN-VIS-SERVING · requirements FR-VIS-001, FR-VIS-009.
Builds on slice 1 (`vision.inspection-observation.v1`).

## Scope

WP-VIS-001 major tasks covered in pure form: artifact fetch by reference,
preprocessing with versioned identity and observation assembly. The deliverable
"artifact-driven preprocessing path" exists; the inference worker and
InspectionRequest consumption exist as library functions, not yet as a broker
consumer.

| Part | Where |
|---|---|
| Request validation (allowlist, Oracle/world checks) | `services/vision-service/src/vision_service/request.py` |
| Bounded PNG decoder (CRC, all five filters, size limits) | `.../png.py` |
| Versioned preprocessing and input quality | `.../preprocessing.py` |
| F2 baseline candidate detector (DEP-059) | `.../baseline.py` |
| Pipeline and observation assembly | `.../pipeline.py` |
| Tests (TEST-VIS-001-002, TEST-VIS-PIPELINE) | `services/vision-service/tests/` |
| CI step | `.github/workflows/ci.yml` t1-unit "Vision inspection pipeline tests and typing (WP-VIS-001)" |

No new dependency: decoding uses `zlib` and the already locked `numpy`.

## Decisions

- The baseline is label-free, so it never emits a known class: all candidates are
  `UNKNOWN_REVIEW_REQUIRED`. This keeps the F2 placeholder from looking like a
  classifier (02 ARCH-INV-VIS-01; AGENTS §10).
- Integrity failures raise instead of producing an observation; unevaluable images
  produce `NOT_EVALUATED`. Degraded input always requires review.
- The request model is Vision's consumed view of IC-VIS-001, whose exact schema is
  not frozen by its producer (02 marks the fields as derived candidates). It is not
  registered as a contract and must be reconciled when IC-VIS-001 is frozen.

## Verification (local, 2026-10-28)

Locked CI toolchain (`uv 0.12.13 sync --project ci --locked`, Python 3.11.16), CI
step commands and t1-unit job environment.

| Check | Result |
|---|---|
| vision-service tests | 56 passed |
| pyright (strict `src`) on vision-service | 0 errors |
| ruff check / format on vision-service | clean |
| `ci/tests` | 773 passed |
| observability tests (coverage registry) | 126 passed |
| test strategy | PASS, 146 files in 25 suites, 0 violations |
| architecture boundaries, static ratchet | PASS; no new static findings |
| JSON Schema contract tier | PASS |

Negative paths exercised: unknown request/subject fields (Oracle/ground-truth/
scenario-id labels), missing fields, blank or non-string identities, world mismatch,
non-image and Oracle-classified artifacts, invalid references; checksum mismatch and
non-AVAILABLE artifact (no observation); undecodable, too-small and unsupported-format
input (NOT_EVALUATED); PNG signature, CRC, truncation, unsupported depth/color/
interlace, hostile dimensions, data-length mismatch, decompression bound, unknown
filter; candidate cap; naive clock.

## REAL object storage (TEST-VIS-001-003)

`services/vision-service/tests/test_pipeline_integration.py` writes a synthetic image
with the writer identity, runs the pipeline with the reader identity against REAL
SeaweedFS and validates the observation against the registered contract; a reference
with a foreign checksum must be refused by the real read. It runs in t1-integration
("Vision pipeline over REAL SeaweedFS (WP-VIS-001)") after the infra profile starts.
It could not run locally (no Docker access for this account): locally it fails with
`CAP_S3_ENDPOINT not set`, by design never skipping. The PR's CI run is the only
REAL result.

## Broker integration: blocked, not attempted

`InspectionRequested` consumption and observation publication need a stream/subject
binding (`packages/contracts/stream-definitions.json`, WP-EVT-001) and a real
IC-VIS-001 producer; neither exists on main. Inventing Vision subjects or streams
would cross the WP-EVT-001 boundary, so this slice does not.

## What this evidence does not claim

No broker consumption or event publication, no persistence
and no telemetry adoption. FR-VIS-001 and FR-VIS-009 are not verified: that requires
the integrated path (E2E-01, AV-SCEN-01). The baseline has no measured accuracy and is
not a ModelPackage. Test images are synthetic.
