# 06A — Asrın Engineering Roadmap
## Manufacturing Intelligence & Core Systems Owner

| Field | Value |
|---|---|
| Document | `06A_Asrin_Engineering_Roadmap.md` |
| Status | **Draft — Derived from Approved 01/02 Baseline** (requires the owner's own review) |
| Version | v0.1.0-draft |
| Generated | 17 Eylül 2026 (pre-implementation) |
| Canonical role (01 Item 62) | Manufacturing Intelligence & Core Systems Owner |
| Owned work packages | 73 of 179 (12 F0 · 46 F1-class · 11 R1 · 4 R2/S) |
| Owned requirements | 124 (92 FR · 32 NFR) |
| Owned dependency nodes (05) | 35 |
| Upstream cross-owner HARD gates | 23 |
| Downstream cross-owner consumers | 18 HARD edges |
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

Own the semantic centre of the Manufacturing Operations Platform: what a lot *is*, what state changes are legal, what the system believes about the world, what the AI may conclude from evidence, and what authority any of that confers. Every other role produces or consumes meaning that is defined here — the Simulator executes Core's legality, Vision produces observations that Core and the Twin ingest, the Scheduler plans against a Twin-derived snapshot, Automation executes Core commands under Asrın-owned authority policy, and the platform runs all of it without touching any of those meanings. The role is therefore judged by semantic coherence under pressure, not by volume of code.

## 2. Removal-Test Statement

Remove Asrın and the project stops being *Intelligent Manufacturing Operations Platform for Critical Aerospace Components*. Without the canonical manufacturing core there is no authoritative lot/serialized component/route model, no legal-transition authority and no revision/idempotency discipline — the Simulator becomes a standalone toy, the Scheduler optimizes a fiction and Automation has nothing safe to execute against. Without the Twin there is no epistemically honest operational picture, so RCA and the Command Center would be reading raw event soup. Without the AI orchestrator, RCA evidence model and authority policy semantics there is no *intelligence* layer and no RQ-1/RQ-3 research contribution: what remains is a simulator with a scheduler and a dashboard.

**Removal test in numbers.** Removing this role removes 12 F0 work packages (WP-CORE-001, WP-CORE-005, WP-CORE-008, WP-EVT-001, WP-TWIN-001, WP-TWIN-006, WP-AI-001, WP-AI-006, WP-HITL-001, WP-UI-001, WP-UI-006, WP-TEST-003), 124 owned requirements and 35 owned dependency nodes, including 14 nodes that other owners depend on through 18 HARD edges.

### 2.1 Boundaries this role may not cross

Ownership is bounded in both directions: these rules protect other roles from this one, and are enforced by tests rather than by convention.

| Boundary | Source | How it is enforced in the plan |
|---|---|---|
| AI cannot directly mutate manufacturing state | Item 62 #32 | AI identity holds no Core mutation credential; Core denies the AI principal (WP-AI-006). |
| AI cannot self-approve | Item 62 #33 | Authority policy evaluation is external to the model and requires an authenticated human (WP-HITL-001, WP-HITL-004). |
| AI cannot read the hidden Oracle in normal runtime | Item 62 #34 | Evaluator-only credentials and namespace separation; runtime denial proven (WP-SEC-007, AV-SCEN-11). |
| Core cannot reach into Scheduler private state | Item 62 #35 | Scheduler internals are consumed only through the plan contract. |
| Core cannot reach into Vision private state | Item 62 #36 | Only published observations are consumed; Core never re-scores a defect. |
| Core does not own platform runtime | Item 62 #37 | Runtime, deployment and resource decisions belong to Yavuz; Core states requirements, not infrastructure choices. |

## 3. Owned Architecture Surfaces

Architecture components (02 registry) reached through this role's work packages, and the 05 readiness nodes that carry them.

| Readiness node (05) | Surface | Type | 02 ARCH anchor | Final readiness required |
|---|---|---|---|---|
| DN-AI-ACTCON | ActionCatalog + ActionProposal contract (authority semantics) | CONTRACT | ARCH-AUTO-ACTIONCAT, ARCH-AI-PROPOSAL | FROZEN |
| DN-AI-ORCH | Deterministic AI orchestrator | CAPABILITY | ARCH-AI-ORCH | FROZEN |
| DN-AI-PROVIDER | LLM provider abstraction + deterministic non-LLM baseline | CAPABILITY | ARCH-AI-PROVIDER | FROZEN |
| DN-AI-RCA | Structured evidence-grounded RCA on real operational evidence | CAPABILITY | ARCH-AI-ORCH, ARCH-AI-TOOLS | FROZEN |
| DN-AI-TOOLCON | AI typed tool schemas + fixtures | CONTRACT | ARCH-AI-TOOLS | FROZEN |
| DN-CORE-CMDCON | Core command contracts (hold / release / dispatch / maintenance request) | CONTRACT | ARCH-CTR-CMDSCHEMA, ARCH-CORE-CMD | FROZEN |
| DN-CORE-CMDEXEC | Core command execution (idempotent, revision-checked, outcome persisted) | CAPABILITY | ARCH-CORE-CMD | FROZEN |
| DN-CORE-CONTRACTS | Core domain contracts (Lot, SerializedComponent, Route, Operation, Equipment refs, state/revision identity) | CONTRACT | ARCH-CORE-DOMAIN, ARCH-CTR-API | FROZEN |
| DN-CORE-GENEALOGY | Temporal genealogy / exposure queries | CAPABILITY | ARCH-CORE-GENEALOGY | FROZEN |
| DN-CORE-LIFECYCLE | Core minimal lifecycle implementation | CAPABILITY | ARCH-CORE-DOMAIN, ARCH-CORE-DB | FROZEN |
| DN-CORE-OUTBOX | Transactional outbox + relay | CAPABILITY | ARCH-CORE-OUTBOX, ARCH-EVT-OUTBOX | FROZEN |
| DN-CORE-SNAPCON | ManufacturingStateSnapshot / SchedulingSnapshot contract | CONTRACT | ARCH-TWIN-API, ARCH-CTR-API | FROZEN |
| DN-CORE-TRANSITIONS | Legal manufacturing transitions (hold/release/rework/split/merge) stable | CAPABILITY | ARCH-CORE-DOMAIN, ARCH-CORE-CMD | FROZEN |
| DN-EVT-CONTRACTS | Event contracts (envelope + domain events, IC registry) | CONTRACT | ARCH-CTR-EVTSCHEMA, ARCH-EVT-SCHEMA, ARCH-CTR-VERSIONING | FROZEN |
| DN-EVT-SPINE | Operational event spine (outbox → NATS → idempotent consumers) | CAPABILITY | ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX | FROZEN |
| DN-FRZ-MODEL | Model / policy freeze (ModelPackages, AIBehaviorBundle, RetrievalProfile, SchedulerPolicy, WorkflowBundle, AuthorityPolicy) | FREEZE | ARCH-VIS-MODEL, ARCH-AI-PROVIDER, ARCH-AI-RAG, ARCH-SCH-ENGINE, ARCH-AUTO-WORKFLOW | FROZEN |
| DN-FRZ-PROTOCOL | ExperimentProtocolFreeze (metrics, analysis plan, hypotheses) | FREEZE | ARCH-DATA-LINEAGE | FROZEN |
| DN-FRZ-RQ1CORPUS | RCA final corpus (RQ-1) | FREEZE | ARCH-AI-RAG | FROZEN |
| DN-FRZ-RQ3AUTH | Authority scenario set (RQ-3) | FREEZE | ARCH-HITL-POLICY | FROZEN |
| DN-HITL-APPROVAL | Real HITL approval bound to identity + exact revision/WorldID/expiry | CAPABILITY | ARCH-HITL-APPROVAL, ARCH-HITL-EXPIRY | FROZEN |
| DN-HITL-POLICY | Authority policy semantics (L0–L4, deterministic evaluation) | CAPABILITY | ARCH-HITL-POLICY | FROZEN |
| DN-ML | Predictive ML M1/M2/M3 (Prediction contract, calibration) | CAPABILITY | ARCH-AI-ORCH (coarse, GAP-RTM-001) | FROZEN |
| DN-RAG | RAG retrieval capability (sparse/dense/hybrid, citations, rights filter) | CAPABILITY | ARCH-AI-RAG, ARCH-DATA-VECTOR | FROZEN |
| DN-RAG-CORPUS | Documentary corpus (DocumentVersion/CorpusVersion) | DATA | ARCH-AI-RAG | FROZEN |
| DN-RES-ANALYSIS | Statistical analysis / AnalysisPackage | EVIDENCE | ARCH-DATA-LINEAGE | FROZEN |
| DN-RES-BASELINES | Baselines (RCA-B*, scheduler/Vision/ML baselines, BaselineRuns) | EVIDENCE | ARCH-DATA-LINEAGE | FROZEN |
| DN-RES-CALIB | Calibration (thresholds, budgets, policies on CAL partitions) | EVIDENCE | ARCH-DATA-LINEAGE | FROZEN |
| DN-RES-CLAIMS | ResearchClaims classification (RQ-1…RQ-4, MC-1, MC-2) | EVIDENCE | — | FROZEN |
| DN-RES-DATASCEN | Evaluation datasets / scenario families (DEV/CAL/FINAL partitions) | DATA | ARCH-DATA-LINEAGE | FROZEN |
| DN-TWIN-PROJ | Meaningful Twin projection (revision/freshness/epistemic/STALE) | CAPABILITY | ARCH-TWIN-STATE, ARCH-TWIN-FRESHNESS | FROZEN |
| DN-TWIN-SKELETON | Twin skeleton (projector + query API) | CAPABILITY | ARCH-TWIN-PROJECTOR, ARCH-TWIN-API | FROZEN |
| DN-TWIN-VERIFY | Twin verification view for effect verification | CAPABILITY | ARCH-TWIN-API, ARCH-AUTO-VERIFY | FROZEN |
| DN-UI-APPROVAL | Approval Center + incident timeline | CAPABILITY | ARCH-HITL-UI, ARCH-EDGE-WEB | FROZEN |
| DN-UI-BFFCON | BFF/OpenAPI contracts + UI fixtures | CONTRACT | ARCH-EDGE-BFF, ARCH-CTR-API | FROZEN |
| DN-UI-SHELL | Command Center shell via BFF | CAPABILITY | ARCH-EDGE-WEB, ARCH-EDGE-BFF | FROZEN |

**ARCH components touched:** `ARCH-AI-ORCH`, `ARCH-AI-PROPOSAL`, `ARCH-AI-PROVIDER`, `ARCH-AI-RAG`, `ARCH-AI-TOOLS`, `ARCH-AUTO-IDEMPOTENCY`, `ARCH-AUTO-VERIFY`, `ARCH-AUTO-WORKFLOW`, `ARCH-CORE-CMD`, `ARCH-CORE-DB`, `ARCH-CORE-DOMAIN`, `ARCH-CORE-GENEALOGY`, `ARCH-CORE-OUTBOX`, `ARCH-CTR-API`, `ARCH-CTR-CMDSCHEMA`, `ARCH-CTR-EVTSCHEMA`, `ARCH-CTR-VERSIONING`, `ARCH-DATA-LINEAGE`, `ARCH-DATA-OBJ`, `ARCH-DATA-PG`, `ARCH-DATA-VECTOR`, `ARCH-EDGE-BFF`, `ARCH-EDGE-NOTIFY`, `ARCH-EDGE-PRESENT`, `ARCH-EDGE-WEB`, `ARCH-EVT-CONSUMER`, `ARCH-EVT-OUTBOX`, `ARCH-EVT-SCHEMA`, `ARCH-HITL-APPROVAL`, `ARCH-HITL-DUAL`, `ARCH-HITL-EXPIRY`, `ARCH-HITL-POLICY`, `ARCH-HITL-UI`, `ARCH-OBS-AUDIT`, `ARCH-OBS-HEALTH`, `ARCH-OBS-TELEMETRY`, `ARCH-OBS-TRACE`, `ARCH-PLAT-CICD`, `ARCH-PLAT-RELEASE`, `ARCH-SCH-ENGINE`, `ARCH-SCH-HEURISTIC`, `ARCH-SEC-AUTHZ`, `ARCH-SIM-ENGINE`, `ARCH-TWIN-API`, `ARCH-TWIN-FRESHNESS`, `ARCH-TWIN-PROJECTOR`, `ARCH-TWIN-REBUILD`, `ARCH-TWIN-STATE`, `ARCH-VIS-EVAL`, `ARCH-VIS-INFER`, `ARCH-WORLD-EVALZONE`, `ARCH-WORLD-ISOLATION`, `ARCH-WORLD-REGISTRY`, `ARCH-WORLD-SCOPE`.

## 4. Owned FR/NFR Families

Ownership here means PrimaryOwner in the 01 catalogue: this role is accountable for the requirement's correctness, its trace mapping (03) and its final disposition.

### 4.FAI FR-AI (13)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-AI-001 | F0 | WP-AI-001, WP-TEST-006, WP-RES-006, WP-R2-002 | TEST-AI-OUTPUT, E2E-01, AV-SCEN-01, BENCH-RQ1-001, BENCH-E2E-001 |
| FR-AI-002 | F1 | WP-AI-002 | TEST-AI-TOOLS, AV-SCEN-01 |
| FR-AI-003 | F1 | WP-AI-002 | TEST-AI-TOOLS, TEST-AUTH-NEG |
| FR-AI-004 | F0 | WP-AI-006, WP-TEST-003, WP-RES-009 | TEST-AUTH-NEG, AV-SCEN-01, BENCH-RQ3-001, TEST-SEC-SVCID |
| FR-AI-005 | F1 | WP-AI-003, WP-RES-007 | TEST-AI-OUTPUT, BENCH-RQ1-001 |
| FR-AI-006 | F1 | WP-AI-003 | TEST-AI-OUTPUT, BENCH-RQ1-001 |
| FR-AI-007 | F1 | WP-AI-003 | TEST-AI-OUTPUT, BENCH-RQ1-001 |
| FR-AI-008 | F1 | WP-AI-003, WP-RES-007 | TEST-AI-OUTPUT, BENCH-RQ1-001, AV-SCEN-03 |
| FR-AI-009 | F1 | WP-AI-004 | TEST-AUTH-NEG, AV-SCEN-01, BENCH-RQ3-001 |
| FR-AI-010 | F1 | WP-AI-004 | TEST-AI-BINDING, AV-SCEN-04 |
| FR-AI-011 | F1 | WP-AI-005, WP-RES-011 | INSP-AI-BEHAVIOR, BENCH-RQ1-001, INSP-REP-LLM |
| FR-AI-012 | F1 | WP-AI-001 | TEST-AI-BUDGET |
| FR-AI-013 | F1 | WP-AI-001 | TEST-AI-OUTPUT, AV-SCEN-01 |

### 4.FCORE FR-CORE (16)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-CORE-001 | F0 | WP-CORE-001 | TEST-CORE-DOMAIN, E2E-01, AV-SCEN-01, BENCH-E2E-001 |
| FR-CORE-002 | F0 | WP-CORE-001 | TEST-CORE-DOMAIN, TEST-CORE-GENEALOGY, E2E-01, AV-SCEN-02, BENCH-E2E-001 |
| FR-CORE-003 | F1 | WP-CORE-002, WP-CORE-008, WP-TEST-003 | TEST-CORE-STATEMACHINE, AV-SCEN-01 |
| FR-CORE-004 | F1 | WP-CORE-003 | TEST-CORE-REVISION, TEST-HITL-REPLAY-NEG |
| FR-CORE-005 | F1 | WP-CORE-003 | TEST-CORE-IDEMP, AV-SCEN-05, RES-DUP-001 |
| FR-CORE-006 | F1 | WP-CORE-003, WP-CORE-008 | TEST-CORE-IDEMP, TEST-AUTO-OUTCOME, AV-SCEN-01 |
| FR-CORE-007 | F1 | WP-CORE-002 | TEST-CORE-STATEMACHINE, E2E-01, AV-SCEN-01 |
| FR-CORE-008 | F1 | WP-CORE-002 | TEST-CORE-STATEMACHINE, TEST-AUTH-NEG |
| FR-CORE-009 | F1 | WP-CORE-004 | TEST-CORE-STATEMACHINE, TEST-CORE-GENEALOGY, BENCH-E2E-001 |
| FR-CORE-010 | F1 | WP-CORE-004 | TEST-CORE-GENEALOGY |
| FR-CORE-011 | F1 | WP-CORE-004 | TEST-CORE-GENEALOGY |
| FR-CORE-012 | F1 | WP-CORE-004 | TEST-CORE-GENEALOGY, AV-SCEN-01, BENCH-RQ1-001 |
| FR-CORE-013 | F1 | WP-CORE-001, WP-CORE-007 | TEST-ARCH-BOUNDARY, TEST-SEC-SVCID, TEST-AUTH-NEG |
| FR-CORE-014 | F1 | WP-CORE-005 | TEST-CORE-OUTBOX, TEST-EVT-SCHEMA, AV-SCEN-01 |
| FR-CORE-015 | F1 | WP-CORE-005 | TEST-CORE-OUTBOX, RES-BROKER-001, AV-SCEN-07 |
| FR-CORE-016 | F1 | WP-CORE-003 | TEST-CORE-CONTRACT, TEST-EVT-SCHEMA |

### 4.FEVAL FR-EVAL (4)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-EVAL-002 | R1 | WP-SIM-007, WP-RES-002, WP-RES-011 | INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK, BENCH-FBC-001 |
| FR-EVAL-006 | R1 | WP-RES-004 | TEST-EVAL-ANALYSIS, INSP-EVAL-CLAIMS, BENCH-FBC-001 |
| FR-EVAL-009 | R1 | WP-RES-012 | INSP-EVAL-CLAIMS, TEST-EVAL-ANALYSIS, BENCH-FBC-001 |
| FR-EVAL-010 | R1 | WP-RES-012, WP-DOC-003 | INSP-EVAL-CLAIMS, BENCH-FBC-001 |

### 4.FEVT FR-EVT (8)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-EVT-001 | F0 | WP-EVT-001 | TEST-EVT-SCHEMA, TEST-ARCH-BOUNDARY, AV-SCEN-01, BENCH-E2E-001 |
| FR-EVT-002 | F1 | WP-EVT-002 | TEST-EVT-ENVELOPE |
| FR-EVT-003 | F1 | WP-EVT-002 | TEST-EVT-ENVELOPE, TEST-OBS-TRACEPROP, AV-SCEN-01 |
| FR-EVT-004 | F1 | WP-EVT-002 | TEST-EVT-ENVELOPE, AV-SCEN-10, AV-SCEN-09 |
| FR-EVT-005 | F1 | WP-EVT-003, WP-TEST-004 | TEST-EVT-CONSUMER-IDEMP, AV-SCEN-05, RES-DUP-001 |
| FR-EVT-006 | F1 | WP-EVT-001, WP-TEST-002 | TEST-EVT-SCHEMA |
| FR-EVT-007 | F1 | WP-EVT-005, WP-TEST-007 | TEST-ARCH-BOUNDARY, TEST-SEC-SVCID |
| FR-EVT-008 | F1 | WP-EVT-001 | TEST-ARCH-BOUNDARY, TEST-EVT-SCHEMA |

### 4.FGOV FR-GOV (7)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-GOV-001 | F1 | WP-GOV-001 | TEST-GOV-CATALOG |
| FR-GOV-002 | F1 | WP-GOV-001 | TEST-GOV-CATALOG, TEST-GOV-TRACELINT |
| FR-GOV-003 | F1 | WP-GOV-001 | TEST-GOV-CATALOG |
| FR-GOV-004 | F1 | WP-GOV-002, WP-DOC-002 | TEST-GOV-TRACELINT |
| FR-GOV-007 | F1 | WP-GOV-004 | INSP-GOV-CHANGECTRL |
| FR-GOV-008 | F1 | WP-GOV-001 | TEST-GOV-CATALOG |
| FR-GOV-010 | F1 | WP-GOV-003, WP-DOC-006 | TEST-GOV-TRACELINT, INSP-GOV-ACCEPT |

### 4.FHITL FR-HITL (8)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-HITL-001 | F0 | WP-HITL-001, WP-RES-009 | TEST-HITL-POLICY, TEST-AUTH-NEG, AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001 |
| FR-HITL-002 | F1 | WP-HITL-001 | TEST-HITL-POLICY, BENCH-RQ3-001 |
| FR-HITL-003 | F1 | WP-HITL-002 | TEST-HITL-BINDING, AV-SCEN-01, AV-SCEN-04 |
| FR-HITL-004 | F1 | WP-HITL-002 | TEST-HITL-BINDING, AV-SCEN-01, AV-SCEN-04 |
| FR-HITL-005 | F1 | WP-HITL-002 | TEST-HITL-BINDING, AV-SCEN-10 |
| FR-HITL-006 | F1 | WP-HITL-003, WP-TEST-003 | TEST-HITL-REPLAY-NEG, AV-SCEN-04, BENCH-RQ3-001 |
| FR-HITL-008 | F1 | WP-HITL-005 | TEST-HITL-RECORD, TEST-SEC-AUDIT |
| FR-HITL-009 | F1 | WP-HITL-006 | TEST-HITL-DUAL, BENCH-RQ3-001 |

### 4.FML FR-ML (8)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-ML-001 | F1 | WP-ML-002, WP-ML-007 | TEST-ML-CONTRACT, BENCH-ML-M1-001 |
| FR-ML-002 | F1 | WP-ML-003, WP-ML-007 | TEST-ML-CONTRACT, TEST-ML-LEAKAGE, BENCH-ML-M2-001 |
| FR-ML-003 | F1 | WP-ML-004, WP-ML-007 | TEST-ML-CONTRACT, TEST-ML-LEAKAGE, BENCH-ML-M3-001 |
| FR-ML-004 | F1 | WP-ML-005 | TEST-ML-CONTRACT, TEST-EVT-SCHEMA |
| FR-ML-005 | F1 | WP-VDATA-004, WP-ML-005 | TEST-ML-CONTRACT, INSP-AI-BEHAVIOR |
| FR-ML-006 | F1 | WP-ML-006 | BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001 |
| FR-ML-007 | F1 | WP-SIM-007, WP-ML-001 | INSP-DATA-PROVENANCE, BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001 |
| FR-ML-008 | F1 | WP-ML-001 | TEST-ML-LEAKAGE, TEST-DATA-SPLITLEAK, INSP-EVAL-PARTITION, BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001 |

### 4.FRAG FR-RAG (10)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-RAG-001 | F1 | WP-RAG-001 | TEST-RAG-RETRIEVAL, AV-SCEN-01 |
| FR-RAG-002 | F1 | WP-RAG-005 | TEST-AI-OUTPUT, TEST-ARCH-BOUNDARY |
| FR-RAG-003 | F1 | WP-RAG-002 | TEST-RAG-RETRIEVAL, BENCH-RAG-001 |
| FR-RAG-004 | F1 | WP-RAG-002 | TEST-RAG-RETRIEVAL, BENCH-RAG-001 |
| FR-RAG-005 | F1 | WP-RAG-002, WP-R2-001 | TEST-RAG-RETRIEVAL, BENCH-RAG-001, BENCH-RQ1-001 |
| FR-RAG-006 | F1 | WP-RAG-003 | TEST-RAG-PROVENANCE, BENCH-RAG-001 |
| FR-RAG-007 | F1 | WP-RAG-004 | TEST-RAG-RIGHTS |
| FR-RAG-008 | F1 | WP-RAG-004 | TEST-RAG-INJECTION, BENCH-RQ3-001 |
| FR-RAG-009 | F1 | WP-RAG-001, WP-RAG-007, WP-RES-011 | INSP-AI-BEHAVIOR, BENCH-RQ1-001, BENCH-RAG-001 |
| FR-RAG-010 | F1 | WP-RAG-003, WP-RES-007 | TEST-RAG-PROVENANCE, TEST-AI-OUTPUT, AV-SCEN-01, BENCH-RQ1-001 |

### 4.FSEC FR-SEC (2)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-SEC-003 | F1 | WP-SEC-003 | TEST-SEC-AUTHZ-NEG, AV-SCEN-04, BENCH-RQ3-001 |
| FR-SEC-009 | F1 | WP-RAG-004 | TEST-RAG-INJECTION, TEST-AUTH-NEG |

### 4.FTWIN FR-TWIN (10)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-TWIN-001 | F0 | WP-TWIN-001 | TEST-TWIN-PROJECTION, E2E-01, AV-SCEN-01, BENCH-E2E-001 |
| FR-TWIN-002 | F1 | WP-TWIN-001 | TEST-TWIN-PROJECTION, TEST-TWIN-READONLY |
| FR-TWIN-003 | F1 | WP-TWIN-002 | TEST-TWIN-EPISTEMIC, AV-SCEN-01, AV-SCEN-09 |
| FR-TWIN-004 | F1 | WP-TWIN-002 | TEST-TWIN-FRESHNESS, AV-SCEN-01, BENCH-PERF-CORE |
| FR-TWIN-005 | F1 | WP-TWIN-002 | TEST-TWIN-FRESHNESS, AV-SCEN-07 |
| FR-TWIN-006 | F1 | WP-TWIN-004, WP-TEST-004 | TEST-TWIN-PROJECTION, RES-TWINREBUILD-001, AV-SCEN-08 |
| FR-TWIN-007 | F1 | WP-TWIN-005, WP-TEST-005 | TEST-TWIN-EPISTEMIC, AV-SCEN-09 |
| FR-TWIN-008 | F1 | WP-TWIN-003 | TEST-TWIN-READONLY, TEST-AUTH-NEG, AV-SCEN-01 |
| FR-TWIN-009 | F1 | WP-TWIN-001 | TEST-TWIN-PROJECTION |
| FR-TWIN-010 | F1 | WP-CORE-008, WP-TWIN-006 | AV-SCEN-01, E2E-01, BENCH-E2E-001, DEMO-GS01-001 |

### 4.FUI FR-UI (6)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-UI-001 | F0 | WP-UI-001 | TEST-UI-BROWSER, E2E-01, AV-SCEN-01, DEMO-GS01-001 |
| FR-UI-002 | F1 | WP-UI-002, WP-S-001 | TEST-UI-BROWSER, AV-SCEN-01, DEMO-GS01-001 |
| FR-UI-004 | F1 | WP-UI-004 | TEST-UI-BROWSER, AV-SCEN-01, DEMO-GS01-001 |
| FR-UI-006 | F1 | WP-UI-006 | TEST-UI-BROWSER, AV-SCEN-01, AV-SCEN-04, DEMO-GS01-001 |
| FR-UI-008 | F1 | WP-UI-008 | TEST-UI-SEMANTICS, AV-SCEN-09, DEMO-GS01-001 |
| FR-UI-010 | F1 | WP-UI-010 | TEST-UI-BROWSER, AV-SCEN-01, DEMO-GS01-001 |

### 4.NCAP NFR-CAP (1)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-CAP-005 | S2 | domain command throughput without correctness failure | 20 cmd/s × 5 min | WP-CORE-006, WP-PERF-003 |

### 4.NDATA NFR-DATA (3)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-DATA-002 | H0 | prohibited entity/group overlap across frozen train/calibration/final partitions | = 0 | WP-VDATA-002, WP-RES-002 |
| NFR-DATA-005 | H0 | formal messages/artifacts in final evidence failing declared schema/version validation | = 0 | WP-EVT-001, WP-TEST-002 |
| NFR-DATA-006 | H0 | formal-claim datasets/corpora identifying source, version, rights/provenance | 100% | WP-VDATA-001 |

### 4.NGOV NFR-GOV (6)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-GOV-001 | H0 | catalog lint violations | 0 missing/duplicate NFRIDs | WP-GOV-001 |
| NFR-GOV-002 | H0 | retired-ID reuse detections | 0 | WP-GOV-001 |
| NFR-GOV-003 | H0 | NFRs without exactly one PrimaryOwner | 0 | WP-GOV-001 |
| NFR-GOV-007 | H0 | NFRs without H0/A1/S2/C3 class | 0 | WP-GOV-001 |
| NFR-GOV-008 | H0 | post-M6 material NFR changes without freeze-impact review | 0 | WP-GOV-004 |
| NFR-GOV-010 | H0 | composite/averaged quality score used for NFR disposition | 0 uses | WP-GOV-003, WP-X-001 |

### 4.NPERF NFR-PERF (8)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-PERF-001 | S2 | backend/BFF receipt→response latency, common Core/Twin reads | p95 ≤ 500 ms | WP-CORE-006, WP-TWIN-003, WP-PERF-002, WP-R2-003 |
| NFR-PERF-002 | S2 | command accepted/rejected decision latency (not effect) | p95 ≤ 750 ms | WP-CORE-006, WP-PERF-002 |
| NFR-PERF-003 | A1 | committed outbox record → durable broker publication delay | p95 ≤ 2 s; p99 ≤ 5 s | WP-EVT-006, WP-PERF-002 |
| NFR-PERF-004 | A1 | canonical event → readable Twin projection lag | p95 ≤ 2 s; p99 ≤ 5 s | WP-TWIN-003, WP-PERF-002 |
| NFR-PERF-005 | S2 | backend/Twin current → primary view reflects update | p95 ≤ 3 s | WP-UI-002, WP-PERF-002 |
| NFR-PERF-006 | S2 | top-k retrieval latency, frozen corpus/RetrievalProfile (excl. LLM) | p95 ≤ 2 s | WP-RAG-002, WP-PERF-002 |
| NFR-PERF-007 | S2 | orchestrator start → structured RCA result | p95 ≤ 60 s (outage scenarios separate) | WP-AI-007 |
| NFR-PERF-014 | S2 | primary route actionable after warm app startup | p95 ≤ 3 s | WP-UI-001, WP-PERF-002 |

### 4.NREC NFR-REC (2)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REC-008 | S2 | mandatory Twin projection rebuild duration | ≤ 60 min | WP-TWIN-004, WP-DR-003 |
| NFR-REC-009 | S2 | Qdrant/RAG index rebuild from canonical artifacts, no manual reconstruction | ≤ 60 min | WP-RAG-006, WP-DR-003 |

### 4.NREL NFR-REL (2)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REL-002 | H0 | accepted stale/replayed/mismatched protected executions | = 0 | WP-HITL-003 |
| NFR-REL-010 | H0 | unresolved semantic mismatch between verified Core effect and Twin state at run end | = 0 per valid closed-loop run | WP-CORE-008, WP-TWIN-006 |

### 4.NREP NFR-REP (2)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REP-002 | H0 | canonical numerical results/tables regenerated from frozen raw inputs + AnalysisPackage | identical under rounding rules | WP-RES-004 |
| NFR-REP-009 | C3 | provider/model identity, timestamps, raw outputs, repeated trials, aggregate uncertainty | C3 — characterize (byte identity not required) | WP-AI-005 |

### 4.NSEC NFR-SEC (2)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-SEC-004 | H0 | rejection rate of unauthorized protected-action attempts | 100% | WP-AI-006, WP-SEC-008, WP-BENCH-003 |
| NFR-SEC-009 | H0 | external LLM requests containing secrets / Oracle truth / rights-prohibited data | = 0 | WP-AI-005, WP-SEC-008 |

### 4.NUX NFR-UX (6)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-UX-001 | A1 | safety/authority-critical states encoded by color only | = 0 | WP-UI-008 |
| NFR-UX-002 | H0 | known-stale user-facing state presented as current | = 0 | WP-TWIN-002, WP-UI-008 |
| NFR-UX-003 | H0 | protected approvals without inspectable proposal/plan/revision/risk context | = 0 | WP-UI-006 |
| NFR-UX-004 | A1 | known failures shown as indefinite success-looking spinner | = 0 | WP-UI-008 |
| NFR-UX-005 | A1 | primary flow browser E2E on current stable Chromium-family + Firefox (versions recorded) | PASS on both at M8 | WP-UI-011 |
| NFR-UX-006 | H0 | approvals/validation/failures/effect verification concealed or bypassed by Presenter Mode | = 0 | WP-UI-012, WP-DOC-004 |

## 5. Critical Contracts

| Node | Contract surface | Readiness deadline | Consumers (owner, edge) |
|---|---|---|---|
| DN-CORE-CONTRACTS | Core domain contracts (Lot, SerializedComponent, Route, Operation, Equipment refs, state/revision identity) | CONTRACT_READY by S1–S2 | DN-CORE-LIFECYCLE (Asrın, DEP-018); DN-EVT-CONTRACTS (Asrın, DEP-021); DN-CORE-CMDCON (Asrın, DEP-026); DN-CORE-SNAPCON (Asrın, DEP-030); DN-SIM-OPSEM (Batu, DEP-038); DN-VIS-ARTCON (Selman, DEP-056) |
| DN-CORE-CMDCON | Core command contracts (hold / release / dispatch / maintenance request) | CONTRACT_READY by S2–S3 | DN-CORE-CMDEXEC (Asrın, DEP-027); DN-AUTO-EXEC (Batu, DEP-097) |
| DN-CORE-SNAPCON | ManufacturingStateSnapshot / SchedulingSnapshot contract | CONTRACT_READY by E2E-01 readiness (end S4) | DN-SCH-DYN (Batu, DEP-079) |
| DN-EVT-CONTRACTS | Event contracts (envelope + domain events, IC registry) | CONTRACT_READY by M1 (S2) | DN-EVT-SPINE (Asrın, DEP-023); DN-TWIN-SKELETON (Asrın, DEP-031) |
| DN-AI-TOOLCON | AI typed tool schemas + fixtures | CONTRACT_READY by S2–S3 | DN-AI-ORCH (Asrın, DEP-064) |
| DN-AI-ACTCON | ActionCatalog + ActionProposal contract (authority semantics) | CONTRACT_READY by E2E-01 readiness (end S4) | DN-AI-RCA (Asrın, DEP-077); DN-AUTO-EXEC (Batu, DEP-096) |
| DN-UI-BFFCON | BFF/OpenAPI contracts + UI fixtures | CONTRACT_READY by S1–S2 | DN-UI-SHELL (Asrın, DEP-105) |

Contract obligations follow 05 DEP-RULE-04: a fixture satisfies development-stage consumption only; milestone and final evidence require the real capability behind the contract.

### 5.1 Contracts this role consumes

| DEP | Contract node (owner) | Consumed by | Required readiness | Need-by | Precise requirement declared (05 DEP-RULE-06) |
|---|---|---|---|---|---|
| DEP-065 | DN-VIS-OBSCON (Selman) | DN-AI-RCA | CONTRACT_READY | E2E-01 readiness (end S4) | AI must not wait for final Vision accuracy |
| DEP-092 | DN-SCH-PLANCON (Batu) | DN-HITL-APPROVAL | CONTRACT_READY | E2E-01 readiness (end S4) | exact plan revision binding |

### 5.2 Verification assets owned by this role

Planned verification families whose semantic correctness belongs to this role (03 §9.X). Asset identities are planning-level; numeric TestIDs are allocated when the assets are created.

| Family | Kind | Scope | Lane / tier | Min environment | Work packages relying on it |
|---|---|---|---|---|---|
| INSP-GOV-CHANGECTRL | INSP | Change-control / freeze-impact review record audit for requirement semantic changes (post-M6 focus) | ENG-A | CI | WP-GOV-004 |
| TEST-ARCH-BOUNDARY | TEST | Architecture-rules-as-code: import boundaries, schema ownership, forbidden cross-service credentials, contract producer uniqueness | ENG-B | CI | WP-CORE-001, WP-CORE-007, WP-EVT-001, WP-EVT-005, WP-RAG-005, WP-TEST-007 |
| TEST-CORE-DOMAIN | TEST | Canonical entity model: order/lot/serialized component/route/step/equipment incl. reentrant route representation | ENG-A | CI | WP-CORE-001 |
| TEST-CORE-STATEMACHINE | TEST | Legal/illegal manufacturing transitions incl. hold/release/rework/split/merge (negative-path mandatory, TEST-INV-08) | ENG-B | CI | WP-CORE-002, WP-CORE-004, WP-CORE-008, WP-TEST-003 |
| TEST-CORE-REVISION | TEST | Revision/freshness precondition rejection (STALE/CONFLICT outcomes) | ENG-B | CI | WP-CORE-003 |
| TEST-CORE-IDEMP | TEST | Command idempotency + durable command-outcome persistence (completed/rejected/unresolved) | ENG-B | CI | WP-CORE-003, WP-CORE-008 |
| TEST-CORE-GENEALOGY | TEST | Temporal genealogy / rework history non-overwrite / split-merge lineage queries | ENG-B | CI | WP-CORE-001, WP-CORE-004 |
| TEST-CORE-OUTBOX | TEST | Atomic mutation+outbox boundary incl. crash between commit and publish (real PostgreSQL, TEST-INV-03) | ENG-B | CI | WP-CORE-005 |
| TEST-CORE-CONTRACT | TEST | Versioned Core query/command contract compatibility (consumer-driven) | ENG-B | CI | WP-CORE-003 |
| TEST-TWIN-PROJECTION | TEST | Event-derived projection: duplicate/out-of-order/gap handling, source revision traceability | ENG-B | CI | WP-TEST-004, WP-TWIN-001, WP-TWIN-004 |
| TEST-TWIN-EPISTEMIC | TEST | ACTUAL/OBSERVED/INFERRED/PREDICTED/PLANNED/COUNTERFACTUAL separation + counterfactual isolation | ENG-B | CI | WP-TEST-005, WP-TWIN-002, WP-TWIN-005 |
| TEST-TWIN-FRESHNESS | TEST | Projection revision/freshness exposure and stale marking | ENG-B | CI | WP-TWIN-002 |
| TEST-TWIN-READONLY | TEST | Twin mutation-API ban + consumer read-only access (AI/Scheduler/BFF) | ENG-C | CI | WP-TWIN-001, WP-TWIN-003 |
| RES-TWINREBUILD-001 | DRILL | Twin projection loss → deterministic rebuild from retained canonical sources (AV-SCEN-08 execution) | ENG-D | INTEGRATION | WP-CORE-008, WP-DR-003, WP-TEST-004, WP-TWIN-004, WP-TWIN-006 |
| TEST-EVT-ENVELOPE | TEST | Message envelope: unique EventID, CorrelationID/CausationID, WorldID presence rules | ENG-B | CI | WP-EVT-002 |
| TEST-EVT-SCHEMA | TEST | Producer/consumer schema validation + compatibility / breaking-change detection | ENG-B | CI | WP-CORE-003, WP-CORE-005, WP-EVT-001, WP-ML-005, WP-TEST-002, WP-VIS-001 |
| TEST-EVT-CONSUMER-IDEMP | TEST | At-least-once consumer idempotency with real NATS JetStream (no fake bus, CI-INV-07) | ENG-B | CI | WP-EVT-003, WP-TEST-004 |
| TEST-ML-CONTRACT | TEST | Common versioned Prediction contract incl. ModelPackage + input revision binding | ENG-B | CI | WP-ML-002, WP-ML-003, WP-ML-004, WP-ML-005, WP-ML-007, WP-VDATA-004 |
| TEST-ML-LEAKAGE | TEST | Feature-leakage / future-information / FINAL-partition guard (ML-INV-01..05) | ENG-C | CI | WP-ML-001, WP-ML-003, WP-ML-004, WP-ML-007 |
| BENCH-ML-M1-001 | BENCH | M1 equipment-risk evaluation (discrimination + calibration separately) | ML | EVALUATION | WP-ML-001, WP-ML-002, WP-ML-006, WP-ML-007, WP-SIM-007 |
| BENCH-ML-M2-001 | BENCH | M2 cycle-time/tardiness evaluation | ML | EVALUATION | WP-ML-001, WP-ML-003, WP-ML-006, WP-ML-007, WP-SIM-007 |
| BENCH-ML-M3-001 | BENCH | M3 pre-inspection quality evaluation | ML | EVALUATION | WP-ML-001, WP-ML-004, WP-ML-006, WP-ML-007, WP-SIM-007 |
| TEST-RAG-RETRIEVAL | TEST | Sparse / dense / hybrid retrieval functional behavior on versioned corpus (real Qdrant) | ENG-A | CI | WP-R2-001, WP-RAG-001, WP-RAG-002 |
| TEST-RAG-PROVENANCE | TEST | Document/chunk provenance + citation-bearing evidence references | ENG-B | CI | WP-RAG-003, WP-RES-007 |
| TEST-RAG-RIGHTS | TEST | Rights/eligibility metadata filtering (negative: ineligible source never returned) | ENG-C | CI | WP-RAG-004 |
| TEST-RAG-INJECTION | TEST | Prompt-injection / retrieved-content cannot change authorization or policy (negative) | ENG-C | CI | WP-RAG-004 |
| BENCH-RAG-001 | BENCH | Retrieval ablation lane RAG-B0..B3 + RAG-PROPOSED bound to CorpusVersion/RetrievalProfile | RQ1 | EVALUATION | WP-R2-001, WP-RAG-001, WP-RAG-002, WP-RAG-003, WP-RAG-007, WP-RES-011 |
| TEST-AI-TOOLS | TEST | Versioned typed tool interfaces; tool allowlist exposes only READ/SIMULATE/PROPOSE | ENG-C | CI | WP-AI-002 |
| TEST-AI-OUTPUT | TEST | RCA structured output: hypothesis vs evidence separation, evidence refs, conflict/missing, abstention, schema validation | ENG-B | CI | WP-AI-001, WP-AI-003, WP-R2-002, WP-RAG-003, WP-RAG-005, WP-RES-006 |
| TEST-AI-BINDING | TEST | Proposal ↔ evidence/revision/world context binding | ENG-C | CI | WP-AI-004 |
| TEST-AI-BUDGET | TEST | AgentBudgetProfile enforcement and bounded termination (no unbounded loop) | ENG-D | CI | WP-AI-001 |
| INSP-AI-BEHAVIOR | INSP | Provider/model + BehaviorBundle/prompt/tool version identity on formal runs | ENG-G | EVALUATION | WP-AI-005, WP-ML-005, WP-RAG-001, WP-RAG-007, WP-RES-011, WP-VDATA-004 |
| TEST-AUTH-NEG | TEST | Cross-cutting authority negative suite: AI mutation/self-approval/credential/bypass attempts (AUTH-INV family) | ENG-C | CI | WP-AI-002, WP-AI-004, WP-AI-006, WP-AUTO-004, WP-BENCH-003, WP-CORE-001 |
| BENCH-RQ1-001 | BENCH | RQ-1 evidence-grounded RCA final evaluation (120 FINAL_TEST cases, baselines RCA-B1..PROPOSED) | RQ1 | EVALUATION | WP-AI-001, WP-AI-003, WP-AI-005, WP-CORE-004, WP-R2-001, WP-R2-002 |
| BENCH-RQ3-001 | BENCH | RQ-3 governed AI-to-action (150 cases, L0–L4 × 30, ≥40% adversarial) | RQ3 | EVALUATION | WP-AI-004, WP-AI-006, WP-BENCH-003, WP-HITL-001, WP-HITL-003, WP-HITL-006 |
| TEST-HITL-POLICY | TEST | L0–L4 policy class mapping and enforcement independent of AI text | ENG-C | CI | WP-HITL-001, WP-RES-009 |
| TEST-HITL-BINDING | TEST | Exact Proposal/Plan revision + WorldID + freshness binding; material plan change invalidates approval | ENG-C | CI | WP-HITL-002 |
| TEST-HITL-REPLAY-NEG | TEST | Stale/expired/replayed/cross-world approval rejection (negative) | ENG-C | CI | WP-CORE-003, WP-HITL-003, WP-TEST-003 |
| TEST-HITL-DUAL | TEST | Dual approval requires two distinct authorized identities | ENG-C | CI | WP-HITL-006 |
| TEST-HITL-RECORD | TEST | Approval record fields: decision, subject, revision binding, actor, timestamp | ENG-C | CI | WP-HITL-004, WP-HITL-005 |
| TEST-UI-BROWSER | TEST | Browser E2E against real BFF/API (DX-INV-40): primary flows, Chromium-family + Firefox | ENG-A | INTEGRATION | WP-S-001, WP-UI-001, WP-UI-002, WP-UI-004, WP-UI-006, WP-UI-010 |
| TEST-UI-SEMANTICS | TEST | Epistemic distinction, staleness, failure state, non-color-only status, Presenter Mode integrity | ENG-C | INTEGRATION | WP-DOC-004, WP-TWIN-002, WP-UI-006, WP-UI-008, WP-UI-012 |
| E2E-01 | SCENARIO | First formal E2E checkpoint: inspection-triggered controlled recovery (pre-M3; small deterministic world) | E2E | INTEGRATION | WP-AI-001, WP-AUTO-001, WP-AUTO-007, WP-BENCH-002, WP-CORE-001, WP-CORE-002 |
| AV-SCEN-01 | SCENARIO | Architecture validation scenario: Inspection-triggered controlled recovery | AVG | INTEGRATION | WP-AI-001, WP-AI-002, WP-AI-004, WP-AI-006, WP-AUTO-001, WP-AUTO-003 |
| AV-SCEN-03 | SCENARIO | Architecture validation scenario: Normal production with no false recovery | AVG | INTEGRATION | WP-AI-003, WP-RES-007 |
| AV-SCEN-04 | SCENARIO | Architecture validation scenario: Stale/replayed/mismatched approval rejection | AVG | INTEGRATION | WP-AI-004, WP-AI-006, WP-AUTO-003, WP-AUTO-004, WP-BENCH-003, WP-HITL-001 |
| AV-SCEN-05 | SCENARIO | Architecture validation scenario: Duplicate/out-of-order event delivery | AVG | INTEGRATION | WP-AUTO-002, WP-BENCH-003, WP-CORE-003, WP-EVT-003, WP-PERF-005, WP-TEST-004 |
| AV-SCEN-08 | SCENARIO | Architecture validation scenario: Twin projection loss/rebuild | AVG | INTEGRATION | WP-DR-003, WP-TEST-004, WP-TWIN-004 |
| AV-SCEN-10 | SCENARIO | Architecture validation scenario: Cross-WorldID mutation rejection | AVG | INTEGRATION | WP-AUTO-003, WP-EVT-002, WP-HITL-002, WP-HITL-003, WP-PERF-003, WP-SIM-004 |
| DEMO-GS01-001 | DEMO | GS-01 formal clean-world demo run (EXP-DEMO; never statistical evidence) | ENG-H | DEMO | WP-AUTO-007, WP-BENCH-002, WP-CORE-008, WP-DOC-004, WP-OBS-002, WP-PLAT-005 |
| TEST-SEC-AUTHZ-NEG | TEST | Backend authorization negative suite (UI visibility ≠ authorization; unknown permission ≠ allow) | ENG-C | INTEGRATION | WP-AI-006, WP-BENCH-003, WP-SEC-003, WP-SEC-008 |
| TEST-SEC-EGRESS | TEST | External LLM request payload audit: no secrets / Oracle truth / rights-prohibited data | ENG-C | EVALUATION | WP-AI-005, WP-SEC-008 |
| INSP-EVAL-PARTITION | INSP | DEV/CAL/FINAL partition + seed-namespace separation in ExperimentDefinitions | RQ* | EVALUATION | WP-ML-001, WP-RES-002, WP-RES-011, WP-SIM-007, WP-VDATA-002 |
| TEST-EVAL-ANALYSIS | TEST | AnalysisPackage regeneration determinism from frozen raw evidence | RQ* | EVALUATION | WP-RES-004, WP-RES-012 |
| INSP-EVAL-CLAIMS | INSP | RQ1–RQ4 outcome derivation + public/thesis metric exports trace to sealed analysis | RQ* | EVALUATION | WP-DOC-003, WP-RES-004, WP-RES-012 |
| BENCH-PERF-CORE | BENCH | Core/Twin read latency, command decision latency, outbox delay, Twin freshness, Core command throughput | PERF | EVALUATION | WP-CORE-006, WP-EVT-006, WP-PERF-002, WP-PERF-003, WP-R2-003, WP-TWIN-002 |
| BENCH-PERF-UI | BENCH | Command Center state visibility and initial actionable load on accepted LAN/client profile | PERF | EVALUATION | WP-PERF-002, WP-UI-001, WP-UI-002 |
| BENCH-PERF-AI | BENCH | RAG top-k retrieval latency and RCA path latency decomposition (provider context retained) | PERF | EVALUATION | WP-AI-007, WP-PERF-002, WP-RAG-002 |
| RES-IDXREBUILD-001 | DRILL | Qdrant/RAG index rebuild from canonical corpus artifacts | ENG-F | INTEGRATION | WP-DR-003, WP-RAG-006 |
| TEST-REP-ANALYSIS | TEST | Deterministic serialization/rounding rules for canonical numerical result tables (unit level, complements TEST-EVAL-ANALYSIS) | ENG-G | CI | WP-RES-004 |
| INSP-REP-LLM | INSP | External LLM characterization protocol: provider/model, timestamps, raw outputs, repeated trials, uncertainty | RQ1 | EVALUATION | WP-AI-005, WP-AI-007, WP-RES-011 |
| TEST-DATA-SPLITLEAK | TEST | Frozen partition entity/group overlap detection against SplitManifest policy | RQ* | EVALUATION | WP-ML-001, WP-RES-002, WP-RES-011, WP-SIM-007, WP-VDATA-002 |
| TEST-DATA-CONTRACTVALID | TEST | Schema/version validation of formal messages/artifacts used in final evidence | ENG-B | EVALUATION | WP-EVT-001, WP-TEST-002 |
| INSP-DATA-PROVENANCE | INSP | Dataset/corpus source, version, rights/provenance status for formal claims | RQ* | EVALUATION | WP-ML-001, WP-SIM-007, WP-VDATA-001 |
| INSP-GOV-NFR | INSP | NFR catalog/measurement-definition completeness: class, metric, context, HardwareProfile/WorkloadProfile binding | ENG-E | CI | WP-GOV-001, WP-GOV-003, WP-PERF-001 |

## 6. Upstream Dependencies

What this role must receive from others before it can pass a stage. Fixture-satisfiable rows are marked; the rest require the real upstream capability.

| DEP | Predecessor (owner) | Feeds node | Kind | Strength | Stage | Required readiness | Need-by | Fallback | Unblock evidence |
|---|---|---|---|---|---|---|---|---|---|
| DEP-019 | DN-RT-PG (Yavuz) | DN-CORE-LIFECYCLE | RUNTIME | HARD | INTEGRATION | SKELETON_READY | M1 (S2) | — | Core migrations apply on PostgreSQL |
| DEP-025 | DN-RT-NATS (Yavuz) | DN-EVT-SPINE | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | M1 (S2) | F1 | real JetStream in CI + INTEGRATION (no fake bus, CI-INV-07) |
| DEP-033 | DN-RT-PG (Yavuz) | DN-TWIN-SKELETON | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | M1 (S2) | — | `twin` schema migrated |
| DEP-035 | DN-SIM-COREINT (Batu) | DN-TWIN-PROJ | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M2 (S4) | — | Twin reflects simulated reentrant world |
| DEP-065 | DN-VIS-OBSCON (Selman) | DN-AI-RCA | CONTRACT | HARD | START | CONTRACT_READY | E2E-01 readiness (end S4) | F1 | contract merged + contract tests green + example fixture published (stable fixtures) |
| DEP-090 | DN-RT-IDP (Yavuz) | DN-HITL-APPROVAL | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 readiness (end S4) | F0 | authenticated approval bound to actor |
| DEP-092 | DN-SCH-PLANCON (Batu) | DN-HITL-APPROVAL | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | F1 | contract merged + contract tests green + example fixture published |
| DEP-108 | DN-RT-IDP (Yavuz) | DN-UI-APPROVAL | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 readiness (end S4) | — | real login in Approval Center |
| DEP-068 | DN-VIS-SERVING (Selman) | DN-AI-RCA | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M3 (S6) | — | real Vision observation consumed as RCA evidence |
| DEP-071 | DN-RT-QDRANT (Yavuz) | DN-RAG | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | M4 (S8) | F3 | RAG retrieval served from Qdrant on INTEGRATION |
| DEP-074 | DN-SIM-SYNTH (Batu) | DN-ML | DATA | HARD | MILESTONE_EXIT | EVALUATION_READY | M4 (S8) | F4 | sufficient historical data/features/labels generated |
| DEP-075 | DN-RT-MLFLOW (Yavuz) | DN-ML | RUNTIME | HARD | MILESTONE_EXIT | INTEGRATION_READY | M4/M5 | — | ML ModelPackage governance in MLflow |
| DEP-121 | DN-SIM-SYNTH (Batu) | DN-RES-DATASCEN | DATA | HARD | MILESTONE_EXIT | EVALUATION_READY | M5 (S10) | F4 | evaluation-ready scenarios/data with partitions |
| DEP-122 | DN-VIS-SPLIT (Selman) | DN-RES-DATASCEN | DATA | HARD | MILESTONE_EXIT | EVALUATION_READY | M5 (S10) | — | Vision splits evaluation-ready |
| DEP-127 | DN-RES-HARNESS (Yavuz) | DN-RES-CALIB | EVIDENCE | HARD | FREEZE | EVALUATION_READY | M5→M6 | — | calibration on CAL partition recorded |
| DEP-132 | DN-FRZ-DATA (Batu) | DN-FRZ-MODEL | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | — | model/policy selection on frozen data |
| DEP-135 | DN-FRZ-DATA (Batu) | DN-FRZ-PROTOCOL | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | — | dataset/scenario selection before protocol freeze |
| DEP-138 | DN-SIM-REALISM (Batu) | DN-FRZ-PROTOCOL | EVIDENCE | HARD | FREEZE | EVALUATION_READY | M6 (S11) | — | Simulation validation before final RQ-2 claim |
| DEP-150 | DN-VIS-OOD (Selman) | DN-FRZ-MODEL | CAPABILITY | HARD | FREEZE | EVALUATION_READY | M6 | — | OOD/spatial evaluation complete before model freeze |
| DEP-151 | DN-VIS-EPISODES (Selman) | DN-FRZ-PROTOCOL | DATA | HARD | FREEZE | EVALUATION_READY | M6 | — | operational episodes available for RQ-4 perception-to-operations |
| DEP-153 | DN-SCH-CPSAT (Batu) | DN-FRZ-MODEL | CAPABILITY | HARD | FREEZE | EVALUATION_READY | M6 | — | SchedulerPolicy selected |
| DEP-154 | DN-SCH-CF (Batu) | DN-FRZ-PROTOCOL | CAPABILITY | HARD | FREEZE | EVALUATION_READY | M6 | — | counterfactual recovery evaluation ready (CRN) |
| DEP-143 | DN-RES-BENCH (Yavuz) | DN-RES-ANALYSIS | EVIDENCE | HARD | FREEZE | FROZEN | M7 (S12) | — | sealed FBC-01 evidence |

## 7. Downstream Consumers

What others cannot do until this role delivers. Every row is a commitment with a need-by point.

| DEP | Delivered node | Consumer (owner) | Kind | Strength | Stage | Required readiness | Need-by | Unblock evidence |
|---|---|---|---|---|---|---|---|---|
| DEP-038 | DN-CORE-CONTRACTS | DN-SIM-OPSEM (Batu) | CONTRACT | HARD | START | CONTRACT_READY | S2 | contract merged + contract tests green + example fixture published (reviewed by Batu) |
| DEP-056 | DN-CORE-CONTRACTS | DN-VIS-ARTCON (Selman) | CONTRACT | HARD | START | CONTRACT_READY | S3 | contract merged + contract tests green + example fixture published |
| DEP-039 | DN-CORE-TRANSITIONS | DN-SIM-OPSEM (Batu) | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M2 (S4) | Simulator manufacturing-validity checks against Core legality |
| DEP-041 | DN-CORE-CMDEXEC | DN-SIM-COREINT (Batu) | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | M2 (S4) | Core-validated physical commands executed by Simulator |
| DEP-042 | DN-EVT-SPINE | DN-SIM-COREINT (Batu) | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | M2 (S4) | real cross-boundary integration test green on INTEGRATION |
| DEP-079 | DN-CORE-SNAPCON | DN-SCH-DYN (Batu) | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | contract merged + contract tests green + example fixture published |
| DEP-080 | DN-TWIN-PROJ | DN-SCH-DYN (Batu) | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | M2 (S4) | SchedulingSnapshot exported from real Twin |
| DEP-096 | DN-AI-ACTCON | DN-AUTO-EXEC (Batu) | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | contract merged + contract tests green + example fixture published |
| DEP-097 | DN-CORE-CMDCON | DN-AUTO-EXEC (Batu) | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | contract merged + contract tests green + example fixture published (typed command client) |
| DEP-098 | DN-CORE-CMDEXEC | DN-AUTO-EXEC (Batu) | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 readiness (end S4) | Core applies approved command idempotently and emits result (#187) |
| DEP-082 | DN-CORE-TRANSITIONS | DN-SCH-VALID (Batu) | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | validator uses canonical domain rules (no unilateral legality) |
| DEP-099 | DN-HITL-APPROVAL | DN-AUTO-EXEC (Batu) | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | valid approval required for protected execution — no fallback |
| DEP-103 | DN-TWIN-VERIFY | DN-AUTO-VERIFY (Batu) | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | verified Core/Twin effect (HTTP success insufficient) |
| DEP-089 | DN-AI-RCA | DN-SCH-DYN (Batu) | CAPABILITY | SOFT | INTEGRATION | COMPONENT_READY | M3 (S6) | trigger/objective context may come from AI, human or policy |
| DEP-104 | DN-AI-RCA | DN-AUTO-EXEC (Batu) | CAPABILITY | SOFT | INTEGRATION | COMPONENT_READY | M3 (S6) | deterministic/human proposals allowed for testing |
| DEP-081 | DN-EVT-SPINE | DN-SCH-DYN (Batu) | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M4 (S8) | event-triggered replanning on failures/holds/excursions |
| DEP-063 | DN-CORE-GENEALOGY | DN-VIS-EPISODES (Selman) | DATA | HARD | MILESTONE_EXIT | INTEGRATION_READY | M5 | genealogy linked to episodes |
| DEP-125 | DN-RES-BASELINES | DN-RES-HARNESS (Yavuz) | EVIDENCE | HARD | INTEGRATION | EVALUATION_READY | M5 (S10) | harness reproduces baseline numbers |
| DEP-129 | DN-RES-CALIB | DN-FRZ-DATA (Batu) | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | calibration closed before freeze |
| DEP-139 | DN-FRZ-PROTOCOL | DN-FRZ-RELEASE (Yavuz) | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | ExperimentProtocolFreeze recorded |

**Delivery load by consumer:** Batu: 14 HARD edges, Selman: 2 HARD edges, Yavuz: 2 HARD edges.

## 8. Milestone-by-Milestone Engineering Objectives

### 8.M0 M0 — Engineering Foundation Ready (End S1 / Week 2)

Nothing of Asrın's domain ships at M0, but the semantic groundwork does: repository conventions for the contracts package, the requirement catalog content, and the first draft of the Core domain concepts that WP-CORE-001 will publish in S1–S2. The single most valuable output of this window is a reviewed, fixture-bearing draft of the Core domain contract — it is the unlock for Batu's Simulator work and must not wait for Core implementation (Item 66 #39/#40).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-GOV-001 | Machine-readable requirement catalog and ID lint | F1 | 4 | L |

**Owned requirements reaching their target in this window (8):** FR-GOV-001, FR-GOV-002, FR-GOV-003, FR-GOV-008, NFR-GOV-001, NFR-GOV-002, NFR-GOV-003, NFR-GOV-007

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M1 M1 — Integrated Spine (End S2 / Week 4)

M1 is where Asrın's spine becomes real: Core lifecycle on PostgreSQL, transactional outbox, event contracts, the Twin skeleton projecting real events, and the Command Center shell reading through the BFF. The acceptance question is not 'does the service run' but 'does a Core mutation reach the Twin through the real outbox and broker with a revision the UI can show'.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-CORE-001 | Canonical manufacturing domain model and core schema | F0 | 4 | L |
| WP-CORE-005 | Domain events and transactional outbox | F0 | 3 | M |
| WP-CORE-007 | Core database migrations and role separation | F1 | 3 | M |
| WP-EVT-001 | Integration Contract Registry and versioning discipline | F0 | 4 | M |
| WP-EVT-002 | Message envelope, correlation and world scoping | F1 | 4 | M |
| WP-TWIN-001 | Twin projection engine | F0 | 3 | M |
| WP-UI-001 | Command Center shell and BFF contract | F0 | 4 | M |

**Owned requirements reaching their target in this window (17):** FR-CORE-001, FR-CORE-002, FR-CORE-013, FR-CORE-014, FR-CORE-015, FR-EVT-001, FR-EVT-002, FR-EVT-003, FR-EVT-004, FR-EVT-006, FR-EVT-008, FR-TWIN-001, FR-TWIN-002, FR-TWIN-009, FR-UI-001, NFR-DATA-005, NFR-PERF-014

**Upstream gates that must close in this window (3):** DEP-019 from Yavuz, DEP-025 from Yavuz, DEP-033 from Yavuz

**Commitments owed to others in this window (1):** DEP-038 → Batu

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M2 M2 — Operational Manufacturing Alpha (End S4 / Week 8)

M2 turns the spine into an operational world Asrın's layers can describe: legal transitions stabilized, command acceptance with idempotency and revision preconditions, genealogy, meaningful Twin projections with freshness and epistemic classes, and the SchedulingSnapshot contract for Batu. In parallel the AI side starts against typed tool fixtures — the orchestrator must be progressing before Vision or RAG are final (Item 66 #59, #66).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-CORE-002 | Manufacturing lifecycle state machine | F1 | 3 | M |
| WP-CORE-003 | Command acceptance: idempotency, revision preconditions, durable outcomes | F1 | 4 | L |
| WP-CORE-004 | Rework, split/merge and temporal genealogy | F1 | 3 | M |
| WP-EVT-003 | Idempotent consumer framework | F1 | 3 | S |
| WP-EVT-005 | Architecture rules as code (boundaries and ownership) | F1 | 3 | S |
| WP-TWIN-002 | Epistemic classes, freshness and staleness semantics | F1 | 3 | M |
| WP-TWIN-003 | Twin query API and scheduling snapshot export | F1 | 3 | M |
| WP-UI-002 | manufacturing facility state and operational views | F1 | 3 | S |
| WP-TEST-002 | Contract and schema test suites | F1 | 3 | S |
| WP-DOC-002 | ADR backfill and decision index | F1 | 3 | S |

**Owned requirements reaching their target in this window (25):** FR-CORE-003, FR-CORE-004, FR-CORE-005, FR-CORE-006, FR-CORE-007, FR-CORE-008, FR-CORE-009, FR-CORE-010, FR-CORE-011, FR-CORE-012, FR-CORE-016, FR-EVT-005, FR-EVT-006, FR-EVT-007, FR-GOV-004, FR-TWIN-003, FR-TWIN-004, FR-TWIN-005, FR-TWIN-008, FR-UI-002, NFR-DATA-005, NFR-PERF-001, NFR-PERF-004, NFR-PERF-005, NFR-UX-002

**Upstream gates that must close in this window (5):** DEP-035 from Batu, DEP-065 from Selman, DEP-090 from Yavuz, DEP-092 from Batu, DEP-108 from Yavuz

**Commitments owed to others in this window (9):** DEP-039 → Batu, DEP-041 → Batu, DEP-042 → Batu, DEP-056 → Selman, DEP-079 → Batu, DEP-080 → Batu, DEP-096 → Batu, DEP-097 → Batu, DEP-098 → Batu

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M3 M3 — Closed-Loop Alpha (End S6 / Week 12)

M3 is the closed loop, and Asrın owns most of its meaning: RCA consuming real Vision observations and real Twin/Core queries, proposals bound to world and revision, the authority policy that decides the human's role, and the Core commands that actually change state. E2E-01 (end S5) is the forcing function; Asrın reviews the whole Core/AI/domain authority path before the formal run (Item 67 #216). The AI path at M3 must work with typed tools and a deterministic or minimally-configured LLM path — it may not depend on final advanced RAG.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-CORE-008 | Core ↔ Simulator ↔ Twin integration and acceptance | F0 | 3 | M |
| WP-TWIN-006 | Effect verification view and Core/Twin consistency | F0 | 2 | S |
| WP-AI-001 | Deterministic orchestrator and execution budgets | F0 | 3 | M |
| WP-AI-002 | Typed tool registry and authority-tagged tool access | F1 | 3 | M |
| WP-AI-003 | Structured evidence-grounded RCA output | F1 | 4 | M |
| WP-AI-004 | Action proposal and context binding | F1 | 3 | S |
| WP-AI-006 | AI authority boundary and negative suite | F0 | 3 | M |
| WP-HITL-001 | Authority policy engine (L0–L4) | F0 | 3 | S |
| WP-HITL-002 | Approval binding to exact proposal/plan revision and world | F1 | 3 | S |
| WP-HITL-003 | Expiry, replay and staleness rejection | F1 | 3 | S |
| WP-UI-006 | Approval Center | F0 | 3 | M |
| WP-SEC-003 | Backend authorization enforcement | F1/H0 | 3 | S |
| WP-TEST-003 | Integration scenarios AV-SCEN-01…04 | F0 | 3 | M |

**Owned requirements reaching their target in this window (27):** FR-AI-001, FR-AI-002, FR-AI-003, FR-AI-004, FR-AI-005, FR-AI-006, FR-AI-007, FR-AI-008, FR-AI-009, FR-AI-010, FR-AI-012, FR-AI-013, FR-CORE-003, FR-CORE-006, FR-HITL-001, FR-HITL-002, FR-HITL-003, FR-HITL-004, FR-HITL-005, FR-HITL-006, FR-SEC-003, FR-TWIN-010, FR-UI-006, NFR-REL-002, NFR-REL-010, NFR-SEC-004, NFR-UX-003

**Upstream gates that must close in this window (1):** DEP-068 from Selman

**Commitments owed to others in this window (3):** DEP-082 → Batu, DEP-099 → Batu, DEP-103 → Batu

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M4 M4 — Mandatory Core Feature Complete (End S8 / Week 16)

M4 completes the mandatory intelligence surface: mandatory RAG configuration with citations and rights filtering, predictive M1/M2/M3 behind the common Prediction contract, the full RCA configuration including genealogy-backed exposure queries, the Approval Center context and the remaining Command Center workspaces. Authority negatives (no mutation credential, no self-approval, no bypass) must be proven on the real runtime, not argued.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-TWIN-005 | Counterfactual/what-if stream isolation | F1 | 2 | S |
| WP-ML-001 | Feature and label pipeline from operational history | F1 | 3 | M |
| WP-ML-002 | M1 — equipment risk model | F1 | 3 | M |
| WP-ML-003 | M2 — cycle-time / tardiness risk model | F1 | 3 | M |
| WP-ML-004 | M3 — pre-inspection quality risk model | F1 | 3 | S |
| WP-ML-005 | Common prediction contract and publication | F1 | 3 | S |
| WP-RAG-001 | Documentary corpus governance and ingestion | F1 | 3 | M |
| WP-RAG-002 | Retrieval profiles: sparse, dense and hybrid | F1 | 4 | M |
| WP-RAG-003 | Citation-bearing provenance in retrieval and RCA | F1 | 3 | S |
| WP-RAG-004 | Rights filtering and prompt-injection resistance | F1 | 3 | M |
| WP-RAG-005 | Evidence typing: documentary vs operational | F1 | 3 | S |
| WP-AI-005 | Provider abstraction, behavior bundle and deterministic baseline | F1 | 4 | M |
| WP-HITL-005 | Approval record, audit trail and protected-action coverage | F1 | 3 | S |
| WP-HITL-006 | Dual approval for highest-risk actions | F1 | 3 | S |
| WP-UI-004 | Incident investigation workspace (RCA) | F1 | 3 | S |

**Owned requirements reaching their target in this window (26):** FR-AI-011, FR-HITL-008, FR-HITL-009, FR-ML-001, FR-ML-002, FR-ML-003, FR-ML-004, FR-ML-005, FR-ML-007, FR-ML-008, FR-RAG-001, FR-RAG-002, FR-RAG-003, FR-RAG-004, FR-RAG-005, FR-RAG-006, FR-RAG-007, FR-RAG-008, FR-RAG-009, FR-RAG-010, FR-SEC-009, FR-TWIN-007, FR-UI-004, NFR-PERF-006, NFR-REP-009, NFR-SEC-009

**Upstream gates that must close in this window (3):** DEP-071 from Yavuz, DEP-074 from Batu, DEP-075 from Yavuz

**Commitments owed to others in this window (1):** DEP-081 → Batu

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M5 M5 — Reliability & Evaluation Ready (End S10 / Week 20)

M5 shifts Asrın from building to making things provable: baselines for RCA, partition/seed governance, the analysis package skeleton, epistemic/staleness semantics finished across the UI, and the measurement definitions for the NFRs Asrın owns (Core/Twin latency, RCA latency, capacity). Everything the research depends on must be runnable by someone else by the end of this window.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-TWIN-004 | Twin rebuild and catch-up | F1 | 3 | S |
| WP-ML-006 | Calibration and uncertainty evaluation | F1 | 3 | S |
| WP-RAG-006 | Index rebuild and recovery | F1 | 3 | S |
| WP-UI-008 | Epistemic, staleness and failure-state semantics | F1 | 3 | M |
| WP-UI-010 | Incident and decision timeline | F1 | 3 | S |
| WP-RES-002 | Partition, seed and protocol governance | R1 | 3 | M |
| WP-RES-006 | Baseline suite across lanes | R1 | 4 | M |

**Owned requirements reaching their target in this window (12):** FR-AI-001, FR-EVAL-002, FR-ML-006, FR-TWIN-006, FR-UI-008, FR-UI-010, NFR-DATA-002, NFR-REC-008, NFR-REC-009, NFR-UX-001, NFR-UX-002, NFR-UX-004

**Upstream gates that must close in this window (3):** DEP-121 from Batu, DEP-122 from Selman, DEP-127 from Yavuz

**Commitments owed to others in this window (2):** DEP-063 → Selman, DEP-125 → Yavuz

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M6 M6 — Research Freeze (End S11 / Week 22)

M6 is a freeze discipline problem. Asrın freezes the RCA corpus, retrieval profile, AI behavior bundle, authority policy and analysis plan, and confirms that no requirement in the owned families still lacks measurement definition or verification design. After this point a semantic change is a change-controlled event with freeze-impact review, not a commit.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-GOV-004 | Change control and freeze-impact tooling | F1 | 3 | S |
| WP-ML-007 | ML evaluation lanes (M1/M2/M3) for the final campaign | R1 | 3 | S |
| WP-RAG-007 | Retrieval ablation lane for RQ-1 | R1 | 3 | S |
| WP-RES-004 | AnalysisPackage and deterministic result regeneration | R1 | 3 | S |
| WP-RES-007 | RQ-1 lane: evidence-grounded RCA evaluation | R1 | 4 | M |
| WP-RES-009 | RQ-3 lane: governed AI-to-action evaluation | R1 | 3 | M |
| WP-RES-011 | Freeze execution for M6 | R1 | 3 | S |

**Owned requirements reaching their target in this window (15):** FR-AI-004, FR-AI-005, FR-AI-008, FR-AI-011, FR-EVAL-002, FR-EVAL-006, FR-GOV-007, FR-HITL-001, FR-ML-001, FR-ML-002, FR-ML-003, FR-RAG-009, FR-RAG-010, NFR-GOV-008, NFR-REP-002

**Upstream gates that must close in this window (7):** DEP-132 from Batu, DEP-135 from Batu, DEP-138 from Batu, DEP-150 from Selman, DEP-151 from Selman, DEP-153 from Batu, DEP-154 from Batu

**Commitments owed to others in this window (2):** DEP-129 → Batu, DEP-139 → Yavuz

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M7 M7 — Final Benchmark Complete (End S12 / Week 24)

During the campaign Asrın executes the RQ-1 and RQ-3 lanes and the MC-1 end-to-end matrix, and reviews evidence for the Core/Twin/AI parts of the engineering lanes. The job here is procedural integrity: run what was frozen, record dispositions including failures, and never adjust a threshold or a rubric after seeing results.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-CORE-006 | Core and Twin read/command performance profile | F1/S2 | 3 | S |
| WP-AI-007 | RCA path performance characterization | F1/A1 | 3 | S |
| WP-BENCH-002 | Final E2E matrix execution (MC-1) | R1 | 3 | S |

**Owned requirements reaching their target in this window (4):** NFR-CAP-005, NFR-PERF-001, NFR-PERF-002, NFR-PERF-007

**Upstream gates that must close in this window (1):** DEP-143 from Yavuz

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M8 M8 — Final Release Candidate (End S13 / Week 26)

M8 is claim discipline: classify RQ outcomes from sealed evidence only, write the thesis and portfolio material within the achieved evidence tier, lead the red-team review of claims, and sign off that every Asrın-owned F0/F1 requirement has a final disposition — including honest FAIL/MISS entries where they exist.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-UI-011 | Browser E2E harness and compatibility validation | F1/S2 | 3 | S |
| WP-UI-012 | Presenter mode integrity | F1 | 3 | S |
| WP-RES-012 | Research claim classification | R1 | 3 | S |
| WP-DOC-003 | Thesis and portfolio artifact production | R1 | 3 | S |
| WP-DOC-004 | Demo infrastructure and GS-01 rehearsal | F1 | 3 | M |
| WP-DOC-006 | Final red-team review execution | F1 | 3 | S |

**Owned requirements reaching their target in this window (5):** FR-EVAL-009, FR-EVAL-010, FR-GOV-010, NFR-UX-005, NFR-UX-006

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.X Unscheduled (R2 / stretch / guard rails)

| Work package | Title | Scope | Rule |
|---|---|---|---|
| WP-R2-001 | R2 retrieval candidates (ColBERT, cross-encoder reranking, alternative embeddings) | R2 | no milestone, no mandatory dependant, cut first under pressure |
| WP-R2-002 | R2 modelling candidates (local LLM runtime, VLM experiment, advanced causal RCA, RL scheduler, alternative solver formulations) | R2 | no milestone, no mandatory dependant, cut first under pressure |
| WP-S-001 | Stretch enhancements register (visualization, mobile UI, multi-node, analytics, extra scenarios) | S | no milestone, no mandatory dependant, cut first under pressure |
| WP-X-001 | Out-of-scope boundary maintenance | S | no milestone, no mandatory dependant, cut first under pressure |

## 9. Work Package Mapping

Each package below is owned by this role. Deliverables and tasks are the 04 definitions; the execution context (gates, consumers, verification, evidence) is projected here so the package can be picked up without cross-reading four documents.

### 9.WP-GOV-001 — Machine-readable requirement catalog and ID lint

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M0 · S1 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Yavuz |
| Source requirements | FR-GOV-001, FR-GOV-002, FR-GOV-003, FR-GOV-008, NFR-GOV-001, NFR-GOV-002, NFR-GOV-003, NFR-GOV-007 |
| Architecture | ARCH-PLAT-CICD |
| Gating edges | none — early unlocker |
| Verification families | INSP-GOV-NFR, TEST-GOV-CATALOG, TEST-GOV-TRACELINT |
| Size band / status | L (≈7–12 focused days) · NOT_STARTED |

**Deliverables.**
- requirements catalog file (schema + 306 entries mirroring 01 Items 81/82)
- catalog JSON Schema
- CI lint job wired into required checks
- generated coverage counts used by 03

**Major tasks.**
- define catalog schema fields (ID, class, PrimaryOwner, ScopeClass, source refs, status, revision)
- import the 306 entries without restating SHALL text
- implement uniqueness / retired-ID / owner / class checks
- fail-closed CI wiring + human-readable lint output
- publish generated counts for 03 regeneration

**Cut/fallback.** No cut. Without it no downstream generation is trustworthy; manual spreadsheets are explicitly rejected.


### 9.WP-CORE-001 — Canonical manufacturing domain model and core schema

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-CORE-CONTRACTS |
| Supporting reviewer | Batu |
| Source requirements | FR-CORE-001, FR-CORE-002, FR-CORE-013 |
| Architecture | ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-CORE-DOMAIN |
| Gating edges | none — early unlocker |
| Verification families | AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, E2E-01, TEST-ARCH-BOUNDARY, TEST-AUTH-NEG, TEST-CORE-DOMAIN, TEST-CORE-GENEALOGY, TEST-SEC-SVCID |
| Size band / status | L (≈7–12 focused days) · NOT_STARTED |

**Deliverables.**
- domain model modules in manufacturing-core
- `core` schema migrations
- versioned Core query contract (v1) + fixtures
- contract test suite

**Major tasks.**
- model entities and identity/revision fields
- design reentrant route/visit representation (operation-class revisit)
- author migrations and per-service DB roles/grants
- publish query contract + example fixtures for Simulator/Twin/Scheduler consumers
- component tests for identity, revision and route traversal

**Cut/fallback.** No cut (F0). Early CONTRACT_READY publication is the unlock for Simulator, Twin, Scheduler and Automation (05 CYC-01).


### 9.WP-CORE-005 — Domain events and transactional outbox

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-CORE-OUTBOX |
| Supporting reviewer | Yavuz |
| Source requirements | FR-CORE-014, FR-CORE-015 |
| Architecture | ARCH-CORE-DB, ARCH-CORE-OUTBOX, ARCH-EVT-OUTBOX |
| Gating edges | DEP-022 (DN-CORE-LIFECYCLE, M1 (S2)) |
| Verification families | AV-SCEN-01, AV-SCEN-07, RES-BROKER-001, TEST-CORE-OUTBOX, TEST-EVT-SCHEMA |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- outbox table + relay worker
- domain event schemas per namespace
- crash-consistency test suite on real PostgreSQL

**Major tasks.**
- define event payloads per accepted transition
- implement atomic mutation+outbox write
- implement relay with at-least-once publication and retry
- test crash between commit and publish
- instrument outbox delay metric for NFR-PERF-003

**Cut/fallback.** No cut (F0 spine).


### 9.WP-CORE-007 — Core database migrations and role separation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M1 · S2 |
| Readiness node | DN-RT-PG |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-DEP-004, FR-CORE-013 |
| Architecture | ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-DATA-PG, ARCH-PLAT-CICD |
| Gating edges | DEP-006 (DN-PLAT-COMPOSE, M0), DEP-007 (DN-PLAT-INTEG, M1 (S2)) |
| Verification families | TEST-ARCH-BOUNDARY, TEST-AUTH-NEG, TEST-DEP-MIGRATION, TEST-SEC-SVCID |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- migration tooling wiring
- per-service role/grant definitions
- migration status surface

**Major tasks.**
- choose migration runner and repository layout
- define roles for core/twin/automation/ai schemas
- wire migrations into CD with inspectable status
- negative test: cross-schema write denied

**Cut/fallback.** No cut; direct DB mutation by non-owner services is architecturally forbidden.


### 9.WP-EVT-001 — Integration Contract Registry and versioning discipline

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-EVT-CONTRACTS |
| Supporting reviewer | Selman |
| Source requirements | FR-EVT-001, FR-EVT-006, FR-EVT-008, NFR-DATA-005 |
| Architecture | ARCH-CTR-API, ARCH-CTR-CMDSCHEMA, ARCH-CTR-EVTSCHEMA, ARCH-CTR-VERSIONING, ARCH-EVT-SCHEMA |
| Gating edges | DEP-021 (DN-CORE-CONTRACTS, S1–S2) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, TEST-ARCH-BOUNDARY, TEST-DATA-CONTRACTVALID, TEST-EVT-SCHEMA |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- contracts package (IC-* namespaces)
- schema validation at producer and consumer boundaries
- compatibility/breaking-change detector
- canonical producer registry + broker subject ACLs

**Major tasks.**
- define contract file layout and version rules
- implement boundary validators
- implement compatibility check in CI
- resolve naming reconciliations 03 GAP-RTM-009/010 before freeze

**Cut/fallback.** No cut (F0). Contract-first is the mechanism that breaks every cycle in 05 §12.


### 9.WP-EVT-002 — Message envelope, correlation and world scoping

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M1 · S2 |
| Readiness node | DN-EVT-CONTRACTS |
| Supporting reviewer | Yavuz |
| Source requirements | FR-EVT-002, FR-EVT-003, FR-EVT-004, NFR-DATA-008 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-EVT-SCHEMA, ARCH-OBS-TRACE, ARCH-WORLD-SCOPE |
| Gating edges | DEP-021 (DN-CORE-CONTRACTS, S1–S2) |
| Verification families | AV-SCEN-01, AV-SCEN-09, AV-SCEN-10, TEST-DATA-TIME, TEST-EVT-ENVELOPE, TEST-OBS-TRACEPROP |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- envelope definition + shared library
- correlation/causation propagation middleware
- WorldID scope tagging and validation
- UTC wall-clock vs simulation-time field semantics

**Major tasks.**
- implement envelope fields (EventID, CorrelationID, CausationID, WorldID, SchemaVersion, OccurredAt, producer identity, entity revision)
- propagate through HTTP, NATS and Temporal boundaries
- reject messages missing required scope fields

**Cut/fallback.** No cut; GS-01 traceability and cross-world safety depend on it.


### 9.WP-TWIN-001 — Twin projection engine

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-TWIN-SKELETON |
| Supporting reviewer | Yavuz |
| Source requirements | FR-TWIN-001, FR-TWIN-002, FR-TWIN-009 |
| Architecture | ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-PROJECTOR, ARCH-TWIN-STATE |
| Gating edges | DEP-031 (DN-EVT-CONTRACTS, S2), DEP-032 (DN-EVT-SPINE, M1 (S2)), DEP-033 (DN-RT-PG, M1 (S2)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, E2E-01, TEST-TWIN-PROJECTION, TEST-TWIN-READONLY |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- twin-projector worker
- `twin` schema + read models
- source-revision ledger

**Major tasks.**
- implement event handlers for production/equipment/quality namespaces
- implement projection revision tracking to source EventID
- reject any mutation endpoint by design and by test
- startup catch-up behaviour

**Cut/fallback.** No cut (F0).


### 9.WP-UI-001 — Command Center shell and BFF contract

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-UI-BFFCON |
| Supporting reviewer | Yavuz |
| Source requirements | FR-UI-001, NFR-PERF-014 |
| Architecture | ARCH-EDGE-BFF, ARCH-EDGE-WEB |
| Gating edges | none — early unlocker |
| Verification families | AV-SCEN-01, BENCH-PERF-UI, DEMO-GS01-001, E2E-01, TEST-UI-BROWSER |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- React/Vite shell
- BFF OpenAPI contract + fixtures
- auth session integration
- route/navigation structure

**Major tasks.**
- define BFF surface from view needs
- implement shell with fixture-driven views
- wire OIDC session
- measure warm startup to actionable route

**Cut/fallback.** No cut (F0). Browser must never reach broker or database directly.


### 9.WP-CORE-002 — Manufacturing lifecycle state machine

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-CORE-TRANSITIONS |
| Supporting reviewer | Batu |
| Source requirements | FR-CORE-003, FR-CORE-007, FR-CORE-008 |
| Architecture | ARCH-CORE-CMD, ARCH-CORE-DOMAIN |
| Gating edges | DEP-020 (DN-CORE-LIFECYCLE, S2–S3) |
| Verification families | AV-SCEN-01, E2E-01, TEST-AUTH-NEG, TEST-CORE-STATEMACHINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- transition guard module
- hold/release command handlers
- negative-path test suite (illegal transitions)

**Major tasks.**
- enumerate legal transitions per entity state
- implement guards with explicit rejection reasons
- implement PlaceLotOnHold / ReleaseMaterialHold handlers (naming per 05 DEP-GAP-06)
- write negative tests as first-class cases (not afterthoughts)

**Cut/fallback.** No cut. Stability of this WP is a HARD precondition for Simulator validity claims, Scheduler validation and Automation execution.


### 9.WP-CORE-003 — Command acceptance: idempotency, revision preconditions, durable outcomes

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-CORE-CMDEXEC |
| Supporting reviewer | Batu |
| Source requirements | FR-CORE-004, FR-CORE-005, FR-CORE-006, FR-CORE-016 |
| Architecture | ARCH-AUTO-IDEMPOTENCY, ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-CTR-API, ARCH-CTR-VERSIONING |
| Gating edges | DEP-027 (DN-CORE-CMDCON, S2–S3), DEP-028 (DN-CORE-TRANSITIONS, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, AV-SCEN-05, RES-DUP-001, TEST-AUTO-OUTCOME, TEST-CORE-CONTRACT, TEST-CORE-IDEMP, TEST-CORE-REVISION, TEST-EVT-SCHEMA, TEST-HITL-REPLAY-NEG |
| Size band / status | L (≈7–12 focused days) · NOT_STARTED |

**Deliverables.**
- idempotency key store
- revision/freshness precondition validator
- CommandOutcome persistence + query
- versioned command contract (v1)

**Major tasks.**
- design idempotency key semantics shared with Automation
- implement STALE/CONFLICT rejection outcomes
- persist completed/rejected/unresolved outcomes
- expose outcome lookup for workflow verification
- duplicate-delivery and restart tests

**Cut/fallback.** No cut (hard-gate NFR-REL-001 depends on it).


### 9.WP-CORE-004 — Rework, split/merge and temporal genealogy

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-CORE-GENEALOGY |
| Supporting reviewer | Asrın |
| Source requirements | FR-CORE-009, FR-CORE-010, FR-CORE-011, FR-CORE-012 |
| Architecture | ARCH-CORE-DB, ARCH-CORE-DOMAIN, ARCH-CORE-GENEALOGY |
| Gating edges | DEP-029 (DN-CORE-LIFECYCLE, M2 (S4)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, BENCH-RQ1-001, TEST-CORE-GENEALOGY, TEST-CORE-STATEMACHINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- append-only route-visit history
- split/merge relation model
- genealogy/exposure query API (relational, per backfill ADR 12)

**Major tasks.**
- implement ReworkDirective execution without overwriting history
- model split/merge lineage relations
- implement exposure queries used by AI tools
- performance-sanity checks on lineage queries at WP-NORMAL scale

**Cut/fallback.** No cut for F1; full-depth exposure queries are HARD for the full RQ-1 RCA configuration at M4 (05 §15).


### 9.WP-DOC-002 — ADR backfill and decision index

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Yavuz |
| Source requirements | FR-GOV-004 |
| Architecture | ARCH-PLAT-CICD |
| Gating edges | none — early unlocker |
| Verification families | TEST-GOV-TRACELINT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- ADR template and index
- 13 backfill ADRs from 02
- ADR linkage in the trace registry

**Major tasks.**
- mint ADR IDs and write records
- link ADRs to requirements and architecture components
- define when a new ADR is required

**Cut/fallback.** No cut; DECIDED_BY edges in 03 point at minted ADR IDs (GAP-RTM-023 RESOLVED by CHG-029).


### 9.WP-EVT-003 — Idempotent consumer framework

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-EVT-SPINE |
| Supporting reviewer | Batu |
| Source requirements | FR-EVT-005 |
| Architecture | ARCH-EVT-CONSUMER |
| Gating edges | DEP-023 (DN-EVT-CONTRACTS, M1 (S2)), DEP-024 (DN-CORE-OUTBOX, M1 (S2)), DEP-025 (DN-RT-NATS, M1 (S2)) |
| Verification families | AV-SCEN-05, RES-DUP-001, TEST-EVT-CONSUMER-IDEMP |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- processed-message ledger
- consumer base library
- duplicate/out-of-order test suite against real JetStream

**Major tasks.**
- design dedup key and retention
- implement library + adoption in Twin, Vision, AI, Scheduler, Automation consumers
- test duplicate, out-of-order and replayed delivery

**Cut/fallback.** No cut (hard-gate NFR-REL-001).


### 9.WP-EVT-005 — Architecture rules as code (boundaries and ownership)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-EVT-CONTRACTS |
| Supporting reviewer | Yavuz |
| Source requirements | FR-EVT-007 |
| Architecture | ARCH-CORE-DB, ARCH-CTR-API |
| Gating edges | DEP-021 (DN-CORE-CONTRACTS, S1–S2) |
| Verification families | TEST-ARCH-BOUNDARY, TEST-SEC-SVCID |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- rule set implementation
- CI gate
- violation report format

**Major tasks.**
- express boundary rules from 02 as executable checks
- wire into required CI checks
- seed with known allowed exceptions, documented

**Cut/fallback.** No cut; prevents silent architecture erosion (Item 84 rules-as-code).


### 9.WP-TEST-002 — Contract and schema test suites

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-EVT-CONTRACTS |
| Supporting reviewer | Selman |
| Source requirements | FR-EVT-006, NFR-DATA-005 |
| Architecture | ARCH-CTR-CMDSCHEMA, ARCH-CTR-EVTSCHEMA, ARCH-EVT-SCHEMA |
| Gating edges | DEP-021 (DN-CORE-CONTRACTS, S1–S2) |
| Verification families | TEST-DATA-CONTRACTVALID, TEST-EVT-SCHEMA |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- producer/consumer contract suites per IC namespace
- schema validation tests
- compatibility regression tests

**Major tasks.**
- implement consumer-driven contract tests
- validate example fixtures against schemas
- detect breaking changes in CI

**Cut/fallback.** No cut.


### 9.WP-TWIN-002 — Epistemic classes, freshness and staleness semantics

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-TWIN-PROJ |
| Supporting reviewer | Asrın |
| Source requirements | FR-TWIN-003, FR-TWIN-004, FR-TWIN-005, NFR-UX-002 |
| Architecture | ARCH-EDGE-WEB, ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-STATE, ARCH-WORLD-SCOPE |
| Gating edges | DEP-034 (DN-TWIN-SKELETON, S3), DEP-035 (DN-SIM-COREINT, M2 (S4)) |
| Verification families | AV-SCEN-01, AV-SCEN-07, AV-SCEN-09, BENCH-PERF-CORE, TEST-TWIN-EPISTEMIC, TEST-TWIN-FRESHNESS, TEST-UI-SEMANTICS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- epistemic tagging in projection model
- revision/freshness metadata on responses
- sequence-gap detector and stale marking

**Major tasks.**
- define epistemic class per read model field group
- implement freshness computation and exposure
- implement gap detection and degraded marking
- tests with delayed/interrupted event flow

**Cut/fallback.** No cut; honest UI and RCA grounding depend on it.


### 9.WP-TWIN-003 — Twin query API and scheduling snapshot export

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-CORE-SNAPCON |
| Supporting reviewer | Batu |
| Source requirements | FR-TWIN-008, NFR-PERF-001, NFR-PERF-004 |
| Architecture | ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-EVT-CONSUMER, ARCH-SEC-AUTHZ, ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-PROJECTOR |
| Gating edges | DEP-030 (DN-CORE-CONTRACTS, S3) |
| Verification families | AV-SCEN-01, BENCH-PERF-CORE, TEST-AUTH-NEG, TEST-TWIN-READONLY |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- Twin query API (versioned)
- SchedulingSnapshot contract + fixtures
- read scopes per consumer identity

**Major tasks.**
- define query surface from actual consumer needs (05 precise requirements)
- implement snapshot export with revision binding
- enforce read-only scopes
- latency instrumentation

**Cut/fallback.** No cut; snapshot contract is on the E2E-01 readiness gate.


### 9.WP-UI-002 — manufacturing facility state and operational views

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Batu |
| Source requirements | FR-UI-002, NFR-PERF-005 |
| Architecture | ARCH-EDGE-BFF, ARCH-EDGE-NOTIFY, ARCH-EDGE-WEB |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-01, BENCH-PERF-UI, DEMO-GS01-001, TEST-UI-BROWSER |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- manufacturing facility/equipment/lot state views
- world selector
- realtime or polled update path

**Major tasks.**
- implement Twin-backed state views
- implement world scoping in every query
- measure state visibility latency

**Cut/fallback.** No cut (F1).


### 9.WP-AI-001 — Deterministic orchestrator and execution budgets

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-AI-ORCH |
| Supporting reviewer | Yavuz |
| Source requirements | FR-AI-001, FR-AI-012, FR-AI-013 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-CTR-EVTSCHEMA |
| Gating edges | DEP-064 (DN-AI-TOOLCON, S2–S3) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, BENCH-RQ1-001, E2E-01, TEST-AI-BUDGET, TEST-AI-OUTPUT |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- orchestrator state machine
- AgentBudgetProfile enforcement
- structured-output validation gate

**Major tasks.**
- define phases (evidence gathering → hypothesis → assessment)
- implement budget accounting (tool calls, tokens, wall clock)
- implement schema validation before publication
- bounded-termination tests

**Cut/fallback.** No cut (F0). Multi-agent persona architecture stays out of the mandatory path.


### 9.WP-AI-002 — Typed tool registry and authority-tagged tool access

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-AI-TOOLCON |
| Supporting reviewer | Yavuz |
| Source requirements | FR-AI-002, FR-AI-003, FR-SEC-004, FR-SEC-005 |
| Architecture | ARCH-AI-TOOLS, ARCH-SEC-AUTHZ |
| Gating edges | none — early unlocker |
| Verification families | AV-SCEN-01, TEST-AI-TOOLS, TEST-AUTH-NEG, TEST-SEC-AISURFACE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- tool interface definitions + fixtures
- allowlist with READ/SIMULATE/PROPOSE tags
- tool surface inventory test (no shell, no arbitrary SQL)

**Major tasks.**
- define tool schemas against Core/Twin/Vision/RAG capabilities
- implement typed clients with failure semantics
- implement allowlist enforcement
- inventory test proving absent capabilities

**Cut/fallback.** No cut (authority hard gate).


### 9.WP-AI-003 — Structured evidence-grounded RCA output

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-AI-RCA |
| Supporting reviewer | Yavuz |
| Source requirements | FR-AI-005, FR-AI-006, FR-AI-007, FR-AI-008 |
| Architecture | ARCH-AI-ORCH |
| Gating edges | DEP-065 (DN-VIS-OBSCON, E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH, S4), DEP-067 (DN-TWIN-PROJ, E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING, M3 (S6)), DEP-069 (DN-CORE-GENEALOGY, M4 (full RQ-1 RCA config)), DEP-072 (DN-RAG, M4/M5), DEP-077 (DN-AI-ACTCON, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-03, BENCH-RQ1-001, TEST-AI-OUTPUT |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- RootCauseAssessment contract (IC-AI-003)
- hypothesis/evidence separation implementation
- abstention path
- assessment test corpus

**Major tasks.**
- define output schema with evidence references
- implement conflicting/missing evidence representation
- implement INSUFFICIENT_EVIDENCE outcome
- test that tool failure is never treated as negative evidence

**Cut/fallback.** No cut (F1 and RQ-1 core).


### 9.WP-AI-004 — Action proposal and context binding

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-AI-ACTCON |
| Supporting reviewer | Batu |
| Source requirements | FR-AI-009, FR-AI-010 |
| Architecture | ARCH-AI-PROPOSAL, ARCH-TWIN-FRESHNESS |
| Gating edges | DEP-076 (DN-HITL-POLICY, S3–S4) |
| Verification families | AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AI-BINDING, TEST-AUTH-NEG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- Recommendation contract (IC-AI-004)
- binding fields (WorldID, base revision, evidence set)
- binding tests

**Major tasks.**
- define proposal schema with no command semantics
- implement binding capture at proposal time
- verify rejection paths when binding is stale (with Automation)

**Cut/fallback.** No cut; stale-proposal rejection is a hard gate.


### 9.WP-AI-006 — AI authority boundary and negative suite

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-AI-RCA |
| Supporting reviewer | Yavuz |
| Source requirements | FR-AI-004, NFR-SEC-004 |
| Architecture | ARCH-AI-ORCH, ARCH-CORE-CMD, ARCH-HITL-POLICY, ARCH-SEC-AUTHZ |
| Gating edges | DEP-065 (DN-VIS-OBSCON, E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH, S4), DEP-067 (DN-TWIN-PROJ, E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING, M3 (S6)), DEP-069 (DN-CORE-GENEALOGY, M4 (full RQ-1 RCA config)), DEP-072 (DN-RAG, M4/M5), DEP-077 (DN-AI-ACTCON, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-SEC-AUTHZ-NEG, TEST-SEC-SVCID |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- credential/identity separation for the AI service
- Core-side denial of AI principal for mutations
- cross-cutting authority negative suite

**Major tasks.**
- remove any mutation-capable credential from the AI identity
- implement Core authorization denial and tests
- build adversarial attempts (self-approval, forged proposals, credential reuse)
- execute on real INTEGRATION runtime

**Cut/fallback.** No cut (F0, hard gate, RQ-3 core).

**Integration checkpoint.** AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001


### 9.WP-CORE-008 — Core ↔ Simulator ↔ Twin integration and acceptance

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-SIM-COREINT |
| Supporting reviewer | Batu |
| Source requirements | FR-CORE-003, FR-CORE-006, FR-TWIN-010, NFR-REL-010 |
| Architecture | ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-CORE-DOMAIN, ARCH-TWIN-API, ARCH-TWIN-PROJECTOR |
| Gating edges | DEP-040 (DN-SIM-OPSEM, M2 (S4)), DEP-041 (DN-CORE-CMDEXEC, M2 (S4)), DEP-042 (DN-EVT-SPINE, M2 (S4)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, E2E-01, RES-TWINREBUILD-001, TEST-AUTO-OUTCOME, TEST-CORE-IDEMP, TEST-CORE-STATEMACHINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- integration test suite across the three services
- AV-SCEN-01 / AV-SCEN-03 execution scripts
- consistency checker for Core vs Twin at run end

**Major tasks.**
- wire real NATS/PostgreSQL integration environment cases
- implement scenario drivers for normal production and inspection-triggered recovery
- implement end-of-run consistency assertion
- record failures as classified integration findings

**Cut/fallback.** No cut (F0 integrated path, 03 View F).

**Integration checkpoint.** AV-SCEN-01, AV-SCEN-03, E2E-01


### 9.WP-HITL-001 — Authority policy engine (L0–L4)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-HITL-POLICY |
| Supporting reviewer | Batu |
| Source requirements | FR-HITL-001, FR-HITL-002 |
| Architecture | ARCH-HITL-POLICY, ARCH-SEC-AUTHZ |
| Gating edges | none — early unlocker |
| Verification families | AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-HITL-POLICY |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- AuthorityPolicy artifact + evaluator
- risk-class mapping for catalogued actions
- policy tests including adversarial inputs

**Major tasks.**
- define L0–L4 semantics per action class
- implement evaluator with no LLM influence
- test that model output cannot change the required level

**Cut/fallback.** No cut (F0).


### 9.WP-HITL-002 — Approval binding to exact proposal/plan revision and world

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-HITL-APPROVAL |
| Supporting reviewer | Batu |
| Source requirements | FR-HITL-003, FR-HITL-004, FR-HITL-005 |
| Architecture | ARCH-HITL-APPROVAL, ARCH-HITL-EXPIRY, ARCH-WORLD-SCOPE |
| Gating edges | DEP-090 (DN-RT-IDP, E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, E2E-01 (end S5)) |
| Verification families | AV-SCEN-01, AV-SCEN-04, AV-SCEN-10, TEST-HITL-BINDING |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- approval binding fields in ApprovalRequest
- material-change invalidation rule
- binding tests

**Major tasks.**
- define binding key (proposal/plan revision + WorldID + freshness)
- implement invalidation on material change
- test cross-world and cross-revision rejection

**Cut/fallback.** No cut (hard gate).


### 9.WP-HITL-003 — Expiry, replay and staleness rejection

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-HITL-APPROVAL |
| Supporting reviewer | Batu |
| Source requirements | FR-HITL-006, NFR-REL-002 |
| Architecture | ARCH-AUTO-WORKFLOW, ARCH-HITL-APPROVAL, ARCH-HITL-EXPIRY |
| Gating edges | DEP-090 (DN-RT-IDP, E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, E2E-01 (end S5)) |
| Verification families | AV-SCEN-04, AV-SCEN-10, BENCH-RQ3-001, TEST-HITL-REPLAY-NEG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- expiry/nonce handling
- execution-time checks
- negative suite (AV-SCEN-04)

**Major tasks.**
- define expiry policy per risk class
- implement replay protection
- build adversarial approval cases for RQ-3

**Cut/fallback.** No cut (hard gate: accepted stale/replayed protected executions must be zero).


### 9.WP-SEC-003 — Backend authorization enforcement

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M3 · S5–S6 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Yavuz |
| Source requirements | FR-SEC-003 |
| Architecture | ARCH-CORE-CMD, ARCH-SEC-AUTHZ |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | AV-SCEN-04, BENCH-RQ3-001, TEST-SEC-AUTHZ-NEG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- policy enforcement points in Core and Automation
- unknown-permission deny default
- authorization negative suite

**Major tasks.**
- define enforcement points per protected action
- implement deny-by-default evaluation
- test UI-bypass attempts directly against APIs

**Cut/fallback.** No cut (H0: unauthorized protected-action attempts must be rejected 100%).


### 9.WP-TEST-003 — Integration scenarios AV-SCEN-01…04

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-SIM-COREINT |
| Supporting reviewer | Batu |
| Source requirements | FR-CORE-003, FR-AI-004, FR-HITL-006, FR-AUTO-008 |
| Architecture | ARCH-AI-ORCH, ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-HITL-EXPIRY, ARCH-SEC-AUTHZ, ARCH-TWIN-API |
| Gating edges | DEP-040 (DN-SIM-OPSEM, M2 (S4)), DEP-041 (DN-CORE-CMDEXEC, M2 (S4)), DEP-042 (DN-EVT-SPINE, M2 (S4)) |
| Verification families | AV-SCEN-01, AV-SCEN-04, BENCH-E2E-001, BENCH-RQ3-001, RES-WORKER-001, TEST-AUTH-NEG, TEST-CORE-STATEMACHINE, TEST-HITL-REPLAY-NEG, TEST-SEC-SVCID |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- scenario drivers for AV-SCEN-01…04
- expected-outcome definitions held by the evaluator side
- execution reports

**Major tasks.**
- implement inspection-triggered recovery scenario
- implement equipment disruption rescheduling scenario
- implement normal-production no-false-recovery scenario
- implement stale/replayed approval rejection scenario

**Cut/fallback.** No cut (F0 integrated evidence).

**Integration checkpoint.** AV-SCEN-01…04


### 9.WP-TWIN-006 — Effect verification view and Core/Twin consistency

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-TWIN-VERIFY |
| Supporting reviewer | Batu |
| Source requirements | FR-TWIN-010, NFR-REL-010 |
| Architecture | ARCH-AUTO-VERIFY, ARCH-CORE-DOMAIN, ARCH-TWIN-API, ARCH-TWIN-PROJECTOR |
| Gating edges | DEP-036 (DN-TWIN-PROJ, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, E2E-01, RES-TWINREBUILD-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- verification query view
- consistency assertion used at end of closed-loop runs

**Major tasks.**
- define verification predicates per protected action
- implement query with freshness guarantees
- wire into automation verification activity
- assert zero unresolved mismatches per run

**Cut/fallback.** No cut (F0 + hard gate).

**Integration checkpoint.** AV-SCEN-01, BENCH-E2E-001


### 9.WP-UI-006 — Approval Center

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-UI-APPROVAL |
| Supporting reviewer | Batu |
| Source requirements | FR-UI-006, NFR-UX-003 |
| Architecture | ARCH-EDGE-WEB, ARCH-HITL-UI |
| Gating edges | DEP-107 (DN-UI-SHELL, S4), DEP-108 (DN-RT-IDP, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, AV-SCEN-04, DEMO-GS01-001, TEST-UI-BROWSER, TEST-UI-SEMANTICS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- pending/completed approvals view
- bound-context panel (proposal, plan, revision, risk)
- approve/reject flow with authenticated identity

**Major tasks.**
- implement approval list and detail views
- render binding and expiry state
- implement rejection with reason
- test that context is never missing for protected approvals

**Cut/fallback.** No cut (F0 human authority surface).

**Integration checkpoint.** E2E-01, AV-SCEN-04, DEMO-GS01-001


### 9.WP-AI-005 — Provider abstraction, behavior bundle and deterministic baseline

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-AI-PROVIDER |
| Supporting reviewer | Yavuz |
| Source requirements | FR-AI-011, NFR-REP-009, NFR-SEC-009 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-PROVIDER, ARCH-DATA-LINEAGE, ARCH-WORLD-EVALZONE |
| Gating edges | none — early unlocker |
| Verification families | AV-SCEN-11, BENCH-RQ1-001, INSP-AI-BEHAVIOR, INSP-REP-LLM, TEST-SEC-EGRESS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- provider abstraction layer
- AIBehaviorBundle (provider/model/prompt/tool versions)
- deterministic non-LLM baseline path
- egress payload audit

**Major tasks.**
- implement provider interface and configuration
- capture behavior bundle per run
- implement deterministic triage baseline usable in CI and E2E-01
- audit outbound payloads for secrets/oracle/rights-prohibited content

**Cut/fallback.** F2 fallback: the deterministic baseline keeps the product testable without external providers (Item 66 #129).


### 9.WP-HITL-005 — Approval record, audit trail and protected-action coverage

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-HITL-APPROVAL |
| Supporting reviewer | Yavuz |
| Source requirements | FR-HITL-008, NFR-SEC-010 |
| Architecture | ARCH-AUTO-VERIFY, ARCH-HITL-APPROVAL, ARCH-OBS-AUDIT |
| Gating edges | DEP-090 (DN-RT-IDP, E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, E2E-01 (end S5)) |
| Verification families | AV-SCEN-01, TEST-HITL-RECORD, TEST-SEC-AUDIT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- ApprovalRecord schema and storage
- audit chain linking proposal → plan → approval → command → effect
- coverage test for protected actions

**Major tasks.**
- define record fields (decision, subject, binding, actor, timestamp)
- implement audit emission at each hop
- verify 100% coverage on formal protected actions

**Cut/fallback.** No cut; approvals may never exist only in logs (Item 67 #149).


### 9.WP-HITL-006 — Dual approval for highest-risk actions

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-HITL-APPROVAL |
| Supporting reviewer | Batu |
| Source requirements | FR-HITL-009 |
| Architecture | ARCH-HITL-DUAL |
| Gating edges | DEP-090 (DN-RT-IDP, E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, E2E-01 (end S5)) |
| Verification families | BENCH-RQ3-001, TEST-HITL-DUAL |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- dual-approval policy entries
- distinct-identity enforcement
- tests including same-identity attempts

**Major tasks.**
- define which catalogued actions require dual approval
- implement enforcement and UI flow
- test self-duplication rejection

**Cut/fallback.** No cut (F1, Item 68 authority set).


### 9.WP-ML-001 — Feature and label pipeline from operational history

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-SIM-SYNTH |
| Supporting reviewer | Batu |
| Source requirements | FR-ML-007, FR-ML-008 |
| Architecture | ARCH-DATA-LINEAGE |
| Gating edges | DEP-048 (DN-SIM-OPSEM, S3–S4) |
| Verification families | BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001, INSP-DATA-PROVENANCE, INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK, TEST-ML-LEAKAGE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- feature extraction pipeline
- label definitions with time semantics
- partition-aware dataset builder

**Major tasks.**
- define feature windows and time-travel rules (no future information)
- implement label generation per model target
- bind datasets to DatasetVersion/SplitManifest
- implement FINAL partition access guard

**Cut/fallback.** No cut; leakage protection is a hard gate (NFR-DATA-002).


### 9.WP-ML-002 — M1 — equipment risk model

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-ML |
| Supporting reviewer | Selman |
| Source requirements | FR-ML-001 |
| Architecture | ARCH-AI-ORCH, ARCH-DATA-LINEAGE |
| Gating edges | DEP-074 (DN-SIM-SYNTH, M4 (S8)), DEP-075 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-ML-M1-001, TEST-ML-CONTRACT |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- M1 ModelPackage
- baseline comparison
- evaluation results on frozen splits

**Major tasks.**
- define target and horizon
- train baseline then candidate model
- evaluate discrimination and calibration separately
- package with lineage

**Cut/fallback.** No cut (F1, Item 68 #66).


### 9.WP-ML-003 — M2 — cycle-time / tardiness risk model

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-ML |
| Supporting reviewer | Batu |
| Source requirements | FR-ML-002 |
| Architecture | ARCH-AI-ORCH, ARCH-DATA-LINEAGE |
| Gating edges | DEP-074 (DN-SIM-SYNTH, M4 (S8)), DEP-075 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-ML-M2-001, TEST-ML-CONTRACT, TEST-ML-LEAKAGE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- M2 ModelPackage
- baseline comparison
- evaluation results

**Major tasks.**
- define target and feature set
- train and evaluate against naive baselines
- check horizon-specific leakage
- package with lineage

**Cut/fallback.** No cut (F1).


### 9.WP-ML-004 — M3 — pre-inspection quality risk model

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-ML |
| Supporting reviewer | Selman |
| Source requirements | FR-ML-003 |
| Architecture | ARCH-AI-ORCH, ARCH-DATA-LINEAGE |
| Gating edges | DEP-074 (DN-SIM-SYNTH, M4 (S8)), DEP-075 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-ML-M3-001, TEST-ML-CONTRACT, TEST-ML-LEAKAGE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- M3 ModelPackage
- baseline comparison
- evaluation results

**Major tasks.**
- define target aligned with inspection outcomes
- ensure no inspection-outcome leakage into features
- train, evaluate, package

**Cut/fallback.** No cut (F1).


### 9.WP-ML-005 — Common prediction contract and publication

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-ML |
| Supporting reviewer | Yavuz |
| Source requirements | FR-ML-004, FR-ML-005 |
| Architecture | ARCH-AI-ORCH, ARCH-CTR-EVTSCHEMA, ARCH-DATA-LINEAGE |
| Gating edges | DEP-074 (DN-SIM-SYNTH, M4 (S8)), DEP-075 (DN-RT-MLFLOW, M4/M5) |
| Verification families | INSP-AI-BEHAVIOR, TEST-EVT-SCHEMA, TEST-ML-CONTRACT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- IC-AI-002 Prediction contract
- prediction publication path
- contract tests

**Major tasks.**
- define common prediction envelope (target, value, uncertainty, model identity, input revision)
- implement serving and event publication
- validate schema at boundaries

**Cut/fallback.** No cut; consumers must not integrate three bespoke shapes.


### 9.WP-RAG-001 — Documentary corpus governance and ingestion

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-RAG-CORPUS |
| Supporting reviewer | Yavuz |
| Source requirements | FR-RAG-001, FR-RAG-009 |
| Architecture | ARCH-AI-RAG, ARCH-DATA-LINEAGE, ARCH-DATA-PG, ARCH-DATA-VECTOR |
| Gating edges | none — early unlocker |
| Verification families | AV-SCEN-01, BENCH-RAG-001, BENCH-RQ1-001, INSP-AI-BEHAVIOR, TEST-RAG-RETRIEVAL |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- DocumentVersion/CorpusVersion model
- ingestion/chunking pipeline
- corpus registry in PostgreSQL

**Major tasks.**
- define corpus sources and licence status
- implement ingestion with stable chunk identity
- record corpus version for experiment binding
- exclude rights-prohibited content

**Cut/fallback.** No cut; RAG is mandatory F1 for the final RCA configuration.


### 9.WP-RAG-002 — Retrieval profiles: sparse, dense and hybrid

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-RAG |
| Supporting reviewer | Yavuz |
| Source requirements | FR-RAG-003, FR-RAG-004, FR-RAG-005, NFR-PERF-006 |
| Architecture | ARCH-AI-RAG, ARCH-DATA-VECTOR |
| Gating edges | DEP-070 (DN-RAG-CORPUS, S3–S4), DEP-071 (DN-RT-QDRANT, M4 (S8)) |
| Verification families | BENCH-PERF-AI, BENCH-RAG-001, BENCH-RQ1-001, TEST-RAG-RETRIEVAL |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- sparse retrieval implementation
- dense retrieval with selected embedding model
- hybrid fusion via Qdrant native support
- RetrievalProfile artifact

**Major tasks.**
- define profile parameters (k, weights, filters)
- implement and test each mode on a fixed corpus
- instrument retrieval latency
- prepare ablation switches for the RQ-1 lane

**Cut/fallback.** No cut for F1 modes; ColBERT/late-interaction stays R2 and must not be assumed here.


### 9.WP-RAG-003 — Citation-bearing provenance in retrieval and RCA

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-RAG |
| Supporting reviewer | Asrın |
| Source requirements | FR-RAG-006, FR-RAG-010 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-RAG |
| Gating edges | DEP-070 (DN-RAG-CORPUS, S3–S4), DEP-071 (DN-RT-QDRANT, M4 (S8)) |
| Verification families | AV-SCEN-01, BENCH-RAG-001, BENCH-RQ1-001, TEST-AI-OUTPUT, TEST-RAG-PROVENANCE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- chunk provenance fields
- EvidenceRef resolution in RCA output
- citation validation tests

**Major tasks.**
- bind chunk → DocumentVersion + span
- implement evidence reference resolution
- reject fabricated or unresolvable references

**Cut/fallback.** No cut; grounding claims depend on resolvable citations.


### 9.WP-RAG-004 — Rights filtering and prompt-injection resistance

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-RAG |
| Supporting reviewer | Yavuz |
| Source requirements | FR-RAG-007, FR-RAG-008, FR-SEC-009 |
| Architecture | ARCH-AI-RAG, ARCH-AI-TOOLS, ARCH-SEC-AUTHZ |
| Gating edges | DEP-070 (DN-RAG-CORPUS, S3–S4), DEP-071 (DN-RT-QDRANT, M4 (S8)) |
| Verification families | BENCH-RQ3-001, TEST-AUTH-NEG, TEST-RAG-INJECTION, TEST-RAG-RIGHTS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- eligibility/rights query filter
- prompt assembly isolation of retrieved content
- negative suite (injection, ineligible source)

**Major tasks.**
- implement metadata filter at query time
- isolate retrieved text from policy/authority context
- build adversarial corpus cases
- prove policy cannot be overridden by document content

**Cut/fallback.** No cut (authority hard gate; feeds RQ-3 adversarial cases).


### 9.WP-RAG-005 — Evidence typing: documentary vs operational

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-RAG |
| Supporting reviewer | Asrın |
| Source requirements | FR-RAG-002 |
| Architecture | ARCH-AI-RAG, ARCH-DATA-VECTOR |
| Gating edges | DEP-070 (DN-RAG-CORPUS, S3–S4), DEP-071 (DN-RT-QDRANT, M4 (S8)) |
| Verification families | TEST-AI-OUTPUT, TEST-ARCH-BOUNDARY |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- evidence class taxonomy in IC-AI-001
- type enforcement in RCA assembly
- tests for mixed-evidence cases

**Major tasks.**
- define evidence classes and required fields
- enforce typing at contract boundary
- verify UI and analysis preserve the distinction

**Cut/fallback.** No cut.


### 9.WP-TWIN-005 — Counterfactual/what-if stream isolation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-TWIN-PROJ |
| Supporting reviewer | Batu |
| Source requirements | FR-TWIN-007, NFR-CAP-010 |
| Architecture | ARCH-TWIN-STATE, ARCH-WORLD-ISOLATION, ARCH-WORLD-REGISTRY |
| Gating edges | DEP-034 (DN-TWIN-SKELETON, S3), DEP-035 (DN-SIM-COREINT, M2 (S4)) |
| Verification families | AV-SCEN-09, AV-SCEN-10, BENCH-CAP-ENV, TEST-TWIN-EPISTEMIC |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- separate projection family per WorldID
- isolation test suite (AV-SCEN-09, AV-SCEN-10)

**Major tasks.**
- implement world-scoped storage and query filters
- test cross-world read/write rejection
- verify ≥5 concurrent isolated worlds

**Cut/fallback.** No cut; counterfactual scheduling (RQ-2) depends on it.


### 9.WP-UI-004 — Incident investigation workspace (RCA)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Selman |
| Source requirements | FR-UI-004 |
| Architecture | ARCH-EDGE-WEB |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-01, DEMO-GS01-001, TEST-UI-BROWSER |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- assessment view with evidence panels
- evidence reference navigation
- abstention/insufficient-evidence presentation

**Major tasks.**
- design view model from IC-AI-003
- implement evidence drill-down to source records
- present conflicting evidence explicitly

**Cut/fallback.** No cut (F1).


### 9.WP-ML-006 — Calibration and uncertainty evaluation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-ML |
| Supporting reviewer | Selman |
| Source requirements | FR-ML-006 |
| Architecture | ARCH-AI-ORCH |
| Gating edges | DEP-074 (DN-SIM-SYNTH, M4 (S8)), DEP-075 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- calibration artifacts per model
- calibration evaluation results
- uncertainty fields in contract

**Major tasks.**
- implement calibration on CAL partition
- evaluate calibration quality separately from discrimination
- bind calibration artifact to ModelPackage

**Cut/fallback.** No cut (Item 68 #69).


### 9.WP-RAG-006 — Index rebuild and recovery

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-RT-QDRANT |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-REC-009 |
| Architecture | ARCH-AI-RAG, ARCH-DATA-VECTOR |
| Gating edges | DEP-013 (DN-PLAT-INTEG, M4 (S8)) |
| Verification families | RES-IDXREBUILD-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- rebuild job from CorpusVersion artifacts
- rebuild drill record
- RecoveryDependencyGraph entry

**Major tasks.**
- implement deterministic re-indexing
- measure rebuild duration at final corpus size
- document operator procedure

**Cut/fallback.** No cut; Qdrant holds no unique canonical data by design.


### 9.WP-RES-002 — Partition, seed and protocol governance

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M5 · S9–S10 |
| Readiness node | DN-RES-DATASCEN |
| Supporting reviewer | Selman |
| Source requirements | FR-EVAL-002, NFR-DATA-002 |
| Architecture | ARCH-DATA-LINEAGE |
| Gating edges | DEP-121 (DN-SIM-SYNTH, M5 (S10)), DEP-122 (DN-VIS-SPLIT, M5 (S10)), DEP-123 (DN-RAG-CORPUS, M5 (S10)) |
| Verification families | BENCH-FBC-001, INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- partition and seed namespace definitions
- FINAL access guard in the runner
- partition audit report

**Major tasks.**
- define partitions per research lane
- implement seed namespace allocation
- implement guard preventing FINAL use before the protocol freeze
- audit for entity/group overlap

**Cut/fallback.** No cut (hard gate).


### 9.WP-RES-006 — Baseline suite across lanes

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M5 · S9–S10 |
| Readiness node | DN-RES-BASELINES |
| Supporting reviewer | Batu |
| Source requirements | FR-SCH-010, FR-AI-001, FR-VIS-002 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-SCH-HEURISTIC, ARCH-VIS-EVAL, ARCH-VIS-INFER |
| Gating edges | DEP-124 (DN-RES-DATASCEN, M5 (S10)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, BENCH-RQ1-001, BENCH-RQ2-001, BENCH-SCH-001, BENCH-VIS-001, E2E-01, TEST-AI-OUTPUT, TEST-VIS-PIPELINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- RCA baselines (RCA-B1…B5)
- scheduler baselines
- Vision and ML baselines
- BaselineRun records

**Major tasks.**
- implement each baseline as a runnable configuration
- execute on DEV/CAL partitions
- record results before calibration (Item 66 #83)

**Cut/fallback.** No cut (R1); literature numbers are context, never a substitute for a local BaselineRun.


### 9.WP-TWIN-004 — Twin rebuild and catch-up

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-TWIN-PROJ |
| Supporting reviewer | Yavuz |
| Source requirements | FR-TWIN-006, NFR-REC-008 |
| Architecture | ARCH-TWIN-REBUILD |
| Gating edges | DEP-034 (DN-TWIN-SKELETON, S3), DEP-035 (DN-SIM-COREINT, M2 (S4)) |
| Verification families | AV-SCEN-08, RES-TWINREBUILD-001, TEST-TWIN-PROJECTION |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- rebuild job
- RecoveryDependencyGraph entry for Twin
- rebuild drill script (AV-SCEN-08)

**Major tasks.**
- implement full and partial rebuild modes
- measure rebuild duration at benchmark-scale data
- document operator procedure

**Cut/fallback.** No cut; recovery evidence at M5/M7 depends on it.


### 9.WP-UI-008 — Epistemic, staleness and failure-state semantics

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Selman |
| Source requirements | FR-UI-008, NFR-UX-001, NFR-UX-002, NFR-UX-004 |
| Architecture | ARCH-EDGE-BFF, ARCH-EDGE-WEB, ARCH-TWIN-FRESHNESS |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-07, AV-SCEN-09, DEMO-GS01-001, TEST-UI-SEMANTICS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- visual encoding system for epistemic classes
- staleness indicators
- failure/timeout presentation patterns

**Major tasks.**
- define encoding that is not colour-only
- implement staleness propagation from Twin freshness
- replace indefinite spinners with explicit failure states
- review pass across all primary views

**Cut/fallback.** No cut (usability hard-gate family).


### 9.WP-UI-010 — Incident and decision timeline

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Yavuz |
| Source requirements | FR-UI-010 |
| Architecture | ARCH-EDGE-WEB, ARCH-OBS-AUDIT, ARCH-OBS-TRACE |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-01, DEMO-GS01-001, TEST-UI-BROWSER |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- timeline view built on CorrelationID
- cross-record navigation
- export/share view for reviews

**Major tasks.**
- define timeline view model from correlated records
- implement navigation between observation, assessment, plan, approval, workflow and effect
- test with real GS-01 run data

**Cut/fallback.** No cut (F1).


### 9.WP-GOV-004 — Change control and freeze-impact tooling

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M6 · S11 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Yavuz |
| Source requirements | FR-GOV-007, NFR-GOV-008 |
| Architecture | ARCH-PLAT-CICD |
| Gating edges | none — early unlocker |
| Verification families | INSP-GOV-CHANGECTRL, TEST-GOV-TRACELINT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- requirement-change PR template
- freeze-impact review record format
- post-M6 change gate in CI

**Major tasks.**
- define change classes and required reviewers
- implement freeze window detection from milestone state
- link change records to trace edges and affected evidence

**Cut/fallback.** No cut; the gate may be manual (checklist) before automation.


### 9.WP-ML-007 — ML evaluation lanes (M1/M2/M3) for the final campaign

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-ML |
| Supporting reviewer | Yavuz |
| Source requirements | FR-ML-001, FR-ML-002, FR-ML-003 |
| Architecture | ARCH-AI-ORCH, ARCH-DATA-LINEAGE |
| Gating edges | DEP-074 (DN-SIM-SYNTH, M4 (S8)), DEP-075 (DN-RT-MLFLOW, M4/M5) |
| Verification families | BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001, TEST-ML-CONTRACT, TEST-ML-LEAKAGE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- per-model experiment definitions
- metric calculators
- FINAL execution scripts

**Major tasks.**
- define per-lane protocol (metrics, seeds, baselines)
- dry-run on DEV/CAL
- freeze protocol before M6

**Cut/fallback.** R1: results may be negative; lanes remain separate and are never averaged into one score.


### 9.WP-RAG-007 — Retrieval ablation lane for RQ-1

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-RAG |
| Supporting reviewer | Yavuz |
| Source requirements | FR-RAG-009 |
| Architecture | ARCH-AI-RAG, ARCH-DATA-LINEAGE |
| Gating edges | DEP-070 (DN-RAG-CORPUS, S3–S4), DEP-071 (DN-RT-QDRANT, M4 (S8)) |
| Verification families | BENCH-RAG-001, BENCH-RQ1-001, INSP-AI-BEHAVIOR |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- ablation configuration set
- lane experiment definition
- DEV/CAL dry-run results

**Major tasks.**
- define ablation arms bound to CorpusVersion + RetrievalProfile
- implement switchable configuration in the runner
- dry-run and freeze before M6

**Cut/fallback.** R1: ablation outcome may show limited benefit; that is a publishable result, not a failure to hide.


### 9.WP-RES-004 — AnalysisPackage and deterministic result regeneration

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-RES-ANALYSIS |
| Supporting reviewer | Yavuz |
| Source requirements | FR-EVAL-006, NFR-REP-002 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-OBJ |
| Gating edges | DEP-143 (DN-RES-BENCH, M7 (S12)), DEP-144 (DN-FRZ-PROTOCOL, M7 (S12)) |
| Verification families | BENCH-FBC-001, INSP-EVAL-CLAIMS, TEST-EVAL-ANALYSIS, TEST-REP-ANALYSIS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- AnalysisPackage (metric calculators, statistical tests, table/figure generators)
- deterministic serialization/rounding rules
- regeneration test

**Major tasks.**
- implement metric calculators per lane
- implement statistical procedures agreed in the protocol
- verify identical regeneration from the same raw inputs

**Cut/fallback.** No cut (R1).


### 9.WP-RES-007 — RQ-1 lane: evidence-grounded RCA evaluation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-FRZ-RQ1CORPUS |
| Supporting reviewer | Yavuz |
| Source requirements | FR-AI-005, FR-AI-008, FR-RAG-010 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-RAG |
| Gating edges | DEP-146 (DN-RAG, M5→M6) |
| Verification families | AV-SCEN-01, AV-SCEN-03, BENCH-RQ1-001, TEST-AI-OUTPUT, TEST-RAG-PROVENANCE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- RQ-1 experiment definition
- case set with evaluator-held ground truth
- robustness protocol (30 cases × 5 generations)
- FINAL execution scripts

**Major tasks.**
- define scoring rubric and grounding metrics
- freeze corpus and behavior bundle before M6
- dry-run on DEV/CAL
- execute in FBC-01

**Cut/fallback.** R1: NOT_SUPPORTED and INCONCLUSIVE are valid outcomes.


### 9.WP-RES-009 — RQ-3 lane: governed AI-to-action evaluation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-FRZ-RQ3AUTH |
| Supporting reviewer | Batu |
| Source requirements | FR-HITL-001, FR-AI-004, FR-AUTO-004 |
| Architecture | ARCH-AI-ORCH, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-HITL-EXPIRY, ARCH-HITL-POLICY, ARCH-SEC-AUTHZ |
| Gating edges | DEP-147 (DN-HITL-POLICY, M5→M6) |
| Verification families | AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-AUTO-FRESHNESS, TEST-HITL-POLICY, TEST-SEC-SVCID |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- authority scenario set
- adversarial case generator
- policy-arm execution harness

**Major tasks.**
- define adversarial classes (stale, revision mismatch, duplicate, replay, malformed, forbidden, lost ACK, expired approval)
- hold the same proposal set across policy arms
- freeze the set before M6
- execute in FBC-01

**Cut/fallback.** R1 with a hard safety gate: zero executed high-risk invariant violations.


### 9.WP-RES-011 — Freeze execution for M6

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-FRZ-PROTOCOL |
| Supporting reviewer | Yavuz |
| Source requirements | FR-EVAL-002, FR-RAG-009, FR-AI-011 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-PROVIDER, ARCH-AI-RAG, ARCH-DATA-LINEAGE |
| Gating edges | DEP-135 (DN-FRZ-DATA, M6 (S11)), DEP-136 (DN-FRZ-MODEL, M6 (S11)), DEP-137 (DN-FRZ-RQ3AUTH, M6 (S11)), DEP-138 (DN-SIM-REALISM, M6 (S11)), DEP-151 (DN-VIS-EPISODES, M6), DEP-154 (DN-SCH-CF, M6) |
| Verification families | BENCH-FBC-001, BENCH-RAG-001, BENCH-RQ1-001, INSP-AI-BEHAVIOR, INSP-EVAL-PARTITION, INSP-REP-LLM, TEST-DATA-SPLITLEAK |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- freeze records per artifact class
- ExperimentProtocolFreeze document
- freeze verification checklist

**Major tasks.**
- collect and verify every freeze prerequisite (05 §9)
- record immutable identities
- verify no critical research dependency remains TBD

**Cut/fallback.** No cut; M6 cannot pass with an open behavioural dependency.


### 9.WP-AI-007 — RCA path performance characterization

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M7 · S12 |
| Readiness node | DN-AI-RCA |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-PERF-007 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-PROVIDER |
| Gating edges | DEP-065 (DN-VIS-OBSCON, E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH, S4), DEP-067 (DN-TWIN-PROJ, E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING, M3 (S6)), DEP-069 (DN-CORE-GENEALOGY, M4 (full RQ-1 RCA config)), DEP-072 (DN-RAG, M4/M5), DEP-077 (DN-AI-ACTCON, E2E-01 readiness (end S4)) |
| Verification families | BENCH-PERF-AI, INSP-REP-LLM |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- latency decomposition instrumentation
- measurement protocol
- recorded results

**Major tasks.**
- instrument phases (retrieval, tool calls, generation)
- define protocol excluding provider outages
- record distributions bound to profiles

**Cut/fallback.** A1: threshold applies to the system path; provider variance is characterized, not hidden.


### 9.WP-BENCH-002 — Final E2E matrix execution (MC-1)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M7 · S12 |
| Readiness node | DN-RES-BENCH |
| Supporting reviewer | Batu |
| Source requirements | FR-VIS-016, FR-AUTO-014, NFR-PERF-013, NFR-OBS-003 |
| Architecture | ARCH-AI-ORCH, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-OBS-TELEMETRY, ARCH-OBS-TRACE, ARCH-SCH-ENGINE, ARCH-SIM-ENGINE, ARCH-TWIN-API, ARCH-VIS-INFER |
| Gating edges | DEP-120 (DN-PLAT-CLEANREPRO, M7 (S12)), DEP-141 (DN-FRZ-RELEASE, M7 (S12)), DEP-142 (DN-ART-HWPROF, M7 (S12)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, BENCH-PERF-WF, DEMO-GS01-001, E2E-01, TEST-OBS-TRACEPROP |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- E2E matrix execution scripts
- per-run evidence capture
- closed-loop outcome metrics

**Major tasks.**
- freeze scenario definitions
- execute 80 base instances with identity binding
- capture traces and verification outcomes

**Cut/fallback.** No cut (R1).

**Integration checkpoint.** BENCH-E2E-001


### 9.WP-CORE-006 — Core and Twin read/command performance profile

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (S2) · M7 · S12 |
| Readiness node | DN-CORE-CMDEXEC |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-PERF-001, NFR-PERF-002, NFR-CAP-005 |
| Architecture | ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-TWIN-API |
| Gating edges | DEP-027 (DN-CORE-CMDCON, S2–S3), DEP-028 (DN-CORE-TRANSITIONS, E2E-01 readiness (end S4)) |
| Verification families | BENCH-PERF-CORE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- benchmark definitions for read/command paths
- measurement harness integration
- recorded distributions (p50/p95/p99) bound to Release/Env/HW/Workload

**Major tasks.**
- define sampling, warm-up and observation-count rules (≥100 observations)
- implement load driver for WP-NORMAL
- run and record; no threshold tuning after the fact

**Cut/fallback.** S2 class: MISS is a valid recorded outcome with analysis, never a silent adjustment.


### 9.WP-DOC-003 — Thesis and portfolio artifact production

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M8 · S13 |
| Readiness node | DN-RES-CLAIMS |
| Supporting reviewer | Selman |
| Source requirements | FR-EVAL-010 |
| Architecture | ARCH-DATA-LINEAGE |
| Gating edges | DEP-145 (DN-RES-ANALYSIS, M7→M8) |
| Verification families | BENCH-FBC-001, INSP-EVAL-CLAIMS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- thesis figure/table generation from AnalysisPackage
- claim-to-evidence mapping appendix
- portfolio metric export

**Major tasks.**
- generate all numbers from sealed analysis outputs
- write method/limitations sections bounded by achieved evidence tiers
- review claim wording against forbidden-claim list

**Cut/fallback.** No cut (R1).


### 9.WP-DOC-004 — Demo infrastructure and GS-01 rehearsal

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M8 · S13 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Yavuz |
| Source requirements | FR-UI-009, NFR-UX-006, NFR-PERF-013 |
| Architecture | ARCH-AI-ORCH, ARCH-AUTO-WORKFLOW, ARCH-EDGE-PRESENT, ARCH-EDGE-WEB, ARCH-OBS-HEALTH, ARCH-PLAT-RELEASE, ARCH-SCH-ENGINE, ARCH-TWIN-API, ARCH-VIS-INFER |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | BENCH-E2E-001, BENCH-PERF-WF, DEMO-GS01-001, TEST-UI-DIAG, TEST-UI-SEMANTICS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- DemoManifest and pinned release
- GS-01 rehearsal script and abort conditions
- demo evidence capture (EXP-DEMO)

**Major tasks.**
- define demo environment and world provisioning
- rehearse the full GS-01 path
- define hard abort conditions (wrong release, test-auth enabled, oracle violation, authority bypass, unverified effect)
- capture demo run evidence separately from statistical evidence

**Cut/fallback.** No cut; demo evidence never substitutes evaluation evidence.

**Integration checkpoint.** DEMO-GS01-001


### 9.WP-DOC-006 — Final red-team review execution

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M8 · S13 |
| Readiness node | DN-RES-CLAIMS |
| Supporting reviewer | Yavuz |
| Source requirements | FR-GOV-010, NFR-GOV-009 |
| Architecture | ARCH-DATA-OBJ, ARCH-PLAT-CICD |
| Gating edges | DEP-145 (DN-RES-ANALYSIS, M7→M8) |
| Verification families | INSP-GOV-ACCEPT, TEST-GOV-TRACELINT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- red-team finding register (RTF-*)
- claim-vs-evidence audit
- resolution records for critical findings

**Major tasks.**
- review every major claim against sealed evidence
- probe authority, oracle and reproducibility boundaries
- resolve or explicitly accept each critical finding before M8

**Cut/fallback.** No cut; M8 requires critical red-team resolutions.


### 9.WP-RES-012 — Research claim classification

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M8 · S13 |
| Readiness node | DN-RES-CLAIMS |
| Supporting reviewer | Selman |
| Source requirements | FR-EVAL-009, FR-EVAL-010 |
| Architecture | ARCH-DATA-LINEAGE |
| Gating edges | DEP-145 (DN-RES-ANALYSIS, M7→M8) |
| Verification families | BENCH-FBC-001, INSP-EVAL-CLAIMS, TEST-EVAL-ANALYSIS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- claim classification procedure (SUPPORTED / PARTIAL / NOT_SUPPORTED / INCONCLUSIVE)
- ThesisClaimRegister entries
- PortfolioMetricExport

**Major tasks.**
- implement derivation from AnalysisPackage outputs
- record claim → evidence references
- produce exports for thesis/portfolio

**Cut/fallback.** No cut (R1); claim wording is bounded by the achieved evidence tier.


### 9.WP-UI-011 — Browser E2E harness and compatibility validation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (S2) · M8 · S13 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-UX-005 |
| Architecture | ARCH-EDGE-WEB |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | TEST-UI-BROWSER |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- browser E2E suite for primary flows
- CI/INTEGRATION execution wiring
- recorded browser versions in evidence

**Major tasks.**
- select flows: state view, inspection, RCA, plan, approval, workflow
- implement suite against real backend (no mocked BFF)
- record versions and results at M8

**Cut/fallback.** S2: MISS on a secondary browser is recorded, not silently dropped.


### 9.WP-UI-012 — Presenter mode integrity

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M8 · S13 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-UX-006 |
| Architecture | ARCH-EDGE-PRESENT |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | DEMO-GS01-001, TEST-UI-SEMANTICS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- presenter mode implementation
- integrity tests proving no concealment
- demo rehearsal checklist entry

**Major tasks.**
- define what presenter mode may change (layout, density) and may not (semantics)
- implement and test against the GS-01 rehearsal
- verify with the demo abort conditions

**Cut/fallback.** No cut; the demo must not be able to lie.


### 9.WP-R2-001 — R2 retrieval candidates (ColBERT, cross-encoder reranking, alternative embeddings)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R2 · — · unscheduled |
| Readiness node | DN-RAG |
| Supporting reviewer | Yavuz |
| Source requirements | FR-RAG-005 |
| Architecture | ARCH-AI-RAG, ARCH-DATA-VECTOR |
| Gating edges | DEP-070 (DN-RAG-CORPUS, S3–S4), DEP-071 (DN-RT-QDRANT, M4 (S8)) |
| Verification families | BENCH-RAG-001, BENCH-RQ1-001, TEST-RAG-RETRIEVAL |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- candidate implementations behind configuration switches
- ablation results on DEV/CAL partitions
- promotion recommendation or rejection record

**Major tasks.**
- implement candidates without touching mandatory defaults
- evaluate against the frozen baseline configuration
- document cost/benefit and resource impact

**Cut/fallback.** First to be cut under schedule pressure. Cannot enter any mandatory path or critical path without formal promotion (DEP-INV-20).


### 9.WP-R2-002 — R2 modelling candidates (local LLM runtime, VLM experiment, advanced causal RCA, RL scheduler, alternative solver formulations)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R2 · — · unscheduled |
| Readiness node | DN-AI-ORCH |
| Supporting reviewer | Batu |
| Source requirements | FR-AI-001, FR-SCH-009 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-SCH-ENGINE |
| Gating edges | DEP-064 (DN-AI-TOOLCON, S2–S3) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, BENCH-PERF-SCH, BENCH-RQ1-001, BENCH-SCH-001, E2E-01, TEST-AI-OUTPUT, TEST-SCH-CONSTRAINTS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- isolated experiment branches/configurations
- evaluation notes with negative results retained
- promotion or rejection records

**Major tasks.**
- scope each candidate to a bounded experiment
- run only on DEV/CAL partitions
- record outcomes regardless of direction

**Cut/fallback.** Cut first; failure does not make the product incomplete (Item 68 #4).


### 9.WP-S-001 — Stretch enhancements register (visualization, mobile UI, multi-node, analytics, extra scenarios)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | S · — · unscheduled |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Selman |
| Source requirements | FR-UI-002 |
| Architecture | ARCH-EDGE-BFF, ARCH-EDGE-NOTIFY, ARCH-EDGE-WEB |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-01, DEMO-GS01-001, TEST-UI-BROWSER |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- stretch register with rationale per item
- entry criteria (only after M8 scope is safe)

**Major tasks.**
- maintain the register from Item 68 §V
- review at milestone boundaries only
- never schedule against mandatory capacity

**Cut/fallback.** Entire package is cuttable by definition; nothing here is required for final acceptance.


### 9.WP-X-001 — Out-of-scope boundary maintenance

| Field | Value |
|---|---|
| Scope / milestone / sprint window | S · — · unscheduled |
| Readiness node | DN-RES-CLAIMS |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-GOV-010 |
| Architecture | ARCH-PLAT-CICD |
| Gating edges | DEP-145 (DN-RES-ANALYSIS, M7→M8) |
| Verification families | INSP-GOV-ACCEPT, TEST-GOV-TRACELINT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- out-of-scope register from Item 68 §VI
- claim-wording checklist used in reviews

**Major tasks.**
- review new proposals against the register
- check thesis/demo wording for scope creep

**Cut/fallback.** Not schedulable work; a standing guard rail.


### 9.SUP Supporting-reviewer packages (86)

Packages owned by others where this role is the named reviewer — review capacity must be planned, not improvised.

| Work package | Title | Owner | Milestone |
|---|---|---|---|
| WP-GOV-002 | Trace registry, edges and trace linter | Yavuz | M2 |
| WP-GOV-003 | Coverage reports and release acceptance record generation | Yavuz | M5 |
| WP-CORE-004 | Rework, split/merge and temporal genealogy | Asrın | M2 |
| WP-EVT-004 | Replay, poison message and DLQ operations | Yavuz | M5 |
| WP-EVT-006 | Event spine throughput and delivery characterization | Yavuz | M7 |
| WP-TWIN-002 | Epistemic classes, freshness and staleness semantics | Asrın | M2 |
| WP-SIM-001 | Deterministic DES kernel | Batu | M1 |
| WP-SIM-003 | Operational semantics: reentrant routing, queues, failures, maintenance, rework | Batu | M2 |
| WP-SIM-006 | External dispatch decision interface and operational telemetry | Batu | M2 |
| WP-SIM-007 | Scenario versioning and synthetic operational history | Batu | M4 |
| WP-SIM-009 | Simulation realism validation suite (RL-3) | Batu | M6 |
| WP-VIS-001 | Inspection pipeline and serving path | Selman | M2 |
| WP-VIS-002 | Defect classification and localization models | Selman | M4 |
| WP-VIS-004 | OOD / UNKNOWN handling and threshold policy | Selman | M4 |
| WP-VIS-005 | Provenance, confidence and calibration in Vision outputs | Selman | M4 |
| WP-VIS-006 | SerializedComponent spatial pattern and cluster analysis | Selman | M4 |
| WP-VIS-007 | Vision-to-loop integration (perception drives RCA) | Selman | M3 |
| WP-VDATA-001 | Dataset governance, rights and provenance | Selman | M4 |
| WP-VDATA-002 | Split manifests and leakage protection | Selman | M5 |
| WP-VDATA-005 | Vision evaluation portfolio and RQ-4 lane preparation | Selman | M6 |
| WP-RAG-003 | Citation-bearing provenance in retrieval and RCA | Asrın | M4 |
| WP-RAG-005 | Evidence typing: documentary vs operational | Asrın | M4 |
| WP-SCH-001 | Dispatch baselines and scheduling instance model | Batu | M2 |
| WP-SCH-002 | Snapshot consumption and recovery plan contract | Batu | M3 |
| WP-SCH-003 | CP-SAT model and hard constraints | Batu | M4 |
| WP-SCH-004 | Rolling horizon and event-triggered rescheduling | Batu | M4 |
| WP-SCH-006 | Counterfactual schedule evaluation on forked worlds | Batu | M4 |
| WP-SCH-007 | Schedule churn and stability metrics | Batu | M5 |
| WP-VALID-001 | Independent schedule validator | Batu | M3 |
| WP-VALID-002 | Execution eligibility gate and AI-origin plan routing | Batu | M3 |
| WP-AUTO-002 | Idempotency and restart safety for protected effects | Batu | M4 |
| WP-AUTO-003 | Pre-execution revalidation and command identity | Batu | M3 |
| WP-AUTO-004 | ActionCatalog and authorization gate | Batu | M3 |
| WP-AUTO-005 | Outcome model and effect verification | Batu | M3 |
| WP-AUTO-006 | Workflow history and audit surface | Batu | M5 |
| WP-AUTO-007 | GS-01 recovery workflow and closed-loop timing | Batu | M4 |
| WP-HITL-004 | Identity-bound approvals | Yavuz | M3 |
| WP-HITL-007 | Break-glass path with mandatory audit | Yavuz | M5 |
| WP-UI-003 | Inspection viewer with overlays | Selman | M4 |
| WP-UI-005 | Planning and validation views | Batu | M4 |
| WP-UI-007 | Workflow progress and verification view | Batu | M4 |
| WP-UI-009 | System health and environment diagnostics view | Yavuz | M4 |
| WP-PLAT-001 | Compose profiles and mandatory runtime composition | Yavuz | M1 |
| WP-PLAT-002 | mfgctl developer and operator CLI | Yavuz | M1 |
| WP-PLAT-004 | Resource profiles and footprint control | Yavuz | M5 |
| WP-PLAT-005 | Environment, release and world manifests | Yavuz | M5 |
| WP-PLAT-006 | Onboarding, executable documentation and diagnostics | Yavuz | M8 |
| WP-CICD-001 | CI pipeline and required gates | Yavuz | M0 |
| WP-CICD-002 | CD to INTEGRATION with immutable artifacts | Yavuz | M1 |
| WP-CICD-003 | Automated migration execution in the deployment path | Yavuz | M2 |
| WP-CICD-004 | Supply chain: pinning, scanning and SBOM | Yavuz | M5 |
| WP-CICD-005 | Release rollback capability | Yavuz | M5 |
| WP-CICD-006 | CI isolation for untrusted contributions | Yavuz | M5 |
| WP-OBS-001 | Telemetry pipeline (OTel → Collector → OpenObserve) | Yavuz | M1 |
| WP-OBS-002 | Distributed trace propagation across the closed loop | Yavuz | M3 |
| WP-OBS-004 | Audit store separation from telemetry | Yavuz | M4 |
| WP-OBS-005 | Redaction and diagnostic bundles | Yavuz | M5 |
| WP-OBS-006 | Telemetry retention, quota and instrumentation overhead | Yavuz | M7 |
| WP-SEC-001 | Keycloak realm, clients and interactive authentication | Yavuz | M3 |
| WP-SEC-002 | Service identities and least-privilege credentials | Yavuz | M4 |
| WP-SEC-004 | AI-reachable capability surface restriction | Yavuz | M4 |
| WP-SEC-005 | Secret sourcing and hygiene | Yavuz | M4 |
| WP-SEC-006 | Test-auth prohibition in formal environments | Yavuz | M5 |
| WP-SEC-008 | Security negative suite and external egress audit | Yavuz | M5 |
| WP-DR-001 | Backup automation and integrity verification | Yavuz | M5 |
| WP-DR-002 | Restore drills: database and full host | Yavuz | M6 |
| WP-DR-003 | Derived-state rebuild paths | Yavuz | M5 |
| WP-DR-004 | Evidence protection and off-host preservation | Yavuz | M7 |
| WP-TEST-001 | Test strategy, tiers and boundary-mode policy | Yavuz | M1 |
| WP-TEST-006 | E2E-01 checkpoint execution | Batu | M3 |
| WP-TEST-007 | Architecture rules and trace validation in CI | Yavuz | M2 |
| WP-TEST-008 | Flake control and release-gate hygiene | Yavuz | M6 |
| WP-PERF-001 | Benchmark definitions, workload profiles and measurement protocol | Yavuz | M5 |
| WP-PERF-002 | Latency and throughput measurement execution | Yavuz | M7 |
| WP-PERF-005 | Soak testing and resource behaviour under sustained load | Yavuz | M7 |
| WP-RES-001 | Experiment runner and run manifest binding | Yavuz | M5 |
| WP-RES-003 | Benchmark run registry and disposition accounting | Yavuz | M6 |
| WP-RES-005 | Evidence sealing and bundle assembly | Yavuz | M7 |
| WP-RES-008 | RQ-2 lane: dynamic recovery evaluation | Batu | M6 |
| WP-RES-010 | RQ-4 lane: perception-to-operations evaluation | Selman | M6 |
| WP-BENCH-001 | Campaign manifest, preflight and lane orchestration | Yavuz | M7 |
| WP-BENCH-003 | Engineering lanes execution (ENG-A…I) | Yavuz | M7 |
| WP-BENCH-004 | Reproduction lanes: clean host, non-owner and public | Yavuz | M8 |
| WP-BENCH-005 | Evidence bundle finalization and acceptance reporting | Yavuz | M8 |
| WP-DOC-001 | Engineering documentation set | Yavuz | M6 |
| WP-DOC-005 | Public release package (v1) | Yavuz | M8 |

## 10. Sprint-Level Execution Projection

Sprint character follows Item 66 §"Sprint-Level Parallelization"; the packages are this role's. This is a projection for planning conversations, not a commitment schedule — 07 owns milestone planning.

| Sprint | Character (Item 66) | Work packages in flight | Upstream gates due | Commitments owed | Milestone |
|---|---|---|---|---|---|
| S1 | maximum independent foundational work | WP-GOV-001 | 0 | 0 | M0 |
| S2 | first Core/event/Twin/platform convergence | WP-CORE-001, WP-CORE-005, WP-CORE-007, WP-EVT-001, WP-EVT-002, WP-TWIN-001, WP-UI-001 | 3 | 1 | M1 |
| S3 | independent depth: Simulator, Vision, Scheduler, AI fixtures | WP-CORE-002, WP-CORE-003, WP-CORE-004, WP-EVT-003, WP-EVT-005, WP-TWIN-002, WP-TWIN-003, WP-UI-002, WP-TEST-002, WP-DOC-002 | 0 | 1 | M2 |
| S4 | depth continues; E2E-01 contract readiness gate closes | WP-CORE-002, WP-CORE-003, WP-CORE-004, WP-EVT-003, WP-EVT-005, WP-TWIN-002, WP-TWIN-003, WP-UI-002, WP-TEST-002, WP-DOC-002 | 5 | 8 | M2 |
| S5 | highest integration density; E2E-01 dry run and formal run | WP-CORE-008, WP-TWIN-006, WP-AI-001, WP-AI-002, WP-AI-003, WP-AI-004, WP-AI-006, WP-HITL-001, WP-HITL-002, WP-HITL-003, WP-UI-006, WP-SEC-003, WP-TEST-003 | 0 | 3 | M3 |
| S6 | highest integration density; M3 closed-loop alpha | WP-CORE-008, WP-TWIN-006, WP-AI-001, WP-AI-002, WP-AI-003, WP-AI-004, WP-AI-006, WP-HITL-001, WP-HITL-002, WP-HITL-003, WP-UI-006, WP-SEC-003, WP-TEST-003 | 1 | 0 | M3 |
| S7 | independent capability depth increases again | WP-TWIN-005, WP-ML-001, WP-ML-002, WP-ML-003, WP-ML-004, WP-ML-005, WP-RAG-001, WP-RAG-002, WP-RAG-003, WP-RAG-004, WP-RAG-005, WP-AI-005, WP-HITL-005, WP-HITL-006, WP-UI-004 | 0 | 0 | M4 |
| S8 | depth continues; M4 mandatory feature complete | WP-TWIN-005, WP-ML-001, WP-ML-002, WP-ML-003, WP-ML-004, WP-ML-005, WP-RAG-001, WP-RAG-002, WP-RAG-003, WP-RAG-004, WP-RAG-005, WP-AI-005, WP-HITL-005, WP-HITL-006, WP-UI-004 | 3 | 1 | M4 |
| S9 | cross-cutting quality and evaluation dependencies dominate | WP-TWIN-004, WP-ML-006, WP-RAG-006, WP-UI-008, WP-UI-010, WP-RES-002, WP-RES-006 | 0 | 0 | M5 |
| S10 | quality/evaluation continues; M5 reliability & evaluation ready | WP-TWIN-004, WP-ML-006, WP-RAG-006, WP-UI-008, WP-UI-010, WP-RES-002, WP-RES-006 | 3 | 2 | M5 |
| S11 | freeze convergence; highest freeze-risk window; M6 | WP-GOV-004, WP-ML-007, WP-RAG-007, WP-RES-004, WP-RES-007, WP-RES-009, WP-RES-011 | 7 | 2 | M6 |
| S12 | graph effectively immutable, formal execution only; M7 | WP-CORE-006, WP-AI-007, WP-BENCH-002 | 1 | 0 | M7 |
| S13 | evidence, release and documentation convergence; M8 | WP-UI-011, WP-UI-012, WP-RES-012, WP-DOC-003, WP-DOC-004, WP-DOC-006 | 0 | 0 | M8 |

Two windows deserve explicit attention for this role: **S5–S6** (highest integration density — avoid unrelated refactoring) and **S11** (freeze convergence — avoid casual experimental changes).

### 10.1 Interface ledger with each teammate

**Asrın ↔ Selman**

| Direction | Count | Edges / packages |
|---|---|---|
| Asrın receives from Selman | 5 | DEP-065 (DN-VIS-OBSCON, by E2E-01 readiness (end S4)), DEP-068 (DN-VIS-SERVING, by M3 (S6)), DEP-122 (DN-VIS-SPLIT, by M5 (S10)), DEP-150 (DN-VIS-OOD, by M6), DEP-151 (DN-VIS-EPISODES, by M6) |
| Asrın delivers to Selman | 2 | DEP-056 (DN-VIS-ARTCON, by S3), DEP-063 (DN-VIS-EPISODES, by M5) |
| shared packages (owner/reviewer) | 22 | WP-EVT-001, WP-VIS-001, WP-VIS-002, WP-VIS-004, WP-VIS-005, WP-VIS-006, WP-VIS-007, WP-VDATA-001, WP-VDATA-002, WP-VDATA-005, WP-ML-002, WP-ML-004, WP-ML-006, WP-UI-003, WP-UI-004, WP-UI-008, WP-TEST-002, WP-RES-002, WP-RES-010, WP-RES-012, WP-DOC-003, WP-S-001 |

**Asrın ↔ Batu**

| Direction | Count | Edges / packages |
|---|---|---|
| Asrın receives from Batu | 9 | DEP-035 (DN-SIM-COREINT, by M2 (S4)), DEP-074 (DN-SIM-SYNTH, by M4 (S8)), DEP-092 (DN-SCH-PLANCON, by E2E-01 readiness (end S4)), DEP-121 (DN-SIM-SYNTH, by M5 (S10)), DEP-132 (DN-FRZ-DATA, by M6 (S11)), DEP-135 (DN-FRZ-DATA, by M6 (S11)), DEP-138 (DN-SIM-REALISM, by M6 (S11)), DEP-153 (DN-SCH-CPSAT, by M6), DEP-154 (DN-SCH-CF, by M6) |
| Asrın delivers to Batu | 16 | DEP-038 (DN-SIM-OPSEM, by S2), DEP-039 (DN-SIM-OPSEM, by M2 (S4)), DEP-041 (DN-SIM-COREINT, by M2 (S4)), DEP-042 (DN-SIM-COREINT, by M2 (S4)), DEP-079 (DN-SCH-DYN, by E2E-01 readiness (end S4)), DEP-080 (DN-SCH-DYN, by M2 (S4)), DEP-081 (DN-SCH-DYN, by M4 (S8)), DEP-082 (DN-SCH-VALID, by E2E-01 (end S5)), DEP-089 (DN-SCH-DYN, by M3 (S6)), DEP-096 (DN-AUTO-EXEC, by E2E-01 readiness (end S4)), DEP-097 (DN-AUTO-EXEC, by E2E-01 readiness (end S4)), DEP-098 (DN-AUTO-EXEC, by E2E-01 readiness (end S4)), DEP-099 (DN-AUTO-EXEC, by E2E-01 (end S5)), DEP-103 (DN-AUTO-VERIFY, by E2E-01 (end S5)), DEP-104 (DN-AUTO-EXEC, by M3 (S6)), DEP-129 (DN-FRZ-DATA, by M6 (S11)) |
| shared packages (owner/reviewer) | 45 | WP-CORE-001, WP-CORE-002, WP-CORE-003, WP-CORE-008, WP-EVT-003, WP-TWIN-003, WP-TWIN-005, WP-TWIN-006, WP-SIM-001, WP-SIM-003, WP-SIM-006, WP-SIM-007, WP-SIM-009, WP-ML-001, WP-ML-003, WP-AI-004, WP-SCH-001, WP-SCH-002, WP-SCH-003, WP-SCH-004, WP-SCH-006, WP-SCH-007, WP-VALID-001, WP-VALID-002, WP-AUTO-002, WP-AUTO-003, WP-AUTO-004, WP-AUTO-005, WP-AUTO-006, WP-AUTO-007, WP-HITL-001, WP-HITL-002, WP-HITL-003, WP-HITL-006, WP-UI-002, WP-UI-005, WP-UI-006, WP-UI-007, WP-TEST-003, WP-TEST-006, WP-RES-006, WP-RES-008, WP-RES-009, WP-BENCH-002, WP-R2-002 |

**Asrın ↔ Yavuz**

| Direction | Count | Edges / packages |
|---|---|---|
| Asrın receives from Yavuz | 9 | DEP-019 (DN-RT-PG, by M1 (S2)), DEP-025 (DN-RT-NATS, by M1 (S2)), DEP-033 (DN-RT-PG, by M1 (S2)), DEP-071 (DN-RT-QDRANT, by M4 (S8)), DEP-075 (DN-RT-MLFLOW, by M4/M5), DEP-090 (DN-RT-IDP, by E2E-01 readiness (end S4)), DEP-108 (DN-RT-IDP, by E2E-01 readiness (end S4)), DEP-127 (DN-RES-HARNESS, by M5→M6), DEP-143 (DN-RES-BENCH, by M7 (S12)) |
| Asrın delivers to Yavuz | 2 | DEP-125 (DN-RES-HARNESS, by M5 (S10)), DEP-139 (DN-FRZ-RELEASE, by M6 (S11)) |
| shared packages (owner/reviewer) | 84 | WP-GOV-001, WP-GOV-002, WP-GOV-003, WP-GOV-004, WP-CORE-005, WP-CORE-006, WP-CORE-007, WP-EVT-002, WP-EVT-004, WP-EVT-005, WP-EVT-006, WP-TWIN-001, WP-TWIN-004, WP-ML-005, WP-ML-007, WP-RAG-001, WP-RAG-002, WP-RAG-004, WP-RAG-006, WP-RAG-007, WP-AI-001, WP-AI-002, WP-AI-003, WP-AI-005, WP-AI-006, WP-AI-007, WP-HITL-004, WP-HITL-005, WP-HITL-007, WP-UI-001, WP-UI-009, WP-UI-010, WP-UI-011, WP-UI-012, WP-PLAT-001, WP-PLAT-002, WP-PLAT-004, WP-PLAT-005, WP-PLAT-006, WP-CICD-001, WP-CICD-002, WP-CICD-003, WP-CICD-004, WP-CICD-005, WP-CICD-006, WP-OBS-001, WP-OBS-002, WP-OBS-004, WP-OBS-005, WP-OBS-006, WP-SEC-001, WP-SEC-002, WP-SEC-003, WP-SEC-004, WP-SEC-005, WP-SEC-006, WP-SEC-008, WP-DR-001, WP-DR-002, WP-DR-003, WP-DR-004, WP-TEST-001, WP-TEST-007, WP-TEST-008, WP-PERF-001, WP-PERF-002, WP-PERF-005, WP-RES-001, WP-RES-003, WP-RES-004, WP-RES-005, WP-RES-007, WP-RES-011, WP-BENCH-001, WP-BENCH-003, WP-BENCH-004, WP-BENCH-005, WP-DOC-001, WP-DOC-002, WP-DOC-004, WP-DOC-005, WP-DOC-006, WP-R2-001, WP-X-001 |

## 11. Integration Checkpoints

| Checkpoint | Work packages | What this role must prove |
|---|---|---|
| E2E-01 (end S5, Item 67) | WP-CORE-008, WP-UI-006 | contract readiness by end S4 and real-boundary behaviour in the formal run; review obligation before the run (Item 67 #215–#218) |
| AV-SCEN-01…12 (Item 84) | WP-CORE-008, WP-TWIN-006, WP-AI-006, WP-UI-006, WP-TEST-003 | architecture validation scenarios executed on the Integration environment |
| GS-01 demo (DEMO-GS01-001) | WP-UI-006, WP-DOC-004 | the hero path works from a pinned release without presentation shortcuts |
| FBC-01 E2E matrix (BENCH-E2E-001) | WP-TWIN-006, WP-BENCH-002 | the role's part of the 4×20 statistical matrix executes unattended |

## 12. Failure and Negative Tests

Negative and failure-path verification owned or co-owned by this role. Happy-path evidence alone can never satisfy an H0 requirement (03 §4.4).

| Verification family | Kind | Scope | Family owner | Minimum environment |
|---|---|---|---|---|
| RES-DUP-001 | DRILL | Duplicate/retry/restart protected-effect suite aggregation (AV-SCEN-05/06 + TEST-AUTO-RESTART-001) | Batu | EVALUATION |
| TEST-AI-BINDING | TEST | Proposal ↔ evidence/revision/world context binding | Asrın | CI |
| TEST-AI-BUDGET | TEST | AgentBudgetProfile enforcement and bounded termination (no unbounded loop) | Asrın | CI |
| TEST-ARCH-BOUNDARY | TEST | Architecture-rules-as-code: import boundaries, schema ownership, forbidden cross-service credentials, contract producer uniqueness | Asrın | CI |
| TEST-AUTH-NEG | TEST | Cross-cutting authority negative suite: AI mutation/self-approval/credential/bypass attempts (AUTH-INV family) | Asrın | CI |
| TEST-AUTO-FRESHNESS | TEST | Pre-execution revalidation of proposal/plan/state freshness, WorldID and action identity | Batu | CI |
| TEST-AUTO-OUTCOME | TEST | ACK ≠ effect; lost/ambiguous response → UNKNOWN_VERIFY_REQUIRED; Core/Twin effect verification | Batu | CI |
| TEST-CORE-IDEMP | TEST | Command idempotency + durable command-outcome persistence (completed/rejected/unresolved) | Asrın | CI |
| TEST-CORE-REVISION | TEST | Revision/freshness precondition rejection (STALE/CONFLICT outcomes) | Asrın | CI |
| TEST-CORE-STATEMACHINE | TEST | Legal/illegal manufacturing transitions incl. hold/release/rework/split/merge (negative-path mandatory, TEST-INV-08) | Asrın | CI |
| TEST-DATA-SPLITLEAK | TEST | Frozen partition entity/group overlap detection against SplitManifest policy | Asrın | EVALUATION |
| TEST-EVT-CONSUMER-IDEMP | TEST | At-least-once consumer idempotency with real NATS JetStream (no fake bus, CI-INV-07) | Asrın | CI |
| TEST-HITL-BINDING | TEST | Exact Proposal/Plan revision + WorldID + freshness binding; material plan change invalidates approval | Asrın | CI |
| TEST-HITL-DUAL | TEST | Dual approval requires two distinct authorized identities | Asrın | CI |
| TEST-HITL-REPLAY-NEG | TEST | Stale/expired/replayed/cross-world approval rejection (negative) | Asrın | CI |
| TEST-ML-LEAKAGE | TEST | Feature-leakage / future-information / FINAL-partition guard (ML-INV-01..05) | Asrın | CI |
| TEST-RAG-INJECTION | TEST | Prompt-injection / retrieved-content cannot change authorization or policy (negative) | Asrın | CI |
| TEST-RAG-RIGHTS | TEST | Rights/eligibility metadata filtering (negative: ineligible source never returned) | Asrın | CI |
| TEST-SEC-AISURFACE | TEST | AI-reachable capability inventory: no shell / no arbitrary SQL surface | Yavuz | CI |
| TEST-SEC-AUTHZ-NEG | TEST | Backend authorization negative suite (UI visibility ≠ authorization; unknown permission ≠ allow) | Asrın | INTEGRATION |
| TEST-SEC-EGRESS | TEST | External LLM request payload audit: no secrets / Oracle truth / rights-prohibited data | Asrın | EVALUATION |
| TEST-SEC-SVCID | TEST | Declared service identities; anonymous mutation rejected; no universal super-credential | Yavuz | INTEGRATION |
| TEST-TWIN-EPISTEMIC | TEST | ACTUAL/OBSERVED/INFERRED/PREDICTED/PLANNED/COUNTERFACTUAL separation + counterfactual isolation | Asrın | CI |
| TEST-TWIN-FRESHNESS | TEST | Projection revision/freshness exposure and stale marking | Asrın | CI |
| TEST-TWIN-READONLY | TEST | Twin mutation-API ban + consumer read-only access (AI/Scheduler/BFF) | Asrın | CI |
| TEST-UI-SEMANTICS | TEST | Epistemic distinction, staleness, failure state, non-color-only status, Presenter Mode integrity | Asrın | INTEGRATION |

**Owned H0 (hard-gate) requirements requiring hard/negative evidence (17):** NFR-DATA-002, NFR-DATA-005, NFR-DATA-006, NFR-GOV-001, NFR-GOV-002, NFR-GOV-003, NFR-GOV-007, NFR-GOV-008, NFR-GOV-010, NFR-REL-002, NFR-REL-010, NFR-REP-002, NFR-SEC-004, NFR-SEC-009, NFR-UX-002, NFR-UX-003, NFR-UX-006.

## 13. Research / Evaluation Responsibilities

Asrın is the primary research owner for **RQ-1 (evidence-grounded RCA)** and **RQ-3 (governed AI-to-action)**, for **MC-1 (end-to-end closed loop)**, and for research traceability across the whole programme (Item 58). That means owning: the governed RCA case set with evaluator-held ground truth, the RCA baseline ladder (RCA-B1…B5 vs PROPOSED, with REF-ORACLE as a reference not a competitor), the retrieval ablation design, the authority scenario set including its ≥40% adversarial share, and the derivation of RQ outcomes from sealed analysis. Negative or inconclusive outcomes are acceptable results; a missing or unreproducible mechanism is not.

| R1 work package | Title | Milestone | Evidence lane |
|---|---|---|---|
| WP-ML-007 | ML evaluation lanes (M1/M2/M3) for the final campaign | M6 | BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001 |
| WP-RAG-007 | Retrieval ablation lane for RQ-1 | M6 | BENCH-RAG-001, BENCH-RQ1-001 |
| WP-RES-002 | Partition, seed and protocol governance | M5 | BENCH-FBC-001, INSP-EVAL-PARTITION |
| WP-RES-004 | AnalysisPackage and deterministic result regeneration | M6 | BENCH-FBC-001, INSP-EVAL-CLAIMS |
| WP-RES-006 | Baseline suite across lanes | M5 | BENCH-E2E-001, BENCH-RQ1-001, BENCH-RQ2-001, BENCH-SCH-001, BENCH-VIS-001 |
| WP-RES-007 | RQ-1 lane: evidence-grounded RCA evaluation | M6 | BENCH-RQ1-001 |
| WP-RES-009 | RQ-3 lane: governed AI-to-action evaluation | M6 | BENCH-RQ3-001 |
| WP-RES-011 | Freeze execution for M6 | M6 | BENCH-FBC-001, BENCH-RAG-001, BENCH-RQ1-001, INSP-EVAL-PARTITION |
| WP-RES-012 | Research claim classification | M8 | BENCH-FBC-001, INSP-EVAL-CLAIMS |
| WP-BENCH-002 | Final E2E matrix execution (MC-1) | M7 | BENCH-E2E-001, BENCH-PERF-WF |
| WP-DOC-003 | Thesis and portfolio artifact production | M8 | BENCH-FBC-001, INSP-EVAL-CLAIMS |

## 14. Documentation and ADR Obligations

Own the ADR index and the backfill ADRs for Core, Twin, AI orchestration, genealogy and RAG decisions (02 backfill list); own the architecture overview and the semantic sections of the contract registry documentation; keep 03 regenerated whenever requirement semantics change.

## 15. Risks and Bottlenecks

| Risk (Item 69) | Exposure for this role | Mitigation carried in this roadmap |
|---|---|---|
| TEAM-R03 | Asrın as universal bottleneck: the largest number of cross-owner HARD dependencies originate here (05 §17). | Contract-first delivery: publish Core domain, command, event, snapshot and proposal contracts with fixtures ahead of consumers; keep review slots reserved in S3–S5. |
| ARCH-R01 | Closed loop integrates late and semantics drift. | E2E-01 at end S5 with Asrın reviewing the Core/AI/authority path before the formal run. |
| AI-R01 | RCA output is fluent but ungrounded. | Structured output with evidence references, abstention path, and RQ-1 grounding metrics over a governed case set. |
| AI-R07 | AI authority boundary erodes under demo pressure. | No mutation credential for the AI identity; negative suite executed on the real runtime; policy evaluation independent of model text. |
| ARCH-R06 | Twin degenerates into a renamed Core query. | Twin is event-derived only, with its own revision/freshness semantics and a mutation-API prohibition test. |
| RES-R01 | Final-partition leakage invalidates RQ-1/RQ-4 results. | Partition governance, FINAL access guard, leakage detection before freeze. |

## 16. Cross-Review Responsibilities

Asrın is the required reviewer wherever manufacturing meaning, authority or cross-service semantics are at stake: Batu's Simulator semantics and ActionCatalog execution paths, Selman's observation contract and evidence typing, Yavuz's platform changes that touch domain data or identity. Asrın also carries architecture/RTM semantic stewardship (Item 83 #120): the trace graph's meaning is owned here even though Yavuz owns the tooling.

Named reviewer on 86 work packages owned by others (§9.SUP). Cross-review is an Item 63 obligation, not a courtesy: a dependency handshake counts as complete only when both sides have validated contract usability (Item 66 #140).

## 17. Final Benchmark Contribution

| Lane / asset | Kind | Scope | Role's obligation |
|---|---|---|---|
| BENCH-CAP-ENV | BENCH | Interactive session concurrency and isolated-WorldID capacity | execute and record dispositions, including failures |
| BENCH-E2E-001 | BENCH | FBC-01 final statistical E2E matrix: 4 frozen scenario definitions × 20 seeds (80 base instances) | execute and record dispositions, including failures |
| BENCH-FBC-001 | BENCH | FBC-01 campaign-level execution: BenchmarkCampaignManifest, preflight, run registry, sealing across all lanes (R1 mechanisms exercised formally) | execute and record dispositions, including failures |
| BENCH-ML-M1-001 | BENCH | M1 equipment-risk evaluation (discrimination + calibration separately) | execute and record dispositions, including failures |
| BENCH-ML-M2-001 | BENCH | M2 cycle-time/tardiness evaluation | execute and record dispositions, including failures |
| BENCH-ML-M3-001 | BENCH | M3 pre-inspection quality evaluation | execute and record dispositions, including failures |
| BENCH-PERF-AI | BENCH | RAG top-k retrieval latency and RCA path latency decomposition (provider context retained) | execute and record dispositions, including failures |
| BENCH-PERF-CORE | BENCH | Core/Twin read latency, command decision latency, outbox delay, Twin freshness, Core command throughput | execute and record dispositions, including failures |
| BENCH-PERF-SCH | BENCH | SP-NORMAL decision budget and SP-STRESS frontier (feasibility, solve time, quality, fallback rate) | execute and record dispositions, including failures |
| BENCH-PERF-UI | BENCH | Command Center state visibility and initial actionable load on accepted LAN/client profile | execute and record dispositions, including failures |
| BENCH-PERF-WF | BENCH | Workflow control-plane overhead, approval persistence, GS-01 system-controlled duration, workflow concurrency | execute and record dispositions, including failures |
| BENCH-RAG-001 | BENCH | Retrieval ablation lane RAG-B0..B3 + RAG-PROPOSED bound to CorpusVersion/RetrievalProfile | execute and record dispositions, including failures |
| BENCH-RQ1-001 | BENCH | RQ-1 evidence-grounded RCA final evaluation (120 FINAL_TEST cases, baselines RCA-B1..PROPOSED) | execute and record dispositions, including failures |
| BENCH-RQ2-001 | BENCH | RQ-2 dynamic closed-loop recovery (4 families × 20 paired seeds, realized execution outcome) | execute and record dispositions, including failures |
| BENCH-RQ3-001 | BENCH | RQ-3 governed AI-to-action (150 cases, L0–L4 × 30, ≥40% adversarial) | execute and record dispositions, including failures |
| BENCH-SCH-001 | BENCH | Scheduler component benchmark (8 families × 30 paired seeds) incl. baselines and churn/stability metrics | execute and record dispositions, including failures |
| BENCH-VIS-001 | BENCH | Final Vision evaluation lane: classification, localization, segmentation, anomaly, OOD, spatial pattern (no single accuracy) | execute and record dispositions, including failures |
| RES-BROKER-001 | DRILL | 5-minute broker interruption under WP-NORMAL → backlog drain, no committed-effect loss (AV-SCEN-07 execution) | execute and record dispositions, including failures |
| RES-DUP-001 | DRILL | Duplicate/retry/restart protected-effect suite aggregation (AV-SCEN-05/06 + TEST-AUTO-RESTART-001) | execute and record dispositions, including failures |
| RES-IDXREBUILD-001 | DRILL | Qdrant/RAG index rebuild from canonical corpus artifacts | execute and record dispositions, including failures |
| RES-TWINREBUILD-001 | DRILL | Twin projection loss → deterministic rebuild from retained canonical sources (AV-SCEN-08 execution) | execute and record dispositions, including failures |
| RES-WORKER-001 | DRILL | Workflow-worker crash/restart resumption without duplicate verified effect (AV-SCEN-06 execution) | execute and record dispositions, including failures |

Campaign discipline that binds this role: run only what was frozen at M6; record every attempted run with a disposition; never adjust a threshold, rubric or scenario after seeing results; a MISS or a NOT_SUPPORTED outcome is a result, not a failure to conceal.

## 18. Demo Contribution

GS-01 is mostly Asrın's semantic path: the inspection evidence becomes an RCA assessment, the proposal is bound, the authority policy demands a human, and the Core command produces a verified effect shown in the Command Center timeline. Asrın owns the narrative integrity of the demo — specifically that the demo cannot conceal approvals, validation or verification (presenter-mode integrity).

## 19. Thesis / Portfolio Evidence

Thesis and portfolio material from this role is a by-product of work that had to happen anyway: the closed-loop architecture and its authority model, the RCA evidence model with abstention behaviour, the retrieval ablation, the authority/HITL evaluation under adversarial cases, and the traceability system that ties 306 requirements to evidence. No feature exists in the plan for CV reasons; if a claim cannot point at sealed evidence in the FBC-01 bundle it does not appear in the thesis.

| Evidence artifact | Produced by | Status today |
|---|---|---|
| Owned requirement dispositions (124) | 03 trace registry at M8 | NOT_YET_EXECUTED |
| Sealed lane results for owned research lanes | FBC-01 bundle at M7 | NOT_YET_EXECUTED |
| Architecture/design record (ADRs, contracts) | continuous from M1 | NOT_STARTED |
| Negative/failure evidence (26 families) | M5–M7 | NOT_YET_EXECUTED |

## 19.1 Requirement Execution Dossier

One block per owned requirement: what must be built, what proves it, where the evidence must come from, and which milestone carries it. This is the checklist the owner works through between M1 and M8.

```yaml
FR-AI-001:
  class: F0
  area: AI
  work_packages: [WP-AI-001, WP-TEST-006, WP-RES-006, WP-R2-002]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH, ARCH-AI-TOOLS]
  planned_surface: "custom deterministic orchestrator state machine (backfill ADR 13, OD-AI-01)"
  boundary_mode_final: REAL
  verification: [TEST-AI-OUTPUT, E2E-01, AV-SCEN-01, BENCH-RQ1-001, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-002:
  class: F1
  area: AI
  work_packages: [WP-AI-002]
  target_milestone: M3
  architecture: [ARCH-AI-TOOLS]
  planned_surface: "typed versioned tool registry (catalog names OD-AI-04)"
  boundary_mode_final: REAL
  verification: [TEST-AI-TOOLS, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-003:
  class: F1
  area: AI
  work_packages: [WP-AI-002]
  target_milestone: M3
  architecture: [ARCH-AI-TOOLS, ARCH-SEC-AUTHZ]
  planned_surface: "tool allowlist with READ/SIMULATE/PROPOSE authority tags"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-AI-TOOLS, TEST-AUTH-NEG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-004:
  class: F0
  area: AI
  work_packages: [WP-AI-006, WP-TEST-003, WP-RES-009]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH, ARCH-CORE-CMD, ARCH-SEC-AUTHZ]
  planned_surface: "no mutation credentials for AI identity; Core command authz denies AI principal"
  boundary_mode_final: REAL
  verification: [TEST-AUTH-NEG, AV-SCEN-01, BENCH-RQ3-001, TEST-SEC-SVCID]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-005:
  class: F1
  area: AI
  work_packages: [WP-AI-003, WP-RES-007]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH]
  planned_surface: "assessment schema separating Hypothesis vs ObservedEvidence"
  boundary_mode_final: REAL
  verification: [TEST-AI-OUTPUT, BENCH-RQ1-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-006:
  class: F1
  area: AI
  work_packages: [WP-AI-003]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH]
  planned_surface: "EvidenceRef list validation (no fabricated IDs, AGENT-INV-13)"
  boundary_mode_final: REAL
  verification: [TEST-AI-OUTPUT, BENCH-RQ1-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-007:
  class: F1
  area: AI
  work_packages: [WP-AI-003]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH]
  planned_surface: "conflicting/missing-evidence representation; tool failure ≠ negative evidence"
  boundary_mode_final: REAL
  verification: [TEST-AI-OUTPUT, BENCH-RQ1-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-008:
  class: F1
  area: AI
  work_packages: [WP-AI-003, WP-RES-007]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH]
  planned_surface: "INSUFFICIENT_EVIDENCE / abstention status"
  boundary_mode_final: REAL
  verification: [TEST-AI-OUTPUT, BENCH-RQ1-001, AV-SCEN-03]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-009:
  class: F1
  area: AI
  work_packages: [WP-AI-004]
  target_milestone: M3
  architecture: [ARCH-AI-PROPOSAL]
  planned_surface: "ActionProposal/Recommendation object (no command semantics)"
  boundary_mode_final: REAL
  verification: [TEST-AUTH-NEG, AV-SCEN-01, BENCH-RQ3-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-010:
  class: F1
  area: AI
  work_packages: [WP-AI-004]
  target_milestone: M3
  architecture: [ARCH-AI-PROPOSAL, ARCH-TWIN-FRESHNESS]
  planned_surface: "proposal base-revision/world/evidence-set binding"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-AI-BINDING, AV-SCEN-04]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-011:
  class: F1
  area: AI
  work_packages: [WP-AI-005, WP-RES-011]
  target_milestone: M4
  architecture: [ARCH-AI-PROVIDER, ARCH-AI-ORCH]
  planned_surface: "AIBehaviorBundle (provider/model/prompt/tool versions) on AgentRun"
  boundary_mode_final: REAL
  verification: [INSP-AI-BEHAVIOR, BENCH-RQ1-001, INSP-REP-LLM]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-012:
  class: F1
  area: AI
  work_packages: [WP-AI-001]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH]
  planned_surface: "AgentBudgetProfile enforcement (numeric limits OD-AI-02)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-AI-BUDGET]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AI-013:
  class: F1
  area: AI
  work_packages: [WP-AI-001]
  target_milestone: M3
  architecture: [ARCH-AI-ORCH, ARCH-CTR-EVTSCHEMA]
  planned_surface: "structured-output schema validation gate before publication"
  boundary_mode_final: REAL
  verification: [TEST-AI-OUTPUT, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-001:
  class: F0
  area: CORE
  work_packages: [WP-CORE-001]
  target_milestone: M1
  architecture: [ARCH-CORE-DOMAIN, ARCH-CORE-DB]
  planned_surface: "production/material/route/equipment domain model + `core` schema migrations"
  boundary_mode_final: REAL
  verification: [TEST-CORE-DOMAIN, E2E-01, AV-SCEN-01, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-002:
  class: F0
  area: CORE
  work_packages: [WP-CORE-001]
  target_milestone: M1
  architecture: [ARCH-CORE-DOMAIN]
  planned_surface: "reentrant route/visit model (visit index, operation-class revisit)"
  boundary_mode_final: REAL
  verification: [TEST-CORE-DOMAIN, TEST-CORE-GENEALOGY, E2E-01, AV-SCEN-02, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-003:
  class: F1
  area: CORE
  work_packages: [WP-CORE-002, WP-CORE-008, WP-TEST-003]
  target_milestone: M2
  architecture: [ARCH-CORE-DOMAIN, ARCH-CORE-CMD]
  planned_surface: "manufacturing state machine / transition guard module"
  boundary_mode_final: REAL
  verification: [TEST-CORE-STATEMACHINE, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-004:
  class: F1
  area: CORE
  work_packages: [WP-CORE-003]
  target_milestone: M2
  architecture: [ARCH-CORE-CMD]
  planned_surface: "command precondition/revision validator (STALE/CONFLICT outcomes)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-CORE-REVISION, TEST-HITL-REPLAY-NEG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-005:
  class: F1
  area: CORE
  work_packages: [WP-CORE-003]
  target_milestone: M2
  architecture: [ARCH-CORE-CMD, ARCH-AUTO-IDEMPOTENCY]
  planned_surface: "command idempotency-key store (Item 83 example: core app + idempotency package)"
  boundary_mode_final: REAL
  verification: [TEST-CORE-IDEMP, AV-SCEN-05, RES-DUP-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-006:
  class: F1
  area: CORE
  work_packages: [WP-CORE-003, WP-CORE-008]
  target_milestone: M2
  architecture: [ARCH-CORE-CMD, ARCH-CORE-DB]
  planned_surface: "durable CommandOutcome record (completed/rejected/unresolved)"
  boundary_mode_final: REAL
  verification: [TEST-CORE-IDEMP, TEST-AUTO-OUTCOME, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-007:
  class: F1
  area: CORE
  work_packages: [WP-CORE-002]
  target_milestone: M2
  architecture: [ARCH-CORE-CMD, ARCH-CORE-DOMAIN]
  planned_surface: "PlaceLotOnHold command handler (CMD-PlaceLotOnHold-v1)"
  boundary_mode_final: REAL
  verification: [TEST-CORE-STATEMACHINE, E2E-01, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-008:
  class: F1
  area: CORE
  work_packages: [WP-CORE-002]
  target_milestone: M2
  architecture: [ARCH-CORE-CMD, ARCH-CORE-DOMAIN]
  planned_surface: "ReleaseMaterialHold eligibility handler"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-CORE-STATEMACHINE, TEST-AUTH-NEG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-009:
  class: F1
  area: CORE
  work_packages: [WP-CORE-004]
  target_milestone: M2
  architecture: [ARCH-CORE-DOMAIN, ARCH-CORE-GENEALOGY]
  planned_surface: "ReworkDirective + append-only route-visit history"
  boundary_mode_final: REAL
  verification: [TEST-CORE-STATEMACHINE, TEST-CORE-GENEALOGY, BENCH-E2E-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-010:
  class: F1
  area: CORE
  work_packages: [WP-CORE-004]
  target_milestone: M2
  architecture: [ARCH-CORE-GENEALOGY]
  planned_surface: "lot split relation model"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-CORE-GENEALOGY]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-011:
  class: F1
  area: CORE
  work_packages: [WP-CORE-004]
  target_milestone: M2
  architecture: [ARCH-CORE-GENEALOGY]
  planned_surface: "lot merge relation model (policy-permitted)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-CORE-GENEALOGY]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-012:
  class: F1
  area: CORE
  work_packages: [WP-CORE-004]
  target_milestone: M2
  architecture: [ARCH-CORE-GENEALOGY, ARCH-CORE-DB]
  planned_surface: "relational temporal genealogy (no mandatory graph DB, backfill ADR 12)"
  boundary_mode_final: REAL
  verification: [TEST-CORE-GENEALOGY, AV-SCEN-01, BENCH-RQ1-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-013:
  class: F1
  area: CORE
  work_packages: [WP-CORE-001, WP-CORE-007]
  target_milestone: M1
  architecture: [ARCH-CORE-DB, ARCH-CORE-CMD]
  planned_surface: "schema-level grants; per-service DB roles; `core` schema privacy"
  boundary_mode_final: REAL
  verification: [TEST-ARCH-BOUNDARY, TEST-SEC-SVCID, TEST-AUTH-NEG]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-014:
  class: F1
  area: CORE
  work_packages: [WP-CORE-005]
  target_milestone: M1
  architecture: [ARCH-CORE-OUTBOX, ARCH-EVT-OUTBOX]
  planned_surface: "domain-event emission per accepted transition"
  boundary_mode_final: REAL
  verification: [TEST-CORE-OUTBOX, TEST-EVT-SCHEMA, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-015:
  class: F1
  area: CORE
  work_packages: [WP-CORE-005]
  target_milestone: M1
  architecture: [ARCH-CORE-OUTBOX, ARCH-CORE-DB, ARCH-EVT-OUTBOX]
  planned_surface: "transactional outbox table + relay"
  boundary_mode_final: REAL
  verification: [TEST-CORE-OUTBOX, RES-BROKER-001, AV-SCEN-07]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-CORE-016:
  class: F1
  area: CORE
  work_packages: [WP-CORE-003]
  target_milestone: M2
  architecture: [ARCH-CORE-CMD, ARCH-CTR-API, ARCH-CTR-VERSIONING]
  planned_surface: "versioned OpenAPI query/command surface"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-CORE-CONTRACT, TEST-EVT-SCHEMA]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-002:
  class: R1
  area: EVAL
  work_packages: [WP-SIM-007, WP-RES-002, WP-RES-011]
  target_milestone: M4
  architecture: [ARCH-DATA-LINEAGE]
  planned_surface: "partition + seed namespace fields in ExperimentDefinition"
  boundary_mode_final: REAL
  verification: [INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-006:
  class: R1
  area: EVAL
  work_packages: [WP-RES-004]
  target_milestone: M6
  architecture: [ARCH-DATA-LINEAGE, ARCH-DATA-OBJ]
  planned_surface: "versioned AnalysisPackage (metric calculators, tests, tables, figures)"
  boundary_mode_final: REAL
  verification: [TEST-EVAL-ANALYSIS, INSP-EVAL-CLAIMS, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-009:
  class: R1
  area: EVAL
  work_packages: [WP-RES-012]
  target_milestone: M8
  architecture: [ARCH-DATA-LINEAGE]
  planned_surface: "RQ outcome derivation step (SUPPORTED/PARTIAL/NOT/INCONCLUSIVE) from sealed evidence"
  boundary_mode_final: REAL
  verification: [INSP-EVAL-CLAIMS, TEST-EVAL-ANALYSIS, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-010:
  class: R1
  area: EVAL
  work_packages: [WP-RES-012, WP-DOC-003]
  target_milestone: M8
  architecture: [ARCH-DATA-LINEAGE]
  planned_surface: "PortfolioMetricExport / thesis tables generated from sealed analysis"
  boundary_mode_final: REAL
  verification: [INSP-EVAL-CLAIMS, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-001:
  class: F0
  area: EVT
  work_packages: [WP-EVT-001]
  target_milestone: M1
  architecture: [ARCH-CTR-CMDSCHEMA, ARCH-CTR-EVTSCHEMA, ARCH-CTR-API, ARCH-CTR-VERSIONING]
  planned_surface: "Integration Contract Registry (Git-backed)"
  boundary_mode_final: REAL
  verification: [TEST-EVT-SCHEMA, TEST-ARCH-BOUNDARY, AV-SCEN-01, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-002:
  class: F1
  area: EVT
  work_packages: [WP-EVT-002]
  target_milestone: M1
  architecture: [ARCH-EVT-SCHEMA]
  planned_surface: "event envelope EventID generation"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-EVT-ENVELOPE]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-003:
  class: F1
  area: EVT
  work_packages: [WP-EVT-002]
  target_milestone: M1
  architecture: [ARCH-EVT-SCHEMA, ARCH-OBS-TRACE]
  planned_surface: "CorrelationID/CausationID propagation middleware"
  boundary_mode_final: REAL
  verification: [TEST-EVT-ENVELOPE, TEST-OBS-TRACEPROP, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-004:
  class: F1
  area: EVT
  work_packages: [WP-EVT-002]
  target_milestone: M1
  architecture: [ARCH-WORLD-SCOPE, ARCH-EVT-SCHEMA]
  planned_surface: "WorldID scope-tagging middleware"
  boundary_mode_final: REAL
  verification: [TEST-EVT-ENVELOPE, AV-SCEN-10, AV-SCEN-09]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-005:
  class: F1
  area: EVT
  work_packages: [WP-EVT-003, WP-TEST-004]
  target_milestone: M2
  architecture: [ARCH-EVT-CONSUMER]
  planned_surface: "idempotent consumer framework (processed-message ledger)"
  boundary_mode_final: REAL
  verification: [TEST-EVT-CONSUMER-IDEMP, AV-SCEN-05, RES-DUP-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-006:
  class: F1
  area: EVT
  work_packages: [WP-EVT-001, WP-TEST-002]
  target_milestone: M1
  architecture: [ARCH-EVT-SCHEMA, ARCH-CTR-EVTSCHEMA]
  planned_surface: "boundary schema validators (producer + consumer)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-EVT-SCHEMA]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-007:
  class: F1
  area: EVT
  work_packages: [WP-EVT-005, WP-TEST-007]
  target_milestone: M2
  architecture: [ARCH-CTR-API, ARCH-CORE-DB]
  planned_surface: "architecture boundary rules + DB role separation"
  boundary_mode_final: REAL
  verification: [TEST-ARCH-BOUNDARY, TEST-SEC-SVCID]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-008:
  class: F1
  area: EVT
  work_packages: [WP-EVT-001]
  target_milestone: M1
  architecture: [ARCH-CTR-VERSIONING, ARCH-EVT-SCHEMA]
  planned_surface: "canonical-producer field + producer ACL on broker subjects"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-ARCH-BOUNDARY, TEST-EVT-SCHEMA]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-001:
  class: F1
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "machine-readable requirement catalog + ID lint"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-GOV-CATALOG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-002:
  class: F1
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "retired/superseded ID registry check in trace linter"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-GOV-CATALOG, TEST-GOV-TRACELINT]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-003:
  class: F1
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "catalog schema: single PrimaryOwner field; CODEOWNERS alignment"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-GOV-CATALOG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-004:
  class: F1
  area: GOV
  work_packages: [WP-GOV-002, WP-DOC-002]
  target_milestone: M2
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "DERIVED_FROM edge completeness rule in trace linter"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-GOV-TRACELINT]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-007:
  class: F1
  area: GOV
  work_packages: [WP-GOV-004]
  target_milestone: M6
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "requirement-change PR template + freeze-impact review record"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [INSP-GOV-CHANGECTRL]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-008:
  class: F1
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "ScopeClass enum F0/F1/R1 in catalog schema"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-GOV-CATALOG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-010:
  class: F1
  area: GOV
  work_packages: [WP-GOV-003, WP-DOC-006]
  target_milestone: M5
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "VERIFIED-state derivation only from applicable CURRENT evidence"
  boundary_mode_final: REAL
  verification: [TEST-GOV-TRACELINT, INSP-GOV-ACCEPT]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-001:
  class: F0
  area: HITL
  work_packages: [WP-HITL-001, WP-RES-009]
  target_milestone: M3
  architecture: [ARCH-HITL-POLICY, ARCH-SEC-AUTHZ]
  planned_surface: "deterministic policy evaluation independent of AI text"
  boundary_mode_final: REAL
  verification: [TEST-HITL-POLICY, TEST-AUTH-NEG, AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-002:
  class: F1
  area: HITL
  work_packages: [WP-HITL-001]
  target_milestone: M3
  architecture: [ARCH-HITL-POLICY]
  planned_surface: "L0–L4 policy classes in AuthorityPolicy/ActionCatalog metadata"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-HITL-POLICY, BENCH-RQ3-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-003:
  class: F1
  area: HITL
  work_packages: [WP-HITL-002]
  target_milestone: M3
  architecture: [ARCH-HITL-APPROVAL]
  planned_surface: "approval ↔ Proposal revision binding"
  boundary_mode_final: REAL
  verification: [TEST-HITL-BINDING, AV-SCEN-01, AV-SCEN-04]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-004:
  class: F1
  area: HITL
  work_packages: [WP-HITL-002]
  target_milestone: M3
  architecture: [ARCH-HITL-APPROVAL]
  planned_surface: "approval ↔ Plan revision binding; material plan change invalidation"
  boundary_mode_final: REAL
  verification: [TEST-HITL-BINDING, AV-SCEN-01, AV-SCEN-04]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-005:
  class: F1
  area: HITL
  work_packages: [WP-HITL-002]
  target_milestone: M3
  architecture: [ARCH-HITL-APPROVAL, ARCH-HITL-EXPIRY, ARCH-WORLD-SCOPE]
  planned_surface: "WorldID + freshness/revision scope on approval"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-HITL-BINDING, AV-SCEN-10]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-006:
  class: F1
  area: HITL
  work_packages: [WP-HITL-003, WP-TEST-003]
  target_milestone: M3
  architecture: [ARCH-HITL-EXPIRY]
  planned_surface: "expiry/replay/nonce checks at execution time"
  boundary_mode_final: REAL
  verification: [TEST-HITL-REPLAY-NEG, AV-SCEN-04, BENCH-RQ3-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-008:
  class: F1
  area: HITL
  work_packages: [WP-HITL-005]
  target_milestone: M4
  architecture: [ARCH-HITL-APPROVAL, ARCH-OBS-AUDIT]
  planned_surface: "ApprovalRecord schema (decision, subject, binding, actor, timestamp)"
  boundary_mode_final: REAL
  verification: [TEST-HITL-RECORD, TEST-SEC-AUDIT]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-009:
  class: F1
  area: HITL
  work_packages: [WP-HITL-006]
  target_milestone: M4
  architecture: [ARCH-HITL-DUAL]
  planned_surface: "dual-approval enforcement (distinct identities)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-HITL-DUAL, BENCH-RQ3-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-001:
  class: F1
  area: ML
  work_packages: [WP-ML-002, WP-ML-007]
  target_milestone: M4
  architecture: [ARCH-AI-ORCH, ARCH-DATA-LINEAGE]
  planned_surface: "M1 equipment-risk model training/inference"
  boundary_mode_final: REAL
  verification: [TEST-ML-CONTRACT, BENCH-ML-M1-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-002:
  class: F1
  area: ML
  work_packages: [WP-ML-003, WP-ML-007]
  target_milestone: M4
  architecture: [ARCH-AI-ORCH, ARCH-DATA-LINEAGE]
  planned_surface: "M2 cycle-time/tardiness model"
  boundary_mode_final: REAL
  verification: [TEST-ML-CONTRACT, TEST-ML-LEAKAGE, BENCH-ML-M2-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-003:
  class: F1
  area: ML
  work_packages: [WP-ML-004, WP-ML-007]
  target_milestone: M4
  architecture: [ARCH-AI-ORCH, ARCH-DATA-LINEAGE]
  planned_surface: "M3 pre-inspection quality model"
  boundary_mode_final: REAL
  verification: [TEST-ML-CONTRACT, TEST-ML-LEAKAGE, BENCH-ML-M3-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-004:
  class: F1
  area: ML
  work_packages: [WP-ML-005]
  target_milestone: M4
  architecture: [ARCH-CTR-EVTSCHEMA, ARCH-AI-ORCH]
  planned_surface: "common Prediction contract + PredictionCreated event"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-ML-CONTRACT, TEST-EVT-SCHEMA]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-005:
  class: F1
  area: ML
  work_packages: [WP-VDATA-004, WP-ML-005]
  target_milestone: M5
  architecture: [ARCH-CTR-EVTSCHEMA, ARCH-DATA-LINEAGE]
  planned_surface: "ModelPackage/version + input revision fields"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-ML-CONTRACT, INSP-AI-BEHAVIOR]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-006:
  class: F1
  area: ML
  work_packages: [WP-ML-006]
  target_milestone: M5
  architecture: [ARCH-AI-ORCH]
  planned_surface: "calibration step + calibrated probability output"
  boundary_mode_final: REAL
  verification: [BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-007:
  class: F1
  area: ML
  work_packages: [WP-SIM-007, WP-ML-001]
  target_milestone: M4
  architecture: [ARCH-DATA-LINEAGE]
  planned_surface: "DatasetVersion/SplitManifest binding in training/eval runs"
  boundary_mode_final: REAL
  verification: [INSP-DATA-PROVENANCE, BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-ML-008:
  class: F1
  area: ML
  work_packages: [WP-ML-001]
  target_milestone: M4
  architecture: [ARCH-DATA-LINEAGE]
  planned_surface: "FINAL-partition access guard in training/tuning jobs"
  boundary_mode_final: REAL
  verification: [TEST-ML-LEAKAGE, TEST-DATA-SPLITLEAK, INSP-EVAL-PARTITION, BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-001:
  class: F1
  area: RAG
  work_packages: [WP-RAG-001]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-DATA-VECTOR, ARCH-DATA-PG]
  planned_surface: "versioned corpus ingestion + DocumentVersion metadata in PostgreSQL"
  boundary_mode_final: REAL
  verification: [TEST-RAG-RETRIEVAL, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-002:
  class: F1
  area: RAG
  work_packages: [WP-RAG-005]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-DATA-VECTOR]
  planned_surface: "documentary evidence type separate from operational evidence type"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-AI-OUTPUT, TEST-ARCH-BOUNDARY]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-003:
  class: F1
  area: RAG
  work_packages: [WP-RAG-002]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-DATA-VECTOR]
  planned_surface: "sparse retrieval profile"
  boundary_mode_final: REAL
  verification: [TEST-RAG-RETRIEVAL, BENCH-RAG-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-004:
  class: F1
  area: RAG
  work_packages: [WP-RAG-002]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-DATA-VECTOR]
  planned_surface: "dense retrieval profile (embedding model: OD-RAG-02)"
  boundary_mode_final: REAL
  verification: [TEST-RAG-RETRIEVAL, BENCH-RAG-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-005:
  class: F1
  area: RAG
  work_packages: [WP-RAG-002, WP-R2-001]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-DATA-VECTOR]
  planned_surface: "hybrid retrieval via Qdrant native fusion"
  boundary_mode_final: REAL
  verification: [TEST-RAG-RETRIEVAL, BENCH-RAG-001, BENCH-RQ1-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-006:
  class: F1
  area: RAG
  work_packages: [WP-RAG-003]
  target_milestone: M4
  architecture: [ARCH-AI-RAG]
  planned_surface: "chunk provenance (DocumentVersion, chunk span) in retrieval results"
  boundary_mode_final: REAL
  verification: [TEST-RAG-PROVENANCE, BENCH-RAG-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-007:
  class: F1
  area: RAG
  work_packages: [WP-RAG-004]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-SEC-AUTHZ]
  planned_surface: "eligibility/rights payload filter at query time"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-RAG-RIGHTS]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-008:
  class: F1
  area: RAG
  work_packages: [WP-RAG-004]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-AI-TOOLS, ARCH-SEC-AUTHZ]
  planned_surface: "retrieved-content-as-data isolation in prompt assembly"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-RAG-INJECTION, BENCH-RQ3-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-009:
  class: F1
  area: RAG
  work_packages: [WP-RAG-001, WP-RAG-007, WP-RES-011]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-DATA-LINEAGE]
  planned_surface: "CorpusVersion/RetrievalProfile binding in ExperimentDefinition"
  boundary_mode_final: REAL
  verification: [INSP-AI-BEHAVIOR, BENCH-RQ1-001, BENCH-RAG-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-RAG-010:
  class: F1
  area: RAG
  work_packages: [WP-RAG-003, WP-RES-007]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-AI-ORCH]
  planned_surface: "citation-bearing EvidenceRef in RootCauseAssessment"
  boundary_mode_final: REAL
  verification: [TEST-RAG-PROVENANCE, TEST-AI-OUTPUT, AV-SCEN-01, BENCH-RQ1-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-003:
  class: F1
  area: SEC
  work_packages: [WP-SEC-003]
  target_milestone: M3
  architecture: [ARCH-SEC-AUTHZ, ARCH-CORE-CMD]
  planned_surface: "backend authorization checks on protected commands"
  boundary_mode_final: REAL
  verification: [TEST-SEC-AUTHZ-NEG, AV-SCEN-04, BENCH-RQ3-001]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-009:
  class: F1
  area: SEC
  work_packages: [WP-RAG-004]
  target_milestone: M4
  architecture: [ARCH-AI-RAG, ARCH-SEC-AUTHZ]
  planned_surface: "authorization policy source isolated from corpus content"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-RAG-INJECTION, TEST-AUTH-NEG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-001:
  class: F0
  area: TWIN
  work_packages: [WP-TWIN-001]
  target_milestone: M1
  architecture: [ARCH-TWIN-PROJECTOR, ARCH-TWIN-STATE, ARCH-TWIN-API]
  planned_surface: "twin-projector-worker + twin-query-api + `twin` schema"
  boundary_mode_final: REAL
  verification: [TEST-TWIN-PROJECTION, E2E-01, AV-SCEN-01, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-002:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-001]
  target_milestone: M1
  architecture: [ARCH-TWIN-PROJECTOR]
  planned_surface: "event-consumer projection handlers (no mutation endpoint)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-TWIN-PROJECTION, TEST-TWIN-READONLY]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-003:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-002]
  target_milestone: M2
  architecture: [ARCH-TWIN-STATE, ARCH-WORLD-SCOPE]
  planned_surface: "epistemic-class tagging in projection model"
  boundary_mode_final: REAL
  verification: [TEST-TWIN-EPISTEMIC, AV-SCEN-01, AV-SCEN-09]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-004:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-002]
  target_milestone: M2
  architecture: [ARCH-TWIN-FRESHNESS, ARCH-TWIN-API]
  planned_surface: "revision/freshness metadata on query responses"
  boundary_mode_final: REAL
  verification: [TEST-TWIN-FRESHNESS, AV-SCEN-01, BENCH-PERF-CORE]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-005:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-002]
  target_milestone: M2
  architecture: [ARCH-TWIN-FRESHNESS]
  planned_surface: "sequence-gap detector + stale marking"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-TWIN-FRESHNESS, AV-SCEN-07]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-006:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-004, WP-TEST-004]
  target_milestone: M5
  architecture: [ARCH-TWIN-REBUILD]
  planned_surface: "rebuild job from retained canonical events/Core sources"
  boundary_mode_final: REAL
  verification: [TEST-TWIN-PROJECTION, RES-TWINREBUILD-001, AV-SCEN-08]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-007:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-005, WP-TEST-005]
  target_milestone: M4
  architecture: [ARCH-TWIN-STATE, ARCH-WORLD-ISOLATION]
  planned_surface: "what-if stream family separated from primary projection"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-TWIN-EPISTEMIC, AV-SCEN-09]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-008:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-003]
  target_milestone: M2
  architecture: [ARCH-TWIN-API, ARCH-SEC-AUTHZ]
  planned_surface: "read-only query API + SchedulingSnapshot export; consumer read scopes"
  boundary_mode_final: REAL
  verification: [TEST-TWIN-READONLY, TEST-AUTH-NEG, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-009:
  class: F1
  area: TWIN
  work_packages: [WP-TWIN-001]
  target_milestone: M1
  architecture: [ARCH-TWIN-PROJECTOR, ARCH-TWIN-FRESHNESS]
  planned_surface: "projection revision ↔ source EventID/revision ledger"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-TWIN-PROJECTION]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-TWIN-010:
  class: F1
  area: TWIN
  work_packages: [WP-CORE-008, WP-TWIN-006]
  target_milestone: M3
  architecture: [ARCH-TWIN-API, ARCH-AUTO-VERIFY]
  planned_surface: "post-condition verification query used by workflows"
  boundary_mode_final: REAL
  verification: [AV-SCEN-01, E2E-01, BENCH-E2E-001, DEMO-GS01-001]
  evidence_env: "INTEGRATION + EVALUATION + DEMO"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-001:
  class: F0
  area: UI
  work_packages: [WP-UI-001]
  target_milestone: M1
  architecture: [ARCH-EDGE-WEB, ARCH-EDGE-BFF]
  planned_surface: "React/Vite SPA shell via BFF only"
  boundary_mode_final: REAL
  verification: [TEST-UI-BROWSER, E2E-01, AV-SCEN-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-002:
  class: F1
  area: UI
  work_packages: [WP-UI-002, WP-S-001]
  target_milestone: M2
  architecture: [ARCH-EDGE-WEB, ARCH-EDGE-BFF, ARCH-EDGE-NOTIFY]
  planned_surface: "manufacturing facility/Twin state views scoped to active WorldID"
  boundary_mode_final: REAL
  verification: [TEST-UI-BROWSER, AV-SCEN-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-004:
  class: F1
  area: UI
  work_packages: [WP-UI-004]
  target_milestone: M4
  architecture: [ARCH-EDGE-WEB]
  planned_surface: "RCA hypothesis/evidence/abstention panels"
  boundary_mode_final: REAL
  verification: [TEST-UI-BROWSER, AV-SCEN-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-006:
  class: F1
  area: UI
  work_packages: [WP-UI-006]
  target_milestone: M3
  architecture: [ARCH-HITL-UI, ARCH-EDGE-WEB]
  planned_surface: "pending/completed approvals with bound context"
  boundary_mode_final: REAL
  verification: [TEST-UI-BROWSER, AV-SCEN-01, AV-SCEN-04, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-008:
  class: F1
  area: UI
  work_packages: [WP-UI-008]
  target_milestone: M5
  architecture: [ARCH-EDGE-WEB]
  planned_surface: "epistemic-class visual encoding system"
  boundary_mode_final: REAL
  verification: [TEST-UI-SEMANTICS, AV-SCEN-09, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-010:
  class: F1
  area: UI
  work_packages: [WP-UI-010]
  target_milestone: M5
  architecture: [ARCH-EDGE-WEB, ARCH-OBS-AUDIT, ARCH-OBS-TRACE]
  planned_surface: "incident/decision timeline composed from correlated records"
  boundary_mode_final: REAL
  verification: [TEST-UI-BROWSER, AV-SCEN-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-005:
  class: S2
  area: CAP
  work_packages: [WP-CORE-006, WP-PERF-003]
  target_milestone: M7
  metric: "domain command throughput without correctness failure"
  threshold: "20 cmd/s × 5 min"
  workload_profile: "controlled synthetic load"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-CORE]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-002:
  class: H0
  area: DATA
  work_packages: [WP-VDATA-002, WP-RES-002]
  target_milestone: M5
  metric: "prohibited entity/group overlap across frozen train/calibration/final partitions"
  threshold: "= 0"
  workload_profile: "all frozen SplitManifests"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DATA-SPLITLEAK, INSP-EVAL-PARTITION]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-005:
  class: H0
  area: DATA
  work_packages: [WP-EVT-001, WP-TEST-002]
  target_milestone: M1
  metric: "formal messages/artifacts in final evidence failing declared schema/version validation"
  threshold: "= 0"
  workload_profile: "final evidence"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DATA-CONTRACTVALID, TEST-EVT-SCHEMA]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-006:
  class: H0
  area: DATA
  work_packages: [WP-VDATA-001]
  target_milestone: M4
  metric: "formal-claim datasets/corpora identifying source, version, rights/provenance"
  threshold: "100%"
  workload_profile: "final datasets/corpora"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-DATA-PROVENANCE, INSP-VIS-DATASET, TEST-DATA-REFINTEGRITY]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-001:
  class: H0
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  metric: "catalog lint violations"
  threshold: "0 missing/duplicate NFRIDs"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-GOV-CATALOG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-002:
  class: H0
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  metric: "retired-ID reuse detections"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-GOV-CATALOG, TEST-GOV-TRACELINT]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-003:
  class: H0
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  metric: "NFRs without exactly one PrimaryOwner"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-GOV-CATALOG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-007:
  class: H0
  area: GOV
  work_packages: [WP-GOV-001]
  target_milestone: M0
  metric: "NFRs without H0/A1/S2/C3 class"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-GOV-CATALOG, INSP-GOV-NFR]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-008:
  class: H0
  area: GOV
  work_packages: [WP-GOV-004]
  target_milestone: M6
  metric: "post-M6 material NFR changes without freeze-impact review"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-GOV-CHANGECTRL, TEST-GOV-TRACELINT]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-010:
  class: H0
  area: GOV
  work_packages: [WP-GOV-003, WP-X-001]
  target_milestone: M5
  metric: "composite/averaged quality score used for NFR disposition"
  threshold: "0 uses"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-GOV-ACCEPT, TEST-GOV-TRACELINT]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-001:
  class: S2
  area: PERF
  work_packages: [WP-CORE-006, WP-TWIN-003, WP-PERF-002, WP-R2-003]
  target_milestone: M7
  metric: "backend/BFF receipt→response latency, common Core/Twin reads"
  threshold: "p95 ≤ 500 ms"
  workload_profile: "WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-CORE]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-002:
  class: S2
  area: PERF
  work_packages: [WP-CORE-006, WP-PERF-002]
  target_milestone: M7
  metric: "command accepted/rejected decision latency (not effect)"
  threshold: "p95 ≤ 750 ms"
  workload_profile: "WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-CORE]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-003:
  class: A1
  area: PERF
  work_packages: [WP-EVT-006, WP-PERF-002]
  target_milestone: M7
  metric: "committed outbox record → durable broker publication delay"
  threshold: "p95 ≤ 2 s; p99 ≤ 5 s"
  workload_profile: "WP-NORMAL (healthy deps)"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-CORE]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-004:
  class: A1
  area: PERF
  work_packages: [WP-TWIN-003, WP-PERF-002]
  target_milestone: M2
  metric: "canonical event → readable Twin projection lag"
  threshold: "p95 ≤ 2 s; p99 ≤ 5 s"
  workload_profile: "WP-NORMAL (healthy backbone)"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-CORE]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-005:
  class: S2
  area: PERF
  work_packages: [WP-UI-002, WP-PERF-002]
  target_milestone: M2
  metric: "backend/Twin current → primary view reflects update"
  threshold: "p95 ≤ 3 s"
  workload_profile: "WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile) + accepted local/integration network"
  verification: [BENCH-PERF-UI]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-006:
  class: S2
  area: PERF
  work_packages: [WP-RAG-002, WP-PERF-002]
  target_milestone: M4
  metric: "top-k retrieval latency, frozen corpus/RetrievalProfile (excl. LLM)"
  threshold: "p95 ≤ 2 s"
  workload_profile: "frozen final corpus"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-AI]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-007:
  class: S2
  area: PERF
  work_packages: [WP-AI-007]
  target_milestone: M7
  metric: "orchestrator start → structured RCA result"
  threshold: "p95 ≤ 60 s (outage scenarios separate)"
  workload_profile: "final RCA cases"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile) + opaque external provider context"
  verification: [BENCH-PERF-AI, INSP-REP-LLM]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-014:
  class: S2
  area: PERF
  work_packages: [WP-UI-001, WP-PERF-002]
  target_milestone: M1
  metric: "primary route actionable after warm app startup"
  threshold: "p95 ≤ 3 s"
  workload_profile: "accepted LAN/client profile"
  hardware_profile: "HP: accepted client profile (recorded)"
  verification: [BENCH-PERF-UI]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-008:
  class: S2
  area: REC
  work_packages: [WP-TWIN-004, WP-DR-003]
  target_milestone: M5
  metric: "mandatory Twin projection rebuild duration"
  threshold: "≤ 60 min"
  workload_profile: "final benchmark-scale retained canonical data"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-TWINREBUILD-001, AV-SCEN-08]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-009:
  class: S2
  area: REC
  work_packages: [WP-RAG-006, WP-DR-003]
  target_milestone: M5
  metric: "Qdrant/RAG index rebuild from canonical artifacts, no manual reconstruction"
  threshold: "≤ 60 min"
  workload_profile: "final corpus"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-IDXREBUILD-001]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-002:
  class: H0
  area: REL
  work_packages: [WP-HITL-003]
  target_milestone: M3
  metric: "accepted stale/replayed/mismatched protected executions"
  threshold: "= 0"
  workload_profile: "final authority suite (BENCH-RQ3-001 adversarial share)"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-HITL-REPLAY-NEG, AV-SCEN-04, AV-SCEN-10, BENCH-RQ3-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-010:
  class: H0
  area: REL
  work_packages: [WP-CORE-008, WP-TWIN-006]
  target_milestone: M3
  metric: "unresolved semantic mismatch between verified Core effect and Twin state at run end"
  threshold: "= 0 per valid closed-loop run"
  workload_profile: "closed-loop runs (E2E matrix, AV-SCEN-01/02)"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [AV-SCEN-01, BENCH-E2E-001, RES-TWINREBUILD-001]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-002:
  class: H0
  area: REP
  work_packages: [WP-RES-004]
  target_milestone: M6
  metric: "canonical numerical results/tables regenerated from frozen raw inputs + AnalysisPackage"
  threshold: "identical under rounding rules"
  workload_profile: "frozen FBC-01 raw evidence"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-EVAL-ANALYSIS, TEST-REP-ANALYSIS]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-009:
  class: C3
  area: REP
  work_packages: [WP-AI-005]
  target_milestone: M4
  metric: "provider/model identity, timestamps, raw outputs, repeated trials, aggregate uncertainty"
  threshold: "C3 — characterize (byte identity not required)"
  workload_profile: "RCA robustness study (30 cases × 5 generations)"
  hardware_profile: "opaque external provider (context recorded)"
  verification: [INSP-REP-LLM, BENCH-RQ1-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-004:
  class: H0
  area: SEC
  work_packages: [WP-AI-006, WP-SEC-008, WP-BENCH-003]
  target_milestone: M3
  metric: "rejection rate of unauthorized protected-action attempts"
  threshold: "100%"
  workload_profile: "final negative authority suite"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-AUTH-NEG, TEST-SEC-AUTHZ-NEG, BENCH-RQ3-001, AV-SCEN-04]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-009:
  class: H0
  area: SEC
  work_packages: [WP-AI-005, WP-SEC-008]
  target_milestone: M4
  metric: "external LLM requests containing secrets / Oracle truth / rights-prohibited data"
  threshold: "= 0"
  workload_profile: "formal AI runs"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-EGRESS, AV-SCEN-11]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-UX-001:
  class: A1
  area: UX
  work_packages: [WP-UI-008]
  target_milestone: M5
  metric: "safety/authority-critical states encoded by color only"
  threshold: "= 0"
  workload_profile: "primary Command Center flows"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-UI-SEMANTICS]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-UX-002:
  class: H0
  area: UX
  work_packages: [WP-TWIN-002, WP-UI-008]
  target_milestone: M2
  metric: "known-stale user-facing state presented as current"
  threshold: "= 0"
  workload_profile: "staleness injection (AV-SCEN-07/08)"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-UI-SEMANTICS, AV-SCEN-07]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-UX-003:
  class: H0
  area: UX
  work_packages: [WP-UI-006]
  target_milestone: M3
  metric: "protected approvals without inspectable proposal/plan/revision/risk context"
  threshold: "= 0"
  workload_profile: "Approval Center flows"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-UI-SEMANTICS, AV-SCEN-01]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-UX-004:
  class: A1
  area: UX
  work_packages: [WP-UI-008]
  target_milestone: M5
  metric: "known failures shown as indefinite success-looking spinner"
  threshold: "= 0"
  workload_profile: "failure-injected UI flows"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-UI-SEMANTICS]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-UX-005:
  class: A1
  area: UX
  work_packages: [WP-UI-011]
  target_milestone: M8
  metric: "primary flow browser E2E on current stable Chromium-family + Firefox (versions recorded)"
  threshold: "PASS on both at M8"
  workload_profile: "primary Command Center flows"
  hardware_profile: "HP: recorded browser versions"
  verification: [TEST-UI-BROWSER]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-UX-006:
  class: H0
  area: UX
  work_packages: [WP-UI-012, WP-DOC-004]
  target_milestone: M8
  metric: "approvals/validation/failures/effect verification concealed or bypassed by Presenter Mode"
  threshold: "= 0"
  workload_profile: "DEMO profile + GS-01 rehearsal"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-UI-SEMANTICS, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
```

## 20. Definition of Final Role Completion

This role is complete at M8 when every line below is true and demonstrable from generated artifacts — not when the owner believes the work is done.

| # | Completion criterion |
|---|---|
| C-1 | All 73 owned work packages are at DoD (04 §4.2), with real repository references replacing `TBD_BY_IMPLEMENTATION` |
| C-2 | All 124 owned requirements have a final disposition in 03 — VERIFIED, or an explicitly recorded FAIL/MISS/REBASELINED with analysis |
| C-3 | Every owned F0 requirement is verified on a real integrated path (FR-AI-001, FR-AI-004, FR-CORE-001, FR-CORE-002, FR-EVT-001, FR-HITL-001, FR-TWIN-001, FR-UI-001) |
| C-4 | Every owned H0 requirement (17) has hard/negative evidence with zero-count assertions satisfied |
| C-5 | Every owned A1/S2/C3 requirement has a measurement executed in the correct environment with its HardwareProfile/WorkloadProfile bound |
| C-6 | Every downstream commitment (18 HARD edges) was delivered at its required readiness with unblock evidence |
| C-7 | All owned contracts are versioned, documented and consumed by their real consumers — no consumer still runs on fixtures in the acceptance path |
| C-8 | Owned ADRs exist for the decisions listed in §14, and 03 trace edges are current |
| C-9 | Owned research lanes executed from frozen artifacts with dispositions recorded; claims traced to sealed evidence |
| C-10 | Owned red-team findings are resolved or explicitly accepted before release |
| C-11 | No owned capability depends on a development fixture, a manual host step or an unrecorded configuration |
| C-12 | A teammate who is not this owner can run the owned capability from documentation alone (cross-familiarity, TEAM-R01) |

---

*End of 06A_Asrin_Engineering_Roadmap.md (Draft — Derived from Approved 01/02 Baseline).*

## Final human reconciliation binding — 2026-10-13

01 §Final Human Reconciliation and02 §Final human reconciliation govern this projection. Vision/NDT publishes immutable InspectionObservation (existing EVT-InspectionObservation-v1); Core normalizes separate InspectionResult (existing IC-VIS-002) and owns canonical manufacturing/quality state. PlaceLotOnHold / CMD-PlaceLotOnHold-v1 is the single hold-placement command; ApplyMaterialHold is deprecated terminology, never a second contract. Other protected identities follow the01 action table, with exact approval/revision/freshness/idempotency binding. Simulator/Oracle, Twin/Qdrant projections, AI READ/SIMULATE/PROPOSE, Scheduler candidates, HITL, identity and UI boundaries remain unchanged.

ARCH-AUTO-WORKFLOW (durable Automation/Temporal layer) coordinates GS-01/E2E across Inspection/NDT→Core quality→RCA→recovery→HITL→governed Core commands→verified effect→Twin/Audit. It does not acquire Core authority. MC-2 accountable owner is Asrın Dündar; contributing WP owners remain73/17/32/57. The primary shared-host HardwareProfile and accepted LaneA/B/C portfolio are pinned in01; acquisition/rights/source fields not locally verified are NEEDS_SOURCE_VERIFICATION, not invented facts or performance results. Real/public held-out evaluation and source-specific limitations remain mandatory where claimed.

HARD/SOFT refer to declared work/readiness consumers, not automatic runtime/deployment/import relations. Non-CONTRACT F1 entries DEP-025/045/058/076/094 have no fixture fallback: real producer readiness at the declared stage is required, while development stubs are not satisfaction evidence. DN-VIS-MODELS now declares INTEGRATION_READY for DEP-060/194; operational serving must load promoted required-mode artifacts with provenance. Source-supported deadlines and per-consumer scope are defined in05, without shifting canonical ownership or schedules.

GAP-RTM-004/005 remain ACCEPTED_WITH_RATIONALE for this pre-implementation baseline: missing canonical record metadata is not fabricated. FR-GOV-001/004 and the relevant NFR owners must supply/review actual fields and measurement definitions before their declared gates; projectctl retains nulls/warnings and never grants READY/VERIFIED from planned prose. Owner trace confirmation GAP-RTM-006 and final schema/version/card specifics remain ordinary implementation/review prerequisites, not unresolved choices among the eight approved policy groups.
