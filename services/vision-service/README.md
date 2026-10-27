# vision-service — Vision inspection pipeline (WP-VIS-001)

Owner: Selman Özdemir. Semantic authority (02 vision-service): InspectionRequest
processing, inspection-artifact access by `ArtifactReference`, `InspectionObservation`
and model provenance. Vision has no quality disposition, hold, root-cause or
acceptance authority.

## Pipeline

`parse_request` → `inspect` (verified artifact read → PNG decode → preprocessing →
baseline inference) → `InspectionObservation` v1 payload
(`contracts/v1/inspection-observation.v1.schema.json`).

| Stage | Module | Identity carried on the observation |
|---|---|---|
| Request (Vision's consumed view of IC-VIS-001) | `request.py` | request/run ids, Lot/SerializedComponent/RouteVisit ids and revisions |
| Artifact read | `pipeline.py` via `cap_artifacts.ArtifactStore.read` | artifact id, version, checksum |
| Decode | `png.py` | — |
| Preprocessing | `preprocessing.py` | `vision-prep-gray-unit/1` |
| Inference (F2 baseline) | `baseline.py` | `vision-baseline-local-deviation` 1.0.0, `vision-tp-baseline-z6/1` |

Behaviour that consumers can rely on:

- Only allowlisted request fields are accepted; any other field (for example an
  Oracle or ground-truth label) rejects the request. Oracle-classified artifacts and
  non-`inspection_image` artifacts are rejected. The request `world_id` must equal the
  artifact context.
- An artifact that is not AVAILABLE or fails checksum verification raises and yields
  **no** observation.
- A readable artifact that cannot be evaluated (undecodable, unsupported format,
  smaller than 16 px) yields `NOT_EVALUATED` with `INVALID_INPUT`, never "no defect".
- Low-contrast input is `DEGRADED_INPUT` and always sets `review_required`.
- The baseline has no defect taxonomy: every candidate is `UNKNOWN_REVIEW_REQUIRED`
  with no class label or confidence, and scores are `UNCALIBRATED` robust z-scores.
  It is a placeholder that computes from real pixels (05 DEP-059, F2), not a trained
  model, and carries no accuracy claim.

## Tests

```sh
uv run --project ci --locked python -m pytest -c services/vision-service/pyproject.toml services/vision-service/tests -q -p pytest_quarantine
uv run --project ci --locked pyright --project services/vision-service/pyrightconfig.json
```

Images and references in the tests are SYNTHETIC TEST data built in the tests; reads
go through the real `ArtifactStore.read` verification path over an in-memory S3
client (STUB_ALLOWED).

## Not yet

Broker consumption of `InspectionRequested`/`RunInspection`, event publication,
SeaweedFS integration test, `vision` schema persistence, telemetry
(`configure()`/`health_report()`), promoted ModelPackages (WP-VIS-002/003) and the
formal Oracle-taint guard (WP-VIS-009) are later work.
