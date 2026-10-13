# Historical undecided decision packet — CTRL-DOC-009 (superseded below)

Eight root decisions remain. This is a decision aid, not approval or an execution registry. Precedence:01 >02 >stable contracts >03 >04–07 >08 >09 >10. No unique option is established for these questions; no option is selected or recommended by this audit. Counts, ownership and topology remain unchanged unless separately approved.

File names below use these exact paths: `docs/01_Master_Project_Specification.md` (01), `docs/02_System_Architecture_Specification.md` (02), `docs/03_Requirements_Traceability_Matrix.md` (03), `docs/04_Work_Breakdown_Structure.md` (04), `docs/05_Dependency_Graph.md` (05), `docs/06A_Asrin_Engineering_Roadmap.md` (06A), `docs/06B_Selman_Engineering_Roadmap.md` (06B), `docs/06C_Batu_Engineering_Roadmap.md` (06C), `docs/06D_Yavuz_Engineering_Roadmap.md` (06D), `docs/07_Milestone_and_Release_Plan.md` (07), `docs/08_Definition_of_Ready_and_Done.md` (08). Each decision also updates its cited `09_change/CHG-NNN.yaml` through09 governance.

| ID / sources | Exact question and why authority cannot decide | Option A and consequence | Option B and consequence | Exact affected files; implementation gate |
|---|---|---|---|---|
| INSPECTION_CONTRACT_CANONICALIZATION — CHG-003, GAP-RTM-009, RTF-023 | Are InspectionObservation and IC-VIS-002 InspectionResult the same versioned perception contract, or distinct artifacts?01 Items62/81/83 and Item22 use different identities without an approved equivalence/transformation. The candidate-field label is corrected; mandatory provenance stands. | One contract with explicitly proven aliases; freeze one schema and equivalent consumer bindings. | Two contracts; freeze producer/consumer identities, versioned transformation and acceptance authority. Vision never gains manufacturing mutation authority. |01,02,03,04,05,06B,07; blocks affected contract freeze/integration. |
| PROTECTED_COMMAND_NAMING — CHG-004, GAP-RTM-010, RTF-024 | Are PlaceLotOnHold/ApplyMaterialHold and isolation/maintenance names equivalent commands or distinct scope-specific operations?01 Items15/34/66/83 do not establish identical payload/scope/idempotency bindings. | Freeze one logical identity only where exact equivalence is proven; update aliases and approval bindings. | Retain distinct identities with explicit adapters and independent bindings; greater contract/test scope. |01,02,03,04,05,06A,06C,07; blocks affected Automation integration. ActivateSchedule/ActivateScheduleCommand is already settled by02 R-003; DispatchLot/ReleaseLot remain distinct. |
| ARCHITECTURE_ANCHOR_ALLOCATION — CHG-010, GAP-RTM-001/002/003, RTF-025/026 | Which exact stable ARCH allocations cover predictive ML/MLOps, experiment/evidence execution, scheduler evaluation and Vision data pipelines? Existing service ownership does not define these registry identities/responsibility boundaries. | Approve append-only component IDs within existing services; explicit trace allocations. | Demonstrate complete allocation to existing IDs; no new IDs, but responsibility evidence required. |02,03,04,05,06A–D,07; blocks affected architecture/trace freeze. Neither option introduces infrastructure. |
| DEPENDENCY_CONSUMER_SEMANTICS — CHG-005 | What valid readiness/fallback/deadline/precise-consumer bindings satisfy the affected gates?05 DEP-060/194 demand INTEGRATION_READY outside DN-VIS-MODELS ladder; DEP-025/045/058/076/094 declare non-CONTRACT F1;29 deadlines are ambiguous and179 HARD precision fields are null. Rules prohibit invalid satisfaction but do not uniquely choose replacements. | Ratify bindings expressible by existing ladders and rules, with exact consumed fields/deadlines; keep topology. | Approve revised semantics through C3 if existing ladders cannot express the gate; otherwise retain unknowns and defer affected readiness. |05 table/YAML mirrors,03,04,06A–D,07; blocks affected readiness/milestone decisions. F1 cannot satisfy non-CONTRACT/milestone/freeze gates under either option. |
| MC2_OWNER — CHG-007, GAP-RTM-020, RTF-027 | Who is accountable for MC-2 research claims?01 Item58 omits a primary owner; scenario/WP ownership is not research accountability. | Name one accountable contribution owner with independent reviewers; fixed accountability. | Define explicit coordination/acceptance roles with accountable owner bound per run; additional reproducibility binding. |01 research responsibilities,03 ViewH,07; blocks MC-2 protocol freeze/claim acceptance, not unrelated WPs. |
| HARDWARE_PROFILE_PINNING — CHG-008, GAP-RTM-021, RTF-028 | Which actual CPU, final Vision and developer profiles are accepted measurement contexts? Existing numerical resource limits and current host facts do not select final benchmark profiles. | Approve verified, versioned hardware/resource/workload profiles; permits identity-bound measurement. | Defer measurement freeze until profiles are verified and accepted; no benchmark PASS claims. |01,02,03,07,08; blocks affected measurement/freeze, not unrelated code.16GiB/p95≤12GiB/30min/peak≤14GiB/noOOM obligations stay fixed. |
| E2E_COORDINATOR — CHG-009, DEP-GAP-13, PLAN-GAP-04, RTF-029 | Who coordinates formal GS-01/E2E runs?01 Item67 names scenario/evidence responsibilities but no unique run coordinator. | Name a fixed coordinator; consistent scheduling accountability. | Approve rotating coordination bound in each run manifest; auditable per-run allocation required. |01 Item67,05,07; blocks formal run coordination, not scenario/evidence authority or unrelated implementation. |
| REAL_PUBLIC_PORTFOLIO_SELECTION — CHG-002, RTF-022 | Which exact source versions, rights, partitions and bounded claims enter the final real/public portfolio?01 Item55 approves candidate directions, not specific acquired/accepted DatasetVersions. | Approve exact source records/cards, rights and leakage-aware splits; enables source-bound evaluation. | Defer affected claims until a smaller approved portfolio is available; reduced claim scope, no synthetic substitute. |01 Item55,03,04,06A–D,07; blocks affected acquisition/evaluation/claim acceptance. Semiconductor identity corrections and LaneA/B/C boundaries are already settled. |

## Existing obligations removed from the semantic ballot

- Missing revision/status and structured NFR fields remain unknown under01 Items81/82 and03's source-gap annotation. No decision to invent values is needed. Owners still must supply/confirm authoritative metadata and validate projected traces under Item83 before their applicable gates. Line-only references without an identity-proven target remain target-identification work; no guessed citation repair is accepted. These gaps are not declared resolved.
- Independent change review/ratification is already mandatory under09 §§7/8 and Item63. It is an existing human workflow gate, not a choice between doing review and bypassing it. CHG-001…016 remain UNDER_REVIEW; genuine reviewer evidence, integration and post-merge verification remain outstanding.
- Product-name/domain propagation, physical dataset identities, schedule-activation authority and mandatory provenance are settled. Reopening these policies is unnecessary. Historical failures and source-bound evidence remain preserved.


# Final authoritative decisions — 2026-10-13

All eight groups are DECIDED by the explicit final user request (SHA-256 96ff255d4431a99a65ced71aa45136937acd7ae5917eaaca7fba764c23901da7). This authorizes this scoped reconciliation branch, not invented peer review, merge, product implementation, runtime readiness or source acquisition acceptance. Historical undecided packet above is retained for provenance and is no longer the active policy.

## INSPECTION_CONTRACT_CANONICALIZATION — DECIDED

Decision: Distinct immutable Vision InspectionObservation (existing EVT identity) and normalized Core InspectionResult (IC-VIS-002).

Rationale: Perception evidence is not canonical manufacturing acceptance.

Affected documents: 01/02/03/04/05/06B/07/10; CHG-003.

Implementation consequence: Separate schemas and provenance-preserving normalization; never alias observation and result.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

## PROTECTED_COMMAND_NAMING — DECIDED

Decision: PlaceLotOnHold / existing CMD-PlaceLotOnHold-v1; one canonical identity per action using01 action table.

Rationale: Stable command identity precedes lower-precedence aliases; hold is not lifecycle.

Affected documents: 01/02/03/04/05/06A/06C/07/10; CHG-004.

Implementation consequence: Freeze exact target/payload/version/approval/idempotency binding in contract WPs; deprecated names are not additional commands.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

## ARCHITECTURE_ANCHOR_ALLOCATION — DECIDED

Decision: Core canonical; Simulator/Oracle isolated; Twin/Qdrant projections; Vision observations; AI propose; Scheduler candidates; HITL approval; Automation coordination; Keycloak identity; UI no DB/broker writes.

Rationale: One authoritative manufacturing state owner; missing component traces allocated within existing services, no infrastructure expansion.

Affected documents: 01/02/03/04/05/06A-D/07/10; CHG-010.

Implementation consequence: Append-only ML/MLOps, experiment/evidence, scheduler-evaluation and Vision-data component IDs in02; do not mint competing services/authorities.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

## DEPENDENCY_CONSUMER_SEMANTICS — DECIDED

Decision: HARD blocks declared work/readiness stage; SOFT does not. Models declare operational-serving INTEGRATION_READY; five non-CONTRACT F1 fallbacks removed.

Rationale: Readiness is consumer-facing and typed; training/artifact existence or development fixtures do not prove integration.

Affected documents: 01/03/04/05/06A-D/07/08/10; CHG-005.

Implementation consequence: Use explicit consumer/need-by interpretation. Unknown exact fields stay null until actual task DoR; no fabricated satisfaction.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

## MC2_OWNER — DECIDED

Decision: Asrın Dündar accountable for MC-2.

Rationale: Cross-cutting project/integration research accountability; no underlying WP reassignment.

Affected documents: 01/03/05/07/10; CHG-007.

Implementation consequence: Bind contribution accountability, retain canonical implementation owners73/17/32/57.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

## HARDWARE_PROFILE_PINNING — DECIDED

Decision: Primary shared host: i7-9700K8c/8t, approximately30GiB usable RAM, RTX2060SUPER8GB, Ubuntu26.04.1LTS, primaryext4; secondaryNVMe not mandatory.

Rationale: Known approved shared-host measurement context without invented measurements or extra mandatory hosts.

Affected documents: 01/02/03/07/08/10; CHG-008.

Implementation consequence: Bind actual release/environment/resource/workload configuration to every measurement; no performance claim from pinning.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

## E2E_COORDINATOR — DECIDED

Decision: Durable Automation/Temporal workflow ARCH-AUTO-WORKFLOW coordinates GS-01/E2E.

Rationale: Coordinates approved execution; Core retains canonical authority and effect must be verified.

Affected documents: 01/02/03/04/05/07/10; CHG-009.

Implementation consequence: Verify exact binding, approval, freshness/expiry/policy; prevent self-approval; Core commands and canonical effect readback.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

## REAL_PUBLIC_PORTFOLIO_SELECTION — DECIDED

Decision: LaneA NASA/Leibniz-Mendeley/CNC sources, auxiliaryMVTecAD/AD2, applicableGDXray; LaneB literature; LaneC controlledSimulator; public scheduling benchmark support.

Rationale: No single source covers all modalities; no semiconductor-to-aerospace relabeling or synthetic substitute for real/public held-out claims.

Affected documents: 01/03/04/06A-D/07/10; CHG-002.

Implementation consequence: Source cards need role/modality/provenance/rights/evaluation/limits; exact unverified metadata NEEDS_SOURCE_VERIFICATION. SECOM/WM/Mixed legacy-methodological only.

Future modification: required09 change control at the existing C2/C3 and CR-3/CR-4 impact where applicable; no silent change. Independent qualified review and integration remain pending for this PR.

Unresolved human-choice placeholders in these eight groups: NONE. Actual artifact production, owner trace review, schema freeze, source verification, acquisition/rights checks and measurement execution remain normal implementation/review gate obligations, not renewed semantic-choice placeholders.


## Review governance supersession —14 October2026

The owner has replaced blanket review quorums with the01/09 actual-risk policy. Historical pending-review statements above describe the previous policy. Normal risk requires one independent approval; actual high risk requires two. Ejlonn approved the previous PR#4 head; the owner separately authorizes this bounded policy migration and closure without requesting another review. No new-head approval is fabricated, no product HITL rule changes, and no Plane/product execution is authorized. Final-head CI, tests, invariants and post-merge validation are still required.
