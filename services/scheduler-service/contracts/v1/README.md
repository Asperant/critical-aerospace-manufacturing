# scheduler.recovery-plan.v1 — IC-SCH-004 RecoveryPlan (WP-SCH-002)

Producer-owned contract of `scheduler-service` (owner Batuhan Kaya), registered as
`packages/contracts/registry/scheduler.recovery-plan.v1.json` (class `ARTIFACT`, authority
"PLAN proposal only"). The schema is `recovery-plan.v1.schema.json`; the decoder that is the
runtime authority is `manufacturing_scheduler.plans`.

A RecoveryPlan is a **proposal**. Nothing in this contract or package activates, approves or
executes a plan, and no field certifies feasibility. Planner is not validator: a candidate's
`validation_result` is the producer's *unattested report*; a consumer needs an independent
validation (DN-SCH-VALID, DEP-084) bound to world, snapshot revision, candidate and
`content_digest` at its own execution boundary.

## Fixtures (both `DEVELOPMENT_FIXTURE`, hand-written, not operational output)

- `recovery-plan.v1.json` — the pending shape: every solve, objective, stability, counterfactual
  and validation entry is `NOT_RUN`/`NOT_COMPUTED`, the rationale `NOT_AVAILABLE`. Rebuilt
  exactly by `propose_recovery_plan` over the published snapshot fixture. Its sibling name lets
  `ci/scripts/check_contracts.py` validate it against the schema once the schema is tracked.
- `recovery-plan.self-reported-valid.json` — a producer that *claims* computed objectives, a
  counterfactual and a valid result (`FIXTURE-NOT-A-VALIDATOR`). It exists to show that such a
  claim authorizes nothing; its ids are labelled fixtures, not real solver or validator results.

## Field sources

`C` = named by docs/02 (IC-SCH-004 field list: `recovery_plan_id`, `incident_id`, affected
material, affected equipment, candidate schedules, assumptions, `ObjectiveProfile`,
counterfactual results, recommended candidate, base revision). `R` = docs/01 requirement text
(FR-SCH-007 source revision, FR-SCH-008 schema, FR-SCH-015 rationale/objective/comparison).
`P` = proposed by this WP to make a named item precise; to be reconciled with the real
generator (DEP-083) and validator (DEP-084) contracts, which this WP does not certify.

| Wire field | Source | Notes |
|---|---|---|
| `contract_version`, `content_digest` | P | digest = `sha256:` of sorted-key compact ASCII JSON without the digest field; `1` and `1.0` differ; binds content, not a signature |
| `recovery_plan_id`, `incident_id` | C | opaque ids, compared unchanged |
| `world_id` | R/C | explicit; equals the snapshot's and every validation binding's world |
| `source_snapshot.{snapshot_revision,generated_at}` | R (FR-SCH-007) | copied from `core.scheduling-snapshot.v1` |
| `base_schedule_version` | C ("base revision") | the snapshot's `current_schedule_version` (nullable) |
| `generated_at`, `valid_until`, `generation` | P | canonical UTC `…Z`; `generation.kind` `GENERATOR_OUTPUT` is reserved for DEP-083 and never emitted here |
| `affected_material[]` | C | `lot_id`, `lot_revision`, `route_id`, `visit_id`, `position` from the snapshot lot; re-entrant visits stay distinct |
| `affected_equipment[]` | C | `equipment_id`, `equipment_revision` from the snapshot |
| `assumptions[]` | C | free-text statements with ids |
| `objective_profile` | C, R (FR-SCH-015) | id, version, method, terms (`metric`, `unit`, direction, weight) |
| `candidate_schedules[]` | C | `candidate_id`, `algorithm`, `horizon`, `assignments[]` (PLANNED, never ACTUAL; optional `batch_id` groups same-equipment, same-interval work), `solve`, `predicted_objectives`, `stability`, `counterfactual`, `validation_result` |
| `predicted_objectives[]` | R (FR-SCH-015) | exactly one per profile term, same metric and unit (comparable); `value` null unless `COMPUTED` |
| `counterfactual` | C | reference only (`result_ref`, `counterfactual_world_id`), `NOT_RUN` unless a real result exists |
| `recommended_candidate_id` | C | must name a candidate of the same plan |
| `comparison` | R (FR-SCH-015) | `NOT_COMPUTED` or a ranking that is a permutation of the candidates |
| `rationale` | R (FR-SCH-015) | `TRACE_DERIVED` needs a summary and algorithm-trace refs; otherwise `NOT_AVAILABLE`; ties the explanation to algorithm-trace refs |
| `validation_result` | P | `NOT_RUN`, or `REPORTED_VALID`/`REPORTED_INVALID` with validator identity, result ref and a binding triple equal to this plan's world, snapshot revision and candidate |

## Rules the decoder enforces beyond the schema

Exact keys at every level; whitespace-free opaque ids; bool is never a number; finite numbers
within ±(2^53−1); canonical UTC timestamps; strict JSON (duplicate fields, `NaN`, `Infinity`,
overflowing floats rejected); no field named like Simulator Oracle state; unique candidate,
assignment, lot, equipment, assumption and metric ids and one assignment per (lot, visit); valid
intervals inside the candidate horizon; consistent `NOT_RUN`/`COMPUTED`/`AVAILABLE` states; a
recommended candidate that exists; `generated_at < valid_until` and the source snapshot not newer
than the plan; and `content_digest` equal to the recomputed digest. The JSON Schema expresses the
structural subset (it also treats `1.0` as an integer, which the decoder does not).

`check_snapshot_binding(plan, snapshot)` additionally requires the plan to cite exactly the
consumed snapshot: world, revision and instant, base schedule version, and each cited lot (revision,
route, visit, position) and equipment (revision). A cited visit must be the lot's **current** visit,
because the v1 snapshot carries no remaining route. Eligibility, overlaps, maintenance windows and
every other feasibility rule are not assessed (`feasibility_assessed` is always `False`).

## Compatibility

First version of a new family: no predecessor exists, so the registry gate performs boundary
validation only. Any breaking change (including an authority change) is a new major and a new
contract id. Adding an optional property is non-breaking for the registry comparator but a strict
consumer rejects unknown fields, so each consumer must be tested before such an addition.
