# Vision InspectionObservation v1

| Registry field | Declaration |
|---|---|
| Contract ID / version | `vision.inspection-observation.v1` / v1 (EVT-InspectionObservation-v1) |
| Type / semantics | EVENT payload; asynchronous; carried in cap `event-envelope.v1` |
| Semantic owner / producer | Selman Özdemir / vision-service only |
| Intended consumers | AI/RCA evidence intake, Digital Twin projection, Core quality normalization |
| Output schema | `inspection-observation.v1.schema.json` |
| Fixtures | `inspection-observation.{defect-candidates,no-defect-candidates,not-evaluated,degraded-input}.json` |
| Authority | Vision perception evidence only; no quality disposition, hold, root-cause or acceptance authority |
| Status / dependency | Published by WP-VIS-001 slice 1. Registering it is not a readiness declaration for DN-VIS-OBSCON or DN-VIS-ARTCON |
| Security | Internal inspection metadata; no image bytes, storage keys, signed URLs, credentials or Oracle labels |
| Deprecation | None; initial version |

## Meaning

An observation is immutable perception evidence for one inspection-image artifact
version: defect candidates with localization, mask reference, class confidence,
anomaly score, open-set decision and the pipeline identity that produced them.
It is **not** the IC-VIS-002 `InspectionResult`. Core normalizes one or more
observations (and any attributed human review) into that separate domain result
and alone owns canonical quality and manufacturing transitions. A re-run or a
human review is a new observation with a new `observation_id`, never an edit.

## Consumed identities

| Field | Source contract | Source field |
|---|---|---|
| `subject.lot_id`, `subject.lot_revision` | `core.order-query.v1` | `Lot.id`, `Lot.revision` |
| `subject.serialized_component_id`, `subject.serialized_component_revision` | `core.order-query.v1` | `SerializedComponent.id`, `SerializedComponent.revision` (its `lot_id` equals `subject.lot_id`) |
| `subject.route_visit_id` | `core.order-query.v1` | `RouteVisit.id` |
| `source_artifact`, `defects[].mask_artifact` | `cap.artifact-ref/v1` | `artifact_id`, `version`, `artifact_type`, `checksum` |
| `context` | `cap.artifact-ref/v1` | `context.world_id`, `context.simulation_run_id`, `context.branch_id` (`world_id` required) |

Core identities and revisions are opaque nonblank strings, preserved unchanged.
The revision is the one named by the inspection request; it is not a freshness
proof. A distinct `route_visit_id` keeps a re-entrant reinspection after rework
distinguishable from the first inspection. Artifacts are referenced by identity
and checksum only; storage location remains a transport detail of the artifact
service.

## Rules enforced by the schema

- `outcome` is `DEFECT_CANDIDATES` (at least one candidate), `NO_DEFECT_CANDIDATES`
  (none) or `NOT_EVALUATED`. `INVALID_INPUT` data quality forces `NOT_EVALUATED`
  with no candidates and no anomaly score: an input that could not be evaluated is
  never reported as "no defect".
- A non-`VALID` data-quality status names at least one flag; `VALID` names none.
- `open_set_decision` follows the 02 open-set rule: `KNOWN_CLASS`,
  `KNOWN_CLASS_REVIEW_REQUIRED`, `UNKNOWN_REVIEW_REQUIRED`, `LOW_CONFIDENCE_REVIEW`.
  `class_label` is null exactly for `UNKNOWN_REVIEW_REQUIRED`. Any non-`KNOWN_CLASS`
  candidate forces `review_required: true`. No decision is named "accepted":
  Vision never performs quality acceptance.
- `confidence_calibration` states whether confidences are calibrated; v1 producers
  before WP-VIS-005 emit `UNCALIBRATED`.
- `pipeline_identity` carries ModelVersion(s), PreprocessingVersion,
  ThresholdPolicyVersion and OutputSchemaVersion (02 VIS-E11).
  `BASELINE_ALGORITHM` marks the simple generic algorithm permitted before
  promoted ModelPackages exist (05 DEP-059, F2).
- Every object is closed (`additionalProperties: false`), so Oracle, ground-truth
  or authority fields cannot be added to a valid payload.

Rules JSON Schema cannot express are checked by the contract tests: unique
`defect_id` values and `completed_at` not earlier than `started_at`.

## Fixtures

Fixtures are deterministic **SYNTHETIC TEST** examples, not factory or real
inspection observations. They reuse the Core `order-query.reentrant.json`
identities and the `cap.artifact-ref/v1` example artifact so consumers can check
cross-contract references. Scores and labels are illustrative values, not model
results.

## Not in this version

The inspection request consumer, artifact fetch, preprocessing, inference worker,
broker subject binding, persistence and runtime publication are later WP-VIS-001
slices. Spatial pattern, embedding and cluster references (WP-VIS-006) and
human-review observations are not part of v1; they require a governed contract
change.
