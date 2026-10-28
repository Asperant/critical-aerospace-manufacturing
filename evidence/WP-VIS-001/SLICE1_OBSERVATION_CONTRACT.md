# WP-VIS-001 — slice 1: InspectionObservation v1 contract

Owner: Selman Özdemir · supporting reviewer: Asrın (advisory, CHG-018) · F0 · M2/S3–S4 ·
readiness node DN-VIS-SERVING (contract nodes DN-VIS-ARTCON, DN-VIS-OBSCON) ·
requirements FR-VIS-009 (contract), FR-VIS-001 (identity of the inspected artifact only).

## Scope

This slice publishes `vision.inspection-observation.v1` (EVT-InspectionObservation-v1)
as a registered EVENT payload contract with SYNTHETIC TEST fixtures. It is
contract-only: no runtime code, broker binding, artifact fetch, preprocessing or
inference is added, and no other owner's code or canonical document is changed.
Because `services/vision-service/` now exists, its telemetry coverage entry
(`infra/observability/coverage.json`) moves from `NOT_PRESENT` to `PENDING` with an
owner exemption expiring 2026-11-20, as the WP-OBS-001 coverage gate requires;
platform-owner confirmation is requested, not claimed.

| Deliverable part | Where |
|---|---|
| Payload schema | `services/vision-service/contracts/v1/inspection-observation.v1.schema.json` |
| Contract documentation | `services/vision-service/contracts/v1/README.md` |
| Fixtures | `services/vision-service/contracts/v1/inspection-observation.*.json` (4) |
| Registry declaration | `packages/contracts/registry/vision.inspection-observation.v1.json` |
| Producer authority | `packages/contracts/producer-authorities.json` (`vision-service`) |
| Boundary tests | `ci/tests/test_vision_inspection_observation_contract.py` (TEST-VIS-001-001) |

## Contract decisions

- Two artifacts, per 01 §Final Human Reconciliation and 05 DEP-GAP-07: this is the
  Vision observation; IC-VIS-002 `InspectionResult` stays a separate Core contract.
- Outcomes are perception outcomes (`DEFECT_CANDIDATES`, `NO_DEFECT_CANDIDATES`,
  `NOT_EVALUATED`). Invalid input forces `NOT_EVALUATED`, so an unevaluable input is
  never reported as "no defect" (02 vision-service: no fabricated no-defect results).
- Open-set decisions follow the 02 open-set rule; UNKNOWN candidates carry no class
  label and force `review_required`. No decision is named "accepted".
- The 02 VIS-E11 pipeline identity tuple is mandatory on every observation.
  `confidence_calibration` makes uncalibrated scores explicit until WP-VIS-005.
- Closed objects throughout: Oracle, ground-truth, hold, disposition, root-cause and
  storage/URL fields are rejected by the schema and by negative tests.

## Consumer requirement for DEP-056 (input, not a readiness claim)

The 2026-10-27 S2/S3 reachability audit (CHG-074 / CTRL-HOST-048) classifies
DEP-056 as `MISSING_EXTERNAL_INPUT` because the Vision consumer contract was not
specified. The precise Core identities this contract consumes are:

- from `core.order-query.v1`: `Lot.id`, `Lot.revision`, `SerializedComponent.id`,
  `SerializedComponent.revision`, `SerializedComponent.lot_id`, `RouteVisit.id`;
- as opaque nonblank strings, preserved unchanged, with no freshness or ordering
  semantics.

The fixtures reuse `order-query.reentrant.json` identities and the tests assert
that the subject resolves against that fixture. Binding DEP-056 READY remains a
separate governed step by its owners; this slice does not change its status.

## Verification (local, 2026-10-27)

Environment: shared host, the locked CI toolchain (`uv 0.12.13 sync --project ci
--locked`, Python 3.11.16), running the workflow's own step commands and job
environment (`PYTHONPATH=ci:ci/scripts` for t1-unit). The first PR CI run failed
t1-unit on `packages/observability/tests/test_health_coverage.py` because the new
directory had no coverage entry; this was not caught earlier because only a subset
of steps had been run locally. The coverage entry above fixes it.

| Check (CI step) | Result |
|---|---|
| `ci/tests` (CI tooling tests) | 773 passed, including 37 new Vision contract tests |
| test strategy, flake policy | PASS, 0 violations |
| event-consumer / Core / Twin / Simulator / mfgctl / artifacts / compose tests | 6 / 384 / 14 / 202 / 113 / 77 / 32 passed |
| observability tests, `cap_observability check-coverage` | 126 passed; PASS (vision-service PENDING) |
| trace tests, `cap_trace validate`, `drift --strict`, TL-13 impact | 125 passed; PASS; no drift; PASS |
| Host Plane queue / transition tests | 44 / 288 OK |
| static ratchet (ruff, pyright), architecture boundaries | PASS, no new findings; PASS |
| `cap_contracts.ci_gate` (base `origin/main`) | PASS: added 1, unchanged 7, validated 8, 0 failures |
| `check_contracts.py` (JSON Schema tier) | PASS, 24 schemas, 8 instances |
| Operations BFF contract tests | 228 passed |

Not run locally: frontend npm steps (no frontend change) and t1-integration
(REAL PostgreSQL/NATS; no runtime change). The PR's CI run is the authoritative
record.

Negative paths exercised: invalid input reported as no defect; NOT_EVALUATED with
valid input, scores or candidates; outcome/candidate disagreement; non-VALID quality
without flags; UNKNOWN with a label and known class without one; uncertain
candidate without review; Oracle/ground-truth/disposition/hold/root-cause/storage/
signed-URL fields; missing or empty pipeline identity; wrong output schema version;
null world, blank identities, out-of-range scores, zero-width box, non-sha256
checksum, non-UUID observation id; duplicate defect ids and reversed inference time.

## What this evidence does not claim

DN-VIS-OBSCON and DN-VIS-ARTCON are not declared CONTRACT_READY and DEP-056/057/
061/065 statuses are unchanged. FR-VIS-001 and FR-VIS-009 are not verified: they
require the integrated Vision path (request consumption, artifact read through
`cap.artifact-ref/v1`, preprocessing, inference and publication; E2E-01,
AV-SCEN-01). Trace edges in 03 are not updated by this slice. Fixtures are
synthetic and their scores are illustrative, not model results.
