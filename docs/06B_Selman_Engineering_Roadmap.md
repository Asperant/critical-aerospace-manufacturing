# 06B — Selman Engineering Roadmap
## Visual Perception & Inspection Intelligence Owner

| Field | Value |
|---|---|
| Document | `06B_Selman_Engineering_Roadmap.md` |
| Status | **Draft — Derived from Approved 01/02 Baseline** (requires the owner's own review) |
| Version | v0.1.0-draft |
| Generated | 17 Eylül 2026 (pre-implementation) |
| Canonical role (01 Item 62) | Visual Perception & Inspection Intelligence Owner |
| Owned work packages | 17 of 179 (2 F0 · 13 F1-class · 2 R1 · 0 R2/S) |
| Owned requirements | 19 (17 FR · 2 NFR) |
| Owned dependency nodes (05) | 11 |
| Upstream cross-owner HARD gates | 5 |
| Downstream cross-owner consumers | 6 HARD edges |
| Status of all work today | `NOT_STARTED` — no implementation, no evidence, no measurement exists |
| Upstream artifacts | 01 (Items 62, 65–69, 79, 81–85), 02, 03 RTM, 04 WBS, 05 Dependency Graph |

> **Scale note.** This roadmap is an *execution projection* of ownership, not a copy of 03/04/05. Per 00 §9 it references requirement, work-package and dependency identities instead of restating their text, so it is shorter than a self-contained document of the same coverage would be.

---

## Table of Contents

1. Role Mission
2. Removal-Test Statement
3. Owned Architecture Surfaces
4. Owned FR/NFR Families
5. Critical Contracts
6. Upstream Dependencies
7. Downstream Consumers
8. Milestone-by-Milestone Engineering Objectives
9. Work Package Mapping
10. Sprint-Level Execution Projection and Interface Ledger
11. Integration Checkpoints
12. Failure and Negative Tests
13. Research / Evaluation Responsibilities
14. Documentation and ADR Obligations
15. Risks and Bottlenecks
16. Cross-Review Responsibilities
17. Final Benchmark Contribution
18. Demo Contribution
19. Thesis / Portfolio Evidence (incl. Requirement Execution Dossier)
20. Definition of Final Role Completion

---

## 1. Role Mission

Own everything that turns raw inspection artifacts into trustworthy perception facts: the artifact pipeline, the models (classification, localization, segmentation, anomaly), the honesty mechanisms (OOD/UNKNOWN, confidence, calibration, provenance), the serialized component-level spatial intelligence that makes a defect operationally meaningful, and the dataset/MLOps governance that makes any of it defensible. Perception is where the closed loop starts; if the observation is wrong or unqualified, every downstream decision inherits the error.

## 2. Removal-Test Statement

Remove Selman and the loop loses its senses. The system could still simulate, schedule and execute, but nothing would *perceive*: the closed loop would be triggered by injected flags rather than by inference over real artifacts, which is exactly the shortcut the architecture forbids (Item 67 #101). RQ-4 disappears entirely, RQ-1 loses its perception-derived evidence class, and the product's claim to visual inspection intelligence collapses into a defect-label generator. This role is also the only one that can say what a defect observation *means* — no other role may rewrite a visual ground truth (Item 62 #120).

**Removal test in numbers.** Removing this role removes 2 F0 work packages (WP-VIS-001, WP-VIS-007), 19 owned requirements and 11 owned dependency nodes, including 6 nodes that other owners depend on through 6 HARD edges.

### 2.1 Boundaries this role may not cross

Ownership is bounded in both directions: these rules protect other roles from this one, and are enforced by tests rather than by convention.

| Boundary | Source | How it is enforced in the plan |
|---|---|---|
| Vision does not own root cause | Item 62 #55 | Vision publishes perception facts with confidence; cross-system interpretation belongs to Asrın's RCA. |
| Vision cannot directly hold a lot | Item 62 #56 | A defect observation never becomes a manufacturing command; holds go through Core under authority policy. |
| Vision cannot rewrite scheduling state | Item 62 #57 | Perception feeds decisions; it does not plan. |
| Vision cannot become a hidden AI fallback | Item 62 #58 | Vision must not be used to emulate RCA when the AI path is weak — the evidence classes stay distinct. |
| Vision cannot read Oracle labels at runtime | Item 67 #95 | Input allowlist and taint rejection (WP-VIS-009). |

## 3. Owned Architecture Surfaces

Architecture components (02 registry) reached through this role's work packages, and the 05 readiness nodes that carry them.

| Readiness node (05) | Surface | Type | 02 ARCH anchor | Final readiness required |
|---|---|---|---|---|
| DN-FRZ-RQ4SPLIT | Vision split freeze (RQ-4) | FREEZE | ARCH-DATA-LINEAGE | FROZEN |
| DN-VIS-ARTCON | Inspection artifact identity contract (ArtifactRef, Lot/SerializedComponent refs, model metadata) | CONTRACT | ARCH-VIS-ARTIFACT, ARCH-CTR-API | FROZEN |
| DN-VIS-BASELINES | Vision baselines | CAPABILITY | ARCH-VIS-EVAL | FROZEN |
| DN-VIS-EPISODES | Operational inspection episodes (ScenarioEpisodes with genealogy/state) | DATA | ARCH-DATA-LINEAGE | FROZEN |
| DN-VIS-MODELS | Deep Vision models (classification/localization/segmentation/anomaly) as ModelPackages | ARTIFACT | ARCH-VIS-MODEL, ARCH-VIS-INFER | FROZEN |
| DN-VIS-OBSCON | InspectionObservation contract + fixtures (name: GAP-RTM-009) | CONTRACT | ARCH-CTR-EVTSCHEMA | FROZEN |
| DN-VIS-OOD | OOD/UNKNOWN + spatial pattern evaluation | CAPABILITY | ARCH-VIS-OOD, ARCH-VIS-EVAL | FROZEN |
| DN-VIS-PUBLIC | Public Vision dataset (rights/version) | DATA | ARCH-DATA-LINEAGE | FROZEN |
| DN-VIS-SERVING | Operational Vision inference over real artifacts | CAPABILITY | ARCH-VIS-INFER, ARCH-VIS-ARTIFACT | FROZEN |
| DN-VIS-SPLIT | Vision DatasetVersion / SplitManifest | ARTIFACT | ARCH-DATA-LINEAGE | FROZEN |
| DN-VIS-SYNTH | Synthetic Vision generator (owned data) | DATA | ARCH-DATA-LINEAGE | FROZEN |

**ARCH components touched:** `ARCH-AI-ORCH`, `ARCH-CTR-EVTSCHEMA`, `ARCH-DATA-LINEAGE`, `ARCH-DATA-OBJ`, `ARCH-EDGE-WEB`, `ARCH-PLAT-CLI`, `ARCH-VIS-ARTIFACT`, `ARCH-VIS-EVAL`, `ARCH-VIS-INFER`, `ARCH-VIS-MODEL`, `ARCH-VIS-OOD`, `ARCH-WORLD-EVALZONE`.

## 4. Owned FR/NFR Families

Ownership here means PrimaryOwner in the 01 catalogue: this role is accountable for the requirement's correctness, its trace mapping (03) and its final disposition.

### 4.FUI FR-UI (1)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-UI-003 | F1 | WP-UI-003 | TEST-UI-VISION, AV-SCEN-01, DEMO-GS01-001 |

### 4.FVIS FR-VIS (16)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-VIS-001 | F0 | WP-OBJ-001, WP-VIS-001 | TEST-VIS-PIPELINE, E2E-01, AV-SCEN-01, BENCH-E2E-001 |
| FR-VIS-002 | F1 | WP-VIS-002, WP-VDATA-005, WP-RES-006 | TEST-VIS-PIPELINE, BENCH-VIS-001 |
| FR-VIS-003 | F1 | WP-VIS-002 | TEST-VIS-PIPELINE, BENCH-VIS-001 |
| FR-VIS-004 | F1 | WP-VIS-003 | TEST-VIS-PIPELINE, BENCH-VIS-001 |
| FR-VIS-005 | F1 | WP-VIS-003 | TEST-VIS-OOD, BENCH-VIS-001 |
| FR-VIS-006 | F1 | WP-VIS-004, WP-VDATA-005, WP-RES-010 | TEST-VIS-OOD, BENCH-VIS-001, BENCH-RQ4-001 |
| FR-VIS-007 | F1 | WP-VIS-005 | TEST-VIS-PROVENANCE, INSP-VIS-DATASET |
| FR-VIS-008 | F1 | WP-VIS-005 | TEST-VIS-PROVENANCE, BENCH-VIS-001 |
| FR-VIS-009 | F1 | WP-VIS-001 | TEST-VIS-PIPELINE, TEST-EVT-SCHEMA, AV-SCEN-01, E2E-01 |
| FR-VIS-010 | F1 | WP-VIS-006, WP-VDATA-005, WP-RES-010 | TEST-VIS-PIPELINE, BENCH-VIS-001, BENCH-RQ4-001 |
| FR-VIS-011 | F1 | WP-VDATA-001, WP-VDATA-003 | INSP-VIS-DATASET, BENCH-VIS-001 |
| FR-VIS-012 | F1 | WP-VDATA-002 | INSP-VIS-DATASET, TEST-DATA-SPLITLEAK, BENCH-VIS-001 |
| FR-VIS-013 | F1 | WP-VIS-009 | TEST-VIS-ORACLE-NEG, AV-SCEN-11, BENCH-VIS-001 |
| FR-VIS-014 | F1 | WP-VIS-008 | TEST-VIS-CPUSMOKE, TEST-RES-CPUONLY |
| FR-VIS-015 | F1 | WP-VDATA-004 | TEST-VIS-PROVENANCE, TEST-DATA-CHECKSUM |
| FR-VIS-016 | F0 | WP-VIS-007, WP-TEST-006, WP-RES-010, WP-BENCH-002 | E2E-01, AV-SCEN-01, DEMO-GS01-001, BENCH-E2E-001 |

### 4.NPERF NFR-PERF (2)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-PERF-009 | A1 | CPU smoke path time per image on accepted small sample | ≤ 15 s/image | WP-VIS-008 |
| NFR-PERF-010 | C3 | cold-start and warm inference latency per CPU/GPU profile | C3 — characterize; no threshold | WP-VIS-010 |

## 5. Critical Contracts

| Node | Contract surface | Readiness deadline | Consumers (owner, edge) |
|---|---|---|---|
| DN-VIS-ARTCON | Inspection artifact identity contract (ArtifactRef, Lot/SerializedComponent refs, model metadata) | CONTRACT_READY by E2E-01 readiness (end S4) | DN-VIS-SERVING (Selman, DEP-057); DN-VIS-OBSCON (Selman, DEP-061) |
| DN-VIS-OBSCON | InspectionObservation contract + fixtures (name: GAP-RTM-009) | CONTRACT_READY by E2E-01 readiness (end S4) | DN-AI-RCA (Asrın, DEP-065) |

Contract obligations follow 05 DEP-RULE-04: a fixture satisfies development-stage consumption only; milestone and final evidence require the real capability behind the contract.

### 5.1 Contracts this role consumes

| DEP | Contract node (owner) | Consumed by | Required readiness | Need-by | Precise requirement declared (05 DEP-RULE-06) |
|---|---|---|---|---|---|
| DEP-056 | DN-CORE-CONTRACTS (Asrın) | DN-VIS-ARTCON | CONTRACT_READY | S3 | Lot/SerializedComponent references |

### 5.2 Verification assets owned by this role

Planned verification families whose semantic correctness belongs to this role (03 §9.X). Asset identities are planning-level; numeric TestIDs are allocated when the assets are created.

| Family | Kind | Scope | Lane / tier | Min environment | Work packages relying on it |
|---|---|---|---|---|---|
| TEST-VIS-PIPELINE | TEST | Versioned ArtifactRef → preprocessing → inference → InspectionObservation publication | ENG-A | CI | WP-OBJ-001, WP-RES-006, WP-RES-010, WP-VDATA-005, WP-VIS-001, WP-VIS-002 |
| TEST-VIS-OOD | TEST | UNKNOWN/OOD outcome emission + anomaly path independent of closed-set classifier | ENG-A | CI | WP-RES-010, WP-VDATA-005, WP-VIS-003, WP-VIS-004 |
| TEST-VIS-PROVENANCE | TEST | Model/preprocessing identity + confidence fields on every output; ModelPackage immutability | ENG-B | CI | WP-VDATA-004, WP-VIS-005 |
| TEST-VIS-CPUSMOKE | TEST | CPU-only smoke inference path on documented small sample | ENG-A | CI | WP-VIS-008 |
| TEST-VIS-ORACLE-NEG | TEST | Oracle/evaluator label exclusion from Vision runtime inputs (negative) | ENG-C | CI | WP-VIS-009 |
| INSP-VIS-DATASET | INSP | DatasetVersion/SplitManifest immutability, synthetic vs public provenance, rights status | ENG-B | EVALUATION | WP-VDATA-001, WP-VDATA-002, WP-VDATA-003, WP-VIS-005 |
| BENCH-VIS-001 | BENCH | Final Vision evaluation lane: classification, localization, segmentation, anomaly, OOD, spatial pattern (no single accuracy) | VISION | EVALUATION | WP-RES-006, WP-RES-010, WP-VDATA-001, WP-VDATA-002, WP-VDATA-003, WP-VDATA-005 |
| BENCH-RQ4-001 | BENCH | RQ-4 perception-to-operations context evaluation (120 episodes) | RQ4 | EVALUATION | WP-RES-010, WP-VDATA-005, WP-VIS-004, WP-VIS-006 |
| TEST-UI-VISION | TEST | Inspection viewer: artifacts, localization/segmentation overlays | ENG-A | INTEGRATION | WP-UI-003 |
| BENCH-PERF-VIS | BENCH | Vision CPU smoke latency and cold/warm CPU/GPU inference characterization | PERF | EVALUATION | WP-VIS-008, WP-VIS-010 |

## 6. Upstream Dependencies

What this role must receive from others before it can pass a stage. Fixture-satisfiable rows are marked; the rest require the real upstream capability.

| DEP | Predecessor (owner) | Feeds node | Kind | Strength | Stage | Required readiness | Need-by | Fallback | Unblock evidence |
|---|---|---|---|---|---|---|---|---|---|
| DEP-056 | DN-CORE-CONTRACTS (Asrın) | DN-VIS-ARTCON | CONTRACT | HARD | START | CONTRACT_READY | S3 | F1 | contract merged + contract tests green + example fixture published |
| DEP-058 | DN-RT-OBJ (Yavuz) | DN-VIS-SERVING | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | F1 | artifact read via ArtifactRef on SeaweedFS |
| DEP-055 | DN-RT-MLFLOW (Yavuz) | DN-VIS-MODELS | RUNTIME | HARD | MILESTONE_EXIT | INTEGRATION_READY | M4/M5 | — | ModelPackage promotion recorded in MLflow + artifact store |
| DEP-062 | DN-SIM-COREINT (Batu) | DN-VIS-EPISODES | DATA | HARD | MILESTONE_EXIT | INTEGRATION_READY | M5 | F4 | ScenarioEpisodes with genealogy/state generated |
| DEP-063 | DN-CORE-GENEALOGY (Asrın) | DN-VIS-EPISODES | DATA | HARD | MILESTONE_EXIT | INTEGRATION_READY | M5 | — | genealogy linked to episodes |

## 7. Downstream Consumers

What others cannot do until this role delivers. Every row is a commitment with a need-by point.

| DEP | Delivered node | Consumer (owner) | Kind | Strength | Stage | Required readiness | Need-by | Unblock evidence |
|---|---|---|---|---|---|---|---|---|
| DEP-065 | DN-VIS-OBSCON | DN-AI-RCA (Asrın) | CONTRACT | HARD | START | CONTRACT_READY | E2E-01 readiness (end S4) | contract merged + contract tests green + example fixture published (stable fixtures) |
| DEP-068 | DN-VIS-SERVING | DN-AI-RCA (Asrın) | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M3 (S6) | real Vision observation consumed as RCA evidence |
| DEP-122 | DN-VIS-SPLIT | DN-RES-DATASCEN (Asrın) | DATA | HARD | MILESTONE_EXIT | EVALUATION_READY | M5 (S10) | Vision splits evaluation-ready |
| DEP-131 | DN-FRZ-RQ4SPLIT | DN-FRZ-DATA (Batu) | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | Vision split frozen before final RQ-4 training/evaluation |
| DEP-150 | DN-VIS-OOD | DN-FRZ-MODEL (Asrın) | CAPABILITY | HARD | FREEZE | EVALUATION_READY | M6 | OOD/spatial evaluation complete before model freeze |
| DEP-151 | DN-VIS-EPISODES | DN-FRZ-PROTOCOL (Asrın) | DATA | HARD | FREEZE | EVALUATION_READY | M6 | operational episodes available for RQ-4 perception-to-operations |

**Delivery load by consumer:** Asrın: 5 HARD edges, Batu: 1 HARD edges.

## 8. Milestone-by-Milestone Engineering Objectives

### 8.M0 M0 — Engineering Foundation Ready (End S1 / Week 2)

Selman's M0 is preparation with real consequences: dataset candidate survey with licence status, local training/inference environment through the Compose profiles, and the first sketch of the artifact identity and observation contracts. Vision work is the most parallelizable in the programme (Item 66 #55) — the only real M0 obligation is not to become blocked on backend readiness.

_No work package of this role targets M0; the role contributes through review, support and preparation in this window._


### 8.M1 M1 — Integrated Spine (End S2 / Week 4)

During M1 Vision runs entirely on its own data and local artifacts: first baselines on a chosen dataset, the synthetic generator taking shape, and the inspection artifact contract drafted with Asrın so that the backend can reference artifacts by identity rather than by file path.

_No work package of this role targets M1; the role contributes through review, support and preparation in this window._


### 8.M2 M2 — Operational Manufacturing Alpha (End S4 / Week 8)

M2 is the first integration obligation: structured visual evidence must exist in the operational world. The inspection pipeline consumes a request, reads an artifact by reference from SeaweedFS, runs an inference path (which may still be a simple algorithm) and publishes an observation with provenance. The observation contract must be CONTRACT_READY with fixtures by end S4 because Asrın's RCA work depends on it (Item 67 readiness table).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-VIS-001 | Inspection pipeline and serving path | F0 | 3 | M |
| WP-VIS-008 | CPU smoke inference path | F1 | 3 | S |

**Owned requirements reaching their target in this window (4):** FR-VIS-001, FR-VIS-009, FR-VIS-014, NFR-PERF-009

**Upstream gates that must close in this window (1):** DEP-056 from Asrın

**Commitments owed to others in this window (1):** DEP-065 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M3 M3 — Closed-Loop Alpha (End S6 / Week 12)

At M3 perception actually drives the loop. The E2E-01 checkpoint requires a real inspection artifact, a computed observation and no injected labels or scenario-ID branching. Selman reviews the Vision contract/artifact path before the formal run (Item 67 #215). Model quality is explicitly not the M3 bar; honest computation on real infrastructure is.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-VIS-007 | Vision-to-loop integration (perception drives RCA) | F0 | 3 | S |
| WP-VIS-009 | Oracle-taint guard for Vision inputs | F1 | 2 | S |

**Owned requirements reaching their target in this window (2):** FR-VIS-013, FR-VIS-016

**Upstream gates that must close in this window (1):** DEP-058 from Yavuz

**Commitments owed to others in this window (1):** DEP-068 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M4 M4 — Mandatory Core Feature Complete (End S8 / Week 16)

M4 is the mandatory capability window: classification, localization, segmentation and anomaly detection served from promoted ModelPackages, OOD/UNKNOWN with a versioned threshold policy, serialized component spatial pattern and cluster analysis, the inspection viewer with overlays, and the CPU smoke path for GPU-less machines. Dataset versions and split manifests must exist with rights status recorded.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-VIS-002 | Defect classification and localization models | F1 | 3 | M |
| WP-VIS-003 | Segmentation and anomaly detection | F1 | 3 | M |
| WP-VIS-004 | OOD / UNKNOWN handling and threshold policy | F1 | 3 | M |
| WP-VIS-005 | Provenance, confidence and calibration in Vision outputs | F1 | 3 | S |
| WP-VIS-006 | SerializedComponent spatial pattern and cluster analysis | F1 | 3 | S |
| WP-VDATA-001 | Dataset governance, rights and provenance | F1 | 3 | S |
| WP-VDATA-003 | Synthetic Vision data generator | F1 | 3 | S |
| WP-UI-003 | Inspection viewer with overlays | F1 | 3 | S |

**Owned requirements reaching their target in this window (10):** FR-UI-003, FR-VIS-002, FR-VIS-003, FR-VIS-004, FR-VIS-005, FR-VIS-006, FR-VIS-007, FR-VIS-008, FR-VIS-010, FR-VIS-011

**Upstream gates that must close in this window (1):** DEP-055 from Yavuz

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M5 M5 — Reliability & Evaluation Ready (End S10 / Week 20)

M5 makes the Vision story evaluable: the evaluation portfolio across all task families, baselines recorded before calibration, splits frozen with leakage checks, and the operational episode dataset assembled with genealogy and operational context for RQ-4. Calibration happens on the CAL partition only.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-VDATA-002 | Split manifests and leakage protection | F1 | 3 | M |
| WP-VDATA-004 | ModelPackage governance and MLflow promotion | F1 | 3 | M |

**Owned requirements reaching their target in this window (2):** FR-VIS-012, FR-VIS-015

**Upstream gates that must close in this window (2):** DEP-062 from Batu, DEP-063 from Asrın

**Commitments owed to others in this window (1):** DEP-122 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M6 M6 — Research Freeze (End S11 / Week 22)

M6 freezes Vision: DatasetVersion, SplitManifest, ModelPackages and ThresholdPolicyVersion. The Vision split freeze is a hard precondition for final RQ-4 training and evaluation (Item 66 #88); after it, a retrained model is a change-controlled event, not an improvement.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-VDATA-005 | Vision evaluation portfolio and RQ-4 lane preparation | R1 | 3 | M |
| WP-RES-010 | RQ-4 lane: perception-to-operations evaluation | R1 | 3 | M |

**Owned requirements reaching their target in this window (4):** FR-VIS-002, FR-VIS-006, FR-VIS-010, FR-VIS-016

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (3):** DEP-131 → Batu, DEP-150 → Asrın, DEP-151 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M7 M7 — Final Benchmark Complete (End S12 / Week 24)

During the campaign Selman executes the Vision evaluation lane and the RQ-4 perception-to-operations lane (120 episodes, 5 seeds, bootstrap resampling), and supplies perception evidence to MC-1 runs. Results are recorded per task family — no single headline accuracy number is produced (Item 68 / Item 30 discipline).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-VIS-010 | Vision inference performance characterization | F1/C3 | 2 | S |

**Owned requirements reaching their target in this window (1):** NFR-PERF-010

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M8 M8 — Final Release Candidate (End S13 / Week 26)

M8 closes the perception story: RQ-4 claim classification from sealed evidence, thesis material on the perception-to-operations coupling, portfolio artifacts (evaluation portfolio, OOD behaviour, spatial analysis), and confirmation that every Selman-owned requirement has a disposition.

_No work package of this role targets M8; the role contributes through review, support and preparation in this window._


## 9. Work Package Mapping

Each package below is owned by this role. Deliverables and tasks are the 04 definitions; the execution context (gates, consumers, verification, evidence) is projected here so the package can be picked up without cross-reading four documents.

### 9.WP-VIS-001 — Inspection pipeline and serving path

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M2 · S3–S4 |
| Readiness node | DN-VIS-SERVING |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-001, FR-VIS-009 |
| Architecture | ARCH-CTR-EVTSCHEMA, ARCH-DATA-OBJ, ARCH-VIS-ARTIFACT, ARCH-VIS-INFER |
| Gating edges | DEP-057 (DN-VIS-ARTCON, E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, E2E-01, TEST-EVT-SCHEMA, TEST-VIS-PIPELINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- vision-service inference worker
- InspectionRequest consumption + observation publication
- artifact-driven preprocessing path

**Major tasks.**
- implement request consumer and artifact fetch by reference
- implement preprocessing with versioned identity
- publish observation contract (naming per 05 DEP-GAP-07)
- integration test with real object storage and broker

**Cut/fallback.** No cut (F0). First algorithm may be simple (F2) for E2E-01; final modes arrive at M4.


### 9.WP-VIS-008 — CPU smoke inference path

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-VIS-SERVING |
| Supporting reviewer | Yavuz |
| Source requirements | FR-VIS-014, NFR-PERF-009, NFR-RES-007 |
| Architecture | ARCH-PLAT-CLI, ARCH-VIS-INFER |
| Gating edges | DEP-057 (DN-VIS-ARTCON, E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | BENCH-PERF-VIS, TEST-RES-CPUONLY, TEST-VIS-CPUSMOKE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- CPU smoke model package (distinct from promoted final models)
- `mfgctl smoke vision` path
- documented CPU baseline timing

**Major tasks.**
- select lightweight smoke model and sample set
- implement CPU-only execution path
- record smoke timing against the documented CPU baseline (05 DEP-GAP-11)

**Cut/fallback.** No cut; developer experience and NFR-RES-007 depend on it.


### 9.WP-VIS-007 — Vision-to-loop integration (perception drives RCA)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-VIS-SERVING |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-016 |
| Architecture | ARCH-AI-ORCH, ARCH-VIS-INFER |
| Gating edges | DEP-057 (DN-VIS-ARTCON, E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, E2E-01 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- integration wiring Vision → AI evidence intake
- scenario-independent triggering logic
- integration tests (AV-SCEN-01)

**Major tasks.**
- ensure observation is consumed as RCA evidence with provenance
- prohibit scenario-ID or boolean-label shortcuts (Item 67 #101/#104)
- verify with real Vision output in INTEGRATION

**Cut/fallback.** No cut (F0). Fixtures are allowed before E2E-01 but never for M3 evidence.

**Integration checkpoint.** E2E-01, AV-SCEN-01, DEMO-GS01-001


### 9.WP-VIS-009 — Oracle-taint guard for Vision inputs

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-VIS-SERVING |
| Supporting reviewer | Batu |
| Source requirements | FR-VIS-013 |
| Architecture | ARCH-VIS-INFER, ARCH-WORLD-EVALZONE |
| Gating edges | DEP-057 (DN-VIS-ARTCON, E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | AV-SCEN-11, BENCH-VIS-001, TEST-VIS-ORACLE-NEG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- input allowlist enforcement
- taint rejection tests

**Major tasks.**
- define allowed input fields
- implement rejection of oracle-derived fields
- negative tests in CI and INTEGRATION

**Cut/fallback.** No cut (research-validity hard gate).


### 9.WP-UI-003 — Inspection viewer with overlays

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Asrın |
| Source requirements | FR-UI-003 |
| Architecture | ARCH-EDGE-WEB, ARCH-VIS-ARTIFACT |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-01, DEMO-GS01-001, TEST-UI-VISION |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- artifact viewer with scoped access
- overlay rendering for boxes/masks
- UNKNOWN/OOD presentation

**Major tasks.**
- implement scoped artifact access through BFF
- render overlays from observation payloads
- present confidence and provenance

**Cut/fallback.** No cut (F1).


### 9.WP-VDATA-001 — Dataset governance, rights and provenance

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-VIS-PUBLIC |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-011, NFR-DATA-006 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-VIS-MODEL |
| Gating edges | none — early unlocker |
| Verification families | BENCH-VIS-001, INSP-DATA-PROVENANCE, INSP-VIS-DATASET, TEST-DATA-REFINTEGRITY |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- DatasetVersion records with provenance class (SYNTHETIC/PUBLIC)
- rights/licence status register
- dataset card template

**Major tasks.**
- inventory candidate public datasets and their licences
- record provenance for owned synthetic data
- exclude ambiguous-rights data from any core dependency

**Cut/fallback.** Public data is SOFT for product operation (synthetic F4 fallback) and HARD only for a public-benchmark claim.


### 9.WP-VDATA-003 — Synthetic Vision data generator

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-VIS-SYNTH |
| Supporting reviewer | Batu |
| Source requirements | FR-VIS-011 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-VIS-MODEL |
| Gating edges | none — early unlocker |
| Verification families | BENCH-VIS-001, INSP-VIS-DATASET |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- synthetic generator with versioned parameters
- generated DatasetVersions
- generator documentation

**Major tasks.**
- define defect/appearance parameter space
- implement generation with seed control
- validate that generated data exercises the required Vision modes

**Cut/fallback.** F4 fallback role: may substitute public data for integration and product execution, never for public-benchmark claims.


### 9.WP-VIS-002 — Defect classification and localization models

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-VIS-MODELS |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-002, FR-VIS-003 |
| Architecture | ARCH-VIS-EVAL, ARCH-VIS-INFER |
| Gating edges | DEP-053 (DN-VIS-BASELINES, M4 (S8)), DEP-055 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-VIS-001, TEST-VIS-PIPELINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- classification model + ModelPackage
- localization model + ModelPackage
- per-task evaluation results on frozen splits

**Major tasks.**
- establish baselines before deep models
- train/evaluate on DatasetVersion with SplitManifest
- record per-class metrics (no single accuracy headline)
- package models with dataset/experiment lineage

**Cut/fallback.** No cut for F1 Vision modes; model family choice is an implementation decision, not a scope change.


### 9.WP-VIS-003 — Segmentation and anomaly detection

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-VIS-MODELS |
| Supporting reviewer | Yavuz |
| Source requirements | FR-VIS-004, FR-VIS-005 |
| Architecture | ARCH-VIS-EVAL, ARCH-VIS-INFER, ARCH-VIS-OOD |
| Gating edges | DEP-053 (DN-VIS-BASELINES, M4 (S8)), DEP-055 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-VIS-001, TEST-VIS-OOD, TEST-VIS-PIPELINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- segmentation model + mask artifact handling
- anomaly model + scoring
- evaluation results per task

**Major tasks.**
- define mask artifact storage and referencing
- train/evaluate segmentation
- implement anomaly path independent of closed-set classifier
- evaluate anomaly separability on held-out data

**Cut/fallback.** No cut for F1.


### 9.WP-VIS-004 — OOD / UNKNOWN handling and threshold policy

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-VIS-OOD |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-006 |
| Architecture | ARCH-VIS-OOD |
| Gating edges | DEP-054 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | BENCH-RQ4-001, BENCH-VIS-001, TEST-VIS-OOD |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- OOD detection component
- ThresholdPolicyVersion artifact
- UNKNOWN routing to human review path

**Major tasks.**
- select and implement OOD scoring
- calibrate thresholds on CAL partition only
- define versioned threshold policy
- wire UNKNOWN outcomes into UI/RCA semantics

**Cut/fallback.** No cut; OOD/UNKNOWN is explicitly F1 (Item 68 #55).


### 9.WP-VIS-005 — Provenance, confidence and calibration in Vision outputs

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-VIS-SERVING |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-007, FR-VIS-008 |
| Architecture | ARCH-VIS-INFER, ARCH-VIS-MODEL, ARCH-VIS-OOD |
| Gating edges | DEP-057 (DN-VIS-ARTCON, E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | BENCH-VIS-001, INSP-VIS-DATASET, TEST-VIS-PROVENANCE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- provenance fields on observation contract
- confidence/uncertainty fields + calibration artifact
- provenance tests

**Major tasks.**
- bind ModelVersion/PreprocessingVersion into outputs
- implement calibration procedure and artifact
- verify immutability of referenced ModelPackages

**Cut/fallback.** No cut; evidence-grounded RCA and RQ-4 depend on provenance.


### 9.WP-VIS-006 — SerializedComponent spatial pattern and cluster analysis

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-VIS-OOD |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-010 |
| Architecture | ARCH-VIS-EVAL, ARCH-VIS-INFER |
| Gating edges | DEP-054 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | BENCH-RQ4-001, BENCH-VIS-001, TEST-VIS-PIPELINE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- spatial pattern analysis component
- cluster/pattern contracts (IC-VIS-004/005)
- pattern evaluation cases

**Major tasks.**
- implement spatial aggregation and clustering
- define pattern taxonomy bound to scenario ground truth (evaluator side only)
- evaluate pattern detection quality

**Cut/fallback.** No cut for F1; advanced pattern families beyond the accepted set are stretch.


### 9.WP-VDATA-002 — Split manifests and leakage protection

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-VIS-SPLIT |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-012, NFR-DATA-002 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-OBJ |
| Gating edges | DEP-051 (DN-VIS-SYNTH, S2–S3) |
| Verification families | BENCH-VIS-001, INSP-EVAL-PARTITION, INSP-VIS-DATASET, TEST-DATA-SPLITLEAK |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- SplitManifest artifacts
- leakage detector (entity/group overlap)
- FINAL partition access guard

**Major tasks.**
- define split policy (entity/group level, not random row level)
- implement overlap detection across partitions
- implement access guard preventing training on FINAL
- seal manifests before M6

**Cut/fallback.** No cut (hard gate NFR-DATA-002).


### 9.WP-VDATA-004 — ModelPackage governance and MLflow promotion

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-RT-MLFLOW |
| Supporting reviewer | Yavuz |
| Source requirements | FR-VIS-015, FR-ML-005 |
| Architecture | ARCH-CTR-EVTSCHEMA, ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-VIS-MODEL |
| Gating edges | DEP-014 (DN-PLAT-INTEG, M4/M5) |
| Verification families | INSP-AI-BEHAVIOR, TEST-DATA-CHECKSUM, TEST-ML-CONTRACT, TEST-VIS-PROVENANCE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- ModelPackage manifest format
- MLflow tracking/registry wiring
- promotion procedure (candidate → promoted)

**Major tasks.**
- define manifest fields (bytes digest, dataset version, experiment run, metrics)
- wire training runs to MLflow
- implement promotion gate requiring evaluation evidence
- verify immutability of promoted packages

**Cut/fallback.** No cut for M4/M5 governance; architecture anchor pending (03 GAP-RTM-001).


### 9.WP-RES-010 — RQ-4 lane: perception-to-operations evaluation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-VIS-EPISODES |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-010, FR-VIS-016, FR-VIS-006 |
| Architecture | ARCH-AI-ORCH, ARCH-VIS-EVAL, ARCH-VIS-INFER, ARCH-VIS-OOD |
| Gating edges | DEP-062 (DN-SIM-COREINT, M5), DEP-063 (DN-CORE-GENEALOGY, M5) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, BENCH-RQ4-001, BENCH-VIS-001, DEMO-GS01-001, E2E-01, TEST-VIS-OOD, TEST-VIS-PIPELINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- operational episode dataset
- downstream impact metrics
- multi-seed execution protocol

**Major tasks.**
- generate episodes with genealogy and operational context
- define perception→operations impact metrics
- freeze splits before M6
- execute in FBC-01

**Cut/fallback.** R1.


### 9.WP-VDATA-005 — Vision evaluation portfolio and RQ-4 lane preparation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-VIS-OOD |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-002, FR-VIS-006, FR-VIS-010 |
| Architecture | ARCH-VIS-EVAL, ARCH-VIS-INFER, ARCH-VIS-OOD |
| Gating edges | DEP-054 (DN-VIS-MODELS, M4 (S8)) |
| Verification families | BENCH-RQ4-001, BENCH-VIS-001, TEST-VIS-OOD, TEST-VIS-PIPELINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- evaluation harness per task family
- baseline vs proposed comparison structure
- multi-seed evaluation protocol

**Major tasks.**
- implement metric calculators per task
- define seeds and bootstrap procedure
- produce DEV/CAL results before freeze
- prepare FINAL execution script for FBC-01

**Cut/fallback.** R1: evaluation must exist and run; positive outcomes are not required.


### 9.WP-VIS-010 — Vision inference performance characterization

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (C3) · M7 · S12 |
| Readiness node | DN-VIS-MODELS |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-PERF-010 |
| Architecture | ARCH-VIS-INFER |
| Gating edges | DEP-053 (DN-VIS-BASELINES, M4 (S8)), DEP-055 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-PERF-VIS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- measurement harness for inference latency
- recorded characterization per HardwareProfile

**Major tasks.**
- define measurement protocol (cold vs warm)
- record results bound to hardware profile
- publish as characterization, not as a threshold claim

**Cut/fallback.** C3: no threshold; absence of a target does not excuse absence of measurement.


### 9.SUP Supporting-reviewer packages (12)

Packages owned by others where this role is the named reviewer — review capacity must be planned, not improvised.

| Work package | Title | Owner | Milestone |
|---|---|---|---|
| WP-EVT-001 | Integration Contract Registry and versioning discipline | Asrın | M1 |
| WP-OBJ-001 | Artifact service: ArtifactRef contract and object storage integration | Yavuz | M2 |
| WP-ML-002 | M1 — equipment risk model | Asrın | M4 |
| WP-ML-004 | M3 — pre-inspection quality risk model | Asrın | M4 |
| WP-ML-006 | Calibration and uncertainty evaluation | Asrın | M5 |
| WP-UI-004 | Incident investigation workspace (RCA) | Asrın | M4 |
| WP-UI-008 | Epistemic, staleness and failure-state semantics | Asrın | M5 |
| WP-TEST-002 | Contract and schema test suites | Asrın | M2 |
| WP-RES-002 | Partition, seed and protocol governance | Asrın | M5 |
| WP-RES-012 | Research claim classification | Asrın | M8 |
| WP-DOC-003 | Thesis and portfolio artifact production | Asrın | M8 |
| WP-S-001 | Stretch enhancements register (visualization, mobile UI, multi-node, analytics, extra scenarios) | Asrın | — |

## 10. Sprint-Level Execution Projection

Sprint character follows Item 66 §"Sprint-Level Parallelization"; the packages are this role's. This is a projection for planning conversations, not a commitment schedule — 07 owns milestone planning.

| Sprint | Character (Item 66) | Work packages in flight | Upstream gates due | Commitments owed | Milestone |
|---|---|---|---|---|---|
| S1 | maximum independent foundational work | — | 0 | 0 | M0 |
| S2 | first Core/event/Twin/platform convergence | — | 0 | 0 | M1 |
| S3 | independent depth: Simulator, Vision, Scheduler, AI fixtures | WP-VIS-001, WP-VIS-008 | 1 | 0 | M2 |
| S4 | depth continues; E2E-01 contract readiness gate closes | WP-VIS-001, WP-VIS-008 | 0 | 1 | M2 |
| S5 | highest integration density; E2E-01 dry run and formal run | WP-VIS-007, WP-VIS-009 | 1 | 0 | M3 |
| S6 | highest integration density; M3 closed-loop alpha | WP-VIS-007, WP-VIS-009 | 0 | 1 | M3 |
| S7 | independent capability depth increases again | WP-VIS-002, WP-VIS-003, WP-VIS-004, WP-VIS-005, WP-VIS-006, WP-VDATA-001, WP-VDATA-003, WP-UI-003 | 0 | 0 | M4 |
| S8 | depth continues; M4 mandatory feature complete | WP-VIS-002, WP-VIS-003, WP-VIS-004, WP-VIS-005, WP-VIS-006, WP-VDATA-001, WP-VDATA-003, WP-UI-003 | 1 | 0 | M4 |
| S9 | cross-cutting quality and evaluation dependencies dominate | WP-VDATA-002, WP-VDATA-004 | 0 | 0 | M5 |
| S10 | quality/evaluation continues; M5 reliability & evaluation ready | WP-VDATA-002, WP-VDATA-004 | 2 | 1 | M5 |
| S11 | freeze convergence; highest freeze-risk window; M6 | WP-VDATA-005, WP-RES-010 | 0 | 3 | M6 |
| S12 | graph effectively immutable, formal execution only; M7 | WP-VIS-010 | 0 | 0 | M7 |
| S13 | evidence, release and documentation convergence; M8 | — | 0 | 0 | M8 |

Two windows deserve explicit attention for this role: **S5–S6** (highest integration density — avoid unrelated refactoring) and **S11** (freeze convergence — avoid casual experimental changes).

### 10.1 Interface ledger with each teammate

**Selman ↔ Asrın**

| Direction | Count | Edges / packages |
|---|---|---|
| Selman receives from Asrın | 2 | DEP-056 (DN-CORE-CONTRACTS, by S3), DEP-063 (DN-CORE-GENEALOGY, by M5) |
| Selman delivers to Asrın | 5 | DEP-065 (DN-AI-RCA, by E2E-01 readiness (end S4)), DEP-068 (DN-AI-RCA, by M3 (S6)), DEP-122 (DN-RES-DATASCEN, by M5 (S10)), DEP-150 (DN-FRZ-MODEL, by M6), DEP-151 (DN-FRZ-PROTOCOL, by M6) |
| shared packages (owner/reviewer) | 22 | WP-EVT-001, WP-VIS-001, WP-VIS-002, WP-VIS-004, WP-VIS-005, WP-VIS-006, WP-VIS-007, WP-VDATA-001, WP-VDATA-002, WP-VDATA-005, WP-ML-002, WP-ML-004, WP-ML-006, WP-UI-003, WP-UI-004, WP-UI-008, WP-TEST-002, WP-RES-002, WP-RES-010, WP-RES-012, WP-DOC-003, WP-S-001 |

**Selman ↔ Batu**

| Direction | Count | Edges / packages |
|---|---|---|
| Selman receives from Batu | 1 | DEP-062 (DN-SIM-COREINT, by M5) |
| Selman delivers to Batu | 1 | DEP-131 (DN-FRZ-DATA, by M6 (S11)) |
| shared packages (owner/reviewer) | 2 | WP-VIS-009, WP-VDATA-003 |

**Selman ↔ Yavuz**

| Direction | Count | Edges / packages |
|---|---|---|
| Selman receives from Yavuz | 2 | DEP-055 (DN-RT-MLFLOW, by M4/M5), DEP-058 (DN-RT-OBJ, by E2E-01 (end S5)) |
| Selman delivers to Yavuz | 0 | — |
| shared packages (owner/reviewer) | 5 | WP-OBJ-001, WP-VIS-003, WP-VIS-008, WP-VIS-010, WP-VDATA-004 |

## 11. Integration Checkpoints

| Checkpoint | Work packages | What this role must prove |
|---|---|---|
| E2E-01 (end S5, Item 67) | WP-VIS-007 | contract readiness by end S4 and real-boundary behaviour in the formal run; review obligation before the run (Item 67 #215–#218) |
| AV-SCEN-01…12 (Item 84) | WP-VIS-007 | architecture validation scenarios executed on the Integration environment |
| GS-01 demo (DEMO-GS01-001) | WP-VIS-007 | the hero path works from a pinned release without presentation shortcuts |
| FBC-01 E2E matrix (BENCH-E2E-001) | — | the role's part of the 4×20 statistical matrix executes unattended |

## 12. Failure and Negative Tests

Negative and failure-path verification owned or co-owned by this role. Happy-path evidence alone can never satisfy an H0 requirement (03 §4.4).

| Verification family | Kind | Scope | Family owner | Minimum environment |
|---|---|---|---|---|
| TEST-DATA-SPLITLEAK | TEST | Frozen partition entity/group overlap detection against SplitManifest policy | Asrın | EVALUATION |
| TEST-VIS-OOD | TEST | UNKNOWN/OOD outcome emission + anomaly path independent of closed-set classifier | Selman | CI |
| TEST-VIS-ORACLE-NEG | TEST | Oracle/evaluator label exclusion from Vision runtime inputs (negative) | Selman | CI |

## 13. Research / Evaluation Responsibilities

Selman is primary research owner for **RQ-4 (perception coupled with spatial/operational context)**, plus Vision ablations, OOD behaviour and synthetic-versus-public comparisons (Item 58). The research contribution is explicitly not 'we trained a classifier': it is whether perception that carries uncertainty and spatial structure improves downstream operational decisions, measured on episodes that contain genealogy and operational state. Selman also owns the honest reporting rule that a public-benchmark claim requires the public dataset (HARD), while the product itself may run entirely on owned synthetic data (Item 66 #124).

| R1 work package | Title | Milestone | Evidence lane |
|---|---|---|---|
| WP-VDATA-005 | Vision evaluation portfolio and RQ-4 lane preparation | M6 | BENCH-RQ4-001, BENCH-VIS-001 |
| WP-RES-010 | RQ-4 lane: perception-to-operations evaluation | M6 | BENCH-E2E-001, BENCH-RQ4-001, BENCH-VIS-001 |

## 14. Documentation and ADR Obligations

Own dataset cards, model cards/ModelPackage documentation, the Vision service and contract documentation, and the ADRs covering model family choices, OOD approach and dataset strategy.

## 15. Risks and Bottlenecks

| Risk (Item 69) | Exposure for this role | Mitigation carried in this roadmap |
|---|---|---|
| VIS-R01 | Vision remains a classification demo and never reaches operational meaning. | Spatial analysis, OOD and the RQ-4 downstream-impact evaluation are mandatory packages, not extras. |
| VIS-R04 | OOD/UNKNOWN behaviour is untested and the model is confidently wrong. | Threshold policy versioning, calibration on CAL only, and OOD cases in the evaluation portfolio. |
| DATA-R03 | Dataset rights are unclear and block a public claim late. | Licence status recorded at dataset selection; synthetic generator as the F4 fallback that keeps the product path clear. |
| DATA-R04 | Split leakage invalidates RQ-4. | Entity/group-level splits, leakage detector, FINAL access guard, freeze before M6. |
| VIS-R06 | No GPU-free path exists and onboarding/CI break. | CPU smoke path with a distinct smoke ModelPackage and a documented CPU baseline. |
| VIS-R07 | Model provenance is lost and results cannot be reproduced. | ModelPackage manifests with dataset/experiment lineage and immutability checks. |

## 16. Cross-Review Responsibilities

Selman reviews anything that consumes or reinterprets perception: the evidence typing in RCA, the UI presentation of observations and UNKNOWN states, and any scheduler/automation logic that would react to a defect label. Selman is the required reviewer for the observation contract and is a reviewer on dataset/evidence provenance questions in the research lanes.

Named reviewer on 12 work packages owned by others (§9.SUP). Cross-review is an Item 63 obligation, not a courtesy: a dependency handshake counts as complete only when both sides have validated contract usability (Item 66 #140).

## 17. Final Benchmark Contribution

| Lane / asset | Kind | Scope | Role's obligation |
|---|---|---|---|
| BENCH-E2E-001 | BENCH | FBC-01 final statistical E2E matrix: 4 frozen scenario definitions × 20 seeds (80 base instances) | execute and record dispositions, including failures |
| BENCH-PERF-VIS | BENCH | Vision CPU smoke latency and cold/warm CPU/GPU inference characterization | execute and record dispositions, including failures |
| BENCH-RQ4-001 | BENCH | RQ-4 perception-to-operations context evaluation (120 episodes) | execute and record dispositions, including failures |
| BENCH-VIS-001 | BENCH | Final Vision evaluation lane: classification, localization, segmentation, anomaly, OOD, spatial pattern (no single accuracy) | execute and record dispositions, including failures |

Campaign discipline that binds this role: run only what was frozen at M6; record every attempted run with a disposition; never adjust a threshold, rubric or scenario after seeing results; a MISS or a NOT_SUPPORTED outcome is a result, not a failure to conceal.

## 18. Demo Contribution

In GS-01 Selman owns the first two visible steps: a real inspection artifact and a computed observation with overlays and confidence shown in the inspection viewer. The demo must show the observation as a perception fact with its uncertainty — never as a verdict about root cause (Item 62 #55).

## 19. Thesis / Portfolio Evidence

Portfolio and thesis material: the multi-axis Vision evaluation (not a single accuracy figure), OOD/UNKNOWN behaviour under unfamiliar inputs, serialized component spatial pattern analysis, the synthetic-versus-public data comparison, and the RQ-4 perception-to-operations result. Every figure is generated from the sealed analysis package; nothing is produced for presentation purposes only.

| Evidence artifact | Produced by | Status today |
|---|---|---|
| Owned requirement dispositions (19) | 03 trace registry at M8 | NOT_YET_EXECUTED |
| Sealed lane results for owned research lanes | FBC-01 bundle at M7 | NOT_YET_EXECUTED |
| Architecture/design record (ADRs, contracts) | continuous from M1 | NOT_STARTED |
| Negative/failure evidence (3 families) | M5–M7 | NOT_YET_EXECUTED |

## 19.1 Requirement Execution Dossier

One block per owned requirement: what must be built, what proves it, where the evidence must come from, and which milestone carries it. This is the checklist the owner works through between M1 and M8.

```yaml
FR-UI-003:
  class: F1
  area: UI
  work_packages: [WP-UI-003]
  target_milestone: M4
  architecture: [ARCH-EDGE-WEB, ARCH-VIS-ARTIFACT]
  planned_surface: "inspection viewer with overlays via scoped artifact access"
  boundary_mode_final: REAL
  verification: [TEST-UI-VISION, AV-SCEN-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-001:
  class: F0
  area: VIS
  work_packages: [WP-OBJ-001, WP-VIS-001]
  target_milestone: M2
  architecture: [ARCH-VIS-ARTIFACT, ARCH-VIS-INFER, ARCH-DATA-OBJ]
  planned_surface: "async InspectionRequested → inference worker over ArtifactRef"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PIPELINE, E2E-01, AV-SCEN-01, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-002:
  class: F1
  area: VIS
  work_packages: [WP-VIS-002, WP-VDATA-005, WP-RES-006]
  target_milestone: M4
  architecture: [ARCH-VIS-INFER, ARCH-VIS-EVAL]
  planned_surface: "classification head for accepted task set"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PIPELINE, BENCH-VIS-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-003:
  class: F1
  area: VIS
  work_packages: [WP-VIS-002]
  target_milestone: M4
  architecture: [ARCH-VIS-INFER, ARCH-VIS-EVAL]
  planned_surface: "localization output (boxes/regions)"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PIPELINE, BENCH-VIS-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-004:
  class: F1
  area: VIS
  work_packages: [WP-VIS-003]
  target_milestone: M4
  architecture: [ARCH-VIS-INFER, ARCH-VIS-EVAL]
  planned_surface: "segmentation output (masks as object artifacts)"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PIPELINE, BENCH-VIS-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-005:
  class: F1
  area: VIS
  work_packages: [WP-VIS-003]
  target_milestone: M4
  architecture: [ARCH-VIS-OOD, ARCH-VIS-EVAL]
  planned_surface: "anomaly model path (independent of classifier)"
  boundary_mode_final: REAL
  verification: [TEST-VIS-OOD, BENCH-VIS-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-006:
  class: F1
  area: VIS
  work_packages: [WP-VIS-004, WP-VDATA-005, WP-RES-010]
  target_milestone: M4
  architecture: [ARCH-VIS-OOD]
  planned_surface: "UNKNOWN/OOD outcome + ThresholdPolicyVersion"
  boundary_mode_final: REAL
  verification: [TEST-VIS-OOD, BENCH-VIS-001, BENCH-RQ4-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-007:
  class: F1
  area: VIS
  work_packages: [WP-VIS-005]
  target_milestone: M4
  architecture: [ARCH-VIS-MODEL, ARCH-VIS-INFER]
  planned_surface: "provenance fields (ModelVersion, PreprocessingVersion) on InspectionResult"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-VIS-PROVENANCE, INSP-VIS-DATASET]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-008:
  class: F1
  area: VIS
  work_packages: [WP-VIS-005]
  target_milestone: M4
  architecture: [ARCH-VIS-INFER, ARCH-VIS-OOD]
  planned_surface: "confidence/uncertainty fields + calibration artifact"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PROVENANCE, BENCH-VIS-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-009:
  class: F1
  area: VIS
  work_packages: [WP-VIS-001]
  target_milestone: M2
  architecture: [ARCH-VIS-INFER, ARCH-CTR-EVTSCHEMA]
  planned_surface: "InspectionObservation/InspectionResult publisher (name reconciliation GAP-RTM-009)"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PIPELINE, TEST-EVT-SCHEMA, AV-SCEN-01, E2E-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-010:
  class: F1
  area: VIS
  work_packages: [WP-VIS-006, WP-VDATA-005, WP-RES-010]
  target_milestone: M4
  architecture: [ARCH-VIS-INFER, ARCH-VIS-EVAL]
  planned_surface: "serialized component spatial-pattern / cluster analysis module"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PIPELINE, BENCH-VIS-001, BENCH-RQ4-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-011:
  class: F1
  area: VIS
  work_packages: [WP-VDATA-001, WP-VDATA-003]
  target_milestone: M4
  architecture: [ARCH-DATA-LINEAGE, ARCH-VIS-MODEL]
  planned_surface: "dataset card + provenance class field (SYNTHETIC/PUBLIC)"
  boundary_mode_final: REAL
  verification: [INSP-VIS-DATASET, BENCH-VIS-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-012:
  class: F1
  area: VIS
  work_packages: [WP-VDATA-002]
  target_milestone: M5
  architecture: [ARCH-DATA-LINEAGE, ARCH-DATA-OBJ]
  planned_surface: "sealed DatasetVersion + SplitManifest (train/calibration/final)"
  boundary_mode_final: REAL
  verification: [INSP-VIS-DATASET, TEST-DATA-SPLITLEAK, BENCH-VIS-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-013:
  class: F1
  area: VIS
  work_packages: [WP-VIS-009]
  target_milestone: M3
  architecture: [ARCH-VIS-INFER, ARCH-WORLD-EVALZONE]
  planned_surface: "input-field allowlist; Oracle-taint rejection"
  boundary_mode_final: REAL
  verification: [TEST-VIS-ORACLE-NEG, AV-SCEN-11, BENCH-VIS-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-014:
  class: F1
  area: VIS
  work_packages: [WP-VIS-008]
  target_milestone: M2
  architecture: [ARCH-VIS-INFER, ARCH-PLAT-CLI]
  planned_surface: "CPU smoke inference profile (mfgctl smoke vision)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-VIS-CPUSMOKE, TEST-RES-CPUONLY]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-015:
  class: F1
  area: VIS
  work_packages: [WP-VDATA-004]
  target_milestone: M5
  architecture: [ARCH-VIS-MODEL, ARCH-DATA-OBJ]
  planned_surface: "ModelPackage manifest (bytes digest, dataset/experiment lineage)"
  boundary_mode_final: REAL
  verification: [TEST-VIS-PROVENANCE, TEST-DATA-CHECKSUM]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-VIS-016:
  class: F0
  area: VIS
  work_packages: [WP-VIS-007, WP-TEST-006, WP-RES-010, WP-BENCH-002]
  target_milestone: M3
  architecture: [ARCH-VIS-INFER, ARCH-AI-ORCH]
  planned_surface: "GS-01 closed-loop wiring: Vision observation as RCA evidence input (no hardcoded defect flag)"
  boundary_mode_final: REAL
  verification: [E2E-01, AV-SCEN-01, DEMO-GS01-001, BENCH-E2E-001]
  evidence_env: "INTEGRATION + EVALUATION + DEMO"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-009:
  class: A1
  area: PERF
  work_packages: [WP-VIS-008]
  target_milestone: M2
  metric: "CPU smoke path time per image on accepted small sample"
  threshold: "≤ 15 s/image"
  workload_profile: "accepted small inspection sample"
  hardware_profile: "HP: documented CPU baseline"
  verification: [BENCH-PERF-VIS, TEST-VIS-CPUSMOKE]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-010:
  class: C3
  area: PERF
  work_packages: [WP-VIS-010]
  target_milestone: M7
  metric: "cold-start and warm inference latency per CPU/GPU profile"
  threshold: "C3 — characterize; no threshold"
  workload_profile: "final inspection workload"
  hardware_profile: "HP: final Vision CPU/GPU profile(s) (schema OD-EVID-01)"
  verification: [BENCH-PERF-VIS]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
```

## 20. Definition of Final Role Completion

This role is complete at M8 when every line below is true and demonstrable from generated artifacts — not when the owner believes the work is done.

| # | Completion criterion |
|---|---|
| C-1 | All 17 owned work packages are at DoD (04 §4.2), with real repository references replacing `TBD_BY_IMPLEMENTATION` |
| C-2 | All 19 owned requirements have a final disposition in 03 — VERIFIED, or an explicitly recorded FAIL/MISS/REBASELINED with analysis |
| C-3 | Every owned F0 requirement is verified on a real integrated path (FR-VIS-001, FR-VIS-016) |
| C-4 | Every owned H0 requirement (0) has hard/negative evidence with zero-count assertions satisfied |
| C-5 | Every owned A1/S2/C3 requirement has a measurement executed in the correct environment with its HardwareProfile/WorkloadProfile bound |
| C-6 | Every downstream commitment (6 HARD edges) was delivered at its required readiness with unblock evidence |
| C-7 | All owned contracts are versioned, documented and consumed by their real consumers — no consumer still runs on fixtures in the acceptance path |
| C-8 | Owned ADRs exist for the decisions listed in §14, and 03 trace edges are current |
| C-9 | Owned research lanes executed from frozen artifacts with dispositions recorded; claims traced to sealed evidence |
| C-10 | Owned red-team findings are resolved or explicitly accepted before release |
| C-11 | No owned capability depends on a development fixture, a manual host step or an unrecorded configuration |
| C-12 | A teammate who is not this owner can run the owned capability from documentation alone (cross-familiarity, TEAM-R01) |

---

*End of 06B_Selman_Engineering_Roadmap.md (Draft — Derived from Approved 01/02 Baseline).*