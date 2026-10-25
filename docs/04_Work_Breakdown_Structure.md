# 04 — Work Breakdown Structure
## Intelligent Manufacturing Operations Platform for Critical Aerospace Components — Capability Areas, Work Packages, Deliverables and Verification Work

| Field | Value |
|---|---|
| Document | `04_Work_Breakdown_Structure.md` |
| Status | **Draft — Derived from Approved 01/02 Baseline** (requires owner review per §16) |
| Version | v0.1.0-draft |
| Generated | 17 Eylül 2026 (pre-implementation) |
| Canonical sources | 01 Master Project Specification (Items 62, 64–69, 79, 81–85); 02 System Architecture Specification |
| Upstream downstream artifacts | 03 Requirements Traceability Matrix v0.1.0-draft; 05 Dependency Graph v0.1.0-draft |
| Production doctrine | 00 Production Guide §13 (File 04) |
| Scale | 179 work packages across 29 capability areas; 306 requirements covered (186 FR + 120 NFR) |
| Mandatory vs optional | 26 F0 · 125 F1 · 23 R1 · 3 R2 · 2 S (R2/S never on a mandatory or critical path) |
| Status of every WP today | `NOT_STARTED` — no implementation, no repository path, no test result exists |
| Machine-readable companion | `04_wbs/` (work packages, requirement coverage, deliverables, task register) |

> **Reading rule.** A work package states *what must exist and be proven*, not how many hours it takes. Repository paths are `TBD_BY_IMPLEMENTATION`; no verification result, evidence ID or completion status is claimed anywhere in this document.

---

## Table of Contents

1. Purpose and Scope
2. Sources, Precedence and Identity Namespaces
3. WBS Hierarchy, Work Package Schema and Sizing Discipline
4. Definition of Ready / Definition of Done (proposed rule sets)
5. Program Summary and Coverage Statistics
6. Capability Areas and Work Packages
7. Requirement Coverage Matrix
8. Milestone Rollup
9. Owner Rollups and Load Analysis
10. Integration, Failure-Path, Observability and Acceptance Work Visibility
11. Dependency Alignment with 05
12. Mandatory vs Stretch Isolation (R2 / S / X)
13. Risk Hooks
14. Findings Register
15. Machine-Readable Companion
16. WBS Maintenance Protocol
17. Rejected Alternatives
18. Guide §13 Compliance Check and Audit

---

## 1. Purpose and Scope

Convert 306 approved requirements, the 02 architecture and the 05 dependency graph into engineering work packages that can actually be picked up — including the work that is usually forgotten: contract implementation, integration, failure paths, observability, acceptance testing, measurement, recovery drills and evidence production.

| In scope | Out of scope (owned elsewhere) |
|---|---|
| Capability areas → work packages → deliverables → major tasks | Per-person sprint sequencing and calendars (06A–D roadmaps) |
| Scope class per WP and explicit stretch isolation | Milestone entry/exit ceremonies (07) |
| Source requirements, architecture components and verification work per WP | DoR/DoD ratification (08 — §4 here is a proposal) |
| Integration and verification work as first-class packages | Change-request mechanics (09) |
| Dependency alignment and blocking relationships | Dependency semantics themselves (05) |
| Requirement coverage proof (every FR/NFR lands in ≥1 WP) | Requirement wording (01 Items 81/82) |

## 2. Sources, Precedence and Identity Namespaces

| Source | Used for |
|---|---|
| 01 Item 68 | ScopeClass semantics F0 / F1 / R1 / R2 / S / X and the mandatory capability inventory |
| 01 Item 62 | PrimaryOwner per capability; supporting-owner boundaries |
| 01 Items 65/66/67 | target milestones, sprint calendar, E2E-01 checkpoint content |
| 01 Item 64 | workflow doctrine: coherent engineering slices of roughly 0.5–3 focused days at task level |
| 01 Items 79/83/84/85 | benchmark campaign, traceability obligations, architecture validation scenarios, red-team review |
| 02 | architecture components (ARCH-*), deployables, contract namespaces |
| 03 RTM | RequirementIDs, verification families, evidence expectations per requirement |
| 05 Dependency Graph | DN-* readiness nodes, DEP-* edges, blocking stages and need-by points |

**Identity namespaces.** `WP-<AREA>-NNN` for work packages and `TASK-<AREA>-NNN` where a task needs its own identity (00 §8). 03 recorded a namespace hazard (GAP-RTM-013): Item 82 uses `WP-SMALL` / `WP-NORMAL` / `WP-STRESS` for **workload profiles**. The two are disambiguated by pattern — work packages always match `WP-[A-Z0-9]+-[0-9]{3}` (the area segment may contain digits, as in `WP-R2-001`), workload profiles never carry a numeric suffix — and every tool that parses either must use the full pattern, not a `WP-` prefix match. Workload profiles are additionally always written with their full name in this document (WBS-GAP-01).

## 3. WBS Hierarchy, Work Package Schema and Sizing Discipline

Decomposition: **Program → Capability Area → Work Package → Deliverable → Major Task / Verification Task**. This document stops at major tasks; it is deliberately not a micro-task tracker (00 §13).

| Field | Meaning in this document |
|---|---|
| WorkPackageID | `WP-<AREA>-NNN`, stable, never reused |
| Title / Purpose | what must exist and why it matters to the product or the research |
| PrimaryOwner / Supporting owners | single accountable owner (Item 62); supporting owner is the most frequent cross-boundary reviewer |
| ScopeClass | F0 / F1 / R1 / R2 / S; NFR-driven packages additionally carry the NFR class (H0/A1/S2/C3) |
| Source RequirementIDs | the requirements this WP is accountable for (03 is the authority for their wording) |
| Architecture components | ARCH-* identities derived from the source requirements via 03 |
| Readiness node / Dependencies | the 05 node this WP advances and the DEP-* edges that gate it |
| Deliverables | artifacts that must exist when the WP is done (code, contract, config, runbook, dataset, measurement, drill record) |
| Major tasks | coherent engineering slices, roughly 0.5–3 focused days each at task level |
| Verification work | planned verification families from 03 (test / benchmark / drill / inspection) |
| Target milestone / sprint window | from Items 65/66/67 |
| DoR / DoD references | proposed rule sets in §4 (08 is authoritative once produced) |
| Cut / fallback semantics | what may be reduced and what may never be reduced (05 fallback classes F0–F4) |
| Expected evidence artifact | the evidence type this WP will eventually produce — never an evidence ID |
| Status | `NOT_STARTED` for all packages in this draft |

**Sizing.** Indicative bands only (S ≈ 1–3, M ≈ 4–7, L ≈ 7–12 focused days). No hour-level estimates are produced: hour precision before implementation is false precision (00 §13). Bands describe a work package as a whole; its internal tasks follow the 0.5–3 day slice discipline.

## 4. Definition of Ready / Definition of Done (proposed rule sets)

08 §14 ratifies the following rule identities, derived from 01 Items 64, 66, 83, 84. Every WP card references these IDs; 08 governs their readiness/completion meaning and evidence obligations. Ratification does not mark any WP READY or DONE (CTRL-DOC-005 / CHG-016).

### 4.1 DoR — a work package may start when

| ID | Rule |
|---|---|
| DOR-WP-01 | Source RequirementIDs are listed and their wording is current in 01/03 |
| DOR-WP-02 | Target milestone and 05 readiness node are declared |
| DOR-WP-03 | Every HARD incoming dependency is at its required readiness, or an approved fallback (F1–F4) applies for development-stage work only |
| DOR-WP-04 | Consumer requirements are precise (05 DEP-RULE-06): the exact artifacts/fields needed are written down |
| DOR-WP-05 | Contracts this WP consumes are CONTRACT_READY with example fixtures, or this WP is the one producing them |
| DOR-WP-06 | Verification approach is identified (which 03 family, which boundary mode) |
| DOR-WP-07 | Owner and supporting reviewer are named; CODEOWNERS routing exists |
| DOR-WP-08 | For R1 packages: partition/seed policy and protocol status are known (no FINAL partition use before freeze) |

### 4.2 DoD — a work package is done when

| ID | Rule | Applies to |
|---|---|---|
| DOD-WP-01 | All declared deliverables exist in the repository or the runtime, with real references (no TBD) | all |
| DOD-WP-02 | Trace edges updated in the same PR (REALIZED_BY, VERIFIED_BY) — 03 §19 | all |
| DOD-WP-03 | Required CI gates green without retry-until-green; no quarantined test covering this WP | all |
| DOD-WP-04 | Negative and failure paths are tested, not only the happy path | F0/F1 + H0 |
| DOD-WP-05 | Cross-boundary behaviour verified against real infrastructure (no mocked broker/DB/identity in the acceptance path) | F0/F1 integration WPs |
| DOD-WP-06 | Observability exists: structured logs, correlation propagation and health surface for the capability | all runtime WPs |
| DOD-WP-07 | Documentation/runbook updated where operator action is possible | all runtime WPs |
| DOD-WP-08 | Measurement definition exists and a measurement has been executed in the correct environment/profile | NFR-driven WPs (H0/A1/S2/C3) |
| DOD-WP-09 | For H0: hard/negative evidence produced and counters are zero | H0 |
| DOD-WP-10 | For R1: the mechanism runs reproducibly; outcome direction is irrelevant to completion | R1 |
| DOD-WP-11 | Evidence produced is bound to Release/Environment/Hardware/Workload identities | evidence-producing WPs |
| DOD-WP-12 | Cut/fallback semantics honoured: no development fixture is used as milestone or final evidence (05 DEP-RULE-04) | all |

## 5. Program Summary and Coverage Statistics

| Prefix | Capability area | #WP | F0 | F1 (incl. NFR-driven) | R1 | R2/S | Owners | #Requirements touched |
|---|---|---|---|---|---|---|---|---|
| WP-GOV | Requirement Governance & Traceability | 4 | 0 | 4 | 0 | 0 | Asrın:2, Yavuz:2 | 20 |
| WP-CORE | Manufacturing Core / Backend | 8 | 3 | 5 | 0 | 0 | Asrın:8 | 22 |
| WP-EVT | Event Spine & Integration Contracts | 6 | 1 | 5 | 0 | 0 | Asrın:4, Yavuz:2 | 14 |
| WP-TWIN | Operational Digital Twin | 6 | 2 | 4 | 0 | 0 | Asrın:6 | 16 |
| WP-SIM | Operational Manufacturing Simulator | 9 | 4 | 4 | 1 | 0 | Batu:9 | 21 |
| WP-OBJ | Object / Artifact Layer | 2 | 0 | 2 | 0 | 0 | Yavuz:2 | 4 |
| WP-VIS | Visual Perception | 10 | 2 | 8 | 0 | 0 | Selman:10 | 16 |
| WP-VDATA | Vision Dataset & MLOps | 5 | 0 | 4 | 1 | 0 | Selman:5 | 9 |
| WP-ML | Predictive ML | 7 | 0 | 6 | 1 | 0 | Asrın:7 | 8 |
| WP-RAG | Documentary RAG | 7 | 0 | 6 | 1 | 0 | Asrın:7 | 13 |
| WP-AI | AI Orchestrator / RCA | 7 | 2 | 5 | 0 | 0 | Asrın:7 | 19 |
| WP-SCH | Scheduling & Optimization | 7 | 1 | 6 | 0 | 0 | Batu:7 | 15 |
| WP-VALID | Schedule Validation | 2 | 1 | 1 | 0 | 0 | Batu:2 | 3 |
| WP-AUTO | Durable Automation | 7 | 3 | 4 | 0 | 0 | Batu:7 | 19 |
| WP-HITL | HITL & Authority | 7 | 1 | 6 | 0 | 0 | Asrın:5, Yavuz:2 | 15 |
| WP-UI | Manufacturing Command Center | 12 | 2 | 10 | 0 | 0 | Asrın:8, Batu:2, Selman:1, Yavuz:1 | 18 |
| WP-PLAT | Platform & Runtime | 7 | 1 | 6 | 0 | 0 | Yavuz:7 | 24 |
| WP-CICD | CI/CD | 6 | 1 | 5 | 0 | 0 | Yavuz:6 | 10 |
| WP-OBS | Observability | 6 | 0 | 6 | 0 | 0 | Yavuz:6 | 14 |
| WP-SEC | Security | 8 | 0 | 8 | 0 | 0 | Yavuz:7, Asrın:1 | 16 |
| WP-DR | Backup & Disaster Recovery | 4 | 0 | 4 | 0 | 0 | Yavuz:4 | 12 |
| WP-TEST | Testing & Integration Scenarios | 8 | 2 | 6 | 0 | 0 | Yavuz:4, Asrın:2, Batu:2 | 22 |
| WP-PERF | Performance & Resilience Measurement | 6 | 0 | 6 | 0 | 0 | Yavuz:4, Batu:2 | 31 |
| WP-RES | Research & Evaluation Infrastructure | 12 | 0 | 0 | 12 | 0 | Asrın:7, Yavuz:3, Batu:1, Selman:1 | 32 |
| WP-BENCH | Final Benchmark Campaign | 5 | 0 | 0 | 5 | 0 | Yavuz:4, Asrın:1 | 17 |
| WP-DOC | Documentation, Thesis, Demo & Public Release | 6 | 0 | 4 | 2 | 0 | Asrın:4, Yavuz:2 | 10 |
| WP-R2 | Evidence-Gated Research Candidates | 3 | 0 | 0 | 0 | 3 | Asrın:2, Yavuz:1 | 4 |
| WP-S | Stretch Register | 1 | 0 | 0 | 0 | 1 | Asrın:1 | 1 |
| WP-X | Out-of-Scope Guard Rail | 1 | 0 | 0 | 0 | 1 | Asrın:1 | 1 |
| **Σ** |  | 179 | 26 | 125 | 23 | 5 |  | 306 |

| Target milestone | Sprint window | #WP | F0 | R1 | Areas |
|---|---|---|---|---|---|
| M0 | S1 | 2 | 0 | 0 | CICD, GOV |
| M1 | S2 | 13 | 8 | 0 | CICD, CORE, EVT, OBS, PLAT, SIM, TEST, TWIN, UI |
| M2 | S3–S4 | 21 | 3 | 0 | CICD, CORE, DOC, EVT, GOV, OBJ, PLAT, SCH, SIM, TEST, TWIN, UI, VIS |
| M3 | S5–S6 | 27 | 14 | 0 | AI, AUTO, CORE, HITL, OBS, SCH, SEC, SIM, TEST, TWIN, UI, VALID, VIS |
| M4 | S7–S8 | 39 | 1 | 0 | AI, AUTO, HITL, ML, OBS, RAG, SCH, SEC, SIM, TWIN, UI, VDATA, VIS |
| M5 | S9–S10 | 30 | 0 | 3 | AUTO, CICD, DR, EVT, GOV, HITL, ML, OBJ, OBS, PERF, PLAT, RAG, RES, SCH, SEC, TEST, TWIN, UI, VDATA |
| M6 | S11 | 17 | 0 | 11 | DOC, DR, GOV, ML, PERF, PLAT, RAG, RES, SIM, TEST, VDATA |
| M7 | S12 | 15 | 0 | 4 | AI, BENCH, CORE, DR, EVT, OBS, PERF, RES, SIM, VIS |
| M8 | S13 | 10 | 0 | 5 | BENCH, DOC, PLAT, RES, UI |
| — | unscheduled | 5 | 0 | 0 | R2, S, X |

| Coverage check | Value |
|---|---|
| Requirements with ≥1 owning WP | 306 / 306 (100%) |
| Work packages without a source requirement | 0 (guide §13 "requirement’sız work packages" avoided) |
| F0 requirements (17) with a dedicated F0 work package | 17 / 17 |
| Capability families demanded by guide §13 | all 24 present, plus governance and out-of-scope guard rails |
| R2/S work packages on a mandatory or critical path | 0 |
| Work packages with a fabricated repository path or test result | 0 |
## 6. Capability Areas and Work Packages

Each card below is one work package. `Status` is `NOT_STARTED` for all of them; repository references are `TBD_BY_IMPLEMENTATION` by design (pre-implementation honesty, 00 §7.3).

### 6.1 Requirement Governance & Traceability (`WP-GOV-*`, 4 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-GOV-001 | Machine-readable requirement catalog and ID lint | Asrın | F1 | M0 | L |
| WP-GOV-002 | Trace registry, edges and trace linter | Yavuz | F1 | M2 | L |
| WP-GOV-003 | Coverage reports and release acceptance record generation | Yavuz | F1 | M5 | M |
| WP-GOV-004 | Change control and freeze-impact tooling | Asrın | F1 | M6 | S |

#### WP-GOV-001 — Machine-readable requirement catalog and ID lint

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M0 / S1 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | L (≈7–12 focused days) |
| Status | NOT_STARTED |
| Repository reference | `requirements/`; `tools/projectctl/src/projectctl/requirement_catalog.py`; `evidence/WP-GOV-001/` |

**Purpose.** Turn the 306 approved requirements into a queryable catalog with enforced ID, class and owner rules so that every downstream artifact can be generated instead of hand-maintained.

**Source requirements (03).** FR-GOV-001, FR-GOV-002, FR-GOV-003, FR-GOV-008, NFR-GOV-001, NFR-GOV-002, NFR-GOV-003, NFR-GOV-007

**Architecture components (02).** ARCH-PLAT-CICD

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

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

**Verification work (03 planned families).** INSP-GOV-NFR, TEST-GOV-CATALOG, TEST-GOV-TRACELINT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut. Without it no downstream generation is trustworthy; manual spreadsheets are explicitly rejected.


#### WP-GOV-002 — Trace registry, edges and trace linter

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | L (≈7–12 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Implement the Item 83 trace graph (nodes, controlled relations, applicability) and the CI validation that keeps 03 honest as code lands.

**Source requirements (03).** FR-GOV-004, FR-GOV-005, FR-GOV-009, NFR-GOV-009

**Architecture components (02).** ARCH-DATA-OBJ, ARCH-PLAT-CICD, ARCH-PLAT-CLI

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- trace_edges registry + JSON Schema (seeded from 03 draft)
- trace linter with checks TL-01…TL-13 (03 §18.1)
- `mfgctl trace` generation of 03 views
- PR Requirement-Impact template

**Major tasks.**
- implement edge schema and registry loader
- implement referential checks against catalog, 02 ARCH registry and verification registry
- implement prefix-boundary-safe ID matching (03 GAP-RTM-016)
- implement generated-view freshness check
- wire PR template + CODEOWNERS routing by requirement owner

**Verification work (03 planned families).** INSP-GOV-ACCEPT, TEST-GOV-TRACELINT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for F0/F1 coverage checks; advanced query surface (`impacted`, `stale`) may follow M5.


#### WP-GOV-003 — Coverage reports and release acceptance record generation

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-RUNNER |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Generate acceptance artefacts (coverage report, release acceptance record) from evidence instead of assembling them manually at M8.

**Source requirements (03).** FR-GOV-006, FR-GOV-010, NFR-GOV-004, NFR-GOV-005, NFR-GOV-006, NFR-GOV-010

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-PLAT-CICD, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-114 (DN-PLAT-FAILVAL → DN-PLAT-RUNNER, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-115 (DN-PLAT-CD → DN-PLAT-RUNNER, HARD/INTEGRATION@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- AcceptanceCoverageReport generator
- ReleaseAcceptanceRecord generator
- evidence applicability resolver (Release/Env/HW/Workload binding)

**Major tasks.**
- define evidence binding rules per NFR class
- implement VERIFIED derivation only from CURRENT applicable evidence
- implement composite-score prohibition check
- dry-run report against empty evidence set to prove the pipeline

**Verification work (03 planned families).** INSP-GOV-ACCEPT, INSP-GOV-NFR, TEST-DATA-REFINTEGRITY, TEST-GOV-TRACELINT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut: M8 acceptance depends on it. May start as read-only report before full automation.


#### WP-GOV-004 — Change control and freeze-impact tooling

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make requirement/NFR changes and post-M6 freeze impacts visible and reviewable rather than silent.

**Source requirements (03).** FR-GOV-007, NFR-GOV-008

**Architecture components (02).** ARCH-PLAT-CICD

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- requirement-change PR template
- freeze-impact review record format
- post-M6 change gate in CI

**Major tasks.**
- define change classes and required reviewers
- implement freeze window detection from milestone state
- link change records to trace edges and affected evidence

**Verification work (03 planned families).** INSP-GOV-CHANGECTRL, TEST-GOV-TRACELINT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; the gate may be manual (checklist) before automation.


### 6.2 Manufacturing Core / Backend (`WP-CORE-*`, 8 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-CORE-001 | Canonical manufacturing domain model and core schema | Asrın | F0 | M1 | L |
| WP-CORE-002 | Manufacturing lifecycle state machine | Asrın | F1 | M2 | M |
| WP-CORE-003 | Command acceptance: idempotency, revision preconditions, durable outcomes | Asrın | F1 | M2 | L |
| WP-CORE-004 | Rework, split/merge and temporal genealogy | Asrın | F1 | M2 | M |
| WP-CORE-005 | Domain events and transactional outbox | Asrın | F0 | M1 | M |
| WP-CORE-006 | Core and Twin read/command performance profile | Asrın | F1 / S2 | M7 | S |
| WP-CORE-007 | Core database migrations and role separation | Asrın | F1 | M1 | M |
| WP-CORE-008 | Core ↔ Simulator ↔ Twin integration and acceptance | Asrın | F0 | M3 | M |

#### WP-CORE-001 — Canonical manufacturing domain model and core schema

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-CORE-CONTRACTS |
| Size band (indicative, no hour estimates) | L (≈7–12 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Establish the single canonical representation of orders, lots, serialized components, routes, operations and equipment references, including reentrant route/visit semantics, as the semantic root of the whole system.

**Source requirements (03).** FR-CORE-001, FR-CORE-002, FR-CORE-013

**Architecture components (02).** ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-CORE-DOMAIN

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

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

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, E2E-01, TEST-ARCH-BOUNDARY, TEST-AUTH-NEG, TEST-CORE-DOMAIN, TEST-CORE-GENEALOGY, TEST-SEC-SVCID

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Early CONTRACT_READY publication is the unlock for Simulator, Twin, Scheduler and Automation (05 CYC-01).


#### WP-CORE-002 — Manufacturing lifecycle state machine

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-CORE-TRANSITIONS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make legal manufacturing transitions (start/complete, hold, release, rework, split, merge) authoritative in Core so no other service invents legality.

**Source requirements (03).** FR-CORE-003, FR-CORE-007, FR-CORE-008

**Architecture components (02).** ARCH-CORE-CMD, ARCH-CORE-DOMAIN

**Inputs / required contracts.** gated by DEP-020 (DN-CORE-LIFECYCLE → DN-CORE-TRANSITIONS, HARD/START@COMPONENT_READY, need-by S2–S3)

**Deliverables.**
- transition guard module
- hold/release command handlers
- negative-path test suite (illegal transitions)

**Major tasks.**
- enumerate legal transitions per entity state
- implement guards with explicit rejection reasons
- implement PlaceLotOnHold / ReleaseMaterialHold handlers (naming per 05 DEP-GAP-06)
- write negative tests as first-class cases (not afterthoughts)

**Verification work (03 planned families).** AV-SCEN-01, E2E-01, TEST-AUTH-NEG, TEST-CORE-STATEMACHINE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut. Stability of this WP is a HARD precondition for Simulator validity claims, Scheduler validation and Automation execution.


#### WP-CORE-003 — Command acceptance: idempotency, revision preconditions, durable outcomes

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-CORE-CMDEXEC |
| Size band (indicative, no hour estimates) | L (≈7–12 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Guarantee that repeated or stale command submissions can never produce duplicate or unsafe manufacturing effects, and that every command has a durable, inspectable outcome.

**Source requirements (03).** FR-CORE-004, FR-CORE-005, FR-CORE-006, FR-CORE-016

**Architecture components (02).** ARCH-AUTO-IDEMPOTENCY, ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-CTR-API, ARCH-CTR-VERSIONING

**Inputs / required contracts.** gated by DEP-027 (DN-CORE-CMDCON → DN-CORE-CMDEXEC, HARD/START@CONTRACT_READY, need-by S2–S3), DEP-028 (DN-CORE-TRANSITIONS → DN-CORE-CMDEXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

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

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-05, RES-DUP-001, TEST-AUTO-OUTCOME, TEST-CORE-CONTRACT, TEST-CORE-IDEMP, TEST-CORE-REVISION, TEST-EVT-SCHEMA, TEST-HITL-REPLAY-NEG

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard-gate NFR-REL-001 depends on it).


#### WP-CORE-004 — Rework, split/merge and temporal genealogy

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-CORE-GENEALOGY |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Preserve full material history so RCA and exposure analysis can reason over lineage rather than current state only.

**Source requirements (03).** FR-CORE-009, FR-CORE-010, FR-CORE-011, FR-CORE-012

**Architecture components (02).** ARCH-CORE-DB, ARCH-CORE-DOMAIN, ARCH-CORE-GENEALOGY

**Inputs / required contracts.** gated by DEP-029 (DN-CORE-LIFECYCLE → DN-CORE-GENEALOGY, HARD/INTEGRATION@COMPONENT_READY, need-by M2 (S4))

**Deliverables.**
- append-only route-visit history
- split/merge relation model
- genealogy/exposure query API (relational, per backfill ADR 12)

**Major tasks.**
- implement ReworkDirective execution without overwriting history
- model split/merge lineage relations
- implement exposure queries used by AI tools
- performance-sanity checks on lineage queries at WP-NORMAL scale

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, BENCH-RQ1-001, TEST-CORE-GENEALOGY, TEST-CORE-STATEMACHINE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for F1; full-depth exposure queries are HARD for the full RQ-1 RCA configuration at M4 (05 §15).


#### WP-CORE-005 — Domain events and transactional outbox

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-CORE-OUTBOX |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Publish every accepted state change exactly once from the same transaction that mutates state, forming the factual basis of the event spine.

**Source requirements (03).** FR-CORE-014, FR-CORE-015

**Architecture components (02).** ARCH-CORE-DB, ARCH-CORE-OUTBOX, ARCH-EVT-OUTBOX

**Inputs / required contracts.** gated by DEP-022 (DN-CORE-LIFECYCLE → DN-CORE-OUTBOX, HARD/INTEGRATION@COMPONENT_READY, need-by M1 (S2))

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

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-07, RES-BROKER-001, TEST-CORE-OUTBOX, TEST-EVT-SCHEMA

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 spine).


#### WP-CORE-006 — Core and Twin read/command performance profile

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class S2) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-CORE-CMDEXEC |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Measure the latency and throughput envelope of the Core/Twin read and command paths under the approved workload profiles.

**Source requirements (03).** NFR-PERF-001, NFR-PERF-002, NFR-CAP-005

**Architecture components (02).** ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-TWIN-API

**Inputs / required contracts.** gated by DEP-027 (DN-CORE-CMDCON → DN-CORE-CMDEXEC, HARD/START@CONTRACT_READY, need-by S2–S3), DEP-028 (DN-CORE-TRANSITIONS → DN-CORE-CMDEXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- benchmark definitions for read/command paths
- measurement harness integration
- recorded distributions (p50/p95/p99) bound to Release/Env/HW/Workload

**Major tasks.**
- define sampling, warm-up and observation-count rules (≥100 observations)
- implement load driver for WP-NORMAL
- run and record; no threshold tuning after the fact

**Verification work (03 planned families).** BENCH-PERF-CORE

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** S2 class: MISS is a valid recorded outcome with analysis, never a silent adjustment.


#### WP-CORE-007 — Core database migrations and role separation

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-RT-PG |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep schema evolution automated, inspectable and privilege-separated from day one.

**Source requirements (03).** NFR-DEP-004, FR-CORE-013

**Architecture components (02).** ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-DATA-PG, ARCH-PLAT-CICD

**Inputs / required contracts.** gated by DEP-006 (DN-PLAT-COMPOSE → DN-RT-PG, HARD/START@SKELETON_READY, need-by M0), DEP-007 (DN-PLAT-INTEG → DN-RT-PG, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- migration tooling wiring
- per-service role/grant definitions
- migration status surface

**Major tasks.**
- choose migration runner and repository layout
- define roles for core/twin/automation/ai schemas
- wire migrations into CD with inspectable status
- negative test: cross-schema write denied

**Verification work (03 planned families).** TEST-ARCH-BOUNDARY, TEST-AUTH-NEG, TEST-DEP-MIGRATION, TEST-SEC-SVCID

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; direct DB mutation by non-owner services is architecturally forbidden.


#### WP-CORE-008 — Core ↔ Simulator ↔ Twin integration and acceptance

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-SIM-COREINT |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prove the Core–Simulator–Twin triangle on real infrastructure: authorized commands produce simulated effects, events project into Twin, and Core/Twin remain semantically consistent.

**Source requirements (03).** FR-CORE-003, FR-CORE-006, FR-TWIN-010, NFR-REL-010

**Architecture components (02).** ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-CORE-DB, ARCH-CORE-DOMAIN, ARCH-TWIN-API, ARCH-TWIN-PROJECTOR

**Inputs / required contracts.** gated by DEP-040 (DN-SIM-OPSEM → DN-SIM-COREINT, HARD/INTEGRATION@COMPONENT_READY, need-by M2 (S4)), DEP-041 (DN-CORE-CMDEXEC → DN-SIM-COREINT, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4)), DEP-042 (DN-EVT-SPINE → DN-SIM-COREINT, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- integration test suite across the three services
- AV-SCEN-01 / AV-SCEN-03 execution scripts
- consistency checker for Core vs Twin at run end

**Major tasks.**
- wire real NATS/PostgreSQL integration environment cases
- implement scenario drivers for normal production and inspection-triggered recovery
- implement end-of-run consistency assertion
- record failures as classified integration findings

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, E2E-01, RES-TWINREBUILD-001, TEST-AUTO-OUTCOME, TEST-CORE-IDEMP, TEST-CORE-STATEMACHINE

**Integration checkpoint.** AV-SCEN-01, AV-SCEN-03, E2E-01

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 integrated path, 03 View F).


### 6.3 Event Spine & Integration Contracts (`WP-EVT-*`, 6 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-EVT-001 | Integration Contract Registry and versioning discipline | Asrın | F0 | M1 | M |
| WP-EVT-002 | Message envelope, correlation and world scoping | Asrın | F1 | M1 | M |
| WP-EVT-003 | Idempotent consumer framework | Asrın | F1 | M2 | S |
| WP-EVT-004 | Replay, poison message and DLQ operations | Yavuz | F1 | M5 | S |
| WP-EVT-005 | Architecture rules as code (boundaries and ownership) | Asrın | F1 | M2 | S |
| WP-EVT-006 | Event spine throughput and delivery characterization | Yavuz | F1 / A1 | M7 | S |

#### WP-EVT-001 — Integration Contract Registry and versioning discipline

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-EVT-CONTRACTS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `packages/contracts/`; `evidence/WP-EVT-001/CLOSEOUT.md` (registry/policy primitives; integrated acceptance pending) |

**Purpose.** Create the single registry of cross-service contracts (commands, events, queries, artifacts) with canonical producer and compatibility rules.

**Source requirements (03).** FR-EVT-001, FR-EVT-006, FR-EVT-008, NFR-DATA-005

**Architecture components (02).** ARCH-CTR-API, ARCH-CTR-CMDSCHEMA, ARCH-CTR-EVTSCHEMA, ARCH-CTR-VERSIONING, ARCH-EVT-SCHEMA

**Inputs / required contracts.** gated by DEP-021 (DN-CORE-CONTRACTS → DN-EVT-CONTRACTS, HARD/START@CONTRACT_READY, need-by S1–S2)

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

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, TEST-ARCH-BOUNDARY, TEST-DATA-CONTRACTVALID, TEST-EVT-SCHEMA

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R01, ARCH-R03, ARCH-R04, ARCH-R05, ARCH-R10

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Contract-first is the mechanism that breaks every cycle in 05 §12.


#### WP-EVT-002 — Message envelope, correlation and world scoping

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-EVT-CONTRACTS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `packages/contracts/src/cap_contracts/envelope.py`; `packages/contracts/schemas/event-envelope.v1.schema.json`; `packages/contracts/fixtures/event-envelope.utc.json`; `packages/contracts/fixtures/event-envelope.simulation.json`; `ci/tests/test_event_envelope.py`; `evidence/WP-EVT-002/TRACE-RECONCILIATION.md` (static/library slices only; HTTP/NATS/Temporal propagation pending) |

**Purpose.** Guarantee that every asynchronous message carries identity, causality, world scope and trace context so the closed loop is reconstructible.

**Source requirements (03).** FR-EVT-002, FR-EVT-003, FR-EVT-004, NFR-DATA-008

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-EVT-SCHEMA, ARCH-OBS-TRACE, ARCH-WORLD-SCOPE

**Inputs / required contracts.** gated by DEP-021 (DN-CORE-CONTRACTS → DN-EVT-CONTRACTS, HARD/START@CONTRACT_READY, need-by S1–S2)

**Deliverables.**
- envelope definition + shared library
- correlation/causation propagation middleware
- WorldID scope tagging and validation
- UTC wall-clock vs simulation-time field semantics

**Major tasks.**
- implement envelope fields (EventID, CorrelationID, CausationID, WorldID, SchemaVersion, OccurredAt, producer identity, entity revision)
- propagate through HTTP, NATS and Temporal boundaries
- reject messages missing required scope fields

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-09, AV-SCEN-10, TEST-DATA-TIME, TEST-EVT-ENVELOPE, TEST-OBS-TRACEPROP

**Expected evidence artifact.** Scoped local envelope/schema/world-guard executions and implementation-head CI are recorded in `evidence/WP-EVT-002/TRACE-RECONCILIATION.md`, with exact files, source commits and historical run records. Required propagation, persisted real-time evidence, downstream adoption and AV-SCEN-01/09/10 acceptance remain pending / `NOT_YET_EXECUTED`; no full WP acceptance is asserted.

**Risk hooks (Item 69).** ARCH-R09

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; GS-01 traceability and cross-world safety depend on it.


#### WP-EVT-003 — Idempotent consumer framework

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-EVT-SPINE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | `packages/event-consumer/`; `evidence/WP-EVT-003/` |

**Purpose.** Make at-least-once delivery safe by construction for every consumer rather than per-service ad hoc handling.

**Source requirements (03).** FR-EVT-005

**Architecture components (02).** ARCH-EVT-CONSUMER

**Inputs / required contracts.** gated by DEP-023 (DN-EVT-CONTRACTS → DN-EVT-SPINE, HARD/INTEGRATION@CONTRACT_READY, need-by M1 (S2)), DEP-024 (DN-CORE-OUTBOX → DN-EVT-SPINE, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2)), DEP-025 (DN-RT-NATS → DN-EVT-SPINE, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- processed-message ledger
- consumer base library
- duplicate/out-of-order test suite against real JetStream

**Major tasks.**
- design dedup key and retention
- implement library + adoption in Twin, Vision, AI, Scheduler, Automation consumers
- test duplicate, out-of-order and replayed delivery

**Verification work (03 planned families).** AV-SCEN-05, RES-DUP-001, TEST-EVT-CONSUMER-IDEMP

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard-gate NFR-REL-001).


#### WP-EVT-004 — Replay, poison message and DLQ operations

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-EVT-SPINE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Allow controlled reprocessing and quarantine without creating duplicate real-world effects or silent data loss.

**Source requirements (03).** FR-EVT-009, FR-EVT-010

**Architecture components (02).** ARCH-EVT-CONSUMER, ARCH-EVT-REPLAY, ARCH-OBS-HEALTH

**Inputs / required contracts.** gated by DEP-023 (DN-EVT-CONTRACTS → DN-EVT-SPINE, HARD/INTEGRATION@CONTRACT_READY, need-by M1 (S2)), DEP-024 (DN-CORE-OUTBOX → DN-EVT-SPINE, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2)), DEP-025 (DN-RT-NATS → DN-EVT-SPINE, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- replay procedure + tooling
- DLQ/quarantine path with alerting
- runbook entry

**Major tasks.**
- define replay guards (world, revision, idempotency)
- implement quarantine and operator visibility
- drill replay on INTEGRATION with verification of no duplicate effects

**Verification work (03 planned families).** RES-BROKER-001, RES-DEPFAIL-001, TEST-EVT-REPLAY-DLQ

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R08

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; ties to resilience evidence (RES-BROKER-001).


#### WP-EVT-005 — Architecture rules as code (boundaries and ownership)

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-EVT-CONTRACTS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Encode the architecture boundaries (import rules, schema ownership, forbidden credentials, single canonical producer) as automated checks.

**Source requirements (03).** FR-EVT-007

**Architecture components (02).** ARCH-CORE-DB, ARCH-CTR-API

**Inputs / required contracts.** gated by DEP-021 (DN-CORE-CONTRACTS → DN-EVT-CONTRACTS, HARD/START@CONTRACT_READY, need-by S1–S2)

**Deliverables.**
- rule set implementation
- CI gate
- violation report format

**Major tasks.**
- express boundary rules from 02 as executable checks
- wire into required CI checks
- seed with known allowed exceptions, documented

**Verification work (03 planned families).** TEST-ARCH-BOUNDARY, TEST-SEC-SVCID

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R05, ARCH-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; prevents silent architecture erosion (Item 84 rules-as-code).


#### WP-EVT-006 — Event spine throughput and delivery characterization

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-EVT-SPINE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Measure the sustained application event rate, outbox publication delay and duplicate/loss behaviour of the spine.

**Source requirements (03).** NFR-PERF-003, NFR-CAP-004

**Architecture components (02).** ARCH-CORE-OUTBOX, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX

**Inputs / required contracts.** gated by DEP-023 (DN-EVT-CONTRACTS → DN-EVT-SPINE, HARD/INTEGRATION@CONTRACT_READY, need-by M1 (S2)), DEP-024 (DN-CORE-OUTBOX → DN-EVT-SPINE, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2)), DEP-025 (DN-RT-NATS → DN-EVT-SPINE, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- event pipeline load driver
- measurement definitions
- recorded results with loss/duplicate counts

**Major tasks.**
- build sustained 100 msg/s × 10 min driver
- instrument outbox → broker delay
- verify zero committed-effect loss and zero duplicate protected effects

**Verification work (03 planned families).** BENCH-CAP-EVT, BENCH-PERF-CORE

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1 class: threshold must PASS or be formally rebaselined.


### 6.4 Operational Digital Twin (`WP-TWIN-*`, 6 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-TWIN-001 | Twin projection engine | Asrın | F0 | M1 | M |
| WP-TWIN-002 | Epistemic classes, freshness and staleness semantics | Asrın | F1 | M2 | M |
| WP-TWIN-003 | Twin query API and scheduling snapshot export | Asrın | F1 | M2 | M |
| WP-TWIN-004 | Twin rebuild and catch-up | Asrın | F1 | M5 | S |
| WP-TWIN-005 | Counterfactual/what-if stream isolation | Asrın | F1 | M4 | S |
| WP-TWIN-006 | Effect verification view and Core/Twin consistency | Asrın | F0 | M3 | S |

#### WP-TWIN-001 — Twin projection engine

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-TWIN-SKELETON |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Build the read-only operational projection derived purely from events, with no mutation authority of its own.

**Source requirements (03).** FR-TWIN-001, FR-TWIN-002, FR-TWIN-009

**Architecture components (02).** ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-PROJECTOR, ARCH-TWIN-STATE

**Inputs / required contracts.** gated by DEP-031 (DN-EVT-CONTRACTS → DN-TWIN-SKELETON, HARD/START@CONTRACT_READY, need-by S2), DEP-032 (DN-EVT-SPINE → DN-TWIN-SKELETON, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2)), DEP-033 (DN-RT-PG → DN-TWIN-SKELETON, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- twin-projector worker
- `twin` schema + read models
- source-revision ledger

**Major tasks.**
- implement event handlers for production/equipment/quality namespaces
- implement projection revision tracking to source EventID
- reject any mutation endpoint by design and by test
- startup catch-up behaviour

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, E2E-01, TEST-TWIN-PROJECTION, TEST-TWIN-READONLY

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0).


#### WP-TWIN-002 — Epistemic classes, freshness and staleness semantics

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-TWIN-PROJ |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure consumers can always distinguish ACTUAL/OBSERVED/INFERRED/PREDICTED/PLANNED/COUNTERFACTUAL state and know when data is stale.

**Source requirements (03).** FR-TWIN-003, FR-TWIN-004, FR-TWIN-005, NFR-UX-002

**Architecture components (02).** ARCH-EDGE-WEB, ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-STATE, ARCH-WORLD-SCOPE

**Inputs / required contracts.** gated by DEP-034 (DN-TWIN-SKELETON → DN-TWIN-PROJ, HARD/START@COMPONENT_READY, need-by S3), DEP-035 (DN-SIM-COREINT → DN-TWIN-PROJ, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- epistemic tagging in projection model
- revision/freshness metadata on responses
- sequence-gap detector and stale marking

**Major tasks.**
- define epistemic class per read model field group
- implement freshness computation and exposure
- implement gap detection and degraded marking
- tests with delayed/interrupted event flow

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-07, AV-SCEN-09, BENCH-PERF-CORE, TEST-TWIN-EPISTEMIC, TEST-TWIN-FRESHNESS, TEST-UI-SEMANTICS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PERF-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; honest UI and RCA grounding depend on it.


#### WP-TWIN-003 — Twin query API and scheduling snapshot export

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-CORE-SNAPCON |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Provide the stable read surface used by UI, AI and Scheduler, including the SchedulingSnapshot contract.

**Source requirements (03).** FR-TWIN-008, NFR-PERF-001, NFR-PERF-004

**Architecture components (02).** ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-EVT-CONSUMER, ARCH-SEC-AUTHZ, ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-PROJECTOR

**Inputs / required contracts.** gated by DEP-030 (DN-CORE-CONTRACTS → DN-CORE-SNAPCON, HARD/START@CONTRACT_READY, need-by S3)

**Deliverables.**
- Twin query API (versioned)
- SchedulingSnapshot contract + fixtures
- read scopes per consumer identity

**Major tasks.**
- define query surface from actual consumer needs (05 precise requirements)
- implement snapshot export with revision binding
- enforce read-only scopes
- latency instrumentation

**Verification work (03 planned families).** AV-SCEN-01, BENCH-PERF-CORE, TEST-AUTH-NEG, TEST-TWIN-READONLY

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PERF-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; snapshot contract is on the E2E-01 readiness gate.


#### WP-TWIN-004 — Twin rebuild and catch-up

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-TWIN-PROJ |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make the projection reconstructible from retained canonical sources within the recovery bound.

**Source requirements (03).** FR-TWIN-006, NFR-REC-008

**Architecture components (02).** ARCH-TWIN-REBUILD

**Inputs / required contracts.** gated by DEP-034 (DN-TWIN-SKELETON → DN-TWIN-PROJ, HARD/START@COMPONENT_READY, need-by S3), DEP-035 (DN-SIM-COREINT → DN-TWIN-PROJ, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- rebuild job
- RecoveryDependencyGraph entry for Twin
- rebuild drill script (AV-SCEN-08)

**Major tasks.**
- implement full and partial rebuild modes
- measure rebuild duration at benchmark-scale data
- document operator procedure

**Verification work (03 planned families).** AV-SCEN-08, RES-TWINREBUILD-001, TEST-TWIN-PROJECTION

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DR-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; recovery evidence at M5/M7 depends on it.


#### WP-TWIN-005 — Counterfactual/what-if stream isolation

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-TWIN-PROJ |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep counterfactual projections strictly separated from the primary world so simulation never contaminates operational truth.

**Source requirements (03).** FR-TWIN-007, NFR-CAP-010

**Architecture components (02).** ARCH-TWIN-STATE, ARCH-WORLD-ISOLATION, ARCH-WORLD-REGISTRY

**Inputs / required contracts.** gated by DEP-034 (DN-TWIN-SKELETON → DN-TWIN-PROJ, HARD/START@COMPONENT_READY, need-by S3), DEP-035 (DN-SIM-COREINT → DN-TWIN-PROJ, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- separate projection family per WorldID
- isolation test suite (AV-SCEN-09, AV-SCEN-10)

**Major tasks.**
- implement world-scoped storage and query filters
- test cross-world read/write rejection
- verify ≥5 concurrent isolated worlds

**Verification work (03 planned families).** AV-SCEN-09, AV-SCEN-10, BENCH-CAP-ENV, TEST-TWIN-EPISTEMIC

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R09

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; counterfactual scheduling (RQ-2) depends on it.


#### WP-TWIN-006 — Effect verification view and Core/Twin consistency

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-TWIN-VERIFY |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Give Automation an authoritative way to verify that a commanded effect actually happened, and keep Core and Twin semantically reconciled.

**Source requirements (03).** FR-TWIN-010, NFR-REL-010

**Architecture components (02).** ARCH-AUTO-VERIFY, ARCH-CORE-DOMAIN, ARCH-TWIN-API, ARCH-TWIN-PROJECTOR

**Inputs / required contracts.** gated by DEP-036 (DN-TWIN-PROJ → DN-TWIN-VERIFY, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- verification query view
- consistency assertion used at end of closed-loop runs

**Major tasks.**
- define verification predicates per protected action
- implement query with freshness guarantees
- wire into automation verification activity
- assert zero unresolved mismatches per run

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, E2E-01, RES-TWINREBUILD-001

**Integration checkpoint.** AV-SCEN-01, BENCH-E2E-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 + hard gate).


### 6.5 Operational Manufacturing Simulator (`WP-SIM-*`, 9 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-SIM-001 | Deterministic DES kernel | Batu | F0 | M1 | M |
| WP-SIM-002 | Determinism, replay and event-hash equivalence | Batu | F1 | M2 | M |
| WP-SIM-003 | Operational semantics: reentrant routing, queues, failures, maintenance, rework | Batu | F0 | M2 | L |
| WP-SIM-004 | Snapshot, fork and world isolation | Batu | F1 | M4 | M |
| WP-SIM-005 | Oracle isolation and evaluator-only data plane | Batu | F0 | M3 | M |
| WP-SIM-006 | External dispatch decision interface and operational telemetry | Batu | F0 | M2 | M |
| WP-SIM-007 | Scenario versioning and synthetic operational history | Batu | F1 | M4 | M |
| WP-SIM-008 | Simulator capacity and scale validation | Batu | F1 / A1 | M7 | S |
| WP-SIM-009 | Simulation realism validation suite (RL-3) | Batu | R1 | M6 | M |

#### WP-SIM-001 — Deterministic DES kernel

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-SIM-KERNEL |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `services/manufacturing-simulator/`; `evidence/WP-SIM-001/` |

**Purpose.** Build the discrete-event simulation core (event queue, simulation clock, named RNG streams) that produces the operational world the whole product observes.

**Source requirements (03).** FR-SIM-001, FR-SIM-007

**Architecture components (02).** ARCH-SIM-CLOCK, ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- DES kernel module
- named RNG stream registry
- kernel unit/property test suite

**Major tasks.**
- implement event queue and clock advance
- implement per-concern RNG streams (arrival, processing, failure, repair, quality, inspection)
- expose scenario-driven world initialization
- property tests for event ordering and time monotonicity

**Verification work (03 planned families).** AV-SCEN-01, BENCH-SIMVAL-001, E2E-01, TEST-SIM-DETERMINISM, TEST-SIM-KERNEL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SIM-R01, SIM-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Custom Python kernel per backfill ADR 7; no external DES framework dependency.


#### WP-SIM-002 — Determinism, replay and event-hash equivalence

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-SIM-KERNEL |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Guarantee that the same release, scenario, state and seed reproduce the same world — the basis of paired experiments.

**Source requirements (03).** FR-SIM-008, NFR-REP-001

**Architecture components (02).** ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- replay harness
- event-sequence hash computation
- determinism regression test

**Major tasks.**
- define canonical serialization for hashing
- implement replay from scenario+seed
- detect nondeterminism sources (dict ordering, time, threads)
- wire determinism check into CI

**Verification work (03 planned families).** BENCH-SIMVAL-001, REPRO-NONOWNER-001, TEST-SIM-DETERMINISM

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SIM-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; RQ-2 paired-seed design and reproducibility claims depend on it.


#### WP-SIM-003 — Operational semantics: reentrant routing, queues, failures, maintenance, rework

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-SIM-OPSEM |
| Size band (indicative, no hour estimates) | L (≈7–12 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make the simulated manufacturing facility behave like a reentrant multi-tool environment with the disruption classes the research needs.

**Source requirements (03).** FR-SIM-002, FR-SIM-003, FR-SIM-004, FR-SIM-005, FR-SIM-006

**Architecture components (02).** ARCH-SIM-ENGINE

**Inputs / required contracts.** gated by DEP-037 (DN-SIM-KERNEL → DN-SIM-OPSEM, HARD/START@COMPONENT_READY, need-by S2), DEP-038 (DN-CORE-CONTRACTS → DN-SIM-OPSEM, HARD/START@CONTRACT_READY, need-by S2), DEP-039 (DN-CORE-TRANSITIONS → DN-SIM-OPSEM, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- routing and queue model
- equipment availability/failure/repair model
- maintenance and rework execution
- scenario-driven disruption injection

**Major tasks.**
- implement reentrant visits aligned to Core route semantics
- implement per-tool queues and dispatch hooks
- implement failure/repair and maintenance effects
- implement rework routing
- validate manufacturing legality against Core transition rules

**Verification work (03 planned families).** AV-SCEN-02, BENCH-E2E-001, BENCH-RQ2-001, BENCH-SIMVAL-001, E2E-01, TEST-SIM-KERNEL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 world identity).


#### WP-SIM-004 — Snapshot, fork and world isolation

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SIM-SNAPFORK |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Enable counterfactual evaluation by snapshotting a world and forking it into an isolated WorldID that can never mutate the primary world.

**Source requirements (03).** FR-SIM-009, FR-SIM-010, FR-SIM-011

**Architecture components (02).** ARCH-SIM-SNAPSHOT, ARCH-WORLD-FORK, ARCH-WORLD-ISOLATION

**Inputs / required contracts.** gated by DEP-044 (DN-SIM-KERNEL → DN-SIM-SNAPFORK, HARD/START@COMPONENT_READY, need-by S3), DEP-045 (DN-RT-OBJ → DN-SIM-SNAPFORK, SOFT/INTEGRATION@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- snapshot writer/reader (object-store backed)
- fork API producing new WorldID
- world-scope guard on command/event paths

**Major tasks.**
- define snapshot content and versioning
- implement restore and fork semantics
- implement scope guard + negative tests (AV-SCEN-09/10)
- store snapshots as artifacts with checksums

**Verification work (03 planned families).** AV-SCEN-09, AV-SCEN-10, BENCH-RQ2-001, TEST-SIM-ISOLATION, TEST-SIM-SNAPSHOT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R09, SIM-R08

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for RQ-2; snapshots may use local files during development (F1) but object-store artifacts for evidence.


#### WP-SIM-005 — Oracle isolation and evaluator-only data plane

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-SIM-ORACLE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep synthetic ground truth strictly separated from every runtime decision path so the system is never evaluated against data it secretly had.

**Source requirements (03).** FR-SIM-012, FR-SEC-010

**Architecture components (02).** ARCH-SEC-AUTHZ, ARCH-SIM-ORACLE, ARCH-WORLD-EVALZONE

**Inputs / required contracts.** gated by DEP-046 (DN-SIM-KERNEL → DN-SIM-ORACLE, HARD/START@COMPONENT_READY, need-by S3), DEP-047 (DN-SEC-BASE → DN-SIM-ORACLE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- Oracle stream/namespace separation
- EVALUATOR_ONLY credential scope
- negative access test (AV-SCEN-11)

**Major tasks.**
- define oracle data plane boundary
- implement separate subjects/schema and credentials
- implement runtime denial for normal service identities
- prove denial in INTEGRATION before E2E-01

**Verification work (03 planned families).** AV-SCEN-11, BENCH-RQ3-001, TEST-SEC-ORACLE-NEG, TEST-SIM-ISOLATION

**Integration checkpoint.** AV-SCEN-11, E2E-01

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R04, SIM-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 research validity; hard gate).


#### WP-SIM-006 — External dispatch decision interface and operational telemetry

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-SIM-DISPIF |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Expose the interface through which external deciders (baseline policy, Scheduler, human) drive the world, plus the operational signals consumers observe.

**Source requirements (03).** FR-SIM-013, FR-SIM-014

**Architecture components (02).** ARCH-CTR-CMDSCHEMA, ARCH-SIM-ENGINE, ARCH-WORLD-EVALZONE

**Inputs / required contracts.** gated by DEP-043 (DN-SIM-KERNEL → DN-SIM-DISPIF, HARD/START@COMPONENT_READY, need-by S2)

**Deliverables.**
- dispatch decision contract + baseline policy implementation
- operational event/telemetry publication without oracle fields
- Simulator↔Core command acceptance path

**Major tasks.**
- define decision request/response contract
- implement deterministic baseline dispatch so Scheduler can plug in later (05 CYC-03)
- publish operational events through the spine
- verify no oracle field leaks into published data

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-02, AV-SCEN-11, BENCH-RQ2-001, TEST-SIM-DECISIONIF, TEST-SIM-ISOLATION

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0).


#### WP-SIM-007 — Scenario versioning and synthetic operational history

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SIM-SYNTH |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Produce versioned, seedable scenario families and the generated history that ML, Scheduler evaluation and RCA cases consume.

**Source requirements (03).** FR-SIM-007, FR-EVAL-002, FR-ML-007

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO

**Inputs / required contracts.** gated by DEP-048 (DN-SIM-OPSEM → DN-SIM-SYNTH, HARD/START@COMPONENT_READY, need-by S3–S4)

**Deliverables.**
- ScenarioVersion definitions and registry
- SeedSet management
- generated history export for downstream training/evaluation

**Major tasks.**
- define scenario schema (routes, tools, arrival patterns, disruption profiles)
- implement scenario library covering normal/bottleneck/failure/excursion/rework/hold classes
- implement dataset export with partition metadata
- document provenance of generated data

**Verification work (03 planned families).** BENCH-FBC-001, BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001, BENCH-SIMVAL-001, INSP-DATA-PROVENANCE, INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK, TEST-SIM-DETERMINISM

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** RES-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; F4 synthetic data is also the fallback that keeps external datasets off the product path.


#### WP-SIM-008 — Simulator capacity and scale validation

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-SIM-OPSEM |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Establish the operational world size and event volume the system sustains without semantic degradation.

**Source requirements (03).** NFR-CAP-001, NFR-CAP-002, NFR-CAP-003

**Architecture components (02).** ARCH-CORE-DOMAIN, ARCH-SIM-ENGINE, ARCH-TWIN-PROJECTOR, ARCH-WORLD-ISOLATION

**Inputs / required contracts.** gated by DEP-037 (DN-SIM-KERNEL → DN-SIM-OPSEM, HARD/START@COMPONENT_READY, need-by S2), DEP-038 (DN-CORE-CONTRACTS → DN-SIM-OPSEM, HARD/START@CONTRACT_READY, need-by S2), DEP-039 (DN-CORE-TRANSITIONS → DN-SIM-OPSEM, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- WP-NORMAL / WP-STRESS world configurations
- ≥250k-event stress run harness
- recorded capacity results

**Major tasks.**
- define workload profile compositions
- instrument correctness counters (corruption, cross-world leakage, invalid transitions, OOM)
- execute and record on the evaluation host

**Verification work (03 planned families).** BENCH-CAP-WORLD, BENCH-RES-FOOTPRINT, RES-SOAK-001, TEST-SIM-DETERMINISM

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1/H0 mix: NFR-CAP-002 counters are hard-zero; the capacity numbers themselves are A1.


#### WP-SIM-009 — Simulation realism validation suite (RL-3)

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-SIM-REALISM |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Produce the literature/public-evidence calibrated realism evidence required before any strong RQ-2 claim.

**Source requirements (03).** FR-SIM-001, NFR-REP-001

**Architecture components (02).** ARCH-SIM-CLOCK, ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO

**Inputs / required contracts.** gated by DEP-049 (DN-SIM-OPSEM → DN-SIM-REALISM, HARD/FREEZE@EVALUATION_READY, need-by M5→M6)

**Deliverables.**
- V-MICRO-01…06 micro-validation cases
- RV-01…15 realism benchmark suite
- IndependentKPIRecalculator
- RealismReport

**Major tasks.**
- implement micro-validations against analytic expectations
- implement multi-KPI comparison with documented references
- implement independent KPI recalculation path
- run replications and record realism level (target RL-3)

**Verification work (03 planned families).** AV-SCEN-01, BENCH-SIMVAL-001, E2E-01, REPRO-NONOWNER-001, TEST-SIM-DETERMINISM, TEST-SIM-KERNEL

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SIM-R01, SIM-R02, SIM-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1: a lower achieved realism level is a valid recorded outcome that bounds RQ-2 claim wording — it is not hidden.


### 6.6 Object / Artifact Layer (`WP-OBJ-*`, 2 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-OBJ-001 | Artifact service: ArtifactRef contract and object storage integration | Yavuz | F1 | M2 | M |
| WP-OBJ-002 | Artifact lifecycle, retention and quota policy | Yavuz | F1 | M5 | S |

#### WP-OBJ-001 — Artifact service: ArtifactRef contract and object storage integration

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-RT-OBJ |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `packages/artifacts/`; `infra/compose/stack.sh` (S3 identities); `evidence/WP-OBJ-001/` |

**Purpose.** Make every large artifact (inspection images, snapshots, models, evidence) addressable by immutable reference with verified integrity.

**Source requirements (03).** FR-VIS-001, NFR-DATA-001

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-VIS-ARTIFACT, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-009 (DN-PLAT-INTEG → DN-RT-OBJ, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- ArtifactRef contract
- SeaweedFS buckets/prefix conventions
- checksum/content-identity verification
- scoped artifact access API

**Major tasks.**
- define reference format and metadata
- implement upload/read paths for producers/consumers
- implement checksum verification and immutability rules
- wire UI-scoped capability access

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, E2E-01, TEST-DATA-CHECKSUM, TEST-VIS-PIPELINE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; local files may unblock development only (05 DEP-GAP-17).


#### WP-OBJ-002 — Artifact lifecycle, retention and quota policy

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-RT-OBJ |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep artifact growth bounded and explicit so the shared host stays inside its resource envelope.

**Source requirements (03).** NFR-RES-006, NFR-OBS-009

**Architecture components (02).** ARCH-DATA-CACHE, ARCH-DATA-OBJ, ARCH-OBS-STORE

**Inputs / required contracts.** gated by DEP-009 (DN-PLAT-INTEG → DN-RT-OBJ, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- retention/quota policy per artifact class
- cleanup automation
- storage headroom check used by benchmark preflight

**Major tasks.**
- classify artifact families and lifetimes
- implement retention enforcement
- expose storage usage metrics

**Verification work (03 planned families).** INSP-OBS-RETENTION, INSP-RES-RETENTION

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; benchmark preflight (NFR-RES-004) depends on measurable headroom.


### 6.7 Visual Perception (`WP-VIS-*`, 10 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-VIS-001 | Inspection pipeline and serving path | Selman | F0 | M2 | M |
| WP-VIS-002 | Defect classification and localization models | Selman | F1 | M4 | M |
| WP-VIS-003 | Segmentation and anomaly detection | Selman | F1 | M4 | M |
| WP-VIS-004 | OOD / UNKNOWN handling and threshold policy | Selman | F1 | M4 | M |
| WP-VIS-005 | Provenance, confidence and calibration in Vision outputs | Selman | F1 | M4 | S |
| WP-VIS-006 | SerializedComponent spatial pattern and cluster analysis | Selman | F1 | M4 | S |
| WP-VIS-007 | Vision-to-loop integration (perception drives RCA) | Selman | F0 | M3 | S |
| WP-VIS-008 | CPU smoke inference path | Selman | F1 | M2 | S |
| WP-VIS-009 | Oracle-taint guard for Vision inputs | Selman | F1 | M3 | S |
| WP-VIS-010 | Vision inference performance characterization | Selman | F1 / C3 | M7 | S |

#### WP-VIS-001 — Inspection pipeline and serving path

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-VIS-SERVING |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Turn an inspection request plus a stored artifact into a published, provenance-bearing observation — the perception entry point of the closed loop.

**Source requirements (03).** FR-VIS-001, FR-VIS-009

**Architecture components (02).** ARCH-CTR-EVTSCHEMA, ARCH-DATA-OBJ, ARCH-VIS-ARTIFACT, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-057 (DN-VIS-ARTCON → DN-VIS-SERVING, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ → DN-VIS-SERVING, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-059 (DN-VIS-BASELINES → DN-VIS-SERVING, SOFT/INTEGRATION@COMPONENT_READY, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS → DN-VIS-SERVING, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- vision-service inference worker
- InspectionRequest consumption + observation publication
- artifact-driven preprocessing path

**Major tasks.**
- implement request consumer and artifact fetch by reference
- implement preprocessing with versioned identity
- publish observation contract (naming per 05 DEP-GAP-07)
- integration test with real object storage and broker

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, E2E-01, TEST-EVT-SCHEMA, TEST-VIS-PIPELINE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). First algorithm may be simple (F2) for E2E-01; final modes arrive at M4.


#### WP-VIS-002 — Defect classification and localization models

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-VIS-MODELS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Deliver the classification and localization capability for the accepted defect task set with a defensible evaluation.

**Source requirements (03).** FR-VIS-002, FR-VIS-003

**Architecture components (02).** ARCH-VIS-EVAL, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-053 (DN-VIS-BASELINES → DN-VIS-MODELS, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-055 (DN-RT-MLFLOW → DN-VIS-MODELS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- classification model + ModelPackage
- localization model + ModelPackage
- per-task evaluation results on frozen splits

**Major tasks.**
- establish baselines before deep models
- train/evaluate on DatasetVersion with SplitManifest
- record per-class metrics (no single accuracy headline)
- package models with dataset/experiment lineage

**Verification work (03 planned families).** BENCH-VIS-001, TEST-VIS-PIPELINE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** VIS-R01, VIS-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for F1 Vision modes; model family choice is an implementation decision, not a scope change.


#### WP-VIS-003 — Segmentation and anomaly detection

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-VIS-MODELS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Provide pixel/region-level defect delineation and a classifier-independent anomaly path.

**Source requirements (03).** FR-VIS-004, FR-VIS-005

**Architecture components (02).** ARCH-VIS-EVAL, ARCH-VIS-INFER, ARCH-VIS-OOD

**Inputs / required contracts.** gated by DEP-053 (DN-VIS-BASELINES → DN-VIS-MODELS, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-055 (DN-RT-MLFLOW → DN-VIS-MODELS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- segmentation model + mask artifact handling
- anomaly model + scoring
- evaluation results per task

**Major tasks.**
- define mask artifact storage and referencing
- train/evaluate segmentation
- implement anomaly path independent of closed-set classifier
- evaluate anomaly separability on held-out data

**Verification work (03 planned families).** BENCH-VIS-001, TEST-VIS-OOD, TEST-VIS-PIPELINE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** VIS-R01, VIS-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for F1.


#### WP-VIS-004 — OOD / UNKNOWN handling and threshold policy

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-VIS-OOD |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure unfamiliar inputs produce explicit UNKNOWN outcomes instead of confident wrong labels.

**Source requirements (03).** FR-VIS-006

**Architecture components (02).** ARCH-VIS-OOD

**Inputs / required contracts.** gated by DEP-054 (DN-VIS-MODELS → DN-VIS-OOD, HARD/MILESTONE_EXIT@COMPONENT_READY, need-by M4 (S8))

**Deliverables.**
- OOD detection component
- ThresholdPolicyVersion artifact
- UNKNOWN routing to human review path

**Major tasks.**
- select and implement OOD scoring
- calibrate thresholds on CAL partition only
- define versioned threshold policy
- wire UNKNOWN outcomes into UI/RCA semantics

**Verification work (03 planned families).** BENCH-RQ4-001, BENCH-VIS-001, TEST-VIS-OOD

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** VIS-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; OOD/UNKNOWN is explicitly F1 (Item 68 #55).


#### WP-VIS-005 — Provenance, confidence and calibration in Vision outputs

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-VIS-SERVING |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make every observation carry model identity, preprocessing identity and calibrated uncertainty so downstream reasoning can weigh it.

**Source requirements (03).** FR-VIS-007, FR-VIS-008

**Architecture components (02).** ARCH-VIS-INFER, ARCH-VIS-MODEL, ARCH-VIS-OOD

**Inputs / required contracts.** gated by DEP-057 (DN-VIS-ARTCON → DN-VIS-SERVING, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ → DN-VIS-SERVING, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-059 (DN-VIS-BASELINES → DN-VIS-SERVING, SOFT/INTEGRATION@COMPONENT_READY, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS → DN-VIS-SERVING, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- provenance fields on observation contract
- confidence/uncertainty fields + calibration artifact
- provenance tests

**Major tasks.**
- bind ModelVersion/PreprocessingVersion into outputs
- implement calibration procedure and artifact
- verify immutability of referenced ModelPackages

**Verification work (03 planned families).** BENCH-VIS-001, INSP-VIS-DATASET, TEST-VIS-PROVENANCE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; evidence-grounded RCA and RQ-4 depend on provenance.


#### WP-VIS-006 — SerializedComponent spatial pattern and cluster analysis

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-VIS-OOD |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Convert per-defect detections into serialized component-level spatial signals that operations can act on.

**Source requirements (03).** FR-VIS-010

**Architecture components (02).** ARCH-VIS-EVAL, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-054 (DN-VIS-MODELS → DN-VIS-OOD, HARD/MILESTONE_EXIT@COMPONENT_READY, need-by M4 (S8))

**Deliverables.**
- spatial pattern analysis component
- cluster/pattern contracts (IC-VIS-004/005)
- pattern evaluation cases

**Major tasks.**
- implement spatial aggregation and clustering
- define pattern taxonomy bound to scenario ground truth (evaluator side only)
- evaluate pattern detection quality

**Verification work (03 planned families).** BENCH-RQ4-001, BENCH-VIS-001, TEST-VIS-PIPELINE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for F1; advanced pattern families beyond the accepted set are stretch.


#### WP-VIS-007 — Vision-to-loop integration (perception drives RCA)

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-VIS-SERVING |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Close the perception→reasoning link with real inference output, not an injected defect flag.

**Source requirements (03).** FR-VIS-016

**Architecture components (02).** ARCH-AI-ORCH, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-057 (DN-VIS-ARTCON → DN-VIS-SERVING, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ → DN-VIS-SERVING, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-059 (DN-VIS-BASELINES → DN-VIS-SERVING, SOFT/INTEGRATION@COMPONENT_READY, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS → DN-VIS-SERVING, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- integration wiring Vision → AI evidence intake
- scenario-independent triggering logic
- integration tests (AV-SCEN-01)

**Major tasks.**
- ensure observation is consumed as RCA evidence with provenance
- prohibit scenario-ID or boolean-label shortcuts (Item 67 #101/#104)
- verify with real Vision output in INTEGRATION

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, E2E-01

**Integration checkpoint.** E2E-01, AV-SCEN-01, DEMO-GS01-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R01, PLAN-R03, VIS-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Fixtures are allowed before E2E-01 but never for M3 evidence.


#### WP-VIS-008 — CPU smoke inference path

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-VIS-SERVING |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Guarantee that a GPU-less machine can still run a meaningful Vision smoke path for onboarding and CI.

**Source requirements (03).** FR-VIS-014, NFR-PERF-009, NFR-RES-007

**Architecture components (02).** ARCH-PLAT-CLI, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-057 (DN-VIS-ARTCON → DN-VIS-SERVING, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ → DN-VIS-SERVING, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-059 (DN-VIS-BASELINES → DN-VIS-SERVING, SOFT/INTEGRATION@COMPONENT_READY, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS → DN-VIS-SERVING, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- CPU smoke model package (distinct from promoted final models)
- `mfgctl smoke vision` path
- documented CPU baseline timing

**Major tasks.**
- select lightweight smoke model and sample set
- implement CPU-only execution path
- record smoke timing against the documented CPU baseline (05 DEP-GAP-11)

**Verification work (03 planned families).** BENCH-PERF-VIS, TEST-RES-CPUONLY, TEST-VIS-CPUSMOKE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** VIS-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; developer experience and NFR-RES-007 depend on it.


#### WP-VIS-009 — Oracle-taint guard for Vision inputs

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-VIS-SERVING |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prevent evaluator-only labels from ever reaching Vision runtime inputs.

**Source requirements (03).** FR-VIS-013

**Architecture components (02).** ARCH-VIS-INFER, ARCH-WORLD-EVALZONE

**Inputs / required contracts.** gated by DEP-057 (DN-VIS-ARTCON → DN-VIS-SERVING, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ → DN-VIS-SERVING, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-059 (DN-VIS-BASELINES → DN-VIS-SERVING, SOFT/INTEGRATION@COMPONENT_READY, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS → DN-VIS-SERVING, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- input allowlist enforcement
- taint rejection tests

**Major tasks.**
- define allowed input fields
- implement rejection of oracle-derived fields
- negative tests in CI and INTEGRATION

**Verification work (03 planned families).** AV-SCEN-11, BENCH-VIS-001, TEST-VIS-ORACLE-NEG

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SIM-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (research-validity hard gate).


#### WP-VIS-010 — Vision inference performance characterization

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class C3) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-VIS-MODELS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Characterize cold-start and warm inference latency on the recorded hardware profiles.

**Source requirements (03).** NFR-PERF-010

**Architecture components (02).** ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-053 (DN-VIS-BASELINES → DN-VIS-MODELS, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-055 (DN-RT-MLFLOW → DN-VIS-MODELS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- measurement harness for inference latency
- recorded characterization per HardwareProfile

**Major tasks.**
- define measurement protocol (cold vs warm)
- record results bound to hardware profile
- publish as characterization, not as a threshold claim

**Verification work (03 planned families).** BENCH-PERF-VIS

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** C3: no threshold; absence of a target does not excuse absence of measurement.


### 6.8 Vision Dataset & MLOps (`WP-VDATA-*`, 5 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-VDATA-001 | Dataset governance, rights and provenance | Selman | F1 | M4 | S |
| WP-VDATA-002 | Split manifests and leakage protection | Selman | F1 | M5 | M |
| WP-VDATA-003 | Synthetic Vision data generator | Selman | F1 | M4 | S |
| WP-VDATA-004 | ModelPackage governance and MLflow promotion | Selman | F1 | M5 | M |
| WP-VDATA-005 | Vision evaluation portfolio and RQ-4 lane preparation | Selman | R1 | M6 | M |

#### WP-VDATA-001 — Dataset governance, rights and provenance

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-VIS-PUBLIC |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep every dataset used for a formal claim identified by source, version and rights status.

**Source requirements (03).** FR-VIS-011, NFR-DATA-006

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-VIS-MODEL

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- DatasetVersion records with provenance class (SYNTHETIC/PUBLIC)
- rights/licence status register
- dataset card template

**Major tasks.**
- inventory candidate public datasets and their licences
- record provenance for owned synthetic data
- exclude ambiguous-rights data from any core dependency

**Verification work (03 planned families).** BENCH-VIS-001, INSP-DATA-PROVENANCE, INSP-VIS-DATASET, TEST-DATA-REFINTEGRITY

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DATA-R02, DATA-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** Public data is SOFT for product operation (synthetic F4 fallback) and HARD only for a public-benchmark claim.


#### WP-VDATA-002 — Split manifests and leakage protection

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-VIS-SPLIT |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Freeze train/calibration/final partitions with entity-level separation and automated leakage detection.

**Source requirements (03).** FR-VIS-012, NFR-DATA-002

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-OBJ

**Inputs / required contracts.** gated by DEP-050 (DN-VIS-PUBLIC → DN-VIS-SPLIT, SOFT/START@COMPONENT_READY, need-by S2–S4), DEP-051 (DN-VIS-SYNTH → DN-VIS-SPLIT, HARD/START@COMPONENT_READY, need-by S2–S3)

**Deliverables.**
- SplitManifest artifacts
- leakage detector (entity/group overlap)
- FINAL partition access guard

**Major tasks.**
- define split policy (entity/group level, not random row level)
- implement overlap detection across partitions
- implement access guard preventing training on FINAL
- seal manifests before M6

**Verification work (03 planned families).** BENCH-VIS-001, INSP-EVAL-PARTITION, INSP-VIS-DATASET, TEST-DATA-SPLITLEAK

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DATA-R04, DATA-R05, DATA-R09, RES-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard gate NFR-DATA-002).


#### WP-VDATA-003 — Synthetic Vision data generator

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-VIS-SYNTH |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Own a data source the team fully controls so integration and product execution never depend on third-party availability.

**Source requirements (03).** FR-VIS-011

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-VIS-MODEL

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- synthetic generator with versioned parameters
- generated DatasetVersions
- generator documentation

**Major tasks.**
- define defect/appearance parameter space
- implement generation with seed control
- validate that generated data exercises the required Vision modes

**Verification work (03 planned families).** BENCH-VIS-001, INSP-VIS-DATASET

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DATA-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** F4 fallback role: may substitute public data for integration and product execution, never for public-benchmark claims.


#### WP-VDATA-004 — ModelPackage governance and MLflow promotion

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-RT-MLFLOW |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make every deployed model an immutable, traceable package with recorded dataset and experiment lineage.

**Source requirements (03).** FR-VIS-015, FR-ML-005

**Architecture components (02).** ARCH-CTR-EVTSCHEMA, ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-VIS-MODEL

**Inputs / required contracts.** gated by DEP-014 (DN-PLAT-INTEG → DN-RT-MLFLOW, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- ModelPackage manifest format
- MLflow tracking/registry wiring
- promotion procedure (candidate → promoted)

**Major tasks.**
- define manifest fields (bytes digest, dataset version, experiment run, metrics)
- wire training runs to MLflow
- implement promotion gate requiring evaluation evidence
- verify immutability of promoted packages

**Verification work (03 planned families).** INSP-AI-BEHAVIOR, TEST-DATA-CHECKSUM, TEST-ML-CONTRACT, TEST-VIS-PROVENANCE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** VIS-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for M4/M5 governance; architecture anchor pending (03 GAP-RTM-001).


#### WP-VDATA-005 — Vision evaluation portfolio and RQ-4 lane preparation

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-VIS-OOD |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Build the multi-axis Vision evaluation (classification, localization, segmentation, anomaly, OOD, spatial) that feeds the final benchmark.

**Source requirements (03).** FR-VIS-002, FR-VIS-006, FR-VIS-010

**Architecture components (02).** ARCH-VIS-EVAL, ARCH-VIS-INFER, ARCH-VIS-OOD

**Inputs / required contracts.** gated by DEP-054 (DN-VIS-MODELS → DN-VIS-OOD, HARD/MILESTONE_EXIT@COMPONENT_READY, need-by M4 (S8))

**Deliverables.**
- evaluation harness per task family
- baseline vs proposed comparison structure
- multi-seed evaluation protocol

**Major tasks.**
- implement metric calculators per task
- define seeds and bootstrap procedure
- produce DEV/CAL results before freeze
- prepare FINAL execution script for FBC-01

**Verification work (03 planned families).** BENCH-RQ4-001, BENCH-VIS-001, TEST-VIS-OOD, TEST-VIS-PIPELINE

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** VIS-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1: evaluation must exist and run; positive outcomes are not required.


### 6.9 Predictive ML (`WP-ML-*`, 7 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-ML-001 | Feature and label pipeline from operational history | Asrın | F1 | M4 | M |
| WP-ML-002 | M1 — equipment risk model | Asrın | F1 | M4 | M |
| WP-ML-003 | M2 — cycle-time / tardiness risk model | Asrın | F1 | M4 | M |
| WP-ML-004 | M3 — pre-inspection quality risk model | Asrın | F1 | M4 | S |
| WP-ML-005 | Common prediction contract and publication | Asrın | F1 | M4 | S |
| WP-ML-006 | Calibration and uncertainty evaluation | Asrın | F1 | M5 | S |
| WP-ML-007 | ML evaluation lanes (M1/M2/M3) for the final campaign | Asrın | R1 | M6 | S |

#### WP-ML-001 — Feature and label pipeline from operational history

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SIM-SYNTH |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Build the leakage-safe feature/label pipeline that turns simulated operational history into training data for the three mandatory models.

**Source requirements (03).** FR-ML-007, FR-ML-008

**Architecture components (02).** ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-048 (DN-SIM-OPSEM → DN-SIM-SYNTH, HARD/START@COMPONENT_READY, need-by S3–S4)

**Deliverables.**
- feature extraction pipeline
- label definitions with time semantics
- partition-aware dataset builder

**Major tasks.**
- define feature windows and time-travel rules (no future information)
- implement label generation per model target
- bind datasets to DatasetVersion/SplitManifest
- implement FINAL partition access guard

**Verification work (03 planned families).** BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001, INSP-DATA-PROVENANCE, INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK, TEST-ML-LEAKAGE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R12, DATA-R04, RES-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; leakage protection is a hard gate (NFR-DATA-002).


#### WP-ML-002 — M1 — equipment risk model

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-ML |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Deliver the equipment-risk prediction used by scheduling/maintenance reasoning, with discrimination and calibration evaluated separately.

**Source requirements (03).** FR-ML-001

**Architecture components (02).** ARCH-AI-ORCH, ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-074 (DN-SIM-SYNTH → DN-ML, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW → DN-ML, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- M1 ModelPackage
- baseline comparison
- evaluation results on frozen splits

**Major tasks.**
- define target and horizon
- train baseline then candidate model
- evaluate discrimination and calibration separately
- package with lineage

**Verification work (03 planned families).** BENCH-ML-M1-001, TEST-ML-CONTRACT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R11

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1, Item 68 #66).


#### WP-ML-003 — M2 — cycle-time / tardiness risk model

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-ML |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Deliver the cycle-time/tardiness prediction used for planning context.

**Source requirements (03).** FR-ML-002

**Architecture components (02).** ARCH-AI-ORCH, ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-074 (DN-SIM-SYNTH → DN-ML, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW → DN-ML, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- M2 ModelPackage
- baseline comparison
- evaluation results

**Major tasks.**
- define target and feature set
- train and evaluate against naive baselines
- check horizon-specific leakage
- package with lineage

**Verification work (03 planned families).** BENCH-ML-M2-001, TEST-ML-CONTRACT, TEST-ML-LEAKAGE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R11

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-ML-004 — M3 — pre-inspection quality risk model

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-ML |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Deliver the pre-inspection quality risk prediction that complements perception evidence.

**Source requirements (03).** FR-ML-003

**Architecture components (02).** ARCH-AI-ORCH, ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-074 (DN-SIM-SYNTH → DN-ML, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW → DN-ML, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- M3 ModelPackage
- baseline comparison
- evaluation results

**Major tasks.**
- define target aligned with inspection outcomes
- ensure no inspection-outcome leakage into features
- train, evaluate, package

**Verification work (03 planned families).** BENCH-ML-M3-001, TEST-ML-CONTRACT, TEST-ML-LEAKAGE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R11

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-ML-005 — Common prediction contract and publication

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-ML |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Expose all three models through one versioned Prediction contract bound to model identity and input revision.

**Source requirements (03).** FR-ML-004, FR-ML-005

**Architecture components (02).** ARCH-AI-ORCH, ARCH-CTR-EVTSCHEMA, ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-074 (DN-SIM-SYNTH → DN-ML, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW → DN-ML, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- IC-AI-002 Prediction contract
- prediction publication path
- contract tests

**Major tasks.**
- define common prediction envelope (target, value, uncertainty, model identity, input revision)
- implement serving and event publication
- validate schema at boundaries

**Verification work (03 planned families).** INSP-AI-BEHAVIOR, TEST-EVT-SCHEMA, TEST-ML-CONTRACT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; consumers must not integrate three bespoke shapes.


#### WP-ML-006 — Calibration and uncertainty evaluation

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-ML |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make predicted probabilities usable by turning raw scores into calibrated, uncertainty-bearing outputs.

**Source requirements (03).** FR-ML-006

**Architecture components (02).** ARCH-AI-ORCH

**Inputs / required contracts.** gated by DEP-074 (DN-SIM-SYNTH → DN-ML, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW → DN-ML, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- calibration artifacts per model
- calibration evaluation results
- uncertainty fields in contract

**Major tasks.**
- implement calibration on CAL partition
- evaluate calibration quality separately from discrimination
- bind calibration artifact to ModelPackage

**Verification work (03 planned families).** BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (Item 68 #69).


#### WP-ML-007 — ML evaluation lanes (M1/M2/M3) for the final campaign

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-ML |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prepare the three separate ML evaluations that run as their own lanes in FBC-01.

**Source requirements (03).** FR-ML-001, FR-ML-002, FR-ML-003

**Architecture components (02).** ARCH-AI-ORCH, ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-074 (DN-SIM-SYNTH → DN-ML, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW → DN-ML, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- per-model experiment definitions
- metric calculators
- FINAL execution scripts

**Major tasks.**
- define per-lane protocol (metrics, seeds, baselines)
- dry-run on DEV/CAL
- freeze protocol before M6

**Verification work (03 planned families).** BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001, TEST-ML-CONTRACT, TEST-ML-LEAKAGE

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R11

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1: results may be negative; lanes remain separate and are never averaged into one score.


### 6.10 Documentary RAG (`WP-RAG-*`, 7 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-RAG-001 | Documentary corpus governance and ingestion | Asrın | F1 | M4 | M |
| WP-RAG-002 | Retrieval profiles: sparse, dense and hybrid | Asrın | F1 | M4 | M |
| WP-RAG-003 | Citation-bearing provenance in retrieval and RCA | Asrın | F1 | M4 | S |
| WP-RAG-004 | Rights filtering and prompt-injection resistance | Asrın | F1 | M4 | M |
| WP-RAG-005 | Evidence typing: documentary vs operational | Asrın | F1 | M4 | S |
| WP-RAG-006 | Index rebuild and recovery | Asrın | F1 | M5 | S |
| WP-RAG-007 | Retrieval ablation lane for RQ-1 | Asrın | R1 | M6 | S |

#### WP-RAG-001 — Documentary corpus governance and ingestion

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-RAG-CORPUS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Create the versioned documentary corpus with per-document provenance and rights metadata.

**Source requirements (03).** FR-RAG-001, FR-RAG-009

**Architecture components (02).** ARCH-AI-RAG, ARCH-DATA-LINEAGE, ARCH-DATA-PG, ARCH-DATA-VECTOR

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- DocumentVersion/CorpusVersion model
- ingestion/chunking pipeline
- corpus registry in PostgreSQL

**Major tasks.**
- define corpus sources and licence status
- implement ingestion with stable chunk identity
- record corpus version for experiment binding
- exclude rights-prohibited content

**Verification work (03 planned families).** AV-SCEN-01, BENCH-RAG-001, BENCH-RQ1-001, INSP-AI-BEHAVIOR, TEST-RAG-RETRIEVAL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; RAG is mandatory F1 for the final RCA configuration.


#### WP-RAG-002 — Retrieval profiles: sparse, dense and hybrid

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-RAG |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Implement the three retrieval modes over Qdrant with an explicit, versioned RetrievalProfile.

**Source requirements (03).** FR-RAG-003, FR-RAG-004, FR-RAG-005, NFR-PERF-006

**Architecture components (02).** ARCH-AI-RAG, ARCH-DATA-VECTOR

**Inputs / required contracts.** gated by DEP-070 (DN-RAG-CORPUS → DN-RAG, HARD/START@COMPONENT_READY, need-by S3–S4), DEP-071 (DN-RT-QDRANT → DN-RAG, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

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

**Verification work (03 planned families).** BENCH-PERF-AI, BENCH-RAG-001, BENCH-RQ1-001, TEST-RAG-RETRIEVAL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for F1 modes; ColBERT/late-interaction stays R2 and must not be assumed here.


#### WP-RAG-003 — Citation-bearing provenance in retrieval and RCA

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-RAG |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure every retrieved fragment and every RCA citation resolves to a real document version and span.

**Source requirements (03).** FR-RAG-006, FR-RAG-010

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-RAG

**Inputs / required contracts.** gated by DEP-070 (DN-RAG-CORPUS → DN-RAG, HARD/START@COMPONENT_READY, need-by S3–S4), DEP-071 (DN-RT-QDRANT → DN-RAG, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- chunk provenance fields
- EvidenceRef resolution in RCA output
- citation validation tests

**Major tasks.**
- bind chunk → DocumentVersion + span
- implement evidence reference resolution
- reject fabricated or unresolvable references

**Verification work (03 planned families).** AV-SCEN-01, BENCH-RAG-001, BENCH-RQ1-001, TEST-AI-OUTPUT, TEST-RAG-PROVENANCE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; grounding claims depend on resolvable citations.


#### WP-RAG-004 — Rights filtering and prompt-injection resistance

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-RAG |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Guarantee that retrieved content is data, never instruction, and that ineligible sources never surface.

**Source requirements (03).** FR-RAG-007, FR-RAG-008, FR-SEC-009

**Architecture components (02).** ARCH-AI-RAG, ARCH-AI-TOOLS, ARCH-SEC-AUTHZ

**Inputs / required contracts.** gated by DEP-070 (DN-RAG-CORPUS → DN-RAG, HARD/START@COMPONENT_READY, need-by S3–S4), DEP-071 (DN-RT-QDRANT → DN-RAG, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- eligibility/rights query filter
- prompt assembly isolation of retrieved content
- negative suite (injection, ineligible source)

**Major tasks.**
- implement metadata filter at query time
- isolate retrieved text from policy/authority context
- build adversarial corpus cases
- prove policy cannot be overridden by document content

**Verification work (03 planned families).** BENCH-RQ3-001, TEST-AUTH-NEG, TEST-RAG-INJECTION, TEST-RAG-RIGHTS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (authority hard gate; feeds RQ-3 adversarial cases).


#### WP-RAG-005 — Evidence typing: documentary vs operational

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-RAG |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep documentary knowledge and operational facts as distinct evidence classes so RCA cannot dress a manual quote as a measurement.

**Source requirements (03).** FR-RAG-002

**Architecture components (02).** ARCH-AI-RAG, ARCH-DATA-VECTOR

**Inputs / required contracts.** gated by DEP-070 (DN-RAG-CORPUS → DN-RAG, HARD/START@COMPONENT_READY, need-by S3–S4), DEP-071 (DN-RT-QDRANT → DN-RAG, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- evidence class taxonomy in IC-AI-001
- type enforcement in RCA assembly
- tests for mixed-evidence cases

**Major tasks.**
- define evidence classes and required fields
- enforce typing at contract boundary
- verify UI and analysis preserve the distinction

**Verification work (03 planned families).** TEST-AI-OUTPUT, TEST-ARCH-BOUNDARY

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut.


#### WP-RAG-006 — Index rebuild and recovery

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-RT-QDRANT |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make the vector index a derived artifact that can be rebuilt from canonical sources within the recovery bound.

**Source requirements (03).** NFR-REC-009

**Architecture components (02).** ARCH-AI-RAG, ARCH-DATA-VECTOR

**Inputs / required contracts.** gated by DEP-013 (DN-PLAT-INTEG → DN-RT-QDRANT, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- rebuild job from CorpusVersion artifacts
- rebuild drill record
- RecoveryDependencyGraph entry

**Major tasks.**
- implement deterministic re-indexing
- measure rebuild duration at final corpus size
- document operator procedure

**Verification work (03 planned families).** RES-IDXREBUILD-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; Qdrant holds no unique canonical data by design.


#### WP-RAG-007 — Retrieval ablation lane for RQ-1

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-RAG |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prepare the RAG-B0…B3 / RAG-PROPOSED ablation that isolates retrieval contribution in the RQ-1 evaluation.

**Source requirements (03).** FR-RAG-009

**Architecture components (02).** ARCH-AI-RAG, ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-070 (DN-RAG-CORPUS → DN-RAG, HARD/START@COMPONENT_READY, need-by S3–S4), DEP-071 (DN-RT-QDRANT → DN-RAG, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- ablation configuration set
- lane experiment definition
- DEV/CAL dry-run results

**Major tasks.**
- define ablation arms bound to CorpusVersion + RetrievalProfile
- implement switchable configuration in the runner
- dry-run and freeze before M6

**Verification work (03 planned families).** BENCH-RAG-001, BENCH-RQ1-001, INSP-AI-BEHAVIOR

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1: ablation outcome may show limited benefit; that is a publishable result, not a failure to hide.


### 6.11 AI Orchestrator / RCA (`WP-AI-*`, 7 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-AI-001 | Deterministic orchestrator and execution budgets | Asrın | F0 | M3 | M |
| WP-AI-002 | Typed tool registry and authority-tagged tool access | Asrın | F1 | M3 | M |
| WP-AI-003 | Structured evidence-grounded RCA output | Asrın | F1 | M3 | M |
| WP-AI-004 | Action proposal and context binding | Asrın | F1 | M3 | S |
| WP-AI-005 | Provider abstraction, behavior bundle and deterministic baseline | Asrın | F1 | M4 | M |
| WP-AI-006 | AI authority boundary and negative suite | Asrın | F0 | M3 | M |
| WP-AI-007 | RCA path performance characterization | Asrın | F1 / A1 | M7 | S |

#### WP-AI-001 — Deterministic orchestrator and execution budgets

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AI-ORCH |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Build the explicit orchestrator state machine (not an open-ended agent loop) with enforced budgets and bounded termination.

**Source requirements (03).** FR-AI-001, FR-AI-012, FR-AI-013

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-CTR-EVTSCHEMA

**Inputs / required contracts.** gated by DEP-064 (DN-AI-TOOLCON → DN-AI-ORCH, HARD/START@CONTRACT_READY, need-by S2–S3)

**Deliverables.**
- orchestrator state machine
- AgentBudgetProfile enforcement
- structured-output validation gate

**Major tasks.**
- define phases (evidence gathering → hypothesis → assessment)
- implement budget accounting (tool calls, tokens, wall clock)
- implement schema validation before publication
- bounded-termination tests

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, BENCH-RQ1-001, E2E-01, TEST-AI-BUDGET, TEST-AI-OUTPUT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R09

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Multi-agent persona architecture stays out of the mandatory path.


#### WP-AI-002 — Typed tool registry and authority-tagged tool access

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AI-TOOLCON |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Give the AI a versioned, typed, allowlisted set of read/simulate/propose tools and nothing else.

**Source requirements (03).** FR-AI-002, FR-AI-003, FR-SEC-004, FR-SEC-005

**Architecture components (02).** ARCH-AI-TOOLS, ARCH-SEC-AUTHZ

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- tool interface definitions + fixtures
- allowlist with READ/SIMULATE/PROPOSE tags
- tool surface inventory test (no shell, no arbitrary SQL)

**Major tasks.**
- define tool schemas against Core/Twin/Vision/RAG capabilities
- implement typed clients with failure semantics
- implement allowlist enforcement
- inventory test proving absent capabilities

**Verification work (03 planned families).** AV-SCEN-01, TEST-AI-TOOLS, TEST-AUTH-NEG, TEST-SEC-AISURFACE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (authority hard gate).


#### WP-AI-003 — Structured evidence-grounded RCA output

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AI-RCA |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Produce assessments that separate hypotheses from evidence, represent conflict and missing data, and abstain when evidence is insufficient.

**Source requirements (03).** FR-AI-005, FR-AI-006, FR-AI-007, FR-AI-008

**Architecture components (02).** ARCH-AI-ORCH

**Inputs / required contracts.** gated by DEP-065 (DN-VIS-OBSCON → DN-AI-RCA, HARD/START@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH → DN-AI-RCA, HARD/START@COMPONENT_READY, need-by S4), DEP-067 (DN-TWIN-PROJ → DN-AI-RCA, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6)), DEP-069 (DN-CORE-GENEALOGY → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (full RQ-1 RCA config)), DEP-072 (DN-RAG → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

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

**Verification work (03 planned families).** AV-SCEN-03, BENCH-RQ1-001, TEST-AI-OUTPUT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R01, AI-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1 and RQ-1 core).


#### WP-AI-004 — Action proposal and context binding

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AI-ACTCON |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Emit proposals that are bound to the exact world, revision and evidence set they were reasoned from.

**Source requirements (03).** FR-AI-009, FR-AI-010

**Architecture components (02).** ARCH-AI-PROPOSAL, ARCH-TWIN-FRESHNESS

**Inputs / required contracts.** gated by DEP-076 (DN-HITL-POLICY → DN-AI-ACTCON, HARD/START@COMPONENT_READY, need-by S3–S4)

**Deliverables.**
- Recommendation contract (IC-AI-004)
- binding fields (WorldID, base revision, evidence set)
- binding tests

**Major tasks.**
- define proposal schema with no command semantics
- implement binding capture at proposal time
- verify rejection paths when binding is stale (with Automation)

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AI-BINDING, TEST-AUTH-NEG

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; stale-proposal rejection is a hard gate.


#### WP-AI-005 — Provider abstraction, behavior bundle and deterministic baseline

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-AI-PROVIDER |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep the LLM provider replaceable, record exactly which behavior produced each result, and keep a non-LLM path that works without a paid provider.

**Source requirements (03).** FR-AI-011, NFR-REP-009, NFR-SEC-009

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-PROVIDER, ARCH-DATA-LINEAGE, ARCH-WORLD-EVALZONE

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

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

**Verification work (03 planned families).** AV-SCEN-11, BENCH-RQ1-001, INSP-AI-BEHAVIOR, INSP-REP-LLM, TEST-SEC-EGRESS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R08, AI-R10

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** F2 fallback: the deterministic baseline keeps the product testable without external providers (Item 66 #129).


#### WP-AI-006 — AI authority boundary and negative suite

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AI-RCA |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prove structurally that the AI cannot mutate manufacturing state or authorize its own actions.

**Source requirements (03).** FR-AI-004, NFR-SEC-004

**Architecture components (02).** ARCH-AI-ORCH, ARCH-CORE-CMD, ARCH-HITL-POLICY, ARCH-SEC-AUTHZ

**Inputs / required contracts.** gated by DEP-065 (DN-VIS-OBSCON → DN-AI-RCA, HARD/START@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH → DN-AI-RCA, HARD/START@COMPONENT_READY, need-by S4), DEP-067 (DN-TWIN-PROJ → DN-AI-RCA, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6)), DEP-069 (DN-CORE-GENEALOGY → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (full RQ-1 RCA config)), DEP-072 (DN-RAG → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- credential/identity separation for the AI service
- Core-side denial of AI principal for mutations
- cross-cutting authority negative suite

**Major tasks.**
- remove any mutation-capable credential from the AI identity
- implement Core authorization denial and tests
- build adversarial attempts (self-approval, forged proposals, credential reuse)
- execute on real INTEGRATION runtime

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-SEC-AUTHZ-NEG, TEST-SEC-SVCID

**Integration checkpoint.** AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0, hard gate, RQ-3 core).


#### WP-AI-007 — RCA path performance characterization

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-AI-RCA |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Measure RCA end-to-end latency with the external provider context recorded, decomposed by phase.

**Source requirements (03).** NFR-PERF-007

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-PROVIDER

**Inputs / required contracts.** gated by DEP-065 (DN-VIS-OBSCON → DN-AI-RCA, HARD/START@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH → DN-AI-RCA, HARD/START@COMPONENT_READY, need-by S4), DEP-067 (DN-TWIN-PROJ → DN-AI-RCA, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6)), DEP-069 (DN-CORE-GENEALOGY → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (full RQ-1 RCA config)), DEP-072 (DN-RAG → DN-AI-RCA, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4/M5)

**Deliverables.**
- latency decomposition instrumentation
- measurement protocol
- recorded results

**Major tasks.**
- instrument phases (retrieval, tool calls, generation)
- define protocol excluding provider outages
- record distributions bound to profiles

**Verification work (03 planned families).** BENCH-PERF-AI, INSP-REP-LLM

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PERF-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1: threshold applies to the system path; provider variance is characterized, not hidden.


### 6.12 Scheduling & Optimization (`WP-SCH-*`, 7 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-SCH-001 | Dispatch baselines and scheduling instance model | Batu | F1 | M2 | S |
| WP-SCH-002 | Snapshot consumption and recovery plan contract | Batu | F0 | M3 | M |
| WP-SCH-003 | CP-SAT model and hard constraints | Batu | F1 | M4 | M |
| WP-SCH-004 | Rolling horizon and event-triggered rescheduling | Batu | F1 | M4 | M |
| WP-SCH-005 | Decision budget, fallback and explicit failure state | Batu | F1 | M5 | S |
| WP-SCH-006 | Counterfactual schedule evaluation on forked worlds | Batu | F1 | M4 | S |
| WP-SCH-007 | Schedule churn and stability metrics | Batu | F1 | M5 | S |

#### WP-SCH-001 — Dispatch baselines and scheduling instance model

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-SCH-HEUR |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Implement the baseline dispatch policies that both unblock early integration and serve as research baselines.

**Source requirements (03).** FR-SCH-010

**Architecture components (02).** ARCH-SCH-HEURISTIC, ARCH-VIS-EVAL

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- FIFO/EDD/CR/SPT/SRPT implementations
- BaselineDefinition records
- instance generator for offline testing

**Major tasks.**
- implement policies over a common decision interface
- validate against generated instances
- record baseline definitions for later comparison

**Verification work (03 planned families).** BENCH-RQ2-001, BENCH-SCH-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SCH-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** F2 role: baselines are the approved fallback if CP-SAT integration slips, and are required as research baselines anyway.


#### WP-SCH-002 — Snapshot consumption and recovery plan contract

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-SCH-PLANCON |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Consume the Twin scheduling snapshot and emit a revision-bound, reviewable RecoveryPlan.

**Source requirements (03).** FR-SCH-001, FR-SCH-007, FR-SCH-008, FR-SCH-015

**Architecture components (02).** ARCH-CTR-EVTSCHEMA, ARCH-EDGE-BFF, ARCH-SCH-ENGINE, ARCH-SCH-HEURISTIC, ARCH-SCH-PLAN, ARCH-TWIN-FRESHNESS

**Inputs / required contracts.** gated by DEP-083 (DN-SCH-DYN → DN-SCH-PLANCON, HARD/INTEGRATION@COMPONENT_READY, need-by E2E-01 (end S5)), DEP-084 (DN-SCH-VALID → DN-SCH-PLANCON, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- snapshot consumption module
- RecoveryPlan contract (IC-SCH-004) + fixtures
- rationale/objective/comparison fields

**Major tasks.**
- implement snapshot → internal instance mapping
- implement plan serialization with source revision binding
- include rationale and objective summary for human review
- contract tests with Automation and HITL consumers

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, BENCH-SCH-001, E2E-01, TEST-AUTO-FRESHNESS, TEST-SCH-CONSTRAINTS, TEST-SCH-PLAN, TEST-UI-PLAN

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0).


#### WP-SCH-003 — CP-SAT model and hard constraints

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SCH-CPSAT |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Express manufacturing constraints in an OR-Tools CP-SAT model that produces feasible recovery schedules within the decision budget.

**Source requirements (03).** FR-SCH-004, FR-SCH-009

**Architecture components (02).** ARCH-SCH-ENGINE

**Inputs / required contracts.** gated by DEP-085 (DN-SCH-HEUR → DN-SCH-CPSAT, SOFT/START@COMPONENT_READY, need-by S5–S8)

**Deliverables.**
- CP-SAT model
- constraint property tests
- solver configuration profile

**Major tasks.**
- encode eligibility, capacity, precedence, maintenance and hold constraints
- implement solve with time budget
- property-based feasibility tests (not golden snapshots)
- tune search parameters within the budget

**Verification work (03 planned families).** BENCH-PERF-SCH, BENCH-SCH-001, TEST-SCH-CONSTRAINTS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SCH-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** F2 fallback exists (heuristics) but F1 requires the CP-SAT candidate at M4.


#### WP-SCH-004 — Rolling horizon and event-triggered rescheduling

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SCH-DYN |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** React to real operational disruptions with bounded, stable replanning instead of static schedules.

**Source requirements (03).** FR-SCH-002, FR-SCH-003

**Architecture components (02).** ARCH-SCH-ENGINE

**Inputs / required contracts.** gated by DEP-078 (DN-SCH-HEUR → DN-SCH-DYN, HARD/START@COMPONENT_READY, need-by S3), DEP-079 (DN-CORE-SNAPCON → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ → DN-SCH-DYN, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-088 (DN-SIM-DISPIF → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by M2 (S4))

**Deliverables.**
- rolling-horizon planner loop
- event-triggered replanning hooks
- disruption class configuration

**Major tasks.**
- define horizon and replan cadence
- subscribe to failure/maintenance/hold/excursion events
- implement replan trigger policy
- integration tests with Simulator disruptions

**Verification work (03 planned families).** AV-SCEN-02, BENCH-RQ2-001, BENCH-SCH-001, TEST-SCH-REPLAN

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SCH-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1, RQ-2 core).


#### WP-SCH-005 — Decision budget, fallback and explicit failure state

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-SCH-DYN |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure the scheduler always returns something safe and explicit within its budget.

**Source requirements (03).** FR-SCH-012, NFR-PERF-008, NFR-CAP-006, NFR-CAP-007

**Architecture components (02).** ARCH-SCH-ENGINE, ARCH-SCH-HEURISTIC, ARCH-SCH-VALIDATOR

**Inputs / required contracts.** gated by DEP-078 (DN-SCH-HEUR → DN-SCH-DYN, HARD/START@COMPONENT_READY, need-by S3), DEP-079 (DN-CORE-SNAPCON → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ → DN-SCH-DYN, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-088 (DN-SIM-DISPIF → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by M2 (S4))

**Deliverables.**
- bounded fallback policy
- explicit failure/no-plan state
- SP-NORMAL/SP-STRESS measurement harness

**Major tasks.**
- implement budget enforcement and graceful degradation
- define failure state semantics for consumers
- measure feasibility rate, solve time, quality and fallback rate

**Verification work (03 planned families).** BENCH-PERF-SCH, TEST-SCH-FALLBACK

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PERF-R04, SCH-R03, SCH-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; silent timeout or an infeasible plan reaching execution is a hard failure.


#### WP-SCH-006 — Counterfactual schedule evaluation on forked worlds

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SCH-CF |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Evaluate candidate plans in isolated forked worlds so alternatives can be compared without touching the primary world.

**Source requirements (03).** FR-SCH-013

**Architecture components (02).** ARCH-SCH-ENGINE, ARCH-SIM-SNAPSHOT, ARCH-WORLD-FORK

**Inputs / required contracts.** gated by DEP-087 (DN-SIM-SNAPFORK → DN-SCH-CF, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- fork-based evaluation harness
- common random number handling
- isolation tests (AV-SCEN-09)

**Major tasks.**
- integrate with Simulator snapshot/fork API
- implement candidate evaluation loop
- ensure exogenous randomness control for paired comparison

**Verification work (03 planned families).** AV-SCEN-09, BENCH-RQ2-001, TEST-SCH-COUNTERFACTUAL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SIM-R08

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut for RQ-2; HARD on Simulator snapshot/fork.


#### WP-SCH-007 — Schedule churn and stability metrics

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-SCH-DYN |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Measure plan stability separately from objective quality so "better" plans are not achieved by thrashing.

**Source requirements (03).** FR-SCH-011

**Architecture components (02).** ARCH-SCH-ENGINE

**Inputs / required contracts.** gated by DEP-078 (DN-SCH-HEUR → DN-SCH-DYN, HARD/START@COMPONENT_READY, need-by S3), DEP-079 (DN-CORE-SNAPCON → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ → DN-SCH-DYN, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-088 (DN-SIM-DISPIF → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by M2 (S4))

**Deliverables.**
- churn/stability metric calculators
- metric definitions in the analysis package
- regression tests on metric behaviour

**Major tasks.**
- define churn measures (assignment changes, sequence disruption)
- implement calculators independent of the objective function
- validate on controlled replan scenarios

**Verification work (03 planned families).** BENCH-RQ2-001, BENCH-SCH-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SCH-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; stability trade-offs are an explicit RQ-2 dimension.


### 6.13 Schedule Validation (`WP-VALID-*`, 2 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-VALID-001 | Independent schedule validator | Batu | F0 | M3 | M |
| WP-VALID-002 | Execution eligibility gate and AI-origin plan routing | Batu | F1 | M3 | S |

#### WP-VALID-001 — Independent schedule validator

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-SCH-VALID |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Build the validator that independently rejects infeasible or illegal plans, implemented separately from the planner.

**Source requirements (03).** FR-SCH-005

**Architecture components (02).** ARCH-SCH-VALIDATOR

**Inputs / required contracts.** gated by DEP-082 (DN-CORE-TRANSITIONS → DN-SCH-VALID, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- validator module (independent code path)
- hard-constraint check set derived from Core rules
- negative test suite with infeasible plans

**Major tasks.**
- derive validation rules from Core domain legality, not from planner internals
- implement deterministic validation result contract
- build infeasible/illegal plan corpus
- verify planner and validator do not share logic

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, BENCH-SCH-001, E2E-01, TEST-SCH-VALIDATOR

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SCH-R01, SCH-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Planner ≠ validator is an architectural invariant (Item 67 #116).


#### WP-VALID-002 — Execution eligibility gate and AI-origin plan routing

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-SCH-VALID |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure only validated plans become executable and that AI-originated plans take the same route with no bypass.

**Source requirements (03).** FR-SCH-006, FR-SCH-014

**Architecture components (02).** ARCH-AI-PROPOSAL, ARCH-AUTO-WORKFLOW, ARCH-SCH-VALIDATOR

**Inputs / required contracts.** gated by DEP-082 (DN-CORE-TRANSITIONS → DN-SCH-VALID, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- eligibility flag in plan contract
- Automation-side rejection of ineligible plans
- bypass-attempt negative tests

**Major tasks.**
- define eligibility semantics and lifetime
- implement gate on the Automation consumption path
- test AI-originated plan routing and bypass attempts

**Verification work (03 planned families).** AV-SCEN-01, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-SCH-VALIDATOR

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SCH-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard gate: infeasible plan must never reach execution).


### 6.14 Durable Automation (`WP-AUTO-*`, 7 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-AUTO-001 | Durable workflow bundle and approval wait | Batu | F0 | M3 | M |
| WP-AUTO-002 | Idempotency and restart safety for protected effects | Batu | F1 | M4 | M |
| WP-AUTO-003 | Pre-execution revalidation and command identity | Batu | F1 | M3 | S |
| WP-AUTO-004 | ActionCatalog and authorization gate | Batu | F1 | M3 | S |
| WP-AUTO-005 | Outcome model and effect verification | Batu | F0 | M3 | M |
| WP-AUTO-006 | Workflow history and audit surface | Batu | F1 | M5 | S |
| WP-AUTO-007 | GS-01 recovery workflow and closed-loop timing | Batu | F0 | M4 | S |

#### WP-AUTO-001 — Durable workflow bundle and approval wait

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AUTO-DURABLE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Implement the Temporal workflows that carry a recovery from proposal to verified effect, surviving restarts and human wait time.

**Source requirements (03).** FR-AUTO-001, FR-AUTO-002, FR-AUTO-003

**Architecture components (02).** ARCH-AUTO-ACTIONCAT, ARCH-AUTO-WORKFLOW, ARCH-HITL-APPROVAL

**Inputs / required contracts.** gated by DEP-094 (DN-AUTO-DESIGN → DN-AUTO-DURABLE, HARD/START@COMPONENT_READY, need-by S3), DEP-095 (DN-RT-TEMPORAL → DN-AUTO-DURABLE, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 formal run (end S5))

**Deliverables.**
- WorkflowBundle definitions
- Temporal worker deployment
- durable approval-wait signal handling
- workflow state contract (IC-AUTO-001)

**Major tasks.**
- design workflow shape (validate → request approval → wait → revalidate → execute → verify)
- implement activities with typed clients
- implement durable signal/timer handling
- restart tests with the real Temporal server

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-06, BENCH-AUTO-001, BENCH-E2E-001, E2E-01, TEST-AUTO-RESTART-001, TEST-AUTO-WORKFLOW

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Stub activities unblock development before the runtime exists (05 CYC-04).


#### WP-AUTO-002 — Idempotency and restart safety for protected effects

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-AUTO-DURABLE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Guarantee that no crash, retry or duplicate delivery can produce a second real manufacturing effect.

**Source requirements (03).** FR-AUTO-005, FR-AUTO-006, NFR-REL-001, NFR-REL-004

**Architecture components (02).** ARCH-AUTO-IDEMPOTENCY, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-EVT-CONSUMER

**Inputs / required contracts.** gated by DEP-094 (DN-AUTO-DESIGN → DN-AUTO-DURABLE, HARD/START@COMPONENT_READY, need-by S3), DEP-095 (DN-RT-TEMPORAL → DN-AUTO-DURABLE, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 formal run (end S5))

**Deliverables.**
- idempotency key propagation to Core commands
- verified-effect ledger before re-issue
- restart/duplicate test matrix (TEST-AUTO-RESTART-001)

**Major tasks.**
- align keys with Core command acceptance
- implement pre-issue effect check
- build the five restart/duplicate cases
- execute against real Temporal + Core

**Verification work (03 planned families).** AV-SCEN-05, AV-SCEN-06, RES-DUP-001, RES-WORKER-001, TEST-AUTO-RESTART-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R01, AUTO-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard gate: duplicate protected effect count must be zero).


#### WP-AUTO-003 — Pre-execution revalidation and command identity

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AUTO-EXEC |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Re-check world, revision, freshness, policy and action identity immediately before any protected command leaves Automation.

**Source requirements (03).** FR-AUTO-004, FR-AUTO-010

**Architecture components (02).** ARCH-AUTO-WORKFLOW, ARCH-HITL-EXPIRY, ARCH-WORLD-SCOPE

**Inputs / required contracts.** gated by DEP-096 (DN-AI-ACTCON → DN-AUTO-EXEC, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-097 (DN-CORE-CMDCON → DN-AUTO-EXEC, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-098 (DN-CORE-CMDEXEC → DN-AUTO-EXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4)), DEP-099 (DN-HITL-APPROVAL → DN-AUTO-EXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-100 (DN-AUTO-DURABLE → DN-AUTO-EXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-101 (DN-SCH-PLANCON → DN-AUTO-EXEC, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- revalidation activity
- command identity fields (WorldID, revision, ActionID)
- stale-rejection tests (AV-SCEN-04)

**Major tasks.**
- define revalidation predicates per action
- implement fail-closed behaviour
- test stale plan/approval/state paths

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, AV-SCEN-10, TEST-AUTO-FRESHNESS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard gate).


#### WP-AUTO-004 — ActionCatalog and authorization gate

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AI-ACTCON |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Constrain execution to catalogued actions with declared risk class, preconditions and approval requirements.

**Source requirements (03).** FR-AUTO-012, FR-AUTO-013

**Architecture components (02).** ARCH-AUTO-ACTIONCAT, ARCH-HITL-POLICY

**Inputs / required contracts.** gated by DEP-076 (DN-HITL-POLICY → DN-AI-ACTCON, HARD/START@COMPONENT_READY, need-by S3–S4)

**Deliverables.**
- ActionCatalog registry
- authorization gate in the execution path
- self-authorization negative tests

**Major tasks.**
- define catalog entries (risk level, preconditions, idempotency, valid world types)
- implement gate consulting AuthorityPolicy
- test unknown/forbidden/self-approved action attempts

**Verification work (03 planned families).** AV-SCEN-04, TEST-AUTH-NEG, TEST-AUTO-ACTIONCAT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F0-adjacent authority boundary).


#### WP-AUTO-005 — Outcome model and effect verification

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-AUTO-VERIFY |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Separate acknowledgement from effect: a workflow may only report success after Core/Twin confirm the change.

**Source requirements (03).** FR-AUTO-007, FR-AUTO-008, FR-AUTO-009

**Architecture components (02).** ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-TWIN-API

**Inputs / required contracts.** gated by DEP-102 (DN-AUTO-EXEC → DN-AUTO-VERIFY, HARD/INTEGRATION@COMPONENT_READY, need-by E2E-01 (end S5)), DEP-103 (DN-TWIN-VERIFY → DN-AUTO-VERIFY, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- AutomationOutcome contract (IC-AUTO-004)
- verification activity against Core events/Twin state
- UNKNOWN_VERIFY_REQUIRED path and reconciliation

**Major tasks.**
- define outcome states (ACCEPTED, VERIFIED_SUCCESS, FAILED, UNKNOWN_VERIFY_REQUIRED)
- implement verification queries and retry/backoff
- implement reconciliation procedure for ambiguous cases
- test lost-ACK scenarios

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, RES-DUP-001, RES-WORKER-001, TEST-AUTO-OUTCOME

**Integration checkpoint.** AV-SCEN-01, AV-SCEN-06

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R02, AUTO-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0, hard gate DEP-INV-16).


#### WP-AUTO-006 — Workflow history and audit surface

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-AUTO-DURABLE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make every execution inspectable in domain terms, not only as engine internals.

**Source requirements (03).** FR-AUTO-011

**Architecture components (02).** ARCH-AUTO-WORKFLOW, ARCH-OBS-AUDIT

**Inputs / required contracts.** gated by DEP-094 (DN-AUTO-DESIGN → DN-AUTO-DURABLE, HARD/START@COMPONENT_READY, need-by S3), DEP-095 (DN-RT-TEMPORAL → DN-AUTO-DURABLE, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 formal run (end S5))

**Deliverables.**
- workflow state/history query API
- audit linkage to approval and command records
- UI-facing projection

**Major tasks.**
- define domain-level history projection
- link workflow run to ApprovalRecord/CommandOutcome
- expose through BFF for the workflow view

**Verification work (03 planned families).** TEST-AUTO-ACTIONCAT, TEST-SEC-AUDIT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; operator trust and audit coverage depend on it.


#### WP-AUTO-007 — GS-01 recovery workflow and closed-loop timing

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-AUTO-EXEC |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Implement the canonical hero recovery workflow (isolation/hold, schedule activation, maintenance request) end to end and measure its system-controlled duration.

**Source requirements (03).** FR-AUTO-014, NFR-PERF-011, NFR-PERF-013, NFR-CAP-008

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AUTO-VERIFY, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-SCH-ENGINE, ARCH-SIM-ENGINE, ARCH-TWIN-API, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-096 (DN-AI-ACTCON → DN-AUTO-EXEC, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-097 (DN-CORE-CMDCON → DN-AUTO-EXEC, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-098 (DN-CORE-CMDEXEC → DN-AUTO-EXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4)), DEP-099 (DN-HITL-APPROVAL → DN-AUTO-EXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-100 (DN-AUTO-DURABLE → DN-AUTO-EXEC, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-101 (DN-SCH-PLANCON → DN-AUTO-EXEC, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- GS-01 workflow definition
- workflow concurrency handling
- duration instrumentation excluding human wait

**Major tasks.**
- implement the full recovery sequence against real Core/Simulator
- instrument control-plane overhead and total system-controlled duration
- test 50 concurrent workflows for state integrity

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, BENCH-PERF-WF, DEMO-GS01-001, E2E-01, RES-DUP-001

**Integration checkpoint.** E2E-01, DEMO-GS01-001, BENCH-E2E-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R01, DEMO-R01, PLAN-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 + demo path). Presenter-mode shortcuts are forbidden.


### 6.15 HITL & Authority (`WP-HITL-*`, 7 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-HITL-001 | Authority policy engine (L0–L4) | Asrın | F0 | M3 | S |
| WP-HITL-002 | Approval binding to exact proposal/plan revision and world | Asrın | F1 | M3 | S |
| WP-HITL-003 | Expiry, replay and staleness rejection | Asrın | F1 | M3 | S |
| WP-HITL-004 | Identity-bound approvals | Yavuz | F1 | M3 | S |
| WP-HITL-005 | Approval record, audit trail and protected-action coverage | Asrın | F1 | M4 | S |
| WP-HITL-006 | Dual approval for highest-risk actions | Asrın | F1 | M4 | S |
| WP-HITL-007 | Break-glass path with mandatory audit | Yavuz | F1 | M5 | S |

#### WP-HITL-001 — Authority policy engine (L0–L4)

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-HITL-POLICY |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Implement deterministic policy evaluation that decides required human involvement independently of any AI text.

**Source requirements (03).** FR-HITL-001, FR-HITL-002

**Architecture components (02).** ARCH-HITL-POLICY, ARCH-SEC-AUTHZ

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- AuthorityPolicy artifact + evaluator
- risk-class mapping for catalogued actions
- policy tests including adversarial inputs

**Major tasks.**
- define L0–L4 semantics per action class
- implement evaluator with no LLM influence
- test that model output cannot change the required level

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-HITL-POLICY

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0).


#### WP-HITL-002 — Approval binding to exact proposal/plan revision and world

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-HITL-APPROVAL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Bind every approval to the precise artifact revision, world and freshness context it was granted for.

**Source requirements (03).** FR-HITL-003, FR-HITL-004, FR-HITL-005

**Architecture components (02).** ARCH-HITL-APPROVAL, ARCH-HITL-EXPIRY, ARCH-WORLD-SCOPE

**Inputs / required contracts.** gated by DEP-090 (DN-RT-IDP → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON → DN-HITL-APPROVAL, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL → DN-HITL-APPROVAL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- approval binding fields in ApprovalRequest
- material-change invalidation rule
- binding tests

**Major tasks.**
- define binding key (proposal/plan revision + WorldID + freshness)
- implement invalidation on material change
- test cross-world and cross-revision rejection

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, AV-SCEN-10, TEST-HITL-BINDING

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard gate).


#### WP-HITL-003 — Expiry, replay and staleness rejection

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-HITL-APPROVAL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Reject stale, expired or replayed approvals at execution time, not only at display time.

**Source requirements (03).** FR-HITL-006, NFR-REL-002

**Architecture components (02).** ARCH-AUTO-WORKFLOW, ARCH-HITL-APPROVAL, ARCH-HITL-EXPIRY

**Inputs / required contracts.** gated by DEP-090 (DN-RT-IDP → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON → DN-HITL-APPROVAL, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL → DN-HITL-APPROVAL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- expiry/nonce handling
- execution-time checks
- negative suite (AV-SCEN-04)

**Major tasks.**
- define expiry policy per risk class
- implement replay protection
- build adversarial approval cases for RQ-3

**Verification work (03 planned families).** AV-SCEN-04, AV-SCEN-10, BENCH-RQ3-001, TEST-HITL-REPLAY-NEG

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R04, AUTO-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (hard gate: accepted stale/replayed protected executions must be zero).


#### WP-HITL-004 — Identity-bound approvals

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-RT-IDP |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure each approval maps to exactly one authenticated, authorized human identity.

**Source requirements (03).** FR-HITL-007, NFR-SEC-005, NFR-PERF-012

**Architecture components (02).** ARCH-EDGE-AUTH, ARCH-EDGE-BFF, ARCH-HITL-APPROVAL, ARCH-SEC-IDP

**Inputs / required contracts.** gated by DEP-010 (DN-PLAT-INTEG → DN-RT-IDP, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- Keycloak-backed session propagation into approvals
- authorization check for approver role
- approval persistence latency measurement

**Major tasks.**
- wire OIDC session to BFF and approval service
- implement approver authorization
- measure submission → durable record latency

**Verification work (03 planned families).** AV-SCEN-01, BENCH-PERF-WF, E2E-01, TEST-HITL-RECORD, TEST-SEC-AUTHN

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R09

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; real HITL requires the identity runtime (05 DEP-GAP-04 timing).


#### WP-HITL-005 — Approval record, audit trail and protected-action coverage

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-HITL-APPROVAL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Persist approvals as canonical application data with a complete audit chain from proposal to verified effect.

**Source requirements (03).** FR-HITL-008, NFR-SEC-010

**Architecture components (02).** ARCH-AUTO-VERIFY, ARCH-HITL-APPROVAL, ARCH-OBS-AUDIT

**Inputs / required contracts.** gated by DEP-090 (DN-RT-IDP → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON → DN-HITL-APPROVAL, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL → DN-HITL-APPROVAL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- ApprovalRecord schema and storage
- audit chain linking proposal → plan → approval → command → effect
- coverage test for protected actions

**Major tasks.**
- define record fields (decision, subject, binding, actor, timestamp)
- implement audit emission at each hop
- verify 100% coverage on formal protected actions

**Verification work (03 planned families).** AV-SCEN-01, TEST-HITL-RECORD, TEST-SEC-AUDIT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; approvals may never exist only in logs (Item 67 #149).


#### WP-HITL-006 — Dual approval for highest-risk actions

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-HITL-APPROVAL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Require two distinct authorized identities where the policy demands it.

**Source requirements (03).** FR-HITL-009

**Architecture components (02).** ARCH-HITL-DUAL

**Inputs / required contracts.** gated by DEP-090 (DN-RT-IDP → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON → DN-HITL-APPROVAL, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL → DN-HITL-APPROVAL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- dual-approval policy entries
- distinct-identity enforcement
- tests including same-identity attempts

**Major tasks.**
- define which catalogued actions require dual approval
- implement enforcement and UI flow
- test self-duplication rejection

**Verification work (03 planned families).** BENCH-RQ3-001, TEST-HITL-DUAL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1, Item 68 authority set).


#### WP-HITL-007 — Break-glass path with mandatory audit

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-HITL-APPROVAL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Provide an explicit emergency path that is always distinguishable, auditable and never able to bypass hard invariants.

**Source requirements (03).** FR-HITL-010, NFR-SEC-012

**Architecture components (02).** ARCH-OBS-AUDIT, ARCH-SEC-BREAKGLASS

**Inputs / required contracts.** gated by DEP-090 (DN-RT-IDP → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY → DN-HITL-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON → DN-HITL-APPROVAL, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL → DN-HITL-APPROVAL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- break-glass procedure and flag
- high-risk audit record emission
- drill test

**Major tasks.**
- define what break-glass may and may not do
- implement flagging and alerting
- drill on INTEGRATION and verify audit completeness

**Verification work (03 planned families).** TEST-SEC-AUDIT, TEST-SEC-BREAKGLASS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; if break-glass is enabled it must be auditable — hard invariants remain non-bypassable.


### 6.16 Manufacturing Command Center (`WP-UI-*`, 12 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-UI-001 | Command Center shell and BFF contract | Asrın | F0 | M1 | M |
| WP-UI-002 | manufacturing facility state and operational views | Asrın | F1 | M2 | S |
| WP-UI-003 | Inspection viewer with overlays | Selman | F1 | M4 | S |
| WP-UI-004 | Incident investigation workspace (RCA) | Asrın | F1 | M4 | S |
| WP-UI-005 | Planning and validation views | Batu | F1 | M4 | S |
| WP-UI-006 | Approval Center | Asrın | F0 | M3 | M |
| WP-UI-007 | Workflow progress and verification view | Batu | F1 | M4 | S |
| WP-UI-008 | Epistemic, staleness and failure-state semantics | Asrın | F1 | M5 | M |
| WP-UI-009 | System health and environment diagnostics view | Yavuz | F1 | M4 | S |
| WP-UI-010 | Incident and decision timeline | Asrın | F1 | M5 | S |
| WP-UI-011 | Browser E2E harness and compatibility validation | Asrın | F1 / S2 | M8 | S |
| WP-UI-012 | Presenter mode integrity | Asrın | F1 | M8 | S |

#### WP-UI-001 — Command Center shell and BFF contract

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-UI-BFFCON |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Stand up the SPA shell and the BFF contract that is the only path from browser to backend.

**Source requirements (03).** FR-UI-001, NFR-PERF-014

**Architecture components (02).** ARCH-EDGE-BFF, ARCH-EDGE-WEB

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

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

**Verification work (03 planned families).** AV-SCEN-01, BENCH-PERF-UI, DEMO-GS01-001, E2E-01, TEST-UI-BROWSER

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0). Browser must never reach broker or database directly.


#### WP-UI-002 — manufacturing facility state and operational views

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Show current operational state scoped to the active world with honest freshness.

**Source requirements (03).** FR-UI-002, NFR-PERF-005

**Architecture components (02).** ARCH-EDGE-BFF, ARCH-EDGE-NOTIFY, ARCH-EDGE-WEB

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- manufacturing facility/equipment/lot state views
- world selector
- realtime or polled update path

**Major tasks.**
- implement Twin-backed state views
- implement world scoping in every query
- measure state visibility latency

**Verification work (03 planned families).** AV-SCEN-01, BENCH-PERF-UI, DEMO-GS01-001, TEST-UI-BROWSER

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-UI-003 — Inspection viewer with overlays

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Let a human inspect the artifact and the model output together, including localization and segmentation overlays.

**Source requirements (03).** FR-UI-003

**Architecture components (02).** ARCH-EDGE-WEB, ARCH-VIS-ARTIFACT

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- artifact viewer with scoped access
- overlay rendering for boxes/masks
- UNKNOWN/OOD presentation

**Major tasks.**
- implement scoped artifact access through BFF
- render overlays from observation payloads
- present confidence and provenance

**Verification work (03 planned families).** AV-SCEN-01, DEMO-GS01-001, TEST-UI-VISION

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-UI-004 — Incident investigation workspace (RCA)

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Present RCA output so hypotheses, evidence, conflicts and abstention are visually distinct.

**Source requirements (03).** FR-UI-004

**Architecture components (02).** ARCH-EDGE-WEB

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- assessment view with evidence panels
- evidence reference navigation
- abstention/insufficient-evidence presentation

**Major tasks.**
- design view model from IC-AI-003
- implement evidence drill-down to source records
- present conflicting evidence explicitly

**Verification work (03 planned families).** AV-SCEN-01, DEMO-GS01-001, TEST-UI-BROWSER

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-UI-005 — Planning and validation views

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Show candidate plans, their rationale and their validation status before anyone approves anything.

**Source requirements (03).** FR-UI-005

**Architecture components (02).** ARCH-EDGE-WEB, ARCH-SCH-PLAN

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- plan comparison view
- validation status presentation
- objective/rationale display

**Major tasks.**
- design view model from IC-SCH-003/004
- present validator verdicts prominently
- handle no-plan/failure states

**Verification work (03 planned families).** AV-SCEN-01, DEMO-GS01-001, TEST-UI-PLAN

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-UI-006 — Approval Center

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-UI-APPROVAL |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Give the human the bound context, risk and consequences needed to approve or reject a protected action.

**Source requirements (03).** FR-UI-006, NFR-UX-003

**Architecture components (02).** ARCH-EDGE-WEB, ARCH-HITL-UI

**Inputs / required contracts.** gated by DEP-107 (DN-UI-SHELL → DN-UI-APPROVAL, HARD/START@COMPONENT_READY, need-by S4), DEP-108 (DN-RT-IDP → DN-UI-APPROVAL, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- pending/completed approvals view
- bound-context panel (proposal, plan, revision, risk)
- approve/reject flow with authenticated identity

**Major tasks.**
- implement approval list and detail views
- render binding and expiry state
- implement rejection with reason
- test that context is never missing for protected approvals

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, DEMO-GS01-001, TEST-UI-BROWSER, TEST-UI-SEMANTICS

**Integration checkpoint.** E2E-01, AV-SCEN-04, DEMO-GS01-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R10, DEMO-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 human authority surface).


#### WP-UI-007 — Workflow progress and verification view

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Show what the system is doing and whether the effect was actually verified.

**Source requirements (03).** FR-UI-007

**Architecture components (02).** ARCH-EDGE-WEB

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- workflow progress view
- verification outcome presentation
- failure/unknown state handling

**Major tasks.**
- project workflow state into domain terms
- render ACCEPTED vs VERIFIED_SUCCESS distinctly
- handle UNKNOWN_VERIFY_REQUIRED honestly

**Verification work (03 planned families).** AV-SCEN-01, DEMO-GS01-001, TEST-UI-PLAN

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-UI-008 — Epistemic, staleness and failure-state semantics

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Encode epistemic class, staleness and failures so the UI never implies certainty it does not have.

**Source requirements (03).** FR-UI-008, NFR-UX-001, NFR-UX-002, NFR-UX-004

**Architecture components (02).** ARCH-EDGE-BFF, ARCH-EDGE-WEB, ARCH-TWIN-FRESHNESS

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- visual encoding system for epistemic classes
- staleness indicators
- failure/timeout presentation patterns

**Major tasks.**
- define encoding that is not colour-only
- implement staleness propagation from Twin freshness
- replace indefinite spinners with explicit failure states
- review pass across all primary views

**Verification work (03 planned families).** AV-SCEN-07, AV-SCEN-09, DEMO-GS01-001, TEST-UI-SEMANTICS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (usability hard-gate family).


#### WP-UI-009 — System health and environment diagnostics view

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Let anyone see which release, environment and world they are looking at, and which capabilities are degraded.

**Source requirements (03).** FR-UI-009

**Architecture components (02).** ARCH-EDGE-WEB, ARCH-OBS-HEALTH, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- diagnostics panel
- release/environment/world identity display
- capability health presentation

**Major tasks.**
- surface ReleaseManifest/EnvironmentManifest through BFF
- render per-capability health states
- link to diagnostic bundle generation

**Verification work (03 planned families).** DEMO-GS01-001, TEST-UI-DIAG

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DEMO-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; demo and debugging integrity depend on it.


#### WP-UI-010 — Incident and decision timeline

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Reconstruct an incident as a correlated sequence of perception, reasoning, decision, execution and verification.

**Source requirements (03).** FR-UI-010

**Architecture components (02).** ARCH-EDGE-WEB, ARCH-OBS-AUDIT, ARCH-OBS-TRACE

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- timeline view built on CorrelationID
- cross-record navigation
- export/share view for reviews

**Major tasks.**
- define timeline view model from correlated records
- implement navigation between observation, assessment, plan, approval, workflow and effect
- test with real GS-01 run data

**Verification work (03 planned families).** AV-SCEN-01, DEMO-GS01-001, TEST-UI-BROWSER

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (F1).


#### WP-UI-011 — Browser E2E harness and compatibility validation

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class S2) |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Validate primary flows in real browsers against the real BFF, on recorded browser versions.

**Source requirements (03).** NFR-UX-005

**Architecture components (02).** ARCH-EDGE-WEB

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- browser E2E suite for primary flows
- CI/INTEGRATION execution wiring
- recorded browser versions in evidence

**Major tasks.**
- select flows: state view, inspection, RCA, plan, approval, workflow
- implement suite against real backend (no mocked BFF)
- record versions and results at M8

**Verification work (03 planned families).** TEST-UI-BROWSER

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** S2: MISS on a secondary browser is recorded, not silently dropped.


#### WP-UI-012 — Presenter mode integrity

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make demo presentation mode incapable of hiding approvals, validation, failures or effect verification.

**Source requirements (03).** NFR-UX-006

**Architecture components (02).** ARCH-EDGE-PRESENT

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- presenter mode implementation
- integrity tests proving no concealment
- demo rehearsal checklist entry

**Major tasks.**
- define what presenter mode may change (layout, density) and may not (semantics)
- implement and test against the GS-01 rehearsal
- verify with the demo abort conditions

**Verification work (03 planned families).** DEMO-GS01-001, TEST-UI-SEMANTICS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DEMO-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; the demo must not be able to lie.


### 6.17 Platform & Runtime (`WP-PLAT-*`, 7 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-PLAT-001 | Compose profiles and mandatory runtime composition | Yavuz | F0 | M1 | M |
| WP-PLAT-002 | mfgctl developer and operator CLI | Yavuz | F1 | M1 | M |
| WP-PLAT-003 | Runtime service bring-up on the shared host | Yavuz | F1 | M2 | M |
| WP-PLAT-004 | Resource profiles and footprint control | Yavuz | F1 / A1 | M5 | M |
| WP-PLAT-005 | Environment, release and world manifests | Yavuz | F1 | M5 | M |
| WP-PLAT-006 | Onboarding, executable documentation and diagnostics | Yavuz | F1 / S2 | M8 | M |
| WP-PLAT-007 | Benchmark and demo preflight tooling | Yavuz | F1 / H0 | M6 | S |

#### WP-PLAT-001 — Compose profiles and mandatory runtime composition

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-PLAT-COMPOSE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `infra/compose/`; `infra/mfgctl/capabilities.json`; `evidence/WP-PLAT-001/` |

**Purpose.** Define the containerized runtime composition (local profiles and the shared Integration profile) that hosts all nine deployables plus infrastructure.

**Source requirements (03).** FR-PLAT-001, FR-PLAT-002, NFR-DEP-001, NFR-DEP-002, NFR-DEP-006

**Architecture components (02).** ARCH-OBS-HEALTH, ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-003 (DN-PLAT-TOOLING → DN-PLAT-COMPOSE, HARD/START@SKELETON_READY, need-by M0 (S1))

**Deliverables.**
- Compose definitions with capability profiles
- Integration profile composition
- startup-to-healthy measurement
- profile validation in CI

**Major tasks.**
- define services, networks, volumes and resource limits
- implement capability profiles (core, vision, ai, automation, full)
- validate profiles render and start on a clean Linux host
- measure startup to healthy with pre-pulled images

**Verification work (03 planned families).** AV-SCEN-12, BENCH-DEP-STARTUP, BENCH-DX-001, BENCH-E2E-001, E2E-01, INSP-DEP-HOST, TEST-DEP-PLATFORM, TEST-PLAT-COMPOSE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 reproducible platform). Kubernetes and cloud remain explicitly out of scope.


#### WP-PLAT-002 — mfgctl developer and operator CLI

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-PLAT-TOOLING |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `tools/mfgctl/`; `tools/mfgctl/schemas/capabilities.schema.json`; `evidence/WP-PLAT-002/` |

**Purpose.** Provide one entry point for bootstrap, doctor, profile control, scenarios, smoke tests and diagnostics.

**Source requirements (03).** FR-PLAT-003, NFR-DX-001, NFR-DX-002, NFR-DX-003, NFR-DX-004

**Architecture components (02).** ARCH-PLAT-CICD, ARCH-PLAT-CLI, ARCH-PLAT-COMPOSE

**Inputs / required contracts.** gated by DEP-001 (DN-PLAT-REPO → DN-PLAT-TOOLING, HARD/START@INTEGRATION_READY, need-by M0 (S1))

**Deliverables.**
- mfgctl command surface
- doctor checks
- smoke commands per capability
- timing instrumentation for DX targets

**Major tasks.**
- define command contract and configuration discovery
- implement bootstrap/doctor/profile/scenario/smoke
- implement diagnostics bundle generation hook
- measure doctor/static/smoke/profile-start durations

**Verification work (03 planned families).** BENCH-DX-001, TEST-PLAT-FABCTL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; onboarding and reproducibility depend on it.


#### WP-PLAT-003 — Runtime service bring-up on the shared host

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-PLAT-INTEG |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Bring PostgreSQL, NATS JetStream, SeaweedFS, Keycloak, Temporal, Qdrant, MLflow (and optional Valkey) to healthy, configured state on the Integration host in dependency order.

**Source requirements (03).** FR-PLAT-001, NFR-DEP-001

**Architecture components (02).** ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-004 (DN-PLAT-COMPOSE → DN-PLAT-INTEG, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M0 (S1))

**Deliverables.**
- per-service configuration and health checks
- dependency-ordered startup (02 Sequence I)
- runtime readiness checklist per E2E-01 gate

**Major tasks.**
- provision each runtime with persistent volumes and limits
- configure Keycloak realm/clients and Temporal namespaces
- verify startup order avoids deadlocks
- stage readiness per 05 need-by dates (S4/S5)

**Verification work (03 planned families).** AV-SCEN-12, BENCH-E2E-001, E2E-01, TEST-DEP-PLATFORM, TEST-PLAT-COMPOSE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; Valkey is optional (F3) and never correctness-bearing.


#### WP-PLAT-004 — Resource profiles and footprint control

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-INTEG |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep the whole system inside the 16 GiB shared-host envelope with measured steady and peak usage.

**Source requirements (03).** NFR-RES-001, NFR-RES-002, NFR-RES-003, NFR-RES-008, NFR-CAP-009

**Architecture components (02).** ARCH-EDGE-BFF, ARCH-PLAT-COMPOSE, ARCH-SEC-IDP

**Inputs / required contracts.** gated by DEP-004 (DN-PLAT-COMPOSE → DN-PLAT-INTEG, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M0 (S1))

**Deliverables.**
- per-container resource limits (ResourceProfiles)
- cgroup-based measurement harness
- concurrency validation for interactive sessions

**Major tasks.**
- assign limits per service class
- implement memory/CPU sampling over steady windows
- run soak measurement and record peaks/OOM counts
- verify ≥8 concurrent authenticated sessions

**Verification work (03 planned families).** BENCH-CAP-ENV, BENCH-RES-FOOTPRINT, RES-SOAK-001

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1 memory envelope; CPU characterization is C3. Exceeding the envelope is a finding, not a silent limit raise.


#### WP-PLAT-005 — Environment, release and world manifests

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-ART-RELEASE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Bind every formal run to an exact environment, release, hardware and world identity.

**Source requirements (03).** FR-PLAT-005, FR-PLAT-010, NFR-REP-003, NFR-REP-007

**Architecture components (02).** ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-116 (DN-PLAT-RUNNER → DN-ART-RELEASE, HARD/FREEZE@EVALUATION_READY, need-by M6 (S11))

**Deliverables.**
- EnvironmentManifest / ReleaseManifest formats
- HardwareProfile records
- manifest binding in runner and demo tooling

**Major tasks.**
- define manifest fields and generation points
- emit manifests from CD and runner
- record hardware profiles for evaluation, CPU baseline and Vision hosts (03 GAP-RTM-021)
- verify immutable artifact identities

**Verification work (03 planned families).** BENCH-FBC-001, DEMO-GS01-001, INSP-DEP-HOST, INSP-GOV-ACCEPT, REPRO-CLEANHOST-001, TEST-EVAL-RUNNER, TEST-PLAT-CD, TEST-REP-LOCKS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R09

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; every quantitative claim depends on this binding.


#### WP-PLAT-006 — Onboarding, executable documentation and diagnostics

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class S2) |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-PLAT-TOOLING |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make a non-author able to clone, bootstrap, verify and diagnose the system within one focused hour.

**Source requirements (03).** NFR-DX-005, NFR-DX-007, NFR-DX-008

**Architecture components (02).** ARCH-PLAT-CLI, ARCH-PLAT-RELEASE, ARCH-SEC-SECRET

**Inputs / required contracts.** gated by DEP-001 (DN-PLAT-REPO → DN-PLAT-TOOLING, HARD/START@INTEGRATION_READY, need-by M0 (S1))

**Deliverables.**
- quickstart and runbook set
- executable documentation validation
- diagnostic bundle with redaction

**Major tasks.**
- write quickstart/reproduction/runbook docs against the real release
- implement doc command validation in CI
- implement diagnostics bundle generation and secret redaction
- run a non-author onboarding walk-through and record it

**Verification work (03 planned families).** BENCH-DX-001, INSP-DX-ONBOARD, TEST-DX-DOCS, TEST-OBS-REDACTION

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** S2 timing targets; the validation itself (NFR-DX-007) is required before M8.


#### WP-PLAT-007 — Benchmark and demo preflight tooling

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-PLAT-RUNNER |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prevent invalid formal runs by checking disk headroom, workload isolation and environment integrity before execution.

**Source requirements (03).** NFR-RES-004, NFR-RES-005

**Architecture components (02).** ARCH-PLAT-CICD, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-114 (DN-PLAT-FAILVAL → DN-PLAT-RUNNER, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-115 (DN-PLAT-CD → DN-PLAT-RUNNER, HARD/INTEGRATION@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- preflight check implementation
- undeclared-workload detection
- preflight record attached to runs

**Major tasks.**
- define preflight checks and thresholds
- implement host-state inspection
- block run start on failure and record the reason

**Verification work (03 planned families).** INSP-DEP-HOST, TEST-RES-PREFLIGHT

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R05, PLAT-R12

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut; a benchmark started on a contended host produces unusable evidence.


### 6.18 CI/CD (`WP-CICD-*`, 6 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-CICD-001 | CI pipeline and required gates | Yavuz | F1 | M0 | M |
| WP-CICD-002 | CD to INTEGRATION with immutable artifacts | Yavuz | F0 | M1 | M |
| WP-CICD-003 | Automated migration execution in the deployment path | Yavuz | F1 | M2 | S |
| WP-CICD-004 | Supply chain: pinning, scanning and SBOM | Yavuz | F1 / H0 | M5 | M |
| WP-CICD-005 | Release rollback capability | Yavuz | F1 / A1 | M5 | S |
| WP-CICD-006 | CI isolation for untrusted contributions | Yavuz | F1 / H0 | M5 | S |

#### WP-CICD-001 — CI pipeline and required gates

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M0 / S1 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `.github/workflows/ci.yml`; `ci/`; `ruff.toml`; `pyrightconfig.json`; `evidence/WP-CICD-001/` |

**Purpose.** Establish the protected pipeline that every change must pass, with tiered test execution and flake control.

**Source requirements (03).** FR-PLAT-004, NFR-DX-006

**Architecture components (02).** ARCH-PLAT-CICD, ARCH-PLAT-RELEASE

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- CI workflows (lint, type, unit, contract, integration tiers)
- required-check configuration
- flaky-test registry and quarantine policy

**Major tasks.**
- define pipeline stages and runtimes
- wire real PostgreSQL/NATS services for integration tier
- implement quarantine registry with expiry
- prohibit retry-until-green on release gates

**Verification work (03 planned families).** INSP-DEP-HOST, TEST-DX-FLAKE, TEST-PLAT-CD

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R08

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut (M0 foundation).


#### WP-CICD-002 — CD to INTEGRATION with immutable artifacts

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-PLAT-CD |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Deploy only main-derived, immutable, digest-pinned artifacts to the Integration host, with a deployment record.

**Source requirements (03).** FR-PLAT-004, FR-PLAT-005, NFR-DEP-003

**Architecture components (02).** ARCH-PLAT-CICD, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-002 (DN-PLAT-REPO → DN-PLAT-CD, HARD/START@INTEGRATION_READY, need-by M0→M1), DEP-005 (DN-PLAT-INTEG → DN-PLAT-CD, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- build-and-publish workflow to GHCR
- deploy workflow with DeploymentRecord emission
- no-host-patch enforcement

**Major tasks.**
- implement image build with provenance and digest pinning
- implement deploy job and rollback hook
- emit DeploymentRecord with release/environment identity
- verify zero manual source patches on host

**Verification work (03 planned families).** INSP-DEP-HOST, TEST-PLAT-CD

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R08

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 reproducible platform).


#### WP-CICD-003 — Automated migration execution in the deployment path

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-PLAT-CD |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Run schema migrations through versioned tooling with inspectable status as part of deployment.

**Source requirements (03).** NFR-DEP-004

**Architecture components (02).** ARCH-DATA-PG, ARCH-PLAT-CICD

**Inputs / required contracts.** gated by DEP-002 (DN-PLAT-REPO → DN-PLAT-CD, HARD/START@INTEGRATION_READY, need-by M0→M1), DEP-005 (DN-PLAT-INTEG → DN-PLAT-CD, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- migration stage in CD
- migration status surface
- failure handling and halt semantics

**Major tasks.**
- wire migration runner into deploy
- implement pre/post checks
- test failed-migration handling

**Verification work (03 planned families).** TEST-DEP-MIGRATION

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; manual SQL on the host is forbidden.


#### WP-CICD-004 — Supply chain: pinning, scanning and SBOM

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep dependency and image identities locked and vulnerabilities dispositioned.

**Source requirements (03).** NFR-SEC-002, NFR-REP-005, NFR-REP-006

**Architecture components (02).** ARCH-CTR-VERSIONING, ARCH-PLAT-CICD, ARCH-SEC-SUPPLYCHAIN

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- lockfiles and digest pins
- vulnerability scanning with disposition records
- SBOM generation
- generated-client drift detection

**Major tasks.**
- enforce pins and prohibit unbounded latest
- wire scanning into CI with severity policy
- generate SBOM per release
- detect stale generated clients/contracts

**Verification work (03 planned families).** TEST-REP-CODEGEN, TEST-REP-LOCKS, TEST-SEC-SUPPLYCHAIN

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0: no known unmitigated Critical vulnerabilities in the final release).


#### WP-CICD-005 — Release rollback capability

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-CD |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Be able to return to a known-good compatible release quickly where migration state permits.

**Source requirements (03).** NFR-REC-005

**Architecture components (02).** ARCH-PLAT-CICD, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-002 (DN-PLAT-REPO → DN-PLAT-CD, HARD/START@INTEGRATION_READY, need-by M0→M1), DEP-005 (DN-PLAT-INTEG → DN-PLAT-CD, HARD/INTEGRATION@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- rollback procedure and tooling
- compatibility rules for migrations
- rollback drill record

**Major tasks.**
- define rollback-safe migration policy
- implement rollback command path
- drill rollback on INTEGRATION and measure duration

**Verification work (03 planned families).** RESTORE-ROLLBACK-001

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1 timing target; rollback may be impossible for irreversible migrations — that constraint is documented, not hidden.


#### WP-CICD-006 — CI isolation for untrusted contributions

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure fork/PR jobs can never obtain privileged credentials or sensitive runners.

**Source requirements (03).** NFR-SEC-011

**Architecture components (02).** ARCH-PLAT-CICD, ARCH-SEC-SUPPLYCHAIN

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- workflow permission model
- secret scoping rules
- negative test for fork PR

**Major tasks.**
- separate trusted and untrusted workflow paths
- scope tokens to least privilege
- verify no secret exposure on fork PRs

**Verification work (03 planned families).** TEST-SEC-CIISOLATION

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0).


### 6.19 Observability (`WP-OBS-*`, 6 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-OBS-001 | Telemetry pipeline (OTel → Collector → OpenObserve) | Yavuz | F1 | M1 | M |
| WP-OBS-002 | Distributed trace propagation across the closed loop | Yavuz | F1 | M3 | S |
| WP-OBS-003 | Health, readiness and degradation states | Yavuz | F1 | M4 | S |
| WP-OBS-004 | Audit store separation from telemetry | Yavuz | F1 / H0 | M4 | S |
| WP-OBS-005 | Redaction and diagnostic bundles | Yavuz | F1 / H0 | M5 | S |
| WP-OBS-006 | Telemetry retention, quota and instrumentation overhead | Yavuz | F1 / S2 | M7 | S |

#### WP-OBS-001 — Telemetry pipeline (OTel → Collector → OpenObserve)

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-RT-OBS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `packages/observability/`; `infra/observability/`; `evidence/WP-OBS-001/` |

**Purpose.** Centralize logs, metrics and traces with consistent service, environment and correlation fields.

**Source requirements (03).** FR-PLAT-006, NFR-OBS-001, NFR-OBS-002

**Architecture components (02).** ARCH-OBS-HEALTH, ARCH-OBS-STORE, ARCH-OBS-TELEMETRY

**Inputs / required contracts.** gated by DEP-011 (DN-PLAT-INTEG → DN-RT-OBS, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M1 (S2)), DEP-109 (DN-PLAT-CD → DN-RT-OBS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6))

**Deliverables.**
- OTel SDK wiring per service
- Collector pipeline configuration
- OpenObserve deployment and dashboards
- structured log field standard

**Major tasks.**
- define resource attributes and log schema
- instrument all mandatory deployables
- configure collector pipelines and storage
- verify field coverage in CI

**Verification work (03 planned families).** AV-SCEN-01, TEST-OBS-HEALTH, TEST-OBS-LOGS, TEST-OBS-TELEMETRY

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; M1 requires health/basic instrumentation, M5 requires evaluation-grade telemetry.


#### WP-OBS-002 — Distributed trace propagation across the closed loop

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-RT-OBS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make one incident traceable across HTTP, NATS and Temporal boundaries end to end.

**Source requirements (03).** FR-PLAT-007, NFR-OBS-003, NFR-OBS-005

**Architecture components (02).** ARCH-OBS-TELEMETRY, ARCH-OBS-TRACE

**Inputs / required contracts.** gated by DEP-011 (DN-PLAT-INTEG → DN-RT-OBS, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M1 (S2)), DEP-109 (DN-PLAT-CD → DN-RT-OBS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6))

**Deliverables.**
- context propagation adapters
- correlation chain verification test
- trace-completeness check for acceptance runs

**Major tasks.**
- propagate trace context through async boundaries
- verify GS-01 chain is inspectable end to end
- assert required identity fields on formal-evidence telemetry

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, TEST-DATA-REFINTEGRITY, TEST-OBS-TRACEPROP

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; M3 requires distributed traceability (05 §7).


#### WP-OBS-003 — Health, readiness and degradation states

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-RT-OBS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Expose per-capability health (HEALTHY/DEGRADED/UNAVAILABLE) rather than binary process liveness.

**Source requirements (03).** NFR-OBS-004, NFR-REL-009

**Architecture components (02).** ARCH-OBS-HEALTH, ARCH-OBS-STORE

**Inputs / required contracts.** gated by DEP-011 (DN-PLAT-INTEG → DN-RT-OBS, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M1 (S2)), DEP-109 (DN-PLAT-CD → DN-RT-OBS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6))

**Deliverables.**
- health/readiness endpoints per deployable
- capability-level health model
- failure-detection latency measurement

**Major tasks.**
- define capability health semantics per service
- implement endpoints and aggregation
- measure detection latency under injected failures

**Verification work (03 planned families).** RES-DEPFAIL-001, RES-PROCESS-001, TEST-OBS-HEALTH

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; resilience evidence depends on observable degradation.


#### WP-OBS-004 — Audit store separation from telemetry

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-RT-OBS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep protected-action audit records in durable application storage, independent of telemetry retention.

**Source requirements (03).** FR-SEC-007, NFR-OBS-007

**Architecture components (02).** ARCH-OBS-AUDIT, ARCH-OBS-STORE, ARCH-SEC-AUTHZ

**Inputs / required contracts.** gated by DEP-011 (DN-PLAT-INTEG → DN-RT-OBS, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M1 (S2)), DEP-109 (DN-PLAT-CD → DN-RT-OBS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6))

**Deliverables.**
- audit store and schema
- separation test (telemetry rotation does not erase audit)
- audit query surface

**Major tasks.**
- define audit record model and retention
- implement write path from protected actions
- test rotation/purge independence

**Verification work (03 planned families).** TEST-OBS-AUDITSEP, TEST-SEC-AUDIT

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PLAT-R11

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0).


#### WP-OBS-005 — Redaction and diagnostic bundles

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-RT-OBS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Guarantee no plaintext secrets leave the system in logs, bundles or evidence.

**Source requirements (03).** NFR-OBS-006, NFR-DX-008

**Architecture components (02).** ARCH-OBS-TELEMETRY, ARCH-PLAT-CLI, ARCH-SEC-SECRET

**Inputs / required contracts.** gated by DEP-011 (DN-PLAT-INTEG → DN-RT-OBS, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M1 (S2)), DEP-109 (DN-PLAT-CD → DN-RT-OBS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6))

**Deliverables.**
- redaction rules
- secret scanning over logs and bundles
- bundle generation timing

**Major tasks.**
- implement redaction at emission and bundle assembly
- scan logs/bundles/evidence in CI and before sealing
- measure bundle generation duration

**Verification work (03 planned families).** BENCH-DX-001, TEST-OBS-REDACTION

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0).


#### WP-OBS-006 — Telemetry retention, quota and instrumentation overhead

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class S2) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-RT-OBS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep observability affordable on the shared host and quantify its cost.

**Source requirements (03).** NFR-OBS-008, NFR-OBS-009

**Architecture components (02).** ARCH-OBS-STORE, ARCH-OBS-TELEMETRY

**Inputs / required contracts.** gated by DEP-011 (DN-PLAT-INTEG → DN-RT-OBS, HARD/MILESTONE_EXIT@SKELETON_READY, need-by M1 (S2)), DEP-109 (DN-PLAT-CD → DN-RT-OBS, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M3 (S6))

**Deliverables.**
- retention/quota configuration
- overhead measurement protocol (instrumented vs diagnostic baseline)
- recorded overhead results

**Major tasks.**
- configure retention windows and quotas
- implement overhead benchmark with instrumentation disabled baseline
- record p95 latency and CPU deltas

**Verification work (03 planned families).** BENCH-OBS-OVERHEAD, INSP-OBS-RETENTION

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PERF-R07, PLAT-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** S2: measured overhead above the guideline is disclosed, not suppressed.


### 6.20 Security (`WP-SEC-*`, 8 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-SEC-001 | Keycloak realm, clients and interactive authentication | Yavuz | F1 | M3 | M |
| WP-SEC-002 | Service identities and least-privilege credentials | Yavuz | F1 / H0 | M4 | M |
| WP-SEC-003 | Backend authorization enforcement | Asrın | F1 / H0 | M3 | S |
| WP-SEC-004 | AI-reachable capability surface restriction | Yavuz | F1 / H0 | M4 | S |
| WP-SEC-005 | Secret sourcing and hygiene | Yavuz | F1 / H0 | M4 | M |
| WP-SEC-006 | Test-auth prohibition in formal environments | Yavuz | F1 / H0 | M5 | S |
| WP-SEC-007 | Oracle access denial at runtime | Yavuz | F1 / H0 | M4 | S |
| WP-SEC-008 | Security negative suite and external egress audit | Yavuz | F1 / H0 | M5 | S |

#### WP-SEC-001 — Keycloak realm, clients and interactive authentication

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-RT-IDP |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Provide real interactive authentication for all formal environments.

**Source requirements (03).** FR-SEC-001, NFR-SEC-003

**Architecture components (02).** ARCH-EDGE-AUTH, ARCH-EDGE-BFF, ARCH-SEC-AUTHZ, ARCH-SEC-IDP

**Inputs / required contracts.** gated by DEP-010 (DN-PLAT-INTEG → DN-RT-IDP, HARD/INTEGRATION@INTEGRATION_READY, need-by E2E-01 readiness (end S4))

**Deliverables.**
- realm/client configuration as code
- OIDC integration in BFF/UI
- TLS on browser ingress for formal environments

**Major tasks.**
- configure realm, clients, roles and users
- implement login/session handling
- enable TLS termination for INTEGRATION/EVALUATION/DEMO
- verify real login before E2E-01

**Verification work (03 planned families).** AV-SCEN-01, E2E-01, TEST-SEC-AUTHN, TEST-SEC-TLS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; E2E-01 requires actual login (05 DEP-GAP-04).


#### WP-SEC-002 — Service identities and least-privilege credentials

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Give every service its own identity and scope; eliminate any universal super-credential.

**Source requirements (03).** FR-SEC-002, NFR-SEC-007, NFR-SEC-008

**Architecture components (02).** ARCH-PLAT-COMPOSE, ARCH-SEC-AUTHZ, ARCH-SEC-IDP, ARCH-SEC-SECRET, ARCH-SEC-SUPPLYCHAIN

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- service identity matrix (DB roles, broker accounts, client credentials)
- container runtime posture (non-root, non-privileged)
- anonymous-mutation negative tests

**Major tasks.**
- define identity per deployable and data plane
- implement credential issuance and rotation approach
- verify container posture and exceptions
- test anonymous and cross-service access denial

**Verification work (03 planned families).** TEST-AUTH-NEG, TEST-SEC-CONTAINER, TEST-SEC-SVCID

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0 family).


#### WP-SEC-003 — Backend authorization enforcement

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | `services/manufacturing-core/src/manufacturing_core/authz.py`; `services/manufacturing-core/src/manufacturing_core/enforcement.py`; `evidence/WP-SEC-003/` |

**Purpose.** Enforce authorization in the backend for every protected command — UI visibility is never authorization.

**Source requirements (03).** FR-SEC-003

**Architecture components (02).** ARCH-CORE-CMD, ARCH-SEC-AUTHZ

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- policy enforcement points in Core and Automation
- unknown-permission deny default
- authorization negative suite

**Major tasks.**
- define enforcement points per protected action
- implement deny-by-default evaluation
- test UI-bypass attempts directly against APIs

**Verification work (03 planned families).** AV-SCEN-04, BENCH-RQ3-001, TEST-SEC-AUTHZ-NEG

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0: unauthorized protected-action attempts must be rejected 100%).


#### WP-SEC-004 — AI-reachable capability surface restriction

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prove the AI runtime has no shell execution and no arbitrary SQL surface.

**Source requirements (03).** FR-SEC-004, FR-SEC-005

**Architecture components (02).** ARCH-AI-TOOLS, ARCH-SEC-AUTHZ

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- capability inventory for the AI service
- static/dynamic checks
- negative tests

**Major tasks.**
- inventory tools and libraries reachable by the AI identity
- implement checks that fail on shell/SQL capability introduction
- document accepted exceptions (none expected)

**Verification work (03 planned families).** TEST-AUTH-NEG, TEST-SEC-AISURFACE

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0; Item 68 X-289 forbids arbitrary shell-executing agents).


#### WP-SEC-005 — Secret sourcing and hygiene

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep live secrets out of Git and images, injected at runtime only.

**Source requirements (03).** FR-SEC-006, NFR-SEC-001

**Architecture components (02).** ARCH-SEC-SECRET, ARCH-SEC-SUPPLYCHAIN

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- runtime secret injection mechanism
- secret scanning of history, images and manifests
- rotation procedure

**Major tasks.**
- select non-Git secret sourcing for the Integration host
- implement injection in Compose/CD
- scan repository history and images
- document rotation and incident handling

**Verification work (03 planned families).** INSP-DEP-HOST, TEST-SEC-SECRETS

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0: zero known live secrets in the final release).


#### WP-SEC-006 — Test-auth prohibition in formal environments

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Ensure bounded development auth shortcuts cannot be enabled in formal runs and that evidence shows zero uses.

**Source requirements (03).** FR-SEC-008, NFR-SEC-006

**Architecture components (02).** ARCH-PLAT-RELEASE, ARCH-SEC-IDP

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- environment-mode enforcement
- startup refusal in formal profiles
- usage counter in run evidence

**Major tasks.**
- define where test-auth is permitted (DEV/CI only)
- implement refusal on formal profiles
- record zero-usage assertion in run evidence

**Verification work (03 planned families).** DEMO-GS01-001, E2E-01, TEST-SEC-TESTAUTH-NEG

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0).


#### WP-SEC-007 — Oracle access denial at runtime

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M4 / S7–S8 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prove at runtime that normal service identities cannot read evaluator-only data.

**Source requirements (03).** FR-SEC-010

**Architecture components (02).** ARCH-SEC-AUTHZ, ARCH-SIM-ORACLE, ARCH-WORLD-EVALZONE

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- credential/network separation for the evaluation zone
- runtime denial tests (AV-SCEN-11)
- evidence of denial in formal runs

**Major tasks.**
- implement separation mechanism (identity and/or network)
- test denial from each operational service identity
- record results as part of benchmark evidence

**Verification work (03 planned families).** AV-SCEN-11, BENCH-RQ3-001, TEST-SEC-ORACLE-NEG

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R04, SIM-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0 research-validity gate).


#### WP-SEC-008 — Security negative suite and external egress audit

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-SEC-BASE |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Consolidate adversarial security testing and verify nothing sensitive leaves the system.

**Source requirements (03).** NFR-SEC-004, NFR-SEC-009, NFR-SEC-010

**Architecture components (02).** ARCH-AI-PROVIDER, ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-HITL-APPROVAL, ARCH-HITL-POLICY, ARCH-OBS-AUDIT, ARCH-SEC-AUTHZ, ARCH-WORLD-EVALZONE

**Inputs / required contracts.** gated by DEP-016 (DN-RT-IDP → DN-SEC-BASE, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8)), DEP-017 (DN-PLAT-CD → DN-SEC-BASE, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- negative suite covering authority, identity, injection and replay
- external LLM payload audit
- audit coverage verification

**Major tasks.**
- assemble suite from HITL/AI/RAG/Core negative cases
- implement egress payload inspection for secrets/oracle/rights-prohibited data
- run before each formal campaign

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, AV-SCEN-11, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-SEC-AUDIT, TEST-SEC-AUTHZ-NEG, TEST-SEC-EGRESS

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R10

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0 family; feeds RQ-3 adversarial share).


### 6.21 Backup & Disaster Recovery (`WP-DR-*`, 4 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-DR-001 | Backup automation and integrity verification | Yavuz | F1 / H0 | M5 | M |
| WP-DR-002 | Restore drills: database and full host | Yavuz | F1 / H0 | M6 | M |
| WP-DR-003 | Derived-state rebuild paths | Yavuz | F1 | M5 | S |
| WP-DR-004 | Evidence protection and off-host preservation | Yavuz | F1 / H0 | M7 | S |

#### WP-DR-001 — Backup automation and integrity verification

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-BACKUP |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Produce verifiable backups of canonical state and critical artifacts on a defined schedule.

**Source requirements (03).** FR-PLAT-008, NFR-REC-001, NFR-REC-006, NFR-REC-010

**Architecture components (02).** ARCH-DATA-OBJ, ARCH-DATA-PG, ARCH-PLAT-BACKUP

**Inputs / required contracts.** gated by DEP-111 (DN-SEC-BASE → DN-PLAT-BACKUP, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10)), DEP-112 (DN-RT-OBS → DN-PLAT-BACKUP, SOFT/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- BackupSet jobs (PostgreSQL, critical objects)
- checksum/integrity verification
- off-host copy path
- drill record format

**Major tasks.**
- define recovery classes (RC-A/RC-B) and schedules
- implement backup jobs and verification
- implement off-host copy with timing measurement
- define mandatory drill record fields

**Verification work (03 planned families).** INSP-REC-BACKUP, RESTORE-HOST-001, RESTORE-PG-001, TEST-DATA-CHECKSUM

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DR-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0 family).


#### WP-DR-002 — Restore drills: database and full host

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-PLAT-BACKUP |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prove recovery by executing real restore drills, not by documenting intent.

**Source requirements (03).** NFR-REC-003, NFR-REC-004, NFR-REC-007

**Architecture components (02).** ARCH-DATA-PG, ARCH-PLAT-BACKUP, ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-111 (DN-SEC-BASE → DN-PLAT-BACKUP, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10)), DEP-112 (DN-RT-OBS → DN-PLAT-BACKUP, SOFT/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- PostgreSQL restore drill (RESTORE-PG-001)
- full-host reconstruction drill (RESTORE-HOST-001)
- drill evidence records

**Major tasks.**
- script restore from accepted backups
- execute application-level smoke validation after restore
- execute host reconstruction from Git + manifests + registry + backups
- record durations against bounds

**Verification work (03 planned families).** RESTORE-HOST-001, RESTORE-PG-001

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DR-R03, DR-R04, PLAT-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut; at least one full-host drill must PASS before M8.


#### WP-DR-003 — Derived-state rebuild paths

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-BACKUP |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Rebuild Twin projections and vector indexes from canonical sources instead of backing them up as truth.

**Source requirements (03).** FR-PLAT-009, NFR-REC-008, NFR-REC-009

**Architecture components (02).** ARCH-AI-RAG, ARCH-DATA-VECTOR, ARCH-PLAT-BACKUP, ARCH-TWIN-REBUILD

**Inputs / required contracts.** gated by DEP-111 (DN-SEC-BASE → DN-PLAT-BACKUP, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10)), DEP-112 (DN-RT-OBS → DN-PLAT-BACKUP, SOFT/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- RecoveryDependencyGraph
- Twin rebuild drill (AV-SCEN-08)
- index rebuild drill

**Major tasks.**
- document which stores are canonical vs derived
- implement rebuild orchestration
- measure rebuild durations at benchmark scale

**Verification work (03 planned families).** AV-SCEN-08, RES-IDXREBUILD-001, RES-TWINREBUILD-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DR-R06, PLAT-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut.


#### WP-DR-004 — Evidence protection and off-host preservation

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-PLAT-BACKUP |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Protect sealed benchmark evidence so a host loss cannot destroy the research result.

**Source requirements (03).** FR-EVAL-008, NFR-REC-002

**Architecture components (02).** ARCH-DATA-OBJ, ARCH-PLAT-BACKUP

**Inputs / required contracts.** gated by DEP-111 (DN-SEC-BASE → DN-PLAT-BACKUP, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10)), DEP-112 (DN-RT-OBS → DN-PLAT-BACKUP, SOFT/MILESTONE_EXIT@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- evidence copy job after EvidenceSeal
- restore test of the evidence bundle
- preservation record for M8

**Major tasks.**
- implement post-seal copy with timing target
- test restore of the bundle
- verify completeness against the run registry

**Verification work (03 planned families).** INSP-REC-BACKUP, RESTORE-EVID-001

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DR-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0).


### 6.22 Testing & Integration Scenarios (`WP-TEST-*`, 8 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-TEST-001 | Test strategy, tiers and boundary-mode policy | Yavuz | F1 | M1 | M |
| WP-TEST-002 | Contract and schema test suites | Asrın | F1 | M2 | S |
| WP-TEST-003 | Integration scenarios AV-SCEN-01…04 | Asrın | F0 | M3 | M |
| WP-TEST-004 | Integration scenarios AV-SCEN-05…08 | Yavuz | F1 | M5 | M |
| WP-TEST-005 | Integration scenarios AV-SCEN-09…12 | Batu | F1 | M5 | M |
| WP-TEST-006 | E2E-01 checkpoint execution | Batu | F0 | M3 | M |
| WP-TEST-007 | Architecture rules and trace validation in CI | Yavuz | F1 | M2 | S |
| WP-TEST-008 | Flake control and release-gate hygiene | Yavuz | F1 / S2 | M6 | S |

#### WP-TEST-001 — Test strategy, tiers and boundary-mode policy

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | `ci/test-strategy.json`; `ci/TEST_STRATEGY.md`; `ci/scripts/check_test_strategy.py`; `evidence/WP-TEST-001/` |

**Purpose.** Define what is tested where (unit, component, contract, integration, scenario, benchmark) and which boundaries must be real.

**Source requirements (03).** NFR-DX-006

**Architecture components (02).** ARCH-PLAT-CICD

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- test tier definition and CI mapping
- boundary-mode policy (REAL / FIXTURE_ALLOWED / STUB_ALLOWED)
- test naming and TestID allocation convention

**Major tasks.**
- define tiers and their runtimes
- document where fixtures are allowed and where they are forbidden
- allocate TestID namespace against 03 verification families
- wire tiers into CI gates

**Verification work (03 planned families).** TEST-DX-FLAKE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; a single final "testing" work package is explicitly rejected.


#### WP-TEST-002 — Contract and schema test suites

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-EVT-CONTRACTS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Verify every cross-service contract from both producer and consumer sides.

**Source requirements (03).** FR-EVT-006, NFR-DATA-005

**Architecture components (02).** ARCH-CTR-CMDSCHEMA, ARCH-CTR-EVTSCHEMA, ARCH-EVT-SCHEMA

**Inputs / required contracts.** gated by DEP-021 (DN-CORE-CONTRACTS → DN-EVT-CONTRACTS, HARD/START@CONTRACT_READY, need-by S1–S2)

**Deliverables.**
- producer/consumer contract suites per IC namespace
- schema validation tests
- compatibility regression tests

**Major tasks.**
- implement consumer-driven contract tests
- validate example fixtures against schemas
- detect breaking changes in CI

**Verification work (03 planned families).** TEST-DATA-CONTRACTVALID, TEST-EVT-SCHEMA

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R03, ARCH-R10

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut.


#### WP-TEST-003 — Integration scenarios AV-SCEN-01…04

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | DN-SIM-COREINT |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute the core closed-loop and authority scenarios on real infrastructure.

**Source requirements (03).** FR-CORE-003, FR-AI-004, FR-HITL-006, FR-AUTO-008

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-HITL-EXPIRY, ARCH-SEC-AUTHZ, ARCH-TWIN-API

**Inputs / required contracts.** gated by DEP-040 (DN-SIM-OPSEM → DN-SIM-COREINT, HARD/INTEGRATION@COMPONENT_READY, need-by M2 (S4)), DEP-041 (DN-CORE-CMDEXEC → DN-SIM-COREINT, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4)), DEP-042 (DN-EVT-SPINE → DN-SIM-COREINT, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- scenario drivers for AV-SCEN-01…04
- expected-outcome definitions held by the evaluator side
- execution reports

**Major tasks.**
- implement inspection-triggered recovery scenario
- implement equipment disruption rescheduling scenario
- implement normal-production no-false-recovery scenario
- implement stale/replayed approval rejection scenario

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, BENCH-E2E-001, BENCH-RQ3-001, RES-WORKER-001, TEST-AUTH-NEG, TEST-CORE-STATEMACHINE, TEST-HITL-REPLAY-NEG, TEST-SEC-SVCID

**Integration checkpoint.** AV-SCEN-01…04

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R07, AUTO-R04, AUTO-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut (F0 integrated evidence).


#### WP-TEST-004 — Integration scenarios AV-SCEN-05…08

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-FAILVAL |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute duplicate delivery, worker crash, broker interruption and Twin rebuild scenarios.

**Source requirements (03).** FR-EVT-005, FR-AUTO-006, FR-TWIN-006, NFR-REL-006

**Architecture components (02).** ARCH-AUTO-IDEMPOTENCY, ARCH-AUTO-WORKFLOW, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-PLAT-COMPOSE, ARCH-TWIN-REBUILD

**Inputs / required contracts.** gated by DEP-110 (DN-RT-OBS → DN-PLAT-FAILVAL, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-113 (DN-PLAT-BACKUP → DN-PLAT-FAILVAL, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10))

**Deliverables.**
- scenario drivers for AV-SCEN-05…08
- fault injection tooling
- execution reports with correctness counters

**Major tasks.**
- implement duplicate/out-of-order delivery injection
- implement worker crash/restart drill
- implement 5-minute broker interruption drill
- implement Twin projection loss and rebuild drill

**Verification work (03 planned families).** AV-SCEN-05, AV-SCEN-06, AV-SCEN-07, AV-SCEN-08, RES-BROKER-001, RES-DUP-001, RES-TWINREBUILD-001, RES-WORKER-001, TEST-AUTO-RESTART-001, TEST-EVT-CONSUMER-IDEMP, TEST-TWIN-PROJECTION

**Integration checkpoint.** AV-SCEN-05…08

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R01, AUTO-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; reliability evidence at M5/M7 depends on these.


#### WP-TEST-005 — Integration scenarios AV-SCEN-09…12

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-SIM-SNAPFORK |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute counterfactual isolation, cross-world rejection, Oracle denial and host reboot scenarios.

**Source requirements (03).** FR-SIM-011, FR-SIM-012, FR-TWIN-007, NFR-REL-005

**Architecture components (02).** ARCH-OBS-HEALTH, ARCH-PLAT-COMPOSE, ARCH-SIM-ORACLE, ARCH-SIM-SNAPSHOT, ARCH-TWIN-STATE, ARCH-WORLD-EVALZONE, ARCH-WORLD-ISOLATION

**Inputs / required contracts.** gated by DEP-044 (DN-SIM-KERNEL → DN-SIM-SNAPFORK, HARD/START@COMPONENT_READY, need-by S3), DEP-045 (DN-RT-OBJ → DN-SIM-SNAPFORK, SOFT/INTEGRATION@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- scenario drivers for AV-SCEN-09…12
- negative assertions per scenario
- execution reports

**Major tasks.**
- implement fork isolation verification
- implement cross-WorldID mutation rejection test
- implement oracle-access negative validation
- implement host reboot and controlled recovery drill

**Verification work (03 planned families).** AV-SCEN-09, AV-SCEN-10, AV-SCEN-11, AV-SCEN-12, BENCH-RQ3-001, RES-REBOOT-001, TEST-SEC-ORACLE-NEG, TEST-SIM-ISOLATION, TEST-TWIN-EPISTEMIC

**Integration checkpoint.** AV-SCEN-09…12

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R09, SEC-R04, SIM-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut.


#### WP-TEST-006 — E2E-01 checkpoint execution

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M3 / S5–S6 |
| Readiness node (05) | CK-E2E01 |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Run the first formal end-to-end checkpoint (dry run mid S5, formal end S5) from an immutable main-derived release.

**Source requirements (03).** FR-VIS-016, FR-AI-001, FR-SCH-005, FR-AUTO-014, FR-HITL-007

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-EDGE-AUTH, ARCH-HITL-APPROVAL, ARCH-SCH-VALIDATOR, ARCH-SEC-IDP, ARCH-SIM-ENGINE, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-178 (DN-VIS-SERVING → CK-E2E01, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-179 (DN-AI-RCA → CK-E2E01, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-180 (DN-SCH-PLANCON → CK-E2E01, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-181 (DN-SCH-VALID → CK-E2E01, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-182 (DN-HITL-APPROVAL → CK-E2E01, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5)), DEP-183 (DN-AUTO-DURABLE → CK-E2E01, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by E2E-01 (end S5))

**Deliverables.**
- E2E-SCENARIO-01 v1 definition
- dry-run report with failure classification
- E2E-RUN-A/B/C formal evidence

**Major tasks.**
- freeze the scenario (two lots, inspection condition, alternative tool)
- execute dry run and classify failures
- execute formal runs from approved main
- include duplicate-input and stale-approval negative gates

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, BENCH-RQ1-001, BENCH-SCH-001, DEMO-GS01-001, E2E-01, TEST-AI-OUTPUT, TEST-SCH-VALIDATOR, TEST-SEC-AUTHN

**Integration checkpoint.** E2E-01

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R01, AUTO-R09, PLAN-R03, PLAN-R04, SCH-R01, SCH-R07, VIS-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 05, 06, 12.

**Cut / fallback semantics.** No cut. A manual patch invalidates the formal run (Item 67 #223); failures are expected engineering feedback in the dry run.


#### WP-TEST-007 — Architecture rules and trace validation in CI

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep architectural and traceability invariants enforced automatically on every change.

**Source requirements (03).** FR-EVT-007, FR-GOV-005

**Architecture components (02).** ARCH-CORE-DB, ARCH-CTR-API, ARCH-PLAT-CICD

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- architecture rule checks
- trace linter integration
- violation reporting

**Major tasks.**
- wire boundary and trace checks as required CI gates
- define exception process
- report violations with requirement context

**Verification work (03 planned families).** TEST-ARCH-BOUNDARY, TEST-GOV-TRACELINT, TEST-SEC-SVCID

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R05, ARCH-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut.


#### WP-TEST-008 — Flake control and release-gate hygiene

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class S2) |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prevent unreliable tests from silently weakening release and benchmark gates.

**Source requirements (03).** NFR-DX-006

**Architecture components (02).** ARCH-PLAT-CICD

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- flaky-test registry
- quarantine policy with expiry
- gate policy prohibiting retry-until-green

**Major tasks.**
- implement registry and reporting
- define quarantine entry/exit rules
- audit gates before M6

**Verification work (03 planned families).** TEST-DX-FLAKE

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** No cut for gate integrity; the timing target itself is S2.


### 6.23 Performance & Resilience Measurement (`WP-PERF-*`, 6 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-PERF-001 | Benchmark definitions, workload profiles and measurement protocol | Yavuz | F1 | M5 | M |
| WP-PERF-002 | Latency and throughput measurement execution | Yavuz | F1 / A1 | M7 | M |
| WP-PERF-003 | Capacity and stress execution | Batu | F1 / A1 | M7 | S |
| WP-PERF-004 | Resilience drill execution | Yavuz | F1 / H0 | M6 | S |
| WP-PERF-005 | Soak testing and resource behaviour under sustained load | Yavuz | F1 / H0 | M7 | S |
| WP-PERF-006 | Scheduler performance frontier measurement | Batu | F1 / A1 | M7 | S |

#### WP-PERF-001 — Benchmark definitions, workload profiles and measurement protocol

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-RUNNER |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Define exactly how every quantitative NFR is measured so numbers are comparable and defensible.

**Source requirements (03).** NFR-GOV-004, NFR-GOV-005, NFR-GOV-006

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-114 (DN-PLAT-FAILVAL → DN-PLAT-RUNNER, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-115 (DN-PLAT-CD → DN-PLAT-RUNNER, HARD/INTEGRATION@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- BenchmarkDefinition set
- WP-SMALL/WP-NORMAL/WP-STRESS and SP-NORMAL/SP-STRESS compositions
- sampling/warm-up protocol
- measurement context binding rules

**Major tasks.**
- define per-metric measurement points and exclusions (simulation time, human wait)
- define workload compositions and load drivers
- define minimum observation counts and percentile reporting
- bind each definition to Release/Env/HW/Workload identities

**Verification work (03 planned families).** INSP-GOV-NFR, TEST-DATA-REFINTEGRITY

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; without this, NFR results are unusable (03 GAP-RTM-004).


#### WP-PERF-002 — Latency and throughput measurement execution

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-PLAT-RUNNER |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute the performance lane for Core, Twin, UI, AI, workflow and approval paths.

**Source requirements (03).** NFR-PERF-001, NFR-PERF-002, NFR-PERF-003, NFR-PERF-004, NFR-PERF-005, NFR-PERF-006, NFR-PERF-011, NFR-PERF-012, NFR-PERF-013, NFR-PERF-014

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-RAG, ARCH-AUTO-VERIFY, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-CORE-OUTBOX, ARCH-DATA-VECTOR, ARCH-EDGE-BFF, ARCH-EDGE-NOTIFY, ARCH-EDGE-WEB, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-HITL-APPROVAL, ARCH-SCH-ENGINE, ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-PROJECTOR, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-114 (DN-PLAT-FAILVAL → DN-PLAT-RUNNER, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-115 (DN-PLAT-CD → DN-PLAT-RUNNER, HARD/INTEGRATION@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- performance lane execution scripts
- recorded distributions per metric
- disposition table (PASS/FAIL/MISS) per NFR

**Major tasks.**
- run each benchmark definition on the evaluation host
- record raw samples and derived percentiles
- attach measurement context to every result
- report failures without post-hoc threshold changes

**Verification work (03 planned families).** BENCH-E2E-001, BENCH-PERF-AI, BENCH-PERF-CORE, BENCH-PERF-UI, BENCH-PERF-WF

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DEMO-R01, PERF-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1/S2 mix: A1 thresholds must PASS or be formally rebaselined; S2 misses are recorded with analysis.


#### WP-PERF-003 — Capacity and stress execution

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-SIM-OPSEM |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Establish the capacity envelope (world size, event rate, workflow concurrency, sessions, worlds).

**Source requirements (03).** NFR-CAP-001, NFR-CAP-002, NFR-CAP-004, NFR-CAP-005, NFR-CAP-008, NFR-CAP-009, NFR-CAP-010

**Architecture components (02).** ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-SEC-IDP, ARCH-SIM-ENGINE, ARCH-TWIN-PROJECTOR, ARCH-WORLD-ISOLATION, ARCH-WORLD-REGISTRY

**Inputs / required contracts.** gated by DEP-037 (DN-SIM-KERNEL → DN-SIM-OPSEM, HARD/START@COMPONENT_READY, need-by S2), DEP-038 (DN-CORE-CONTRACTS → DN-SIM-OPSEM, HARD/START@CONTRACT_READY, need-by S2), DEP-039 (DN-CORE-TRANSITIONS → DN-SIM-OPSEM, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M2 (S4))

**Deliverables.**
- capacity lane scripts
- stress frontier results
- correctness counters at stress

**Major tasks.**
- execute WP-NORMAL and WP-STRESS runs
- execute event pipeline and workflow concurrency load
- verify zero corruption/leakage/invalid transitions at stress

**Verification work (03 planned families).** AV-SCEN-10, BENCH-CAP-ENV, BENCH-CAP-EVT, BENCH-CAP-WORLD, BENCH-PERF-CORE, BENCH-PERF-WF, BENCH-RES-FOOTPRINT, RES-DUP-001, RES-SOAK-001

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R09

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1 for capacity numbers; correctness counters are hard-zero.


#### WP-PERF-004 — Resilience drill execution

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-PLAT-FAILVAL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute the fault-injection drills that produce reliability evidence.

**Source requirements (03).** NFR-REL-003, NFR-REL-004, NFR-REL-005, NFR-REL-006, NFR-REL-008, NFR-REL-009

**Architecture components (02).** ARCH-AUTO-WORKFLOW, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-OBS-HEALTH, ARCH-OBS-TELEMETRY, ARCH-PLAT-COMPOSE

**Inputs / required contracts.** gated by DEP-110 (DN-RT-OBS → DN-PLAT-FAILVAL, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-113 (DN-PLAT-BACKUP → DN-PLAT-FAILVAL, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10))

**Deliverables.**
- drill scripts (process crash, worker crash, broker interruption, reboot, dependency loss)
- recovery timing measurement
- drill evidence records

**Major tasks.**
- implement injection and recovery measurement
- execute each drill on INTEGRATION
- record recovery times and any committed-effect loss (must be zero)

**Verification work (03 planned families).** AV-SCEN-06, AV-SCEN-07, AV-SCEN-12, BENCH-CAP-EVT, RES-BROKER-001, RES-DEPFAIL-001, RES-PROCESS-001, RES-REBOOT-001, RES-SOAK-001, RES-WORKER-001

**Integration checkpoint.** AV-SCEN-06, AV-SCEN-07, AV-SCEN-12

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PERF-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut; reliability claims require executed drills, not design arguments.


#### WP-PERF-005 — Soak testing and resource behaviour under sustained load

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 (NFR class H0) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-PLAT-FAILVAL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Run the 8-hour soak that exposes leaks, queue growth, crash loops and duplication over time.

**Source requirements (03).** NFR-REL-007, NFR-REL-001

**Architecture components (02).** ARCH-AUTO-IDEMPOTENCY, ARCH-CORE-CMD, ARCH-EVT-CONSUMER, ARCH-OBS-HEALTH, ARCH-PLAT-COMPOSE

**Inputs / required contracts.** gated by DEP-110 (DN-RT-OBS → DN-PLAT-FAILVAL, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-113 (DN-PLAT-BACKUP → DN-PLAT-FAILVAL, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10))

**Deliverables.**
- soak harness and monitoring
- soak report with counters
- memory/queue trend analysis

**Major tasks.**
- configure WP-NORMAL sustained load
- monitor crash loops, corruption, duplicate effects, OOM, queue growth
- record and analyse trends

**Verification work (03 planned families).** AV-SCEN-05, AV-SCEN-06, RES-DUP-001, RES-SOAK-001, TEST-AUTO-RESTART-001

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 09, 11.

**Cut / fallback semantics.** No cut (H0).


#### WP-PERF-006 — Scheduler performance frontier measurement

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 (NFR class A1) |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-SCH-DYN |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Measure decision latency, feasibility and fallback behaviour at SP-NORMAL and characterize SP-STRESS.

**Source requirements (03).** NFR-PERF-008, NFR-CAP-006, NFR-CAP-007

**Architecture components (02).** ARCH-SCH-ENGINE, ARCH-SCH-HEURISTIC, ARCH-SCH-VALIDATOR

**Inputs / required contracts.** gated by DEP-078 (DN-SCH-HEUR → DN-SCH-DYN, HARD/START@COMPONENT_READY, need-by S3), DEP-079 (DN-CORE-SNAPCON → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ → DN-SCH-DYN, HARD/INTEGRATION@INTEGRATION_READY, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT → DN-SCH-DYN, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M4 (S8)), DEP-088 (DN-SIM-DISPIF → DN-SCH-DYN, HARD/INTEGRATION@CONTRACT_READY, need-by M2 (S4))

**Deliverables.**
- scheduler benchmark scripts
- SP-NORMAL results vs 30 s budget
- SP-STRESS characterization

**Major tasks.**
- generate instance sets at both profiles
- measure solve time, feasibility rate, quality and fallback rate
- record frontier behaviour

**Verification work (03 planned families).** BENCH-PERF-SCH, TEST-SCH-FALLBACK

**Expected evidence artifact.** measurement record bound to Release/Environment/HardwareProfile/WorkloadProfile — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** PERF-R04, SCH-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 08, 11.

**Cut / fallback semantics.** A1 at SP-NORMAL; SP-STRESS is C3 characterization.


### 6.24 Research & Evaluation Infrastructure (`WP-RES-*`, 12 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-RES-001 | Experiment runner and run manifest binding | Yavuz | R1 | M5 | M |
| WP-RES-002 | Partition, seed and protocol governance | Asrın | R1 | M5 | M |
| WP-RES-003 | Benchmark run registry and disposition accounting | Yavuz | R1 | M6 | S |
| WP-RES-004 | AnalysisPackage and deterministic result regeneration | Asrın | R1 | M6 | S |
| WP-RES-005 | Evidence sealing and bundle assembly | Yavuz | R1 | M7 | S |
| WP-RES-006 | Baseline suite across lanes | Asrın | R1 | M5 | M |
| WP-RES-007 | RQ-1 lane: evidence-grounded RCA evaluation | Asrın | R1 | M6 | M |
| WP-RES-008 | RQ-2 lane: dynamic recovery evaluation | Batu | R1 | M6 | M |
| WP-RES-009 | RQ-3 lane: governed AI-to-action evaluation | Asrın | R1 | M6 | M |
| WP-RES-010 | RQ-4 lane: perception-to-operations evaluation | Selman | R1 | M6 | M |
| WP-RES-011 | Freeze execution for M6 | Asrın | R1 | M6 | S |
| WP-RES-012 | Research claim classification | Asrın | R1 | M8 | S |

#### WP-RES-001 — Experiment runner and run manifest binding

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-PLAT-RUNNER |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Build the runner that binds every experimental run to release, environment, hardware, data, scenario and seed identities.

**Source requirements (03).** FR-EVAL-001, FR-PLAT-010

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-114 (DN-PLAT-FAILVAL → DN-PLAT-RUNNER, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-115 (DN-PLAT-CD → DN-PLAT-RUNNER, HARD/INTEGRATION@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- experiment runner CLI/service
- ExperimentDefinition format
- run manifest emission

**Major tasks.**
- define experiment definition schema
- implement execution with identity capture
- implement non-owner reproducible invocation
- dry-run all lanes before M6

**Verification work (03 planned families).** BENCH-FBC-001, DEMO-GS01-001, INSP-GOV-ACCEPT, REPRO-NONOWNER-001, TEST-EVAL-RUNNER

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** RES-R08, RES-R15

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1). Architecture anchor pending (03 GAP-RTM-002).


#### WP-RES-002 — Partition, seed and protocol governance

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | R1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-RES-DATASCEN |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep DEVELOPMENT / CALIBRATION / FINAL_TEST partitions and seed namespaces separated and auditable.

**Source requirements (03).** FR-EVAL-002, NFR-DATA-002

**Architecture components (02).** ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-121 (DN-SIM-SYNTH → DN-RES-DATASCEN, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-122 (DN-VIS-SPLIT → DN-RES-DATASCEN, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-123 (DN-RAG-CORPUS → DN-RES-DATASCEN, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10))

**Deliverables.**
- partition and seed namespace definitions
- FINAL access guard in the runner
- partition audit report

**Major tasks.**
- define partitions per research lane
- implement seed namespace allocation
- implement guard preventing FINAL use before the protocol freeze
- audit for entity/group overlap

**Verification work (03 planned families).** BENCH-FBC-001, INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DATA-R04, DATA-R05, RES-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (hard gate).


#### WP-RES-003 — Benchmark run registry and disposition accounting

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-PLAT-RUNNER |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Record every attempted run — including failed and invalid ones — with a documented disposition.

**Source requirements (03).** FR-EVAL-003, FR-EVAL-004, FR-EVAL-005, NFR-DATA-003, NFR-DATA-007

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-PG

**Inputs / required contracts.** gated by DEP-114 (DN-PLAT-FAILVAL → DN-PLAT-RUNNER, HARD/MILESTONE_EXIT@EVALUATION_READY, need-by M5 (S10)), DEP-115 (DN-PLAT-CD → DN-PLAT-RUNNER, HARD/INTEGRATION@INTEGRATION_READY, need-by M5 (S10))

**Deliverables.**
- BenchmarkRunRecord store
- RunDispositionRegister
- planned-vs-executed reconciliation report

**Major tasks.**
- define record fields and append-only semantics
- implement RetryOf/disposition provenance
- implement reconciliation against planned experimental units

**Verification work (03 planned families).** BENCH-FBC-001, TEST-DATA-ACCOUNTING, TEST-DATA-REFINTEGRITY, TEST-EVAL-RUNRECORD

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** RES-R05, RES-R14

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut; silent disappearance of runs is a hard-gate failure.


#### WP-RES-004 — AnalysisPackage and deterministic result regeneration

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-RES-ANALYSIS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make every published number regenerable from frozen raw evidence by a versioned analysis package.

**Source requirements (03).** FR-EVAL-006, NFR-REP-002

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-OBJ

**Inputs / required contracts.** gated by DEP-143 (DN-RES-BENCH → DN-RES-ANALYSIS, HARD/FREEZE@FROZEN, need-by M7 (S12)), DEP-144 (DN-FRZ-PROTOCOL → DN-RES-ANALYSIS, HARD/FREEZE@FROZEN, need-by M7 (S12))

**Deliverables.**
- AnalysisPackage (metric calculators, statistical tests, table/figure generators)
- deterministic serialization/rounding rules
- regeneration test

**Major tasks.**
- implement metric calculators per lane
- implement statistical procedures agreed in the protocol
- verify identical regeneration from the same raw inputs

**Verification work (03 planned families).** BENCH-FBC-001, INSP-EVAL-CLAIMS, TEST-EVAL-ANALYSIS, TEST-REP-ANALYSIS

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** RES-R13

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1).


#### WP-RES-005 — Evidence sealing and bundle assembly

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-RES-BENCH |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Seal final evidence into an immutable, complete, reference-resolvable bundle.

**Source requirements (03).** FR-EVAL-007, NFR-DATA-004

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-OBJ

**Inputs / required contracts.** gated by DEP-120 (DN-PLAT-CLEANREPRO → DN-RES-BENCH, HARD/FREEZE@EVALUATION_READY, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12))

**Deliverables.**
- EvidenceSeal mechanism
- FinalBenchmarkEvidenceBundle assembly
- completeness and reference-integrity checks

**Major tasks.**
- define bundle contents per lane
- implement sealing with content identity
- verify zero unresolved references before sealing

**Verification work (03 planned families).** BENCH-FBC-001, INSP-EVAL-SEAL, TEST-DATA-REFINTEGRITY

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1).


#### WP-RES-006 — Baseline suite across lanes

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | R1 |
| Target milestone / sprint window | M5 / S9–S10 |
| Readiness node (05) | DN-RES-BASELINES |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Implement and record the baselines every proposed approach is compared against.

**Source requirements (03).** FR-SCH-010, FR-AI-001, FR-VIS-002

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-SCH-HEURISTIC, ARCH-VIS-EVAL, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-124 (DN-RES-DATASCEN → DN-RES-BASELINES, HARD/START@EVALUATION_READY, need-by M5 (S10))

**Deliverables.**
- RCA baselines (RCA-B1…B5)
- scheduler baselines
- Vision and ML baselines
- BaselineRun records

**Major tasks.**
- implement each baseline as a runnable configuration
- execute on DEV/CAL partitions
- record results before calibration (Item 66 #83)

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, BENCH-RQ1-001, BENCH-RQ2-001, BENCH-SCH-001, BENCH-VIS-001, E2E-01, TEST-AI-OUTPUT, TEST-VIS-PIPELINE

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SCH-R06

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1); literature numbers are context, never a substitute for a local BaselineRun.


#### WP-RES-007 — RQ-1 lane: evidence-grounded RCA evaluation

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-FRZ-RQ1CORPUS |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prepare and execute the RQ-1 evaluation (120 FINAL_TEST cases; RCA-B1…PROPOSED; robustness study).

**Source requirements (03).** FR-AI-005, FR-AI-008, FR-RAG-010

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-RAG

**Inputs / required contracts.** gated by DEP-146 (DN-RAG → DN-FRZ-RQ1CORPUS, HARD/FREEZE@EVALUATION_READY, need-by M5→M6)

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

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-03, BENCH-RQ1-001, TEST-AI-OUTPUT, TEST-RAG-PROVENANCE

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R01, AI-R02

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1: NOT_SUPPORTED and INCONCLUSIVE are valid outcomes.


#### WP-RES-008 — RQ-2 lane: dynamic recovery evaluation

| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-SIM-REALISM |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prepare and execute the RQ-2 evaluation (component 8×30, full recovery 4×20, realized execution outcome).

**Source requirements (03).** FR-SCH-003, FR-SCH-013, FR-AUTO-008

**Architecture components (02).** ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-SCH-ENGINE, ARCH-SIM-SNAPSHOT, ARCH-TWIN-API, ARCH-WORLD-FORK

**Inputs / required contracts.** gated by DEP-049 (DN-SIM-OPSEM → DN-SIM-REALISM, HARD/FREEZE@EVALUATION_READY, need-by M5→M6)

**Deliverables.**
- RQ-2 experiment definitions
- paired-seed harness with common random numbers
- realized-outcome measurement

**Major tasks.**
- define scenario families and disruption profiles
- implement paired comparison execution
- ensure realism evidence precedes final claims
- execute in FBC-01

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-02, AV-SCEN-09, BENCH-E2E-001, BENCH-RQ2-001, RES-WORKER-001, TEST-SCH-COUNTERFACTUAL, TEST-SCH-REPLAN

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R06, SCH-R05, SIM-R08

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1; simulation realism (WP-SIM-009) is a HARD evidence precondition.


#### WP-RES-009 — RQ-3 lane: governed AI-to-action evaluation

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-FRZ-RQ3AUTH |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prepare and execute the RQ-3 evaluation (150 cases, L0–L4 × 30, ≥40% adversarial).

**Source requirements (03).** FR-HITL-001, FR-AI-004, FR-AUTO-004

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-HITL-EXPIRY, ARCH-HITL-POLICY, ARCH-SEC-AUTHZ

**Inputs / required contracts.** gated by DEP-147 (DN-HITL-POLICY → DN-FRZ-RQ3AUTH, HARD/FREEZE@EVALUATION_READY, need-by M5→M6)

**Deliverables.**
- authority scenario set
- adversarial case generator
- policy-arm execution harness

**Major tasks.**
- define adversarial classes (stale, revision mismatch, duplicate, replay, malformed, forbidden, lost ACK, expired approval)
- hold the same proposal set across policy arms
- freeze the set before M6
- execute in FBC-01

**Verification work (03 planned families).** AV-SCEN-01, AV-SCEN-04, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-AUTO-FRESHNESS, TEST-HITL-POLICY, TEST-SEC-SVCID

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R07, AUTO-R05

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1 with a hard safety gate: zero executed high-risk invariant violations.


#### WP-RES-010 — RQ-4 lane: perception-to-operations evaluation

| Field | Value |
|---|---|
| PrimaryOwner | Selman |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-VIS-EPISODES |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prepare and execute the RQ-4 evaluation (120 episodes, 5 seeds, bootstrap resampling).

**Source requirements (03).** FR-VIS-010, FR-VIS-016, FR-VIS-006

**Architecture components (02).** ARCH-AI-ORCH, ARCH-VIS-EVAL, ARCH-VIS-INFER, ARCH-VIS-OOD

**Inputs / required contracts.** gated by DEP-062 (DN-SIM-COREINT → DN-VIS-EPISODES, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M5), DEP-063 (DN-CORE-GENEALOGY → DN-VIS-EPISODES, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M5)

**Deliverables.**
- operational episode dataset
- downstream impact metrics
- multi-seed execution protocol

**Major tasks.**
- generate episodes with genealogy and operational context
- define perception→operations impact metrics
- freeze splits before M6
- execute in FBC-01

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, BENCH-RQ4-001, BENCH-VIS-001, DEMO-GS01-001, E2E-01, TEST-VIS-OOD, TEST-VIS-PIPELINE

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R01, PLAN-R03, VIS-R01, VIS-R04

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1.


#### WP-RES-011 — Freeze execution for M6

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | R1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-FRZ-PROTOCOL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute the coordinated freeze of data, models, policies, metrics, analysis plan and environment.

**Source requirements (03).** FR-EVAL-002, FR-RAG-009, FR-AI-011

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-PROVIDER, ARCH-AI-RAG, ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-135 (DN-FRZ-DATA → DN-FRZ-PROTOCOL, HARD/FREEZE@FROZEN, need-by M6 (S11)), DEP-136 (DN-FRZ-MODEL → DN-FRZ-PROTOCOL, HARD/FREEZE@FROZEN, need-by M6 (S11)), DEP-137 (DN-FRZ-RQ3AUTH → DN-FRZ-PROTOCOL, HARD/FREEZE@FROZEN, need-by M6 (S11)), DEP-138 (DN-SIM-REALISM → DN-FRZ-PROTOCOL, HARD/FREEZE@EVALUATION_READY, need-by M6 (S11)), DEP-151 (DN-VIS-EPISODES → DN-FRZ-PROTOCOL, HARD/FREEZE@EVALUATION_READY, need-by M6), DEP-154 (DN-SCH-CF → DN-FRZ-PROTOCOL, HARD/FREEZE@EVALUATION_READY, need-by M6)

**Deliverables.**
- freeze records per artifact class
- ExperimentProtocolFreeze document
- freeze verification checklist

**Major tasks.**
- collect and verify every freeze prerequisite (05 §9)
- record immutable identities
- verify no critical research dependency remains TBD

**Verification work (03 planned families).** BENCH-FBC-001, BENCH-RAG-001, BENCH-RQ1-001, INSP-AI-BEHAVIOR, INSP-EVAL-PARTITION, INSP-REP-LLM, TEST-DATA-SPLITLEAK

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R08, RES-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut; M6 cannot pass with an open behavioural dependency.


#### WP-RES-012 — Research claim classification

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | R1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-RES-CLAIMS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Derive RQ outcomes and exported metrics strictly from sealed evidence.

**Source requirements (03).** FR-EVAL-009, FR-EVAL-010

**Architecture components (02).** ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-145 (DN-RES-ANALYSIS → DN-RES-CLAIMS, HARD/MILESTONE_EXIT@FROZEN, need-by M7→M8)

**Deliverables.**
- claim classification procedure (SUPPORTED / PARTIAL / NOT_SUPPORTED / INCONCLUSIVE)
- ThesisClaimRegister entries
- PortfolioMetricExport

**Major tasks.**
- implement derivation from AnalysisPackage outputs
- record claim → evidence references
- produce exports for thesis/portfolio

**Verification work (03 planned families).** BENCH-FBC-001, INSP-EVAL-CLAIMS, TEST-EVAL-ANALYSIS

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DOC-R05, RES-R12

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1); claim wording is bounded by the achieved evidence tier.


### 6.25 Final Benchmark Campaign (`WP-BENCH-*`, 5 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-BENCH-001 | Campaign manifest, preflight and lane orchestration | Yavuz | R1 | M7 | S |
| WP-BENCH-002 | Final E2E matrix execution (MC-1) | Asrın | R1 | M7 | S |
| WP-BENCH-003 | Engineering lanes execution (ENG-A…I) | Yavuz | R1 | M7 | S |
| WP-BENCH-004 | Reproduction lanes: clean host, non-owner and public | Yavuz | R1 | M8 | M |
| WP-BENCH-005 | Evidence bundle finalization and acceptance reporting | Yavuz | R1 | M8 | S |

#### WP-BENCH-001 — Campaign manifest, preflight and lane orchestration

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-RES-BENCH |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Run FBC-01 as one governed campaign rather than scattered ad hoc runs.

**Source requirements (03).** FR-EVAL-001, FR-EVAL-003

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-PG, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-120 (DN-PLAT-CLEANREPRO → DN-RES-BENCH, HARD/FREEZE@EVALUATION_READY, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12))

**Deliverables.**
- BenchmarkCampaignManifest
- lane orchestration scripts (ENG-A…I, RQ lanes)
- preflight gate integration

**Major tasks.**
- define campaign structure and lane order
- implement orchestration with run registry integration
- enforce preflight before each lane

**Verification work (03 planned families).** BENCH-FBC-001, REPRO-NONOWNER-001, TEST-EVAL-RUNNER, TEST-EVAL-RUNRECORD

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** RES-R08, RES-R15

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1).


#### WP-BENCH-002 — Final E2E matrix execution (MC-1)

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | R1 |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-RES-BENCH |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute the 4 frozen scenario families × 20 seeds end-to-end matrix.

**Source requirements (03).** FR-VIS-016, FR-AUTO-014, NFR-PERF-013, NFR-OBS-003

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-OBS-TELEMETRY, ARCH-OBS-TRACE, ARCH-SCH-ENGINE, ARCH-SIM-ENGINE, ARCH-TWIN-API, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-120 (DN-PLAT-CLEANREPRO → DN-RES-BENCH, HARD/FREEZE@EVALUATION_READY, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12))

**Deliverables.**
- E2E matrix execution scripts
- per-run evidence capture
- closed-loop outcome metrics

**Major tasks.**
- freeze scenario definitions
- execute 80 base instances with identity binding
- capture traces and verification outcomes

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, BENCH-PERF-WF, DEMO-GS01-001, E2E-01, TEST-OBS-TRACEPROP

**Integration checkpoint.** BENCH-E2E-001

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** ARCH-R01, DEMO-R01, PLAN-R03, PLAN-R04, VIS-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1).


#### WP-BENCH-003 — Engineering lanes execution (ENG-A…I)

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M7 / S12 |
| Readiness node (05) | DN-RES-BENCH |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Execute the engineering evidence lanes: correctness, integration, authority/security, resilience, performance, recovery, reproducibility, demo and public reproduction.

**Source requirements (03).** NFR-REL-001, NFR-SEC-004, NFR-REC-007, NFR-REP-004

**Architecture components (02).** ARCH-AUTO-IDEMPOTENCY, ARCH-CORE-CMD, ARCH-EVT-CONSUMER, ARCH-HITL-POLICY, ARCH-PLAT-BACKUP, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE, ARCH-SEC-AUTHZ

**Inputs / required contracts.** gated by DEP-120 (DN-PLAT-CLEANREPRO → DN-RES-BENCH, HARD/FREEZE@EVALUATION_READY, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12))

**Deliverables.**
- lane execution scripts
- evidence capture per lane
- lane completion report

**Major tasks.**
- map each lane to its verification assets
- execute in campaign order
- record dispositions including MISS/FAIL

**Verification work (03 planned families).** AV-SCEN-04, AV-SCEN-05, AV-SCEN-06, BENCH-RQ3-001, REPRO-NONOWNER-001, RES-DUP-001, RESTORE-HOST-001, TEST-AUTH-NEG, TEST-AUTO-RESTART-001, TEST-SEC-AUTHZ-NEG

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AUTO-R01, DR-R03, PLAT-R06, TEAM-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1).


#### WP-BENCH-004 — Reproduction lanes: clean host, non-owner and public

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-PLAT-CLEANREPRO |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Prove that others can rerun the system and selected experiments from published artifacts.

**Source requirements (03).** NFR-REP-003, NFR-REP-004, NFR-REP-008, NFR-DEP-005

**Architecture components (02).** ARCH-PLAT-CLI, ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-118 (DN-ART-RELEASE → DN-PLAT-CLEANREPRO, HARD/MILESTONE_EXIT@FROZEN, need-by M6→M7), DEP-119 (DN-ART-HWPROF → DN-PLAT-CLEANREPRO, HARD/MILESTONE_EXIT@FROZEN, need-by M6→M7)

**Deliverables.**
- clean-host deployment run
- non-owner reproduction run
- public/sanitized package reproduction (OSR-3)

**Major tasks.**
- execute clean-host deploy from the exact ReleaseManifest
- have a non-owner reproduce a selected final scenario
- execute the public package hero reproduction
- record hidden-dependency findings if any

**Verification work (03 planned families).** INSP-DEP-HOST, REPRO-CLEANHOST-001, REPRO-NONOWNER-001, REPRO-OSR3-001

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DEMO-R03, PLAT-R10, TEAM-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1/H0 mix: NFR-REP-003 is H0-grade reproducibility evidence).


#### WP-BENCH-005 — Evidence bundle finalization and acceptance reporting

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-RES-BENCH |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Close the campaign with sealed evidence, generated coverage and a release acceptance record.

**Source requirements (03).** FR-GOV-006, FR-EVAL-007, NFR-DATA-003, NFR-DATA-004

**Architecture components (02).** ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-PLAT-CICD

**Inputs / required contracts.** gated by DEP-120 (DN-PLAT-CLEANREPRO → DN-RES-BENCH, HARD/FREEZE@EVALUATION_READY, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF → DN-RES-BENCH, HARD/FREEZE@FROZEN, need-by M7 (S12))

**Deliverables.**
- sealed FinalBenchmarkEvidenceBundle
- AcceptanceCoverageReport
- ReleaseAcceptanceRecord

**Major tasks.**
- assemble and seal bundles per lane
- generate coverage and acceptance artifacts from the trace registry
- verify off-host preservation

**Verification work (03 planned families).** BENCH-FBC-001, INSP-EVAL-SEAL, INSP-GOV-ACCEPT, TEST-DATA-REFINTEGRITY, TEST-GOV-TRACELINT

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut.


### 6.26 Documentation, Thesis, Demo & Public Release (`WP-DOC-*`, 6 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-DOC-001 | Engineering documentation set | Yavuz | F1 | M6 | S |
| WP-DOC-002 | ADR backfill and decision index | Asrın | F1 | M2 | S |
| WP-DOC-003 | Thesis and portfolio artifact production | Asrın | R1 | M8 | S |
| WP-DOC-004 | Demo infrastructure and GS-01 rehearsal | Asrın | F1 | M8 | M |
| WP-DOC-005 | Public release package (v1) | Yavuz | R1 | M8 | S |
| WP-DOC-006 | Final red-team review execution | Asrın | F1 | M8 | S |

#### WP-DOC-001 — Engineering documentation set

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F1 |
| Target milestone / sprint window | M6 / S11 |
| Readiness node (05) | DN-PLAT-TOOLING |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Maintain the documentation that lets someone operate, debug and extend the system — written continuously, not at the end.

**Source requirements (03).** NFR-DX-007

**Architecture components (02).** ARCH-PLAT-CLI, ARCH-PLAT-RELEASE

**Inputs / required contracts.** gated by DEP-001 (DN-PLAT-REPO → DN-PLAT-TOOLING, HARD/START@INTEGRATION_READY, need-by M0 (S1))

**Deliverables.**
- architecture overview and service docs
- runbooks (deploy, restore, replay, incident)
- quickstart and reproduction guides

**Major tasks.**
- write docs alongside each capability WP
- validate documented commands against the release
- keep ownership per document

**Verification work (03 planned families).** TEST-DX-DOCS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; a single final documentation task is explicitly rejected.


#### WP-DOC-002 — ADR backfill and decision index

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M2 / S3–S4 |
| Readiness node (05) | DN-PLAT-REPO |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | `docs/adr/`; `ci/tests/test_adr_scaffold.py`; `evidence/WP-DOC-002/` |

**Purpose.** Mint the backfill ADRs for decisions already made and keep new decisions recorded as they happen.

**Source requirements (03).** FR-GOV-004

**Architecture components (02).** ARCH-PLAT-CICD

**Inputs / required contracts.** no inbound dependency edges in 05 — this package is an early unlocker

**Deliverables.**
- ADR template and index
- 13 backfill ADRs from 02
- ADR linkage in the trace registry

**Major tasks.**
- mint ADR IDs and write records
- link ADRs to requirements and architecture components
- define when a new ADR is required

**Verification work (03 planned families).** TEST-GOV-TRACELINT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; DECIDED_BY edges in 03 point at minted ADR IDs (GAP-RTM-023 RESOLVED by CHG-029).


#### WP-DOC-003 — Thesis and portfolio artifact production

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | R1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-RES-CLAIMS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Produce thesis chapters, figures and portfolio metric exports strictly from sealed evidence.

**Source requirements (03).** FR-EVAL-010

**Architecture components (02).** ARCH-DATA-LINEAGE

**Inputs / required contracts.** gated by DEP-145 (DN-RES-ANALYSIS → DN-RES-CLAIMS, HARD/MILESTONE_EXIT@FROZEN, need-by M7→M8)

**Deliverables.**
- thesis figure/table generation from AnalysisPackage
- claim-to-evidence mapping appendix
- portfolio metric export

**Major tasks.**
- generate all numbers from sealed analysis outputs
- write method/limitations sections bounded by achieved evidence tiers
- review claim wording against forbidden-claim list

**Verification work (03 planned families).** BENCH-FBC-001, INSP-EVAL-CLAIMS

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DOC-R05, RES-R12

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** No cut (R1).


#### WP-DOC-004 — Demo infrastructure and GS-01 rehearsal

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | M (≈4–7 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Make the hero demo a reproducible run of the real system from a pinned release.

**Source requirements (03).** FR-UI-009, NFR-UX-006, NFR-PERF-013

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AUTO-WORKFLOW, ARCH-EDGE-PRESENT, ARCH-EDGE-WEB, ARCH-OBS-HEALTH, ARCH-PLAT-RELEASE, ARCH-SCH-ENGINE, ARCH-TWIN-API, ARCH-VIS-INFER

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- DemoManifest and pinned release
- GS-01 rehearsal script and abort conditions
- demo evidence capture (EXP-DEMO)

**Major tasks.**
- define demo environment and world provisioning
- rehearse the full GS-01 path
- define hard abort conditions (wrong release, test-auth enabled, oracle violation, authority bypass, unverified effect)
- capture demo run evidence separately from statistical evidence

**Verification work (03 planned families).** BENCH-E2E-001, BENCH-PERF-WF, DEMO-GS01-001, TEST-UI-DIAG, TEST-UI-SEMANTICS

**Integration checkpoint.** DEMO-GS01-001

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** DEMO-R01, DEMO-R04, DEMO-R07

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; demo evidence never substitutes evaluation evidence.


#### WP-DOC-005 — Public release package (v1)

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | R1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-PLAT-CLEANREPRO |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Publish a sanitized, reproducible package that a third party can clone and run.

**Source requirements (03).** NFR-REP-008, NFR-SEC-001

**Architecture components (02).** ARCH-PLAT-RELEASE, ARCH-SEC-SECRET, ARCH-SEC-SUPPLYCHAIN

**Inputs / required contracts.** gated by DEP-118 (DN-ART-RELEASE → DN-PLAT-CLEANREPRO, HARD/MILESTONE_EXIT@FROZEN, need-by M6→M7), DEP-119 (DN-ART-HWPROF → DN-PLAT-CLEANREPRO, HARD/MILESTONE_EXIT@FROZEN, need-by M6→M7)

**Deliverables.**
- public repository structure and licence review
- sanitized artifacts and documentation
- OSR-3 hero reproduction verification

**Major tasks.**
- review code, data and evidence for rights and secrets
- prepare public quickstart and reproduction instructions
- execute clean-clone reproduction

**Verification work (03 planned families).** REPRO-OSR3-001, TEST-SEC-SECRETS

**Expected evidence artifact.** research evidence within the FBC-01 bundle (lane result, no EvidenceID yet) — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** SEC-R01

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…03, 10, 11.

**Cut / fallback semantics.** R1/stretch-adjacent: scope may be reduced to a sanitized subset; reduction is declared, not silent.


#### WP-DOC-006 — Final red-team review execution

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | F1 |
| Target milestone / sprint window | M8 / S13 |
| Readiness node (05) | DN-RES-CLAIMS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Run the adversarial review of claims, evidence and safety before release.

**Source requirements (03).** FR-GOV-010, NFR-GOV-009

**Architecture components (02).** ARCH-DATA-OBJ, ARCH-PLAT-CICD

**Inputs / required contracts.** gated by DEP-145 (DN-RES-ANALYSIS → DN-RES-CLAIMS, HARD/MILESTONE_EXIT@FROZEN, need-by M7→M8)

**Deliverables.**
- red-team finding register (RTF-*)
- claim-vs-evidence audit
- resolution records for critical findings

**Major tasks.**
- review every major claim against sealed evidence
- probe authority, oracle and reproducibility boundaries
- resolve or explicitly accept each critical finding before M8

**Verification work (03 planned families).** INSP-GOV-ACCEPT, TEST-GOV-TRACELINT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** No cut; M8 requires critical red-team resolutions.


### 6.27 Evidence-Gated Research Candidates (`WP-R2-*`, 3 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-R2-001 | R2 retrieval candidates (ColBERT, cross-encoder reranking, alternative embeddings) | Asrın | R2 | — | S |
| WP-R2-002 | R2 modelling candidates (local LLM runtime, VLM experiment, advanced causal RCA, RL scheduler, alternative solver formulations) | Asrın | R2 | — | S |
| WP-R2-003 | R2 infrastructure candidates (Neo4j, TimescaleDB, Valkey optimization, GPU/distributed simulator) | Yavuz | R2 | — | S |

#### WP-R2-001 — R2 retrieval candidates (ColBERT, cross-encoder reranking, alternative embeddings)

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | R2 |
| Target milestone / sprint window | — / unscheduled |
| Readiness node (05) | DN-RAG |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Investigate retrieval enhancements as evidence-gated candidates that may be promoted only with evidence and a declared strength change.

**Source requirements (03).** FR-RAG-005

**Architecture components (02).** ARCH-AI-RAG, ARCH-DATA-VECTOR

**Inputs / required contracts.** gated by DEP-070 (DN-RAG-CORPUS → DN-RAG, HARD/START@COMPONENT_READY, need-by S3–S4), DEP-071 (DN-RT-QDRANT → DN-RAG, HARD/INTEGRATION@INTEGRATION_READY, need-by M4 (S8))

**Deliverables.**
- candidate implementations behind configuration switches
- ablation results on DEV/CAL partitions
- promotion recommendation or rejection record

**Major tasks.**
- implement candidates without touching mandatory defaults
- evaluate against the frozen baseline configuration
- document cost/benefit and resource impact

**Verification work (03 planned families).** BENCH-RAG-001, BENCH-RQ1-001, TEST-RAG-RETRIEVAL

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** AI-R03

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** First to be cut under schedule pressure. Cannot enter any mandatory path or critical path without formal promotion (DEP-INV-20).


#### WP-R2-002 — R2 modelling candidates (local LLM runtime, VLM experiment, advanced causal RCA, RL scheduler, alternative solver formulations)

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | R2 |
| Target milestone / sprint window | — / unscheduled |
| Readiness node (05) | DN-AI-ORCH |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Explore higher-risk research candidates in isolation from the mandatory baseline.

**Source requirements (03).** FR-AI-001, FR-SCH-009

**Architecture components (02).** ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-SCH-ENGINE

**Inputs / required contracts.** gated by DEP-064 (DN-AI-TOOLCON → DN-AI-ORCH, HARD/START@CONTRACT_READY, need-by S2–S3)

**Deliverables.**
- isolated experiment branches/configurations
- evaluation notes with negative results retained
- promotion or rejection records

**Major tasks.**
- scope each candidate to a bounded experiment
- run only on DEV/CAL partitions
- record outcomes regardless of direction

**Verification work (03 planned families).** AV-SCEN-01, BENCH-E2E-001, BENCH-PERF-SCH, BENCH-RQ1-001, BENCH-SCH-001, E2E-01, TEST-AI-OUTPUT, TEST-SCH-CONSTRAINTS

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** Cut first; failure does not make the product incomplete (Item 68 #4).


#### WP-R2-003 — R2 infrastructure candidates (Neo4j, TimescaleDB, Valkey optimization, GPU/distributed simulator)

| Field | Value |
|---|---|
| PrimaryOwner | Yavuz |
| Supporting owner (most frequent reviewer) | Batu |
| ScopeClass | R2 |
| Target milestone / sprint window | — / unscheduled |
| Readiness node (05) | DN-RT-VALKEY |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Evaluate optional infrastructure only where a measured bottleneck justifies it.

**Source requirements (03).** NFR-PERF-001

**Architecture components (02).** ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-TWIN-API

**Inputs / required contracts.** gated by DEP-015 (DN-PLAT-INTEG → DN-RT-VALKEY, SOFT/INTEGRATION@SKELETON_READY, need-by — (R2/S))

**Deliverables.**
- bottleneck analysis
- prototype measurements
- adopt/reject record

**Major tasks.**
- identify measured bottlenecks from performance lanes
- prototype narrowly
- compare against the mandatory baseline cost

**Verification work (03 planned families).** BENCH-PERF-CORE

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** Cut first. Adoption would require a declared dependency change and an ADR; none is assumed.


### 6.28 Stretch Register (`WP-S-*`, 1 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-S-001 | Stretch enhancements register (visualization, mobile UI, multi-node, analytics, extra scenarios) | Asrın | S | — | S |

#### WP-S-001 — Stretch enhancements register (visualization, mobile UI, multi-node, analytics, extra scenarios)

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Selman |
| ScopeClass | S |
| Target milestone / sprint window | — / unscheduled |
| Readiness node (05) | DN-UI-SHELL |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep valuable-but-optional enhancements visible and explicitly unscheduled so they cannot leak into the mandatory plan.

**Source requirements (03).** FR-UI-002

**Architecture components (02).** ARCH-EDGE-BFF, ARCH-EDGE-NOTIFY, ARCH-EDGE-WEB

**Inputs / required contracts.** gated by DEP-105 (DN-UI-BFFCON → DN-UI-SHELL, HARD/START@CONTRACT_READY, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON → DN-UI-SHELL, HARD/MILESTONE_EXIT@INTEGRATION_READY, need-by M1 (S2))

**Deliverables.**
- stretch register with rationale per item
- entry criteria (only after M8 scope is safe)

**Major tasks.**
- maintain the register from Item 68 §V
- review at milestone boundaries only
- never schedule against mandatory capacity

**Verification work (03 planned families).** AV-SCEN-01, DEMO-GS01-001, TEST-UI-BROWSER

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** Entire package is cuttable by definition; nothing here is required for final acceptance.


### 6.29 Out-of-Scope Guard Rail (`WP-X-*`, 1 work packages)

| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-X-001 | Out-of-scope boundary maintenance | Asrın | S | — | S |

#### WP-X-001 — Out-of-scope boundary maintenance

| Field | Value |
|---|---|
| PrimaryOwner | Asrın |
| Supporting owner (most frequent reviewer) | Yavuz |
| ScopeClass | S |
| Target milestone / sprint window | — / unscheduled |
| Readiness node (05) | DN-RES-CLAIMS |
| Size band (indicative, no hour estimates) | S (≈1–3 focused days) |
| Status | NOT_STARTED |
| Repository reference | TBD_BY_IMPLEMENTATION |

**Purpose.** Keep explicitly out-of-scope items (real manufacturing facility control, process physics, MES/ERP replacement, mandatory cloud/Kubernetes, self-approving AI) out of the plan and out of claim wording.

**Source requirements (03).** NFR-GOV-010

**Architecture components (02).** ARCH-PLAT-CICD

**Inputs / required contracts.** gated by DEP-145 (DN-RES-ANALYSIS → DN-RES-CLAIMS, HARD/MILESTONE_EXIT@FROZEN, need-by M7→M8)

**Deliverables.**
- out-of-scope register from Item 68 §VI
- claim-wording checklist used in reviews

**Major tasks.**
- review new proposals against the register
- check thesis/demo wording for scope creep

**Verification work (03 planned families).** INSP-GOV-ACCEPT, TEST-GOV-TRACELINT

**Expected evidence artifact.** CI/integration test evidence; for F0 also integrated scenario evidence — `NOT_YET_EXECUTED`.

**Risk hooks (Item 69).** —

**DoR / DoD.** DOR-WP-01…08 apply; DoD: DOD-WP-01…04, 06, 07, 12.

**Cut / fallback semantics.** Not schedulable work; a standing guard rail.

## 7. Requirement Coverage Matrix

Every one of the 306 normative requirements maps to at least one accountable work package. Multiple WPs may share a requirement (e.g., implementation + measurement + scenario execution); the first listed WP is the primary implementer.

### 7.1 Functional requirements (186)

**FR-GOV**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-GOV-001 | F1 | Asrın | WP-GOV-001 | WP-GOV-001 |
| FR-GOV-002 | F1 | Asrın | WP-GOV-001 | WP-GOV-001 |
| FR-GOV-003 | F1 | Asrın | WP-GOV-001 | WP-GOV-001 |
| FR-GOV-004 | F1 | Asrın | WP-GOV-002, WP-DOC-002 | WP-GOV-002 |
| FR-GOV-005 | F1 | Yavuz | WP-GOV-002, WP-TEST-007 | WP-GOV-002 |
| FR-GOV-006 | F1 | Yavuz | WP-GOV-003, WP-BENCH-005 | WP-GOV-003 |
| FR-GOV-007 | F1 | Asrın | WP-GOV-004 | WP-GOV-004 |
| FR-GOV-008 | F1 | Asrın | WP-GOV-001 | WP-GOV-001 |
| FR-GOV-009 | F1 | Yavuz | WP-GOV-002 | WP-GOV-002 |
| FR-GOV-010 | F1 | Asrın | WP-GOV-003, WP-DOC-006 | WP-GOV-003 |

**FR-CORE**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-CORE-001 | F0 | Asrın | WP-CORE-001 | WP-CORE-001 |
| FR-CORE-002 | F0 | Asrın | WP-CORE-001 | WP-CORE-001 |
| FR-CORE-003 | F1 | Asrın | WP-CORE-002, WP-CORE-008, WP-TEST-003 | WP-CORE-002 |
| FR-CORE-004 | F1 | Asrın | WP-CORE-003 | WP-CORE-003 |
| FR-CORE-005 | F1 | Asrın | WP-CORE-003 | WP-CORE-003 |
| FR-CORE-006 | F1 | Asrın | WP-CORE-003, WP-CORE-008 | WP-CORE-003 |
| FR-CORE-007 | F1 | Asrın | WP-CORE-002 | WP-CORE-002 |
| FR-CORE-008 | F1 | Asrın | WP-CORE-002 | WP-CORE-002 |
| FR-CORE-009 | F1 | Asrın | WP-CORE-004 | WP-CORE-004 |
| FR-CORE-010 | F1 | Asrın | WP-CORE-004 | WP-CORE-004 |
| FR-CORE-011 | F1 | Asrın | WP-CORE-004 | WP-CORE-004 |
| FR-CORE-012 | F1 | Asrın | WP-CORE-004 | WP-CORE-004 |
| FR-CORE-013 | F1 | Asrın | WP-CORE-001, WP-CORE-007 | WP-CORE-001 |
| FR-CORE-014 | F1 | Asrın | WP-CORE-005 | WP-CORE-005 |
| FR-CORE-015 | F1 | Asrın | WP-CORE-005 | WP-CORE-005 |
| FR-CORE-016 | F1 | Asrın | WP-CORE-003 | WP-CORE-003 |

**FR-SIM**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-SIM-001 | F0 | Batu | WP-SIM-001, WP-SIM-009 | WP-SIM-001 |
| FR-SIM-002 | F0 | Batu | WP-SIM-003 | WP-SIM-003 |
| FR-SIM-003 | F1 | Batu | WP-SIM-003 | WP-SIM-003 |
| FR-SIM-004 | F1 | Batu | WP-SIM-003 | WP-SIM-003 |
| FR-SIM-005 | F1 | Batu | WP-SIM-003 | WP-SIM-003 |
| FR-SIM-006 | F1 | Batu | WP-SIM-003 | WP-SIM-003 |
| FR-SIM-007 | F1 | Batu | WP-SIM-001, WP-SIM-007 | WP-SIM-001 |
| FR-SIM-008 | F1 | Batu | WP-SIM-002 | WP-SIM-002 |
| FR-SIM-009 | F1 | Batu | WP-SIM-004 | WP-SIM-004 |
| FR-SIM-010 | F1 | Batu | WP-SIM-004 | WP-SIM-004 |
| FR-SIM-011 | F1 | Batu | WP-SIM-004, WP-TEST-005 | WP-SIM-004 |
| FR-SIM-012 | F1 | Batu | WP-SIM-005, WP-TEST-005 | WP-SIM-005 |
| FR-SIM-013 | F1 | Batu | WP-SIM-006 | WP-SIM-006 |
| FR-SIM-014 | F1 | Batu | WP-SIM-006 | WP-SIM-006 |

**FR-TWIN**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-TWIN-001 | F0 | Asrın | WP-TWIN-001 | WP-TWIN-001 |
| FR-TWIN-002 | F1 | Asrın | WP-TWIN-001 | WP-TWIN-001 |
| FR-TWIN-003 | F1 | Asrın | WP-TWIN-002 | WP-TWIN-002 |
| FR-TWIN-004 | F1 | Asrın | WP-TWIN-002 | WP-TWIN-002 |
| FR-TWIN-005 | F1 | Asrın | WP-TWIN-002 | WP-TWIN-002 |
| FR-TWIN-006 | F1 | Asrın | WP-TWIN-004, WP-TEST-004 | WP-TWIN-004 |
| FR-TWIN-007 | F1 | Asrın | WP-TWIN-005, WP-TEST-005 | WP-TWIN-005 |
| FR-TWIN-008 | F1 | Asrın | WP-TWIN-003 | WP-TWIN-003 |
| FR-TWIN-009 | F1 | Asrın | WP-TWIN-001 | WP-TWIN-001 |
| FR-TWIN-010 | F1 | Asrın | WP-CORE-008, WP-TWIN-006 | WP-CORE-008 |

**FR-EVT**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-EVT-001 | F0 | Asrın | WP-EVT-001 | WP-EVT-001 |
| FR-EVT-002 | F1 | Asrın | WP-EVT-002 | WP-EVT-002 |
| FR-EVT-003 | F1 | Asrın | WP-EVT-002 | WP-EVT-002 |
| FR-EVT-004 | F1 | Asrın | WP-EVT-002 | WP-EVT-002 |
| FR-EVT-005 | F1 | Asrın | WP-EVT-003, WP-TEST-004 | WP-EVT-003 |
| FR-EVT-006 | F1 | Asrın | WP-EVT-001, WP-TEST-002 | WP-EVT-001 |
| FR-EVT-007 | F1 | Asrın | WP-EVT-005, WP-TEST-007 | WP-EVT-005 |
| FR-EVT-008 | F1 | Asrın | WP-EVT-001 | WP-EVT-001 |
| FR-EVT-009 | F1 | Yavuz | WP-EVT-004 | WP-EVT-004 |
| FR-EVT-010 | F1 | Yavuz | WP-EVT-004 | WP-EVT-004 |

**FR-VIS**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-VIS-001 | F0 | Selman | WP-OBJ-001, WP-VIS-001 | WP-OBJ-001 |
| FR-VIS-002 | F1 | Selman | WP-VIS-002, WP-VDATA-005, WP-RES-006 | WP-VIS-002 |
| FR-VIS-003 | F1 | Selman | WP-VIS-002 | WP-VIS-002 |
| FR-VIS-004 | F1 | Selman | WP-VIS-003 | WP-VIS-003 |
| FR-VIS-005 | F1 | Selman | WP-VIS-003 | WP-VIS-003 |
| FR-VIS-006 | F1 | Selman | WP-VIS-004, WP-VDATA-005, WP-RES-010 | WP-VIS-004 |
| FR-VIS-007 | F1 | Selman | WP-VIS-005 | WP-VIS-005 |
| FR-VIS-008 | F1 | Selman | WP-VIS-005 | WP-VIS-005 |
| FR-VIS-009 | F1 | Selman | WP-VIS-001 | WP-VIS-001 |
| FR-VIS-010 | F1 | Selman | WP-VIS-006, WP-VDATA-005, WP-RES-010 | WP-VIS-006 |
| FR-VIS-011 | F1 | Selman | WP-VDATA-001, WP-VDATA-003 | WP-VDATA-001 |
| FR-VIS-012 | F1 | Selman | WP-VDATA-002 | WP-VDATA-002 |
| FR-VIS-013 | F1 | Selman | WP-VIS-009 | WP-VIS-009 |
| FR-VIS-014 | F1 | Selman | WP-VIS-008 | WP-VIS-008 |
| FR-VIS-015 | F1 | Selman | WP-VDATA-004 | WP-VDATA-004 |
| FR-VIS-016 | F0 | Selman | WP-VIS-007, WP-TEST-006, WP-RES-010, WP-BENCH-002 | WP-VIS-007 |

**FR-ML**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-ML-001 | F1 | Asrın | WP-ML-002, WP-ML-007 | WP-ML-002 |
| FR-ML-002 | F1 | Asrın | WP-ML-003, WP-ML-007 | WP-ML-003 |
| FR-ML-003 | F1 | Asrın | WP-ML-004, WP-ML-007 | WP-ML-004 |
| FR-ML-004 | F1 | Asrın | WP-ML-005 | WP-ML-005 |
| FR-ML-005 | F1 | Asrın | WP-VDATA-004, WP-ML-005 | WP-VDATA-004 |
| FR-ML-006 | F1 | Asrın | WP-ML-006 | WP-ML-006 |
| FR-ML-007 | F1 | Asrın | WP-SIM-007, WP-ML-001 | WP-SIM-007 |
| FR-ML-008 | F1 | Asrın | WP-ML-001 | WP-ML-001 |

**FR-RAG**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-RAG-001 | F1 | Asrın | WP-RAG-001 | WP-RAG-001 |
| FR-RAG-002 | F1 | Asrın | WP-RAG-005 | WP-RAG-005 |
| FR-RAG-003 | F1 | Asrın | WP-RAG-002 | WP-RAG-002 |
| FR-RAG-004 | F1 | Asrın | WP-RAG-002 | WP-RAG-002 |
| FR-RAG-005 | F1 | Asrın | WP-RAG-002, WP-R2-001 | WP-RAG-002 |
| FR-RAG-006 | F1 | Asrın | WP-RAG-003 | WP-RAG-003 |
| FR-RAG-007 | F1 | Asrın | WP-RAG-004 | WP-RAG-004 |
| FR-RAG-008 | F1 | Asrın | WP-RAG-004 | WP-RAG-004 |
| FR-RAG-009 | F1 | Asrın | WP-RAG-001, WP-RAG-007, WP-RES-011 | WP-RAG-001 |
| FR-RAG-010 | F1 | Asrın | WP-RAG-003, WP-RES-007 | WP-RAG-003 |

**FR-AI**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-AI-001 | F0 | Asrın | WP-AI-001, WP-TEST-006, WP-RES-006, WP-R2-002 | WP-AI-001 |
| FR-AI-002 | F1 | Asrın | WP-AI-002 | WP-AI-002 |
| FR-AI-003 | F1 | Asrın | WP-AI-002 | WP-AI-002 |
| FR-AI-004 | F0 | Asrın | WP-AI-006, WP-TEST-003, WP-RES-009 | WP-AI-006 |
| FR-AI-005 | F1 | Asrın | WP-AI-003, WP-RES-007 | WP-AI-003 |
| FR-AI-006 | F1 | Asrın | WP-AI-003 | WP-AI-003 |
| FR-AI-007 | F1 | Asrın | WP-AI-003 | WP-AI-003 |
| FR-AI-008 | F1 | Asrın | WP-AI-003, WP-RES-007 | WP-AI-003 |
| FR-AI-009 | F1 | Asrın | WP-AI-004 | WP-AI-004 |
| FR-AI-010 | F1 | Asrın | WP-AI-004 | WP-AI-004 |
| FR-AI-011 | F1 | Asrın | WP-AI-005, WP-RES-011 | WP-AI-005 |
| FR-AI-012 | F1 | Asrın | WP-AI-001 | WP-AI-001 |
| FR-AI-013 | F1 | Asrın | WP-AI-001 | WP-AI-001 |

**FR-SCH**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-SCH-001 | F0 | Batu | WP-SCH-002 | WP-SCH-002 |
| FR-SCH-002 | F1 | Batu | WP-SCH-004 | WP-SCH-004 |
| FR-SCH-003 | F1 | Batu | WP-SCH-004, WP-RES-008 | WP-SCH-004 |
| FR-SCH-004 | F1 | Batu | WP-SCH-003 | WP-SCH-003 |
| FR-SCH-005 | F0 | Batu | WP-VALID-001, WP-TEST-006 | WP-VALID-001 |
| FR-SCH-006 | F1 | Batu | WP-VALID-002 | WP-VALID-002 |
| FR-SCH-007 | F1 | Batu | WP-SCH-002 | WP-SCH-002 |
| FR-SCH-008 | F1 | Batu | WP-SCH-002 | WP-SCH-002 |
| FR-SCH-009 | F1 | Batu | WP-SCH-003, WP-R2-002 | WP-SCH-003 |
| FR-SCH-010 | F1 | Batu | WP-SCH-001, WP-RES-006 | WP-SCH-001 |
| FR-SCH-011 | F1 | Batu | WP-SCH-007 | WP-SCH-007 |
| FR-SCH-012 | F1 | Batu | WP-SCH-005 | WP-SCH-005 |
| FR-SCH-013 | F1 | Batu | WP-SCH-006, WP-RES-008 | WP-SCH-006 |
| FR-SCH-014 | F1 | Batu | WP-VALID-002 | WP-VALID-002 |
| FR-SCH-015 | F1 | Batu | WP-SCH-002 | WP-SCH-002 |

**FR-AUTO**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-AUTO-001 | F0 | Batu | WP-AUTO-001 | WP-AUTO-001 |
| FR-AUTO-002 | F1 | Batu | WP-AUTO-001 | WP-AUTO-001 |
| FR-AUTO-003 | F1 | Batu | WP-AUTO-001 | WP-AUTO-001 |
| FR-AUTO-004 | F1 | Batu | WP-AUTO-003, WP-RES-009 | WP-AUTO-003 |
| FR-AUTO-005 | F1 | Batu | WP-AUTO-002 | WP-AUTO-002 |
| FR-AUTO-006 | F1 | Batu | WP-AUTO-002, WP-TEST-004 | WP-AUTO-002 |
| FR-AUTO-007 | F1 | Batu | WP-AUTO-005 | WP-AUTO-005 |
| FR-AUTO-008 | F1 | Batu | WP-AUTO-005, WP-TEST-003, WP-RES-008 | WP-AUTO-005 |
| FR-AUTO-009 | F1 | Batu | WP-AUTO-005 | WP-AUTO-005 |
| FR-AUTO-010 | F1 | Batu | WP-AUTO-003 | WP-AUTO-003 |
| FR-AUTO-011 | F1 | Batu | WP-AUTO-006 | WP-AUTO-006 |
| FR-AUTO-012 | F1 | Batu | WP-AUTO-004 | WP-AUTO-004 |
| FR-AUTO-013 | F1 | Batu | WP-AUTO-004 | WP-AUTO-004 |
| FR-AUTO-014 | F0 | Batu | WP-AUTO-007, WP-TEST-006, WP-BENCH-002 | WP-AUTO-007 |

**FR-HITL**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-HITL-001 | F0 | Asrın | WP-HITL-001, WP-RES-009 | WP-HITL-001 |
| FR-HITL-002 | F1 | Asrın | WP-HITL-001 | WP-HITL-001 |
| FR-HITL-003 | F1 | Asrın | WP-HITL-002 | WP-HITL-002 |
| FR-HITL-004 | F1 | Asrın | WP-HITL-002 | WP-HITL-002 |
| FR-HITL-005 | F1 | Asrın | WP-HITL-002 | WP-HITL-002 |
| FR-HITL-006 | F1 | Asrın | WP-HITL-003, WP-TEST-003 | WP-HITL-003 |
| FR-HITL-007 | F1 | Yavuz | WP-HITL-004, WP-TEST-006 | WP-HITL-004 |
| FR-HITL-008 | F1 | Asrın | WP-HITL-005 | WP-HITL-005 |
| FR-HITL-009 | F1 | Asrın | WP-HITL-006 | WP-HITL-006 |
| FR-HITL-010 | F1 | Yavuz | WP-HITL-007 | WP-HITL-007 |

**FR-UI**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-UI-001 | F0 | Asrın | WP-UI-001 | WP-UI-001 |
| FR-UI-002 | F1 | Asrın | WP-UI-002, WP-S-001 | WP-UI-002 |
| FR-UI-003 | F1 | Selman | WP-UI-003 | WP-UI-003 |
| FR-UI-004 | F1 | Asrın | WP-UI-004 | WP-UI-004 |
| FR-UI-005 | F1 | Batu | WP-UI-005 | WP-UI-005 |
| FR-UI-006 | F1 | Asrın | WP-UI-006 | WP-UI-006 |
| FR-UI-007 | F1 | Batu | WP-UI-007 | WP-UI-007 |
| FR-UI-008 | F1 | Asrın | WP-UI-008 | WP-UI-008 |
| FR-UI-009 | F1 | Yavuz | WP-UI-009, WP-DOC-004 | WP-UI-009 |
| FR-UI-010 | F1 | Asrın | WP-UI-010 | WP-UI-010 |

**FR-PLAT**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-PLAT-001 | F0 | Yavuz | WP-PLAT-001, WP-PLAT-003 | WP-PLAT-001 |
| FR-PLAT-002 | F1 | Yavuz | WP-PLAT-001 | WP-PLAT-001 |
| FR-PLAT-003 | F1 | Yavuz | WP-PLAT-002 | WP-PLAT-002 |
| FR-PLAT-004 | F1 | Yavuz | WP-CICD-001, WP-CICD-002 | WP-CICD-001 |
| FR-PLAT-005 | F1 | Yavuz | WP-PLAT-005, WP-CICD-002 | WP-PLAT-005 |
| FR-PLAT-006 | F1 | Yavuz | WP-OBS-001 | WP-OBS-001 |
| FR-PLAT-007 | F1 | Yavuz | WP-OBS-002 | WP-OBS-002 |
| FR-PLAT-008 | F1 | Yavuz | WP-DR-001 | WP-DR-001 |
| FR-PLAT-009 | F1 | Yavuz | WP-DR-003 | WP-DR-003 |
| FR-PLAT-010 | F1 | Yavuz | WP-PLAT-005, WP-RES-001 | WP-PLAT-005 |

**FR-SEC**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-SEC-001 | F1 | Yavuz | WP-SEC-001 | WP-SEC-001 |
| FR-SEC-002 | F1 | Yavuz | WP-SEC-002 | WP-SEC-002 |
| FR-SEC-003 | F1 | Asrın | WP-SEC-003 | WP-SEC-003 |
| FR-SEC-004 | F1 | Yavuz | WP-AI-002, WP-SEC-004 | WP-AI-002 |
| FR-SEC-005 | F1 | Yavuz | WP-AI-002, WP-SEC-004 | WP-AI-002 |
| FR-SEC-006 | F1 | Yavuz | WP-SEC-005 | WP-SEC-005 |
| FR-SEC-007 | F1 | Yavuz | WP-OBS-004 | WP-OBS-004 |
| FR-SEC-008 | F1 | Yavuz | WP-SEC-006 | WP-SEC-006 |
| FR-SEC-009 | F1 | Asrın | WP-RAG-004 | WP-RAG-004 |
| FR-SEC-010 | F1 | Yavuz | WP-SIM-005, WP-SEC-007 | WP-SIM-005 |

**FR-EVAL**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| FR-EVAL-001 | R1 | Yavuz | WP-RES-001, WP-BENCH-001 | WP-RES-001 |
| FR-EVAL-002 | R1 | Asrın | WP-SIM-007, WP-RES-002, WP-RES-011 | WP-SIM-007 |
| FR-EVAL-003 | R1 | Yavuz | WP-RES-003, WP-BENCH-001 | WP-RES-003 |
| FR-EVAL-004 | R1 | Yavuz | WP-RES-003 | WP-RES-003 |
| FR-EVAL-005 | R1 | Yavuz | WP-RES-003 | WP-RES-003 |
| FR-EVAL-006 | R1 | Asrın | WP-RES-004 | WP-RES-004 |
| FR-EVAL-007 | R1 | Yavuz | WP-RES-005, WP-BENCH-005 | WP-RES-005 |
| FR-EVAL-008 | R1 | Yavuz | WP-DR-004 | WP-DR-004 |
| FR-EVAL-009 | R1 | Asrın | WP-RES-012 | WP-RES-012 |
| FR-EVAL-010 | R1 | Asrın | WP-RES-012, WP-DOC-003 | WP-RES-012 |

### 7.2 Non-functional requirements (120)

**NFR-GOV**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-GOV-001 | H0 | Asrın | WP-GOV-001 | WP-GOV-001 |
| NFR-GOV-002 | H0 | Asrın | WP-GOV-001 | WP-GOV-001 |
| NFR-GOV-003 | H0 | Asrın | WP-GOV-001 | WP-GOV-001 |
| NFR-GOV-004 | H0 | Yavuz | WP-GOV-003, WP-PERF-001 | WP-GOV-003 |
| NFR-GOV-005 | H0 | Yavuz | WP-GOV-003, WP-PERF-001 | WP-GOV-003 |
| NFR-GOV-006 | H0 | Yavuz | WP-GOV-003, WP-PERF-001 | WP-GOV-003 |
| NFR-GOV-007 | H0 | Asrın | WP-GOV-001 | WP-GOV-001 |
| NFR-GOV-008 | H0 | Asrın | WP-GOV-004 | WP-GOV-004 |
| NFR-GOV-009 | H0 | Yavuz | WP-GOV-002, WP-DOC-006 | WP-GOV-002 |
| NFR-GOV-010 | H0 | Asrın | WP-GOV-003, WP-X-001 | WP-GOV-003 |

**NFR-PERF**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-PERF-001 | S2 | Asrın | WP-CORE-006, WP-TWIN-003, WP-PERF-002, WP-R2-003 | WP-CORE-006 |
| NFR-PERF-002 | S2 | Asrın | WP-CORE-006, WP-PERF-002 | WP-CORE-006 |
| NFR-PERF-003 | A1 | Asrın | WP-EVT-006, WP-PERF-002 | WP-EVT-006 |
| NFR-PERF-004 | A1 | Asrın | WP-TWIN-003, WP-PERF-002 | WP-TWIN-003 |
| NFR-PERF-005 | S2 | Asrın | WP-UI-002, WP-PERF-002 | WP-UI-002 |
| NFR-PERF-006 | S2 | Asrın | WP-RAG-002, WP-PERF-002 | WP-RAG-002 |
| NFR-PERF-007 | S2 | Asrın | WP-AI-007 | WP-AI-007 |
| NFR-PERF-008 | A1 | Batu | WP-SCH-005, WP-PERF-006 | WP-SCH-005 |
| NFR-PERF-009 | A1 | Selman | WP-VIS-008 | WP-VIS-008 |
| NFR-PERF-010 | C3 | Selman | WP-VIS-010 | WP-VIS-010 |
| NFR-PERF-011 | S2 | Batu | WP-AUTO-007, WP-PERF-002 | WP-AUTO-007 |
| NFR-PERF-012 | S2 | Yavuz | WP-HITL-004, WP-PERF-002 | WP-HITL-004 |
| NFR-PERF-013 | S2 | Batu | WP-AUTO-007, WP-PERF-002, WP-BENCH-002, WP-DOC-004 | WP-AUTO-007 |
| NFR-PERF-014 | S2 | Asrın | WP-UI-001, WP-PERF-002 | WP-UI-001 |

**NFR-CAP**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-CAP-001 | A1 | Batu | WP-SIM-008, WP-PERF-003 | WP-SIM-008 |
| NFR-CAP-002 | A1 | Batu | WP-SIM-008, WP-PERF-003 | WP-SIM-008 |
| NFR-CAP-003 | A1 | Batu | WP-SIM-008 | WP-SIM-008 |
| NFR-CAP-004 | A1 | Yavuz | WP-EVT-006, WP-PERF-003 | WP-EVT-006 |
| NFR-CAP-005 | S2 | Asrın | WP-CORE-006, WP-PERF-003 | WP-CORE-006 |
| NFR-CAP-006 | A1 | Batu | WP-SCH-005, WP-PERF-006 | WP-SCH-005 |
| NFR-CAP-007 | C3 | Batu | WP-SCH-005, WP-PERF-006 | WP-SCH-005 |
| NFR-CAP-008 | A1 | Batu | WP-AUTO-007, WP-PERF-003 | WP-AUTO-007 |
| NFR-CAP-009 | S2 | Yavuz | WP-PLAT-004, WP-PERF-003 | WP-PLAT-004 |
| NFR-CAP-010 | S2 | Yavuz | WP-TWIN-005, WP-PERF-003 | WP-TWIN-005 |

**NFR-REL**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-REL-001 | H0 | Batu | WP-AUTO-002, WP-PERF-005, WP-BENCH-003 | WP-AUTO-002 |
| NFR-REL-002 | H0 | Asrın | WP-HITL-003 | WP-HITL-003 |
| NFR-REL-003 | A1 | Yavuz | WP-PERF-004 | WP-PERF-004 |
| NFR-REL-004 | A1 | Batu | WP-AUTO-002, WP-PERF-004 | WP-AUTO-002 |
| NFR-REL-005 | A1 | Yavuz | WP-TEST-005, WP-PERF-004 | WP-TEST-005 |
| NFR-REL-006 | A1 | Yavuz | WP-TEST-004, WP-PERF-004 | WP-TEST-004 |
| NFR-REL-007 | A1 | Yavuz | WP-PERF-005 | WP-PERF-005 |
| NFR-REL-008 | A1 | Yavuz | WP-PERF-004 | WP-PERF-004 |
| NFR-REL-009 | A1 | Yavuz | WP-OBS-003, WP-PERF-004 | WP-OBS-003 |
| NFR-REL-010 | H0 | Asrın | WP-CORE-008, WP-TWIN-006 | WP-CORE-008 |

**NFR-REC**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-REC-001 | A1 | Yavuz | WP-DR-001 | WP-DR-001 |
| NFR-REC-002 | H0 | Yavuz | WP-DR-004 | WP-DR-004 |
| NFR-REC-003 | A1 | Yavuz | WP-DR-002 | WP-DR-002 |
| NFR-REC-004 | A1 | Yavuz | WP-DR-002 | WP-DR-002 |
| NFR-REC-005 | S2 | Yavuz | WP-CICD-005 | WP-CICD-005 |
| NFR-REC-006 | H0 | Yavuz | WP-DR-001 | WP-DR-001 |
| NFR-REC-007 | H0 | Yavuz | WP-DR-002, WP-BENCH-003 | WP-DR-002 |
| NFR-REC-008 | S2 | Asrın | WP-TWIN-004, WP-DR-003 | WP-TWIN-004 |
| NFR-REC-009 | S2 | Asrın | WP-RAG-006, WP-DR-003 | WP-RAG-006 |
| NFR-REC-010 | H0 | Yavuz | WP-DR-001 | WP-DR-001 |

**NFR-SEC**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-SEC-001 | H0 | Yavuz | WP-SEC-005, WP-DOC-005 | WP-SEC-005 |
| NFR-SEC-002 | H0 | Yavuz | WP-CICD-004 | WP-CICD-004 |
| NFR-SEC-003 | A1 | Yavuz | WP-SEC-001 | WP-SEC-001 |
| NFR-SEC-004 | H0 | Asrın | WP-AI-006, WP-SEC-008, WP-BENCH-003 | WP-AI-006 |
| NFR-SEC-005 | H0 | Yavuz | WP-HITL-004 | WP-HITL-004 |
| NFR-SEC-006 | H0 | Yavuz | WP-SEC-006 | WP-SEC-006 |
| NFR-SEC-007 | H0 | Yavuz | WP-SEC-002 | WP-SEC-002 |
| NFR-SEC-008 | A1 | Yavuz | WP-SEC-002 | WP-SEC-002 |
| NFR-SEC-009 | H0 | Asrın | WP-AI-005, WP-SEC-008 | WP-AI-005 |
| NFR-SEC-010 | H0 | Yavuz | WP-HITL-005, WP-SEC-008 | WP-HITL-005 |
| NFR-SEC-011 | H0 | Yavuz | WP-CICD-006 | WP-CICD-006 |
| NFR-SEC-012 | H0 | Yavuz | WP-HITL-007 | WP-HITL-007 |

**NFR-OBS**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-OBS-001 | A1 | Yavuz | WP-OBS-001 | WP-OBS-001 |
| NFR-OBS-002 | A1 | Yavuz | WP-OBS-001 | WP-OBS-001 |
| NFR-OBS-003 | A1 | Yavuz | WP-OBS-002, WP-BENCH-002 | WP-OBS-002 |
| NFR-OBS-004 | A1 | Yavuz | WP-OBS-003 | WP-OBS-003 |
| NFR-OBS-005 | H0 | Yavuz | WP-OBS-002 | WP-OBS-002 |
| NFR-OBS-006 | H0 | Yavuz | WP-OBS-005 | WP-OBS-005 |
| NFR-OBS-007 | H0 | Yavuz | WP-OBS-004 | WP-OBS-004 |
| NFR-OBS-008 | S2 | Yavuz | WP-OBS-006 | WP-OBS-006 |
| NFR-OBS-009 | A1 | Yavuz | WP-OBJ-002, WP-OBS-006 | WP-OBJ-002 |

**NFR-REP**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-REP-001 | H0 | Batu | WP-SIM-002, WP-SIM-009 | WP-SIM-002 |
| NFR-REP-002 | H0 | Asrın | WP-RES-004 | WP-RES-004 |
| NFR-REP-003 | A1 | Yavuz | WP-PLAT-005, WP-BENCH-004 | WP-PLAT-005 |
| NFR-REP-004 | A1 | Yavuz | WP-BENCH-003, WP-BENCH-004 | WP-BENCH-003 |
| NFR-REP-005 | H0 | Yavuz | WP-CICD-004 | WP-CICD-004 |
| NFR-REP-006 | H0 | Yavuz | WP-CICD-004 | WP-CICD-004 |
| NFR-REP-007 | H0 | Yavuz | WP-PLAT-005 | WP-PLAT-005 |
| NFR-REP-008 | A1 | Yavuz | WP-BENCH-004, WP-DOC-005 | WP-BENCH-004 |
| NFR-REP-009 | C3 | Asrın | WP-AI-005 | WP-AI-005 |

**NFR-RES**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-RES-001 | A1 | Yavuz | WP-PLAT-004 | WP-PLAT-004 |
| NFR-RES-002 | A1 | Yavuz | WP-PLAT-004 | WP-PLAT-004 |
| NFR-RES-003 | H0 | Yavuz | WP-PLAT-004 | WP-PLAT-004 |
| NFR-RES-004 | A1 | Yavuz | WP-PLAT-007 | WP-PLAT-007 |
| NFR-RES-005 | H0 | Yavuz | WP-PLAT-007 | WP-PLAT-007 |
| NFR-RES-006 | A1 | Yavuz | WP-OBJ-002 | WP-OBJ-002 |
| NFR-RES-007 | A1 | Yavuz | WP-VIS-008 | WP-VIS-008 |
| NFR-RES-008 | C3 | Yavuz | WP-PLAT-004 | WP-PLAT-004 |

**NFR-DEP**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-DEP-001 | A1 | Yavuz | WP-PLAT-001, WP-PLAT-003 | WP-PLAT-001 |
| NFR-DEP-002 | S2 | Yavuz | WP-PLAT-001 | WP-PLAT-001 |
| NFR-DEP-003 | H0 | Yavuz | WP-CICD-002 | WP-CICD-002 |
| NFR-DEP-004 | A1 | Yavuz | WP-CORE-007, WP-CICD-003 | WP-CORE-007 |
| NFR-DEP-005 | H0 | Yavuz | WP-BENCH-004 | WP-BENCH-004 |
| NFR-DEP-006 | H0 | Yavuz | WP-PLAT-001 | WP-PLAT-001 |

**NFR-DX**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-DX-001 | S2 | Yavuz | WP-PLAT-002 | WP-PLAT-002 |
| NFR-DX-002 | S2 | Yavuz | WP-PLAT-002 | WP-PLAT-002 |
| NFR-DX-003 | S2 | Yavuz | WP-PLAT-002 | WP-PLAT-002 |
| NFR-DX-004 | S2 | Yavuz | WP-PLAT-002 | WP-PLAT-002 |
| NFR-DX-005 | S2 | Yavuz | WP-PLAT-006 | WP-PLAT-006 |
| NFR-DX-006 | H0 | Yavuz | WP-CICD-001, WP-TEST-001, WP-TEST-008 | WP-CICD-001 |
| NFR-DX-007 | A1 | Yavuz | WP-PLAT-006, WP-DOC-001 | WP-PLAT-006 |
| NFR-DX-008 | S2 | Yavuz | WP-PLAT-006, WP-OBS-005 | WP-PLAT-006 |

**NFR-DATA**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-DATA-001 | H0 | Yavuz | WP-OBJ-001 | WP-OBJ-001 |
| NFR-DATA-002 | H0 | Asrın | WP-VDATA-002, WP-RES-002 | WP-VDATA-002 |
| NFR-DATA-003 | H0 | Yavuz | WP-RES-003, WP-BENCH-005 | WP-RES-003 |
| NFR-DATA-004 | H0 | Yavuz | WP-RES-005, WP-BENCH-005 | WP-RES-005 |
| NFR-DATA-005 | H0 | Asrın | WP-EVT-001, WP-TEST-002 | WP-EVT-001 |
| NFR-DATA-006 | H0 | Asrın | WP-VDATA-001 | WP-VDATA-001 |
| NFR-DATA-007 | H0 | Yavuz | WP-RES-003 | WP-RES-003 |
| NFR-DATA-008 | H0 | Yavuz | WP-EVT-002 | WP-EVT-002 |

**NFR-UX**

| Requirement | Class | PrimaryOwner (01) | Owning work packages | Primary implementer |
|---|---|---|---|---|
| NFR-UX-001 | A1 | Asrın | WP-UI-008 | WP-UI-008 |
| NFR-UX-002 | H0 | Asrın | WP-TWIN-002, WP-UI-008 | WP-TWIN-002 |
| NFR-UX-003 | H0 | Asrın | WP-UI-006 | WP-UI-006 |
| NFR-UX-004 | A1 | Asrın | WP-UI-008 | WP-UI-008 |
| NFR-UX-005 | A1 | Asrın | WP-UI-011 | WP-UI-011 |
| NFR-UX-006 | H0 | Asrın | WP-UI-012, WP-DOC-004 | WP-UI-012 |

## 8. Milestone Rollup

### 8.M0 M0 — S1 (2 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-GOV-001 | Machine-readable requirement catalog and ID lint | Asrın | F1 | GOV |
| WP-CICD-001 | CI pipeline and required gates | Yavuz | F1 | CICD |

### 8.M1 M1 — S2 (13 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-CORE-001 | Canonical manufacturing domain model and core schema | Asrın | F0 | CORE |
| WP-CORE-005 | Domain events and transactional outbox | Asrın | F0 | CORE |
| WP-CORE-007 | Core database migrations and role separation | Asrın | F1 | CORE |
| WP-EVT-001 | Integration Contract Registry and versioning discipline | Asrın | F0 | EVT |
| WP-EVT-002 | Message envelope, correlation and world scoping | Asrın | F1 | EVT |
| WP-TWIN-001 | Twin projection engine | Asrın | F0 | TWIN |
| WP-SIM-001 | Deterministic DES kernel | Batu | F0 | SIM |
| WP-UI-001 | Command Center shell and BFF contract | Asrın | F0 | UI |
| WP-PLAT-001 | Compose profiles and mandatory runtime composition | Yavuz | F0 | PLAT |
| WP-PLAT-002 | mfgctl developer and operator CLI | Yavuz | F1 | PLAT |
| WP-CICD-002 | CD to INTEGRATION with immutable artifacts | Yavuz | F0 | CICD |
| WP-OBS-001 | Telemetry pipeline (OTel → Collector → OpenObserve) | Yavuz | F1 | OBS |
| WP-TEST-001 | Test strategy, tiers and boundary-mode policy | Yavuz | F1 | TEST |

### 8.M2 M2 — S3–S4 (21 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-GOV-002 | Trace registry, edges and trace linter | Yavuz | F1 | GOV |
| WP-CORE-002 | Manufacturing lifecycle state machine | Asrın | F1 | CORE |
| WP-CORE-003 | Command acceptance: idempotency, revision preconditions, durable outcomes | Asrın | F1 | CORE |
| WP-CORE-004 | Rework, split/merge and temporal genealogy | Asrın | F1 | CORE |
| WP-EVT-003 | Idempotent consumer framework | Asrın | F1 | EVT |
| WP-EVT-005 | Architecture rules as code (boundaries and ownership) | Asrın | F1 | EVT |
| WP-TWIN-002 | Epistemic classes, freshness and staleness semantics | Asrın | F1 | TWIN |
| WP-TWIN-003 | Twin query API and scheduling snapshot export | Asrın | F1 | TWIN |
| WP-SIM-002 | Determinism, replay and event-hash equivalence | Batu | F1 | SIM |
| WP-SIM-003 | Operational semantics: reentrant routing, queues, failures, maintenance, rework | Batu | F0 | SIM |
| WP-SIM-006 | External dispatch decision interface and operational telemetry | Batu | F0 | SIM |
| WP-OBJ-001 | Artifact service: ArtifactRef contract and object storage integration | Yavuz | F1 | OBJ |
| WP-VIS-001 | Inspection pipeline and serving path | Selman | F0 | VIS |
| WP-VIS-008 | CPU smoke inference path | Selman | F1 | VIS |
| WP-SCH-001 | Dispatch baselines and scheduling instance model | Batu | F1 | SCH |
| WP-UI-002 | manufacturing facility state and operational views | Asrın | F1 | UI |
| WP-PLAT-003 | Runtime service bring-up on the shared host | Yavuz | F1 | PLAT |
| WP-CICD-003 | Automated migration execution in the deployment path | Yavuz | F1 | CICD |
| WP-TEST-002 | Contract and schema test suites | Asrın | F1 | TEST |
| WP-TEST-007 | Architecture rules and trace validation in CI | Yavuz | F1 | TEST |
| WP-DOC-002 | ADR backfill and decision index | Asrın | F1 | DOC |

### 8.M3 M3 — S5–S6 (27 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-CORE-008 | Core ↔ Simulator ↔ Twin integration and acceptance | Asrın | F0 | CORE |
| WP-TWIN-006 | Effect verification view and Core/Twin consistency | Asrın | F0 | TWIN |
| WP-SIM-005 | Oracle isolation and evaluator-only data plane | Batu | F0 | SIM |
| WP-VIS-007 | Vision-to-loop integration (perception drives RCA) | Selman | F0 | VIS |
| WP-VIS-009 | Oracle-taint guard for Vision inputs | Selman | F1 | VIS |
| WP-AI-001 | Deterministic orchestrator and execution budgets | Asrın | F0 | AI |
| WP-AI-002 | Typed tool registry and authority-tagged tool access | Asrın | F1 | AI |
| WP-AI-003 | Structured evidence-grounded RCA output | Asrın | F1 | AI |
| WP-AI-004 | Action proposal and context binding | Asrın | F1 | AI |
| WP-AI-006 | AI authority boundary and negative suite | Asrın | F0 | AI |
| WP-SCH-002 | Snapshot consumption and recovery plan contract | Batu | F0 | SCH |
| WP-VALID-001 | Independent schedule validator | Batu | F0 | VALID |
| WP-VALID-002 | Execution eligibility gate and AI-origin plan routing | Batu | F1 | VALID |
| WP-AUTO-001 | Durable workflow bundle and approval wait | Batu | F0 | AUTO |
| WP-AUTO-003 | Pre-execution revalidation and command identity | Batu | F1 | AUTO |
| WP-AUTO-004 | ActionCatalog and authorization gate | Batu | F1 | AUTO |
| WP-AUTO-005 | Outcome model and effect verification | Batu | F0 | AUTO |
| WP-HITL-001 | Authority policy engine (L0–L4) | Asrın | F0 | HITL |
| WP-HITL-002 | Approval binding to exact proposal/plan revision and world | Asrın | F1 | HITL |
| WP-HITL-003 | Expiry, replay and staleness rejection | Asrın | F1 | HITL |
| WP-HITL-004 | Identity-bound approvals | Yavuz | F1 | HITL |
| WP-UI-006 | Approval Center | Asrın | F0 | UI |
| WP-OBS-002 | Distributed trace propagation across the closed loop | Yavuz | F1 | OBS |
| WP-SEC-001 | Keycloak realm, clients and interactive authentication | Yavuz | F1 | SEC |
| WP-SEC-003 | Backend authorization enforcement | Asrın | F1/H0 | SEC |
| WP-TEST-003 | Integration scenarios AV-SCEN-01…04 | Asrın | F0 | TEST |
| WP-TEST-006 | E2E-01 checkpoint execution | Batu | F0 | TEST |

### 8.M4 M4 — S7–S8 (39 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-TWIN-005 | Counterfactual/what-if stream isolation | Asrın | F1 | TWIN |
| WP-SIM-004 | Snapshot, fork and world isolation | Batu | F1 | SIM |
| WP-SIM-007 | Scenario versioning and synthetic operational history | Batu | F1 | SIM |
| WP-VIS-002 | Defect classification and localization models | Selman | F1 | VIS |
| WP-VIS-003 | Segmentation and anomaly detection | Selman | F1 | VIS |
| WP-VIS-004 | OOD / UNKNOWN handling and threshold policy | Selman | F1 | VIS |
| WP-VIS-005 | Provenance, confidence and calibration in Vision outputs | Selman | F1 | VIS |
| WP-VIS-006 | SerializedComponent spatial pattern and cluster analysis | Selman | F1 | VIS |
| WP-VDATA-001 | Dataset governance, rights and provenance | Selman | F1 | VDATA |
| WP-VDATA-003 | Synthetic Vision data generator | Selman | F1 | VDATA |
| WP-ML-001 | Feature and label pipeline from operational history | Asrın | F1 | ML |
| WP-ML-002 | M1 — equipment risk model | Asrın | F1 | ML |
| WP-ML-003 | M2 — cycle-time / tardiness risk model | Asrın | F1 | ML |
| WP-ML-004 | M3 — pre-inspection quality risk model | Asrın | F1 | ML |
| WP-ML-005 | Common prediction contract and publication | Asrın | F1 | ML |
| WP-RAG-001 | Documentary corpus governance and ingestion | Asrın | F1 | RAG |
| WP-RAG-002 | Retrieval profiles: sparse, dense and hybrid | Asrın | F1 | RAG |
| WP-RAG-003 | Citation-bearing provenance in retrieval and RCA | Asrın | F1 | RAG |
| WP-RAG-004 | Rights filtering and prompt-injection resistance | Asrın | F1 | RAG |
| WP-RAG-005 | Evidence typing: documentary vs operational | Asrın | F1 | RAG |
| WP-AI-005 | Provider abstraction, behavior bundle and deterministic baseline | Asrın | F1 | AI |
| WP-SCH-003 | CP-SAT model and hard constraints | Batu | F1 | SCH |
| WP-SCH-004 | Rolling horizon and event-triggered rescheduling | Batu | F1 | SCH |
| WP-SCH-006 | Counterfactual schedule evaluation on forked worlds | Batu | F1 | SCH |
| WP-AUTO-002 | Idempotency and restart safety for protected effects | Batu | F1 | AUTO |
| WP-AUTO-007 | GS-01 recovery workflow and closed-loop timing | Batu | F0 | AUTO |
| WP-HITL-005 | Approval record, audit trail and protected-action coverage | Asrın | F1 | HITL |
| WP-HITL-006 | Dual approval for highest-risk actions | Asrın | F1 | HITL |
| WP-UI-003 | Inspection viewer with overlays | Selman | F1 | UI |
| WP-UI-004 | Incident investigation workspace (RCA) | Asrın | F1 | UI |
| WP-UI-005 | Planning and validation views | Batu | F1 | UI |
| WP-UI-007 | Workflow progress and verification view | Batu | F1 | UI |
| WP-UI-009 | System health and environment diagnostics view | Yavuz | F1 | UI |
| WP-OBS-003 | Health, readiness and degradation states | Yavuz | F1 | OBS |
| WP-OBS-004 | Audit store separation from telemetry | Yavuz | F1/H0 | OBS |
| WP-SEC-002 | Service identities and least-privilege credentials | Yavuz | F1/H0 | SEC |
| WP-SEC-004 | AI-reachable capability surface restriction | Yavuz | F1/H0 | SEC |
| WP-SEC-005 | Secret sourcing and hygiene | Yavuz | F1/H0 | SEC |
| WP-SEC-007 | Oracle access denial at runtime | Yavuz | F1/H0 | SEC |

### 8.M5 M5 — S9–S10 (30 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-GOV-003 | Coverage reports and release acceptance record generation | Yavuz | F1 | GOV |
| WP-EVT-004 | Replay, poison message and DLQ operations | Yavuz | F1 | EVT |
| WP-TWIN-004 | Twin rebuild and catch-up | Asrın | F1 | TWIN |
| WP-OBJ-002 | Artifact lifecycle, retention and quota policy | Yavuz | F1 | OBJ |
| WP-VDATA-002 | Split manifests and leakage protection | Selman | F1 | VDATA |
| WP-VDATA-004 | ModelPackage governance and MLflow promotion | Selman | F1 | VDATA |
| WP-ML-006 | Calibration and uncertainty evaluation | Asrın | F1 | ML |
| WP-RAG-006 | Index rebuild and recovery | Asrın | F1 | RAG |
| WP-SCH-005 | Decision budget, fallback and explicit failure state | Batu | F1 | SCH |
| WP-SCH-007 | Schedule churn and stability metrics | Batu | F1 | SCH |
| WP-AUTO-006 | Workflow history and audit surface | Batu | F1 | AUTO |
| WP-HITL-007 | Break-glass path with mandatory audit | Yavuz | F1 | HITL |
| WP-UI-008 | Epistemic, staleness and failure-state semantics | Asrın | F1 | UI |
| WP-UI-010 | Incident and decision timeline | Asrın | F1 | UI |
| WP-PLAT-004 | Resource profiles and footprint control | Yavuz | F1/A1 | PLAT |
| WP-PLAT-005 | Environment, release and world manifests | Yavuz | F1 | PLAT |
| WP-CICD-004 | Supply chain: pinning, scanning and SBOM | Yavuz | F1/H0 | CICD |
| WP-CICD-005 | Release rollback capability | Yavuz | F1/A1 | CICD |
| WP-CICD-006 | CI isolation for untrusted contributions | Yavuz | F1/H0 | CICD |
| WP-OBS-005 | Redaction and diagnostic bundles | Yavuz | F1/H0 | OBS |
| WP-SEC-006 | Test-auth prohibition in formal environments | Yavuz | F1/H0 | SEC |
| WP-SEC-008 | Security negative suite and external egress audit | Yavuz | F1/H0 | SEC |
| WP-DR-001 | Backup automation and integrity verification | Yavuz | F1/H0 | DR |
| WP-DR-003 | Derived-state rebuild paths | Yavuz | F1 | DR |
| WP-TEST-004 | Integration scenarios AV-SCEN-05…08 | Yavuz | F1 | TEST |
| WP-TEST-005 | Integration scenarios AV-SCEN-09…12 | Batu | F1 | TEST |
| WP-PERF-001 | Benchmark definitions, workload profiles and measurement protocol | Yavuz | F1 | PERF |
| WP-RES-001 | Experiment runner and run manifest binding | Yavuz | R1 | RES |
| WP-RES-002 | Partition, seed and protocol governance | Asrın | R1 | RES |
| WP-RES-006 | Baseline suite across lanes | Asrın | R1 | RES |

### 8.M6 M6 — S11 (17 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-GOV-004 | Change control and freeze-impact tooling | Asrın | F1 | GOV |
| WP-SIM-009 | Simulation realism validation suite (RL-3) | Batu | R1 | SIM |
| WP-VDATA-005 | Vision evaluation portfolio and RQ-4 lane preparation | Selman | R1 | VDATA |
| WP-ML-007 | ML evaluation lanes (M1/M2/M3) for the final campaign | Asrın | R1 | ML |
| WP-RAG-007 | Retrieval ablation lane for RQ-1 | Asrın | R1 | RAG |
| WP-PLAT-007 | Benchmark and demo preflight tooling | Yavuz | F1/H0 | PLAT |
| WP-DR-002 | Restore drills: database and full host | Yavuz | F1/H0 | DR |
| WP-TEST-008 | Flake control and release-gate hygiene | Yavuz | F1/S2 | TEST |
| WP-PERF-004 | Resilience drill execution | Yavuz | F1/H0 | PERF |
| WP-RES-003 | Benchmark run registry and disposition accounting | Yavuz | R1 | RES |
| WP-RES-004 | AnalysisPackage and deterministic result regeneration | Asrın | R1 | RES |
| WP-RES-007 | RQ-1 lane: evidence-grounded RCA evaluation | Asrın | R1 | RES |
| WP-RES-008 | RQ-2 lane: dynamic recovery evaluation | Batu | R1 | RES |
| WP-RES-009 | RQ-3 lane: governed AI-to-action evaluation | Asrın | R1 | RES |
| WP-RES-010 | RQ-4 lane: perception-to-operations evaluation | Selman | R1 | RES |
| WP-RES-011 | Freeze execution for M6 | Asrın | R1 | RES |
| WP-DOC-001 | Engineering documentation set | Yavuz | F1 | DOC |

### 8.M7 M7 — S12 (15 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-CORE-006 | Core and Twin read/command performance profile | Asrın | F1/S2 | CORE |
| WP-EVT-006 | Event spine throughput and delivery characterization | Yavuz | F1/A1 | EVT |
| WP-SIM-008 | Simulator capacity and scale validation | Batu | F1/A1 | SIM |
| WP-VIS-010 | Vision inference performance characterization | Selman | F1/C3 | VIS |
| WP-AI-007 | RCA path performance characterization | Asrın | F1/A1 | AI |
| WP-OBS-006 | Telemetry retention, quota and instrumentation overhead | Yavuz | F1/S2 | OBS |
| WP-DR-004 | Evidence protection and off-host preservation | Yavuz | F1/H0 | DR |
| WP-PERF-002 | Latency and throughput measurement execution | Yavuz | F1/A1 | PERF |
| WP-PERF-003 | Capacity and stress execution | Batu | F1/A1 | PERF |
| WP-PERF-005 | Soak testing and resource behaviour under sustained load | Yavuz | F1/H0 | PERF |
| WP-PERF-006 | Scheduler performance frontier measurement | Batu | F1/A1 | PERF |
| WP-RES-005 | Evidence sealing and bundle assembly | Yavuz | R1 | RES |
| WP-BENCH-001 | Campaign manifest, preflight and lane orchestration | Yavuz | R1 | BENCH |
| WP-BENCH-002 | Final E2E matrix execution (MC-1) | Asrın | R1 | BENCH |
| WP-BENCH-003 | Engineering lanes execution (ENG-A…I) | Yavuz | R1 | BENCH |

### 8.M8 M8 — S13 (10 work packages)

| WP | Title | Owner | Scope | Area |
|---|---|---|---|---|
| WP-UI-011 | Browser E2E harness and compatibility validation | Asrın | F1/S2 | UI |
| WP-UI-012 | Presenter mode integrity | Asrın | F1 | UI |
| WP-PLAT-006 | Onboarding, executable documentation and diagnostics | Yavuz | F1/S2 | PLAT |
| WP-RES-012 | Research claim classification | Asrın | R1 | RES |
| WP-BENCH-004 | Reproduction lanes: clean host, non-owner and public | Yavuz | R1 | BENCH |
| WP-BENCH-005 | Evidence bundle finalization and acceptance reporting | Yavuz | R1 | BENCH |
| WP-DOC-003 | Thesis and portfolio artifact production | Asrın | R1 | DOC |
| WP-DOC-004 | Demo infrastructure and GS-01 rehearsal | Asrın | F1 | DOC |
| WP-DOC-005 | Public release package (v1) | Yavuz | R1 | DOC |
| WP-DOC-006 | Final red-team review execution | Asrın | F1 | DOC |

### 8.X Unscheduled (R2 / S / guard rails) — 5 work packages

| WP | Title | Owner | Scope |
|---|---|---|---|
| WP-R2-001 | R2 retrieval candidates (ColBERT, cross-encoder reranking, alternative embeddings) | Asrın | R2 |
| WP-R2-002 | R2 modelling candidates (local LLM runtime, VLM experiment, advanced causal RCA, RL scheduler, alternative solver formulations) | Asrın | R2 |
| WP-R2-003 | R2 infrastructure candidates (Neo4j, TimescaleDB, Valkey optimization, GPU/distributed simulator) | Yavuz | R2 |
| WP-S-001 | Stretch enhancements register (visualization, mobile UI, multi-node, analytics, extra scenarios) | Asrın | S |
| WP-X-001 | Out-of-scope boundary maintenance | Asrın | S |

## 9. Owner Rollups and Load Analysis

| Owner | #WP owned | F0 | F1 (incl. NFR-driven) | R1 | R2/S | #WP supported as reviewer | #Requirements owned through WPs |
|---|---|---|---|---|---|---|---|
| Asrın | 73 | 12 | 46 | 11 | 4 | 86 | 139 |
| Selman | 17 | 2 | 13 | 2 | 0 | 12 | 23 |
| Batu | 32 | 10 | 20 | 2 | 0 | 32 | 69 |
| Yavuz | 57 | 2 | 46 | 8 | 1 | 49 | 126 |

**Honest load reading.** The distribution is deliberately unequal (00 §13 rejects artificial balance). Asrın owns the semantic centre (Core, Twin, events, AI, RAG, HITL policy, Command Center shell) and Yavuz owns the entire reproducibility spine (CP-3), so both carry more packages than Selman, whose perception domain is deep but narrower. Two consequences must be planned for, not hidden:

- **TEAM-R03 (Asrın as universal bottleneck).** Asrın is the predecessor on the largest number of cross-owner HARD dependencies (05 §17). Mitigation is contract-first delivery: the contract packages (WP-CORE-001, WP-CORE-003, WP-EVT-001/002, WP-TWIN-003, WP-AI-004) must reach CONTRACT_READY ahead of their consumers, and supporting-owner review must be scheduled, not improvised.
- **TEAM-R04 (Yavuz as support queue).** Platform, CI/CD, observability, security, DR, benchmark infrastructure and reproduction lanes are all Yavuz-owned. The S9–S11 window concentrates that load; research lane owners must take their own lane execution (WP-RES-007…010) rather than delegating it.

### 9.1 Asrın — 73 work packages

| WP | Title | Scope | Milestone | Size band |
|---|---|---|---|---|
| WP-GOV-001 | Machine-readable requirement catalog and ID lint | F1 | M0 | L |
| WP-GOV-004 | Change control and freeze-impact tooling | F1 | M6 | S |
| WP-CORE-001 | Canonical manufacturing domain model and core schema | F0 | M1 | L |
| WP-CORE-002 | Manufacturing lifecycle state machine | F1 | M2 | M |
| WP-CORE-003 | Command acceptance: idempotency, revision preconditions, durable outcomes | F1 | M2 | L |
| WP-CORE-004 | Rework, split/merge and temporal genealogy | F1 | M2 | M |
| WP-CORE-005 | Domain events and transactional outbox | F0 | M1 | M |
| WP-CORE-006 | Core and Twin read/command performance profile | F1/S2 | M7 | S |
| WP-CORE-007 | Core database migrations and role separation | F1 | M1 | M |
| WP-CORE-008 | Core ↔ Simulator ↔ Twin integration and acceptance | F0 | M3 | M |
| WP-EVT-001 | Integration Contract Registry and versioning discipline | F0 | M1 | M |
| WP-EVT-002 | Message envelope, correlation and world scoping | F1 | M1 | M |
| WP-EVT-003 | Idempotent consumer framework | F1 | M2 | S |
| WP-EVT-005 | Architecture rules as code (boundaries and ownership) | F1 | M2 | S |
| WP-TWIN-001 | Twin projection engine | F0 | M1 | M |
| WP-TWIN-002 | Epistemic classes, freshness and staleness semantics | F1 | M2 | M |
| WP-TWIN-003 | Twin query API and scheduling snapshot export | F1 | M2 | M |
| WP-TWIN-004 | Twin rebuild and catch-up | F1 | M5 | S |
| WP-TWIN-005 | Counterfactual/what-if stream isolation | F1 | M4 | S |
| WP-TWIN-006 | Effect verification view and Core/Twin consistency | F0 | M3 | S |
| WP-ML-001 | Feature and label pipeline from operational history | F1 | M4 | M |
| WP-ML-002 | M1 — equipment risk model | F1 | M4 | M |
| WP-ML-003 | M2 — cycle-time / tardiness risk model | F1 | M4 | M |
| WP-ML-004 | M3 — pre-inspection quality risk model | F1 | M4 | S |
| WP-ML-005 | Common prediction contract and publication | F1 | M4 | S |
| WP-ML-006 | Calibration and uncertainty evaluation | F1 | M5 | S |
| WP-ML-007 | ML evaluation lanes (M1/M2/M3) for the final campaign | R1 | M6 | S |
| WP-RAG-001 | Documentary corpus governance and ingestion | F1 | M4 | M |
| WP-RAG-002 | Retrieval profiles: sparse, dense and hybrid | F1 | M4 | M |
| WP-RAG-003 | Citation-bearing provenance in retrieval and RCA | F1 | M4 | S |
| WP-RAG-004 | Rights filtering and prompt-injection resistance | F1 | M4 | M |
| WP-RAG-005 | Evidence typing: documentary vs operational | F1 | M4 | S |
| WP-RAG-006 | Index rebuild and recovery | F1 | M5 | S |
| WP-RAG-007 | Retrieval ablation lane for RQ-1 | R1 | M6 | S |
| WP-AI-001 | Deterministic orchestrator and execution budgets | F0 | M3 | M |
| WP-AI-002 | Typed tool registry and authority-tagged tool access | F1 | M3 | M |
| WP-AI-003 | Structured evidence-grounded RCA output | F1 | M3 | M |
| WP-AI-004 | Action proposal and context binding | F1 | M3 | S |
| WP-AI-005 | Provider abstraction, behavior bundle and deterministic baseline | F1 | M4 | M |
| WP-AI-006 | AI authority boundary and negative suite | F0 | M3 | M |
| WP-AI-007 | RCA path performance characterization | F1/A1 | M7 | S |
| WP-HITL-001 | Authority policy engine (L0–L4) | F0 | M3 | S |
| WP-HITL-002 | Approval binding to exact proposal/plan revision and world | F1 | M3 | S |
| WP-HITL-003 | Expiry, replay and staleness rejection | F1 | M3 | S |
| WP-HITL-005 | Approval record, audit trail and protected-action coverage | F1 | M4 | S |
| WP-HITL-006 | Dual approval for highest-risk actions | F1 | M4 | S |
| WP-UI-001 | Command Center shell and BFF contract | F0 | M1 | M |
| WP-UI-002 | manufacturing facility state and operational views | F1 | M2 | S |
| WP-UI-004 | Incident investigation workspace (RCA) | F1 | M4 | S |
| WP-UI-006 | Approval Center | F0 | M3 | M |
| WP-UI-008 | Epistemic, staleness and failure-state semantics | F1 | M5 | M |
| WP-UI-010 | Incident and decision timeline | F1 | M5 | S |
| WP-UI-011 | Browser E2E harness and compatibility validation | F1/S2 | M8 | S |
| WP-UI-012 | Presenter mode integrity | F1 | M8 | S |
| WP-SEC-003 | Backend authorization enforcement | F1/H0 | M3 | S |
| WP-TEST-002 | Contract and schema test suites | F1 | M2 | S |
| WP-TEST-003 | Integration scenarios AV-SCEN-01…04 | F0 | M3 | M |
| WP-RES-002 | Partition, seed and protocol governance | R1 | M5 | M |
| WP-RES-004 | AnalysisPackage and deterministic result regeneration | R1 | M6 | S |
| WP-RES-006 | Baseline suite across lanes | R1 | M5 | M |
| WP-RES-007 | RQ-1 lane: evidence-grounded RCA evaluation | R1 | M6 | M |
| WP-RES-009 | RQ-3 lane: governed AI-to-action evaluation | R1 | M6 | M |
| WP-RES-011 | Freeze execution for M6 | R1 | M6 | S |
| WP-RES-012 | Research claim classification | R1 | M8 | S |
| WP-BENCH-002 | Final E2E matrix execution (MC-1) | R1 | M7 | S |
| WP-DOC-002 | ADR backfill and decision index | F1 | M2 | S |
| WP-DOC-003 | Thesis and portfolio artifact production | R1 | M8 | S |
| WP-DOC-004 | Demo infrastructure and GS-01 rehearsal | F1 | M8 | M |
| WP-DOC-006 | Final red-team review execution | F1 | M8 | S |
| WP-R2-001 | R2 retrieval candidates (ColBERT, cross-encoder reranking, alternative embeddings) | R2 | — | S |
| WP-R2-002 | R2 modelling candidates (local LLM runtime, VLM experiment, advanced causal RCA, RL scheduler, alternative solver formulations) | R2 | — | S |
| WP-S-001 | Stretch enhancements register (visualization, mobile UI, multi-node, analytics, extra scenarios) | S | — | S |
| WP-X-001 | Out-of-scope boundary maintenance | S | — | S |

### 9.2 Selman — 17 work packages

| WP | Title | Scope | Milestone | Size band |
|---|---|---|---|---|
| WP-VIS-001 | Inspection pipeline and serving path | F0 | M2 | M |
| WP-VIS-002 | Defect classification and localization models | F1 | M4 | M |
| WP-VIS-003 | Segmentation and anomaly detection | F1 | M4 | M |
| WP-VIS-004 | OOD / UNKNOWN handling and threshold policy | F1 | M4 | M |
| WP-VIS-005 | Provenance, confidence and calibration in Vision outputs | F1 | M4 | S |
| WP-VIS-006 | SerializedComponent spatial pattern and cluster analysis | F1 | M4 | S |
| WP-VIS-007 | Vision-to-loop integration (perception drives RCA) | F0 | M3 | S |
| WP-VIS-008 | CPU smoke inference path | F1 | M2 | S |
| WP-VIS-009 | Oracle-taint guard for Vision inputs | F1 | M3 | S |
| WP-VIS-010 | Vision inference performance characterization | F1/C3 | M7 | S |
| WP-VDATA-001 | Dataset governance, rights and provenance | F1 | M4 | S |
| WP-VDATA-002 | Split manifests and leakage protection | F1 | M5 | M |
| WP-VDATA-003 | Synthetic Vision data generator | F1 | M4 | S |
| WP-VDATA-004 | ModelPackage governance and MLflow promotion | F1 | M5 | M |
| WP-VDATA-005 | Vision evaluation portfolio and RQ-4 lane preparation | R1 | M6 | M |
| WP-UI-003 | Inspection viewer with overlays | F1 | M4 | S |
| WP-RES-010 | RQ-4 lane: perception-to-operations evaluation | R1 | M6 | M |

### 9.3 Batu — 32 work packages

| WP | Title | Scope | Milestone | Size band |
|---|---|---|---|---|
| WP-SIM-001 | Deterministic DES kernel | F0 | M1 | M |
| WP-SIM-002 | Determinism, replay and event-hash equivalence | F1 | M2 | M |
| WP-SIM-003 | Operational semantics: reentrant routing, queues, failures, maintenance, rework | F0 | M2 | L |
| WP-SIM-004 | Snapshot, fork and world isolation | F1 | M4 | M |
| WP-SIM-005 | Oracle isolation and evaluator-only data plane | F0 | M3 | M |
| WP-SIM-006 | External dispatch decision interface and operational telemetry | F0 | M2 | M |
| WP-SIM-007 | Scenario versioning and synthetic operational history | F1 | M4 | M |
| WP-SIM-008 | Simulator capacity and scale validation | F1/A1 | M7 | S |
| WP-SIM-009 | Simulation realism validation suite (RL-3) | R1 | M6 | M |
| WP-SCH-001 | Dispatch baselines and scheduling instance model | F1 | M2 | S |
| WP-SCH-002 | Snapshot consumption and recovery plan contract | F0 | M3 | M |
| WP-SCH-003 | CP-SAT model and hard constraints | F1 | M4 | M |
| WP-SCH-004 | Rolling horizon and event-triggered rescheduling | F1 | M4 | M |
| WP-SCH-005 | Decision budget, fallback and explicit failure state | F1 | M5 | S |
| WP-SCH-006 | Counterfactual schedule evaluation on forked worlds | F1 | M4 | S |
| WP-SCH-007 | Schedule churn and stability metrics | F1 | M5 | S |
| WP-VALID-001 | Independent schedule validator | F0 | M3 | M |
| WP-VALID-002 | Execution eligibility gate and AI-origin plan routing | F1 | M3 | S |
| WP-AUTO-001 | Durable workflow bundle and approval wait | F0 | M3 | M |
| WP-AUTO-002 | Idempotency and restart safety for protected effects | F1 | M4 | M |
| WP-AUTO-003 | Pre-execution revalidation and command identity | F1 | M3 | S |
| WP-AUTO-004 | ActionCatalog and authorization gate | F1 | M3 | S |
| WP-AUTO-005 | Outcome model and effect verification | F0 | M3 | M |
| WP-AUTO-006 | Workflow history and audit surface | F1 | M5 | S |
| WP-AUTO-007 | GS-01 recovery workflow and closed-loop timing | F0 | M4 | S |
| WP-UI-005 | Planning and validation views | F1 | M4 | S |
| WP-UI-007 | Workflow progress and verification view | F1 | M4 | S |
| WP-TEST-005 | Integration scenarios AV-SCEN-09…12 | F1 | M5 | M |
| WP-TEST-006 | E2E-01 checkpoint execution | F0 | M3 | M |
| WP-PERF-003 | Capacity and stress execution | F1/A1 | M7 | S |
| WP-PERF-006 | Scheduler performance frontier measurement | F1/A1 | M7 | S |
| WP-RES-008 | RQ-2 lane: dynamic recovery evaluation | R1 | M6 | M |

### 9.4 Yavuz — 57 work packages

| WP | Title | Scope | Milestone | Size band |
|---|---|---|---|---|
| WP-GOV-002 | Trace registry, edges and trace linter | F1 | M2 | L |
| WP-GOV-003 | Coverage reports and release acceptance record generation | F1 | M5 | M |
| WP-EVT-004 | Replay, poison message and DLQ operations | F1 | M5 | S |
| WP-EVT-006 | Event spine throughput and delivery characterization | F1/A1 | M7 | S |
| WP-OBJ-001 | Artifact service: ArtifactRef contract and object storage integration | F1 | M2 | M |
| WP-OBJ-002 | Artifact lifecycle, retention and quota policy | F1 | M5 | S |
| WP-HITL-004 | Identity-bound approvals | F1 | M3 | S |
| WP-HITL-007 | Break-glass path with mandatory audit | F1 | M5 | S |
| WP-UI-009 | System health and environment diagnostics view | F1 | M4 | S |
| WP-PLAT-001 | Compose profiles and mandatory runtime composition | F0 | M1 | M |
| WP-PLAT-002 | mfgctl developer and operator CLI | F1 | M1 | M |
| WP-PLAT-003 | Runtime service bring-up on the shared host | F1 | M2 | M |
| WP-PLAT-004 | Resource profiles and footprint control | F1/A1 | M5 | M |
| WP-PLAT-005 | Environment, release and world manifests | F1 | M5 | M |
| WP-PLAT-006 | Onboarding, executable documentation and diagnostics | F1/S2 | M8 | M |
| WP-PLAT-007 | Benchmark and demo preflight tooling | F1/H0 | M6 | S |
| WP-CICD-001 | CI pipeline and required gates | F1 | M0 | M |
| WP-CICD-002 | CD to INTEGRATION with immutable artifacts | F0 | M1 | M |
| WP-CICD-003 | Automated migration execution in the deployment path | F1 | M2 | S |
| WP-CICD-004 | Supply chain: pinning, scanning and SBOM | F1/H0 | M5 | M |
| WP-CICD-005 | Release rollback capability | F1/A1 | M5 | S |
| WP-CICD-006 | CI isolation for untrusted contributions | F1/H0 | M5 | S |
| WP-OBS-001 | Telemetry pipeline (OTel → Collector → OpenObserve) | F1 | M1 | M |
| WP-OBS-002 | Distributed trace propagation across the closed loop | F1 | M3 | S |
| WP-OBS-003 | Health, readiness and degradation states | F1 | M4 | S |
| WP-OBS-004 | Audit store separation from telemetry | F1/H0 | M4 | S |
| WP-OBS-005 | Redaction and diagnostic bundles | F1/H0 | M5 | S |
| WP-OBS-006 | Telemetry retention, quota and instrumentation overhead | F1/S2 | M7 | S |
| WP-SEC-001 | Keycloak realm, clients and interactive authentication | F1 | M3 | M |
| WP-SEC-002 | Service identities and least-privilege credentials | F1/H0 | M4 | M |
| WP-SEC-004 | AI-reachable capability surface restriction | F1/H0 | M4 | S |
| WP-SEC-005 | Secret sourcing and hygiene | F1/H0 | M4 | M |
| WP-SEC-006 | Test-auth prohibition in formal environments | F1/H0 | M5 | S |
| WP-SEC-007 | Oracle access denial at runtime | F1/H0 | M4 | S |
| WP-SEC-008 | Security negative suite and external egress audit | F1/H0 | M5 | S |
| WP-DR-001 | Backup automation and integrity verification | F1/H0 | M5 | M |
| WP-DR-002 | Restore drills: database and full host | F1/H0 | M6 | M |
| WP-DR-003 | Derived-state rebuild paths | F1 | M5 | S |
| WP-DR-004 | Evidence protection and off-host preservation | F1/H0 | M7 | S |
| WP-TEST-001 | Test strategy, tiers and boundary-mode policy | F1 | M1 | M |
| WP-TEST-004 | Integration scenarios AV-SCEN-05…08 | F1 | M5 | M |
| WP-TEST-007 | Architecture rules and trace validation in CI | F1 | M2 | S |
| WP-TEST-008 | Flake control and release-gate hygiene | F1/S2 | M6 | S |
| WP-PERF-001 | Benchmark definitions, workload profiles and measurement protocol | F1 | M5 | M |
| WP-PERF-002 | Latency and throughput measurement execution | F1/A1 | M7 | M |
| WP-PERF-004 | Resilience drill execution | F1/H0 | M6 | S |
| WP-PERF-005 | Soak testing and resource behaviour under sustained load | F1/H0 | M7 | S |
| WP-RES-001 | Experiment runner and run manifest binding | R1 | M5 | M |
| WP-RES-003 | Benchmark run registry and disposition accounting | R1 | M6 | S |
| WP-RES-005 | Evidence sealing and bundle assembly | R1 | M7 | S |
| WP-BENCH-001 | Campaign manifest, preflight and lane orchestration | R1 | M7 | S |
| WP-BENCH-003 | Engineering lanes execution (ENG-A…I) | R1 | M7 | S |
| WP-BENCH-004 | Reproduction lanes: clean host, non-owner and public | R1 | M8 | M |
| WP-BENCH-005 | Evidence bundle finalization and acceptance reporting | R1 | M8 | S |
| WP-DOC-001 | Engineering documentation set | F1 | M6 | S |
| WP-DOC-005 | Public release package (v1) | R1 | M8 | S |
| WP-R2-003 | R2 infrastructure candidates (Neo4j, TimescaleDB, Valkey optimization, GPU/distributed simulator) | R2 | — | S |

## 10. Integration, Failure-Path, Observability and Acceptance Work Visibility

Guide §13 requires that these categories exist as separate work items rather than being implied inside "component implementation". The matrix shows where each category lives per capability family.

| Capability family | Component implementation | Contract implementation | Integration | Failure-path verification | Observability | Acceptance / evidence |
|---|---|---|---|---|---|---|
| Manufacturing Core | WP-CORE-001, WP-CORE-002, WP-CORE-003 | WP-CORE-005, WP-EVT-001 | WP-CORE-008 | WP-CORE-003 (stale/conflict), WP-TEST-003 | WP-OBS-001, WP-OBS-002 | WP-CORE-008, WP-TEST-003 |
| Event spine | WP-EVT-002, WP-EVT-003 | WP-EVT-001 | WP-EVT-006 | WP-EVT-004, WP-TEST-004 | WP-OBS-002 | WP-TEST-002, WP-TEST-004 |
| Digital Twin | WP-TWIN-001, WP-TWIN-002 | WP-TWIN-003 | WP-CORE-008 | WP-TWIN-004, WP-TEST-004 | WP-OBS-001 | WP-TWIN-006, WP-TEST-003 |
| Simulator | WP-SIM-001, WP-SIM-003 | WP-SIM-006 | WP-CORE-008 | WP-SIM-004, WP-TEST-005 | WP-OBS-001 | WP-SIM-008, WP-TEST-005 |
| Vision | WP-VIS-002, WP-VIS-003, WP-VIS-004 | WP-VIS-001, WP-VIS-005 | WP-VIS-007 | WP-VIS-009, WP-VIS-008 | WP-OBS-001 | WP-VDATA-005, WP-TEST-003 |
| Predictive ML | WP-ML-002, WP-ML-003, WP-ML-004 | WP-ML-005 | WP-ML-005 | WP-ML-001 (leakage guard) | WP-OBS-001 | WP-ML-007 |
| RAG | WP-RAG-002, WP-RAG-003 | WP-RAG-001, WP-RAG-005 | WP-RAG-002 | WP-RAG-004, WP-RAG-006 | WP-OBS-001 | WP-RAG-007 |
| AI / RCA | WP-AI-001, WP-AI-003 | WP-AI-002, WP-AI-004 | WP-VIS-007, WP-TEST-003 | WP-AI-006, WP-SEC-004 | WP-OBS-002 | WP-RES-007, WP-TEST-003 |
| Scheduler | WP-SCH-003, WP-SCH-004 | WP-SCH-002 | WP-SCH-004, WP-TEST-003 | WP-SCH-005, WP-VALID-002 | WP-OBS-001 | WP-PERF-006, WP-RES-008 |
| Schedule validation | WP-VALID-001 | WP-SCH-002 | WP-VALID-002 | WP-VALID-001 (infeasible corpus) | WP-OBS-003 | WP-TEST-003 |
| Automation | WP-AUTO-001, WP-AUTO-007 | WP-AUTO-004 | WP-AUTO-005 | WP-AUTO-002, WP-AUTO-003, WP-TEST-004 | WP-OBS-002, WP-AUTO-006 | WP-TEST-003, WP-BENCH-002 |
| HITL / authority | WP-HITL-001, WP-HITL-002 | WP-HITL-004 | WP-HITL-005 | WP-HITL-003, WP-SEC-003 | WP-OBS-004 | WP-RES-009, WP-TEST-003 |
| Command Center | WP-UI-002…WP-UI-007 | WP-UI-001 | WP-UI-006 | WP-UI-008 | WP-UI-009 | WP-UI-011, WP-TEST-006 |
| Platform / runtime | WP-PLAT-001, WP-PLAT-002 | WP-PLAT-003 | WP-CICD-002 | WP-PERF-004, WP-DR-002 | WP-OBS-001 | WP-BENCH-004 |
| Security | WP-SEC-002, WP-SEC-005 | WP-SEC-001 | WP-SEC-003 | WP-SEC-006, WP-SEC-007, WP-SEC-008 | WP-OBS-004, WP-OBS-005 | WP-SEC-008, WP-BENCH-003 |
| Research infrastructure | WP-RES-001, WP-RES-004 | WP-RES-002 | WP-BENCH-001 | WP-RES-003 (disposition accounting) | WP-RES-003 | WP-BENCH-005 |

## 11. Dependency Alignment with 05

Every work package declares the 05 readiness node it advances. The table lists, per WP, the HARD dependency edges that must be satisfied before it can integrate or exit its milestone. A WP whose gating edges are unsatisfied is not READY (DOR-WP-03).

| WP | Readiness node | #HARD gates | Gating edges (first 5) |
|---|---|---|---|
| WP-GOV-003 | DN-PLAT-RUNNER | 2 | DEP-114 (DN-PLAT-FAILVAL, MILESTONE_EXIT, need-by M5 (S10)), DEP-115 (DN-PLAT-CD, INTEGRATION, need-by M5 (S10)) |
| WP-CORE-002 | DN-CORE-TRANSITIONS | 1 | DEP-020 (DN-CORE-LIFECYCLE, START, need-by S2–S3) |
| WP-CORE-003 | DN-CORE-CMDEXEC | 2 | DEP-027 (DN-CORE-CMDCON, START, need-by S2–S3), DEP-028 (DN-CORE-TRANSITIONS, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-CORE-004 | DN-CORE-GENEALOGY | 1 | DEP-029 (DN-CORE-LIFECYCLE, INTEGRATION, need-by M2 (S4)) |
| WP-CORE-005 | DN-CORE-OUTBOX | 1 | DEP-022 (DN-CORE-LIFECYCLE, INTEGRATION, need-by M1 (S2)) |
| WP-CORE-006 | DN-CORE-CMDEXEC | 2 | DEP-027 (DN-CORE-CMDCON, START, need-by S2–S3), DEP-028 (DN-CORE-TRANSITIONS, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-CORE-007 | DN-RT-PG | 2 | DEP-006 (DN-PLAT-COMPOSE, START, need-by M0), DEP-007 (DN-PLAT-INTEG, INTEGRATION, need-by M1 (S2)) |
| WP-CORE-008 | DN-SIM-COREINT | 3 | DEP-040 (DN-SIM-OPSEM, INTEGRATION, need-by M2 (S4)), DEP-041 (DN-CORE-CMDEXEC, INTEGRATION, need-by M2 (S4)), DEP-042 (DN-EVT-SPINE, INTEGRATION, need-by M2 (S4)) |
| WP-EVT-001 | DN-EVT-CONTRACTS | 1 | DEP-021 (DN-CORE-CONTRACTS, START, need-by S1–S2) |
| WP-EVT-002 | DN-EVT-CONTRACTS | 1 | DEP-021 (DN-CORE-CONTRACTS, START, need-by S1–S2) |
| WP-EVT-003 | DN-EVT-SPINE | 3 | DEP-023 (DN-EVT-CONTRACTS, INTEGRATION, need-by M1 (S2)), DEP-024 (DN-CORE-OUTBOX, INTEGRATION, need-by M1 (S2)), DEP-025 (DN-RT-NATS, INTEGRATION, need-by M1 (S2)) |
| WP-EVT-004 | DN-EVT-SPINE | 3 | DEP-023 (DN-EVT-CONTRACTS, INTEGRATION, need-by M1 (S2)), DEP-024 (DN-CORE-OUTBOX, INTEGRATION, need-by M1 (S2)), DEP-025 (DN-RT-NATS, INTEGRATION, need-by M1 (S2)) |
| WP-EVT-005 | DN-EVT-CONTRACTS | 1 | DEP-021 (DN-CORE-CONTRACTS, START, need-by S1–S2) |
| WP-EVT-006 | DN-EVT-SPINE | 3 | DEP-023 (DN-EVT-CONTRACTS, INTEGRATION, need-by M1 (S2)), DEP-024 (DN-CORE-OUTBOX, INTEGRATION, need-by M1 (S2)), DEP-025 (DN-RT-NATS, INTEGRATION, need-by M1 (S2)) |
| WP-TWIN-001 | DN-TWIN-SKELETON | 3 | DEP-031 (DN-EVT-CONTRACTS, START, need-by S2), DEP-032 (DN-EVT-SPINE, INTEGRATION, need-by M1 (S2)), DEP-033 (DN-RT-PG, INTEGRATION, need-by M1 (S2)) |
| WP-TWIN-002 | DN-TWIN-PROJ | 2 | DEP-034 (DN-TWIN-SKELETON, START, need-by S3), DEP-035 (DN-SIM-COREINT, MILESTONE_EXIT, need-by M2 (S4)) |
| WP-TWIN-003 | DN-CORE-SNAPCON | 1 | DEP-030 (DN-CORE-CONTRACTS, START, need-by S3) |
| WP-TWIN-004 | DN-TWIN-PROJ | 2 | DEP-034 (DN-TWIN-SKELETON, START, need-by S3), DEP-035 (DN-SIM-COREINT, MILESTONE_EXIT, need-by M2 (S4)) |
| WP-TWIN-005 | DN-TWIN-PROJ | 2 | DEP-034 (DN-TWIN-SKELETON, START, need-by S3), DEP-035 (DN-SIM-COREINT, MILESTONE_EXIT, need-by M2 (S4)) |
| WP-TWIN-006 | DN-TWIN-VERIFY | 1 | DEP-036 (DN-TWIN-PROJ, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-SIM-003 | DN-SIM-OPSEM | 3 | DEP-037 (DN-SIM-KERNEL, START, need-by S2), DEP-038 (DN-CORE-CONTRACTS, START, need-by S2), DEP-039 (DN-CORE-TRANSITIONS, MILESTONE_EXIT, need-by M2 (S4)) |
| WP-SIM-004 | DN-SIM-SNAPFORK | 1 | DEP-044 (DN-SIM-KERNEL, START, need-by S3) |
| WP-SIM-005 | DN-SIM-ORACLE | 2 | DEP-046 (DN-SIM-KERNEL, START, need-by S3), DEP-047 (DN-SEC-BASE, MILESTONE_EXIT, need-by E2E-01 (end S5)) |
| WP-SIM-006 | DN-SIM-DISPIF | 1 | DEP-043 (DN-SIM-KERNEL, START, need-by S2) |
| WP-SIM-007 | DN-SIM-SYNTH | 1 | DEP-048 (DN-SIM-OPSEM, START, need-by S3–S4) |
| WP-SIM-008 | DN-SIM-OPSEM | 3 | DEP-037 (DN-SIM-KERNEL, START, need-by S2), DEP-038 (DN-CORE-CONTRACTS, START, need-by S2), DEP-039 (DN-CORE-TRANSITIONS, MILESTONE_EXIT, need-by M2 (S4)) |
| WP-SIM-009 | DN-SIM-REALISM | 1 | DEP-049 (DN-SIM-OPSEM, FREEZE, need-by M5→M6) |
| WP-OBJ-001 | DN-RT-OBJ | 1 | DEP-009 (DN-PLAT-INTEG, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-OBJ-002 | DN-RT-OBJ | 1 | DEP-009 (DN-PLAT-INTEG, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-VIS-001 | DN-VIS-SERVING | 3 | DEP-057 (DN-VIS-ARTCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-VIS-002 | DN-VIS-MODELS | 2 | DEP-053 (DN-VIS-BASELINES, MILESTONE_EXIT, need-by M4 (S8)), DEP-055 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-VIS-003 | DN-VIS-MODELS | 2 | DEP-053 (DN-VIS-BASELINES, MILESTONE_EXIT, need-by M4 (S8)), DEP-055 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-VIS-004 | DN-VIS-OOD | 1 | DEP-054 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-VIS-005 | DN-VIS-SERVING | 3 | DEP-057 (DN-VIS-ARTCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-VIS-006 | DN-VIS-OOD | 1 | DEP-054 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-VIS-007 | DN-VIS-SERVING | 3 | DEP-057 (DN-VIS-ARTCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-VIS-008 | DN-VIS-SERVING | 3 | DEP-057 (DN-VIS-ARTCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-VIS-009 | DN-VIS-SERVING | 3 | DEP-057 (DN-VIS-ARTCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-058 (DN-RT-OBJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-060 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-VIS-010 | DN-VIS-MODELS | 2 | DEP-053 (DN-VIS-BASELINES, MILESTONE_EXIT, need-by M4 (S8)), DEP-055 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-VDATA-002 | DN-VIS-SPLIT | 1 | DEP-051 (DN-VIS-SYNTH, START, need-by S2–S3) |
| WP-VDATA-004 | DN-RT-MLFLOW | 1 | DEP-014 (DN-PLAT-INTEG, MILESTONE_EXIT, need-by M4/M5) |
| WP-VDATA-005 | DN-VIS-OOD | 1 | DEP-054 (DN-VIS-MODELS, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-ML-001 | DN-SIM-SYNTH | 1 | DEP-048 (DN-SIM-OPSEM, START, need-by S3–S4) |
| WP-ML-002 | DN-ML | 2 | DEP-074 (DN-SIM-SYNTH, MILESTONE_EXIT, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-ML-003 | DN-ML | 2 | DEP-074 (DN-SIM-SYNTH, MILESTONE_EXIT, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-ML-004 | DN-ML | 2 | DEP-074 (DN-SIM-SYNTH, MILESTONE_EXIT, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-ML-005 | DN-ML | 2 | DEP-074 (DN-SIM-SYNTH, MILESTONE_EXIT, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-ML-006 | DN-ML | 2 | DEP-074 (DN-SIM-SYNTH, MILESTONE_EXIT, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-ML-007 | DN-ML | 2 | DEP-074 (DN-SIM-SYNTH, MILESTONE_EXIT, need-by M4 (S8)), DEP-075 (DN-RT-MLFLOW, MILESTONE_EXIT, need-by M4/M5) |
| WP-RAG-002 | DN-RAG | 2 | DEP-070 (DN-RAG-CORPUS, START, need-by S3–S4), DEP-071 (DN-RT-QDRANT, INTEGRATION, need-by M4 (S8)) |
| WP-RAG-003 | DN-RAG | 2 | DEP-070 (DN-RAG-CORPUS, START, need-by S3–S4), DEP-071 (DN-RT-QDRANT, INTEGRATION, need-by M4 (S8)) |
| WP-RAG-004 | DN-RAG | 2 | DEP-070 (DN-RAG-CORPUS, START, need-by S3–S4), DEP-071 (DN-RT-QDRANT, INTEGRATION, need-by M4 (S8)) |
| WP-RAG-005 | DN-RAG | 2 | DEP-070 (DN-RAG-CORPUS, START, need-by S3–S4), DEP-071 (DN-RT-QDRANT, INTEGRATION, need-by M4 (S8)) |
| WP-RAG-006 | DN-RT-QDRANT | 1 | DEP-013 (DN-PLAT-INTEG, INTEGRATION, need-by M4 (S8)) |
| WP-RAG-007 | DN-RAG | 2 | DEP-070 (DN-RAG-CORPUS, START, need-by S3–S4), DEP-071 (DN-RT-QDRANT, INTEGRATION, need-by M4 (S8)) |
| WP-AI-001 | DN-AI-ORCH | 1 | DEP-064 (DN-AI-TOOLCON, START, need-by S2–S3) |
| WP-AI-003 | DN-AI-RCA | 7 | DEP-065 (DN-VIS-OBSCON, START, need-by E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH, START, need-by S4), DEP-067 (DN-TWIN-PROJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING, MILESTONE_EXIT, need-by M3 (S6)), DEP-069 (DN-CORE-GENEALOGY, MILESTONE_EXIT, need-by M4 (full RQ-1 RCA config)) … |
| WP-AI-004 | DN-AI-ACTCON | 1 | DEP-076 (DN-HITL-POLICY, START, need-by S3–S4) |
| WP-AI-006 | DN-AI-RCA | 7 | DEP-065 (DN-VIS-OBSCON, START, need-by E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH, START, need-by S4), DEP-067 (DN-TWIN-PROJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING, MILESTONE_EXIT, need-by M3 (S6)), DEP-069 (DN-CORE-GENEALOGY, MILESTONE_EXIT, need-by M4 (full RQ-1 RCA config)) … |
| WP-AI-007 | DN-AI-RCA | 7 | DEP-065 (DN-VIS-OBSCON, START, need-by E2E-01 readiness (end S4)), DEP-066 (DN-AI-ORCH, START, need-by S4), DEP-067 (DN-TWIN-PROJ, INTEGRATION, need-by E2E-01 (end S5)), DEP-068 (DN-VIS-SERVING, MILESTONE_EXIT, need-by M3 (S6)), DEP-069 (DN-CORE-GENEALOGY, MILESTONE_EXIT, need-by M4 (full RQ-1 RCA config)) … |
| WP-SCH-002 | DN-SCH-PLANCON | 2 | DEP-083 (DN-SCH-DYN, INTEGRATION, need-by E2E-01 (end S5)), DEP-084 (DN-SCH-VALID, INTEGRATION, need-by E2E-01 (end S5)) |
| WP-SCH-004 | DN-SCH-DYN | 6 | DEP-078 (DN-SCH-HEUR, START, need-by S3), DEP-079 (DN-CORE-SNAPCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, INTEGRATION, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE, MILESTONE_EXIT, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT, MILESTONE_EXIT, need-by M4 (S8)) … |
| WP-SCH-005 | DN-SCH-DYN | 6 | DEP-078 (DN-SCH-HEUR, START, need-by S3), DEP-079 (DN-CORE-SNAPCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, INTEGRATION, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE, MILESTONE_EXIT, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT, MILESTONE_EXIT, need-by M4 (S8)) … |
| WP-SCH-006 | DN-SCH-CF | 1 | DEP-087 (DN-SIM-SNAPFORK, INTEGRATION, need-by M4 (S8)) |
| WP-SCH-007 | DN-SCH-DYN | 6 | DEP-078 (DN-SCH-HEUR, START, need-by S3), DEP-079 (DN-CORE-SNAPCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, INTEGRATION, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE, MILESTONE_EXIT, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT, MILESTONE_EXIT, need-by M4 (S8)) … |
| WP-VALID-001 | DN-SCH-VALID | 1 | DEP-082 (DN-CORE-TRANSITIONS, INTEGRATION, need-by E2E-01 (end S5)) |
| WP-VALID-002 | DN-SCH-VALID | 1 | DEP-082 (DN-CORE-TRANSITIONS, INTEGRATION, need-by E2E-01 (end S5)) |
| WP-AUTO-001 | DN-AUTO-DURABLE | 2 | DEP-094 (DN-AUTO-DESIGN, START, need-by S3), DEP-095 (DN-RT-TEMPORAL, INTEGRATION, need-by E2E-01 formal run (end S5)) |
| WP-AUTO-002 | DN-AUTO-DURABLE | 2 | DEP-094 (DN-AUTO-DESIGN, START, need-by S3), DEP-095 (DN-RT-TEMPORAL, INTEGRATION, need-by E2E-01 formal run (end S5)) |
| WP-AUTO-003 | DN-AUTO-EXEC | 6 | DEP-096 (DN-AI-ACTCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-097 (DN-CORE-CMDCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-098 (DN-CORE-CMDEXEC, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-099 (DN-HITL-APPROVAL, INTEGRATION, need-by E2E-01 (end S5)), DEP-100 (DN-AUTO-DURABLE, INTEGRATION, need-by E2E-01 (end S5)) … |
| WP-AUTO-004 | DN-AI-ACTCON | 1 | DEP-076 (DN-HITL-POLICY, START, need-by S3–S4) |
| WP-AUTO-005 | DN-AUTO-VERIFY | 2 | DEP-102 (DN-AUTO-EXEC, INTEGRATION, need-by E2E-01 (end S5)), DEP-103 (DN-TWIN-VERIFY, INTEGRATION, need-by E2E-01 (end S5)) |
| WP-AUTO-006 | DN-AUTO-DURABLE | 2 | DEP-094 (DN-AUTO-DESIGN, START, need-by S3), DEP-095 (DN-RT-TEMPORAL, INTEGRATION, need-by E2E-01 formal run (end S5)) |
| WP-AUTO-007 | DN-AUTO-EXEC | 6 | DEP-096 (DN-AI-ACTCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-097 (DN-CORE-CMDCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-098 (DN-CORE-CMDEXEC, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-099 (DN-HITL-APPROVAL, INTEGRATION, need-by E2E-01 (end S5)), DEP-100 (DN-AUTO-DURABLE, INTEGRATION, need-by E2E-01 (end S5)) … |
| WP-HITL-002 | DN-HITL-APPROVAL | 4 | DEP-090 (DN-RT-IDP, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, INTEGRATION, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, MILESTONE_EXIT, need-by E2E-01 (end S5)) |
| WP-HITL-003 | DN-HITL-APPROVAL | 4 | DEP-090 (DN-RT-IDP, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, INTEGRATION, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, MILESTONE_EXIT, need-by E2E-01 (end S5)) |
| WP-HITL-004 | DN-RT-IDP | 1 | DEP-010 (DN-PLAT-INTEG, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-HITL-005 | DN-HITL-APPROVAL | 4 | DEP-090 (DN-RT-IDP, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, INTEGRATION, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, MILESTONE_EXIT, need-by E2E-01 (end S5)) |
| WP-HITL-006 | DN-HITL-APPROVAL | 4 | DEP-090 (DN-RT-IDP, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, INTEGRATION, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, MILESTONE_EXIT, need-by E2E-01 (end S5)) |
| WP-HITL-007 | DN-HITL-APPROVAL | 4 | DEP-090 (DN-RT-IDP, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, INTEGRATION, need-by E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, MILESTONE_EXIT, need-by E2E-01 (end S5)) |
| WP-UI-002 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-003 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-004 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-005 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-006 | DN-UI-APPROVAL | 2 | DEP-107 (DN-UI-SHELL, START, need-by S4), DEP-108 (DN-RT-IDP, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-UI-007 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-008 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-009 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-010 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-011 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-UI-012 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-PLAT-001 | DN-PLAT-COMPOSE | 1 | DEP-003 (DN-PLAT-TOOLING, START, need-by M0 (S1)) |
| WP-PLAT-002 | DN-PLAT-TOOLING | 1 | DEP-001 (DN-PLAT-REPO, START, need-by M0 (S1)) |
| WP-PLAT-003 | DN-PLAT-INTEG | 1 | DEP-004 (DN-PLAT-COMPOSE, MILESTONE_EXIT, need-by M0 (S1)) |
| WP-PLAT-004 | DN-PLAT-INTEG | 1 | DEP-004 (DN-PLAT-COMPOSE, MILESTONE_EXIT, need-by M0 (S1)) |
| WP-PLAT-005 | DN-ART-RELEASE | 1 | DEP-116 (DN-PLAT-RUNNER, FREEZE, need-by M6 (S11)) |
| WP-PLAT-006 | DN-PLAT-TOOLING | 1 | DEP-001 (DN-PLAT-REPO, START, need-by M0 (S1)) |
| WP-PLAT-007 | DN-PLAT-RUNNER | 2 | DEP-114 (DN-PLAT-FAILVAL, MILESTONE_EXIT, need-by M5 (S10)), DEP-115 (DN-PLAT-CD, INTEGRATION, need-by M5 (S10)) |
| WP-CICD-002 | DN-PLAT-CD | 2 | DEP-002 (DN-PLAT-REPO, START, need-by M0→M1), DEP-005 (DN-PLAT-INTEG, INTEGRATION, need-by M1 (S2)) |
| WP-CICD-003 | DN-PLAT-CD | 2 | DEP-002 (DN-PLAT-REPO, START, need-by M0→M1), DEP-005 (DN-PLAT-INTEG, INTEGRATION, need-by M1 (S2)) |
| WP-CICD-004 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-CICD-005 | DN-PLAT-CD | 2 | DEP-002 (DN-PLAT-REPO, START, need-by M0→M1), DEP-005 (DN-PLAT-INTEG, INTEGRATION, need-by M1 (S2)) |
| WP-OBS-001 | DN-RT-OBS | 2 | DEP-011 (DN-PLAT-INTEG, MILESTONE_EXIT, need-by M1 (S2)), DEP-109 (DN-PLAT-CD, MILESTONE_EXIT, need-by M3 (S6)) |
| WP-OBS-002 | DN-RT-OBS | 2 | DEP-011 (DN-PLAT-INTEG, MILESTONE_EXIT, need-by M1 (S2)), DEP-109 (DN-PLAT-CD, MILESTONE_EXIT, need-by M3 (S6)) |
| WP-OBS-003 | DN-RT-OBS | 2 | DEP-011 (DN-PLAT-INTEG, MILESTONE_EXIT, need-by M1 (S2)), DEP-109 (DN-PLAT-CD, MILESTONE_EXIT, need-by M3 (S6)) |
| WP-OBS-004 | DN-RT-OBS | 2 | DEP-011 (DN-PLAT-INTEG, MILESTONE_EXIT, need-by M1 (S2)), DEP-109 (DN-PLAT-CD, MILESTONE_EXIT, need-by M3 (S6)) |
| WP-OBS-005 | DN-RT-OBS | 2 | DEP-011 (DN-PLAT-INTEG, MILESTONE_EXIT, need-by M1 (S2)), DEP-109 (DN-PLAT-CD, MILESTONE_EXIT, need-by M3 (S6)) |
| WP-OBS-006 | DN-RT-OBS | 2 | DEP-011 (DN-PLAT-INTEG, MILESTONE_EXIT, need-by M1 (S2)), DEP-109 (DN-PLAT-CD, MILESTONE_EXIT, need-by M3 (S6)) |
| WP-SEC-001 | DN-RT-IDP | 1 | DEP-010 (DN-PLAT-INTEG, INTEGRATION, need-by E2E-01 readiness (end S4)) |
| WP-SEC-002 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-SEC-003 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-SEC-004 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-SEC-005 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-SEC-006 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-SEC-007 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-SEC-008 | DN-SEC-BASE | 2 | DEP-016 (DN-RT-IDP, INTEGRATION, need-by M4 (S8)), DEP-017 (DN-PLAT-CD, MILESTONE_EXIT, need-by M4 (S8)) |
| WP-DR-001 | DN-PLAT-BACKUP | 1 | DEP-111 (DN-SEC-BASE, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-DR-002 | DN-PLAT-BACKUP | 1 | DEP-111 (DN-SEC-BASE, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-DR-003 | DN-PLAT-BACKUP | 1 | DEP-111 (DN-SEC-BASE, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-DR-004 | DN-PLAT-BACKUP | 1 | DEP-111 (DN-SEC-BASE, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-TEST-002 | DN-EVT-CONTRACTS | 1 | DEP-021 (DN-CORE-CONTRACTS, START, need-by S1–S2) |
| WP-TEST-003 | DN-SIM-COREINT | 3 | DEP-040 (DN-SIM-OPSEM, INTEGRATION, need-by M2 (S4)), DEP-041 (DN-CORE-CMDEXEC, INTEGRATION, need-by M2 (S4)), DEP-042 (DN-EVT-SPINE, INTEGRATION, need-by M2 (S4)) |
| WP-TEST-004 | DN-PLAT-FAILVAL | 2 | DEP-110 (DN-RT-OBS, MILESTONE_EXIT, need-by M5 (S10)), DEP-113 (DN-PLAT-BACKUP, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-TEST-005 | DN-SIM-SNAPFORK | 1 | DEP-044 (DN-SIM-KERNEL, START, need-by S3) |
| WP-TEST-006 | CK-E2E01 | 10 | DEP-178 (DN-VIS-SERVING, MILESTONE_EXIT, need-by E2E-01 (end S5)), DEP-179 (DN-AI-RCA, MILESTONE_EXIT, need-by E2E-01 (end S5)), DEP-180 (DN-SCH-PLANCON, MILESTONE_EXIT, need-by E2E-01 (end S5)), DEP-181 (DN-SCH-VALID, MILESTONE_EXIT, need-by E2E-01 (end S5)), DEP-182 (DN-HITL-APPROVAL, MILESTONE_EXIT, need-by E2E-01 (end S5)) … |
| WP-PERF-001 | DN-PLAT-RUNNER | 2 | DEP-114 (DN-PLAT-FAILVAL, MILESTONE_EXIT, need-by M5 (S10)), DEP-115 (DN-PLAT-CD, INTEGRATION, need-by M5 (S10)) |
| WP-PERF-002 | DN-PLAT-RUNNER | 2 | DEP-114 (DN-PLAT-FAILVAL, MILESTONE_EXIT, need-by M5 (S10)), DEP-115 (DN-PLAT-CD, INTEGRATION, need-by M5 (S10)) |
| WP-PERF-003 | DN-SIM-OPSEM | 3 | DEP-037 (DN-SIM-KERNEL, START, need-by S2), DEP-038 (DN-CORE-CONTRACTS, START, need-by S2), DEP-039 (DN-CORE-TRANSITIONS, MILESTONE_EXIT, need-by M2 (S4)) |
| WP-PERF-004 | DN-PLAT-FAILVAL | 2 | DEP-110 (DN-RT-OBS, MILESTONE_EXIT, need-by M5 (S10)), DEP-113 (DN-PLAT-BACKUP, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-PERF-005 | DN-PLAT-FAILVAL | 2 | DEP-110 (DN-RT-OBS, MILESTONE_EXIT, need-by M5 (S10)), DEP-113 (DN-PLAT-BACKUP, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-PERF-006 | DN-SCH-DYN | 6 | DEP-078 (DN-SCH-HEUR, START, need-by S3), DEP-079 (DN-CORE-SNAPCON, INTEGRATION, need-by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, INTEGRATION, need-by M2 (S4)), DEP-081 (DN-EVT-SPINE, MILESTONE_EXIT, need-by M4 (S8)), DEP-086 (DN-SCH-CPSAT, MILESTONE_EXIT, need-by M4 (S8)) … |
| WP-RES-001 | DN-PLAT-RUNNER | 2 | DEP-114 (DN-PLAT-FAILVAL, MILESTONE_EXIT, need-by M5 (S10)), DEP-115 (DN-PLAT-CD, INTEGRATION, need-by M5 (S10)) |
| WP-RES-002 | DN-RES-DATASCEN | 3 | DEP-121 (DN-SIM-SYNTH, MILESTONE_EXIT, need-by M5 (S10)), DEP-122 (DN-VIS-SPLIT, MILESTONE_EXIT, need-by M5 (S10)), DEP-123 (DN-RAG-CORPUS, MILESTONE_EXIT, need-by M5 (S10)) |
| WP-RES-003 | DN-PLAT-RUNNER | 2 | DEP-114 (DN-PLAT-FAILVAL, MILESTONE_EXIT, need-by M5 (S10)), DEP-115 (DN-PLAT-CD, INTEGRATION, need-by M5 (S10)) |
| WP-RES-004 | DN-RES-ANALYSIS | 2 | DEP-143 (DN-RES-BENCH, FREEZE, need-by M7 (S12)), DEP-144 (DN-FRZ-PROTOCOL, FREEZE, need-by M7 (S12)) |
| WP-RES-005 | DN-RES-BENCH | 3 | DEP-120 (DN-PLAT-CLEANREPRO, FREEZE, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE, FREEZE, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF, FREEZE, need-by M7 (S12)) |
| WP-RES-006 | DN-RES-BASELINES | 1 | DEP-124 (DN-RES-DATASCEN, START, need-by M5 (S10)) |
| WP-RES-007 | DN-FRZ-RQ1CORPUS | 1 | DEP-146 (DN-RAG, FREEZE, need-by M5→M6) |
| WP-RES-008 | DN-SIM-REALISM | 1 | DEP-049 (DN-SIM-OPSEM, FREEZE, need-by M5→M6) |
| WP-RES-009 | DN-FRZ-RQ3AUTH | 1 | DEP-147 (DN-HITL-POLICY, FREEZE, need-by M5→M6) |
| WP-RES-010 | DN-VIS-EPISODES | 2 | DEP-062 (DN-SIM-COREINT, MILESTONE_EXIT, need-by M5), DEP-063 (DN-CORE-GENEALOGY, MILESTONE_EXIT, need-by M5) |
| WP-RES-011 | DN-FRZ-PROTOCOL | 6 | DEP-135 (DN-FRZ-DATA, FREEZE, need-by M6 (S11)), DEP-136 (DN-FRZ-MODEL, FREEZE, need-by M6 (S11)), DEP-137 (DN-FRZ-RQ3AUTH, FREEZE, need-by M6 (S11)), DEP-138 (DN-SIM-REALISM, FREEZE, need-by M6 (S11)), DEP-151 (DN-VIS-EPISODES, FREEZE, need-by M6) … |
| WP-RES-012 | DN-RES-CLAIMS | 1 | DEP-145 (DN-RES-ANALYSIS, MILESTONE_EXIT, need-by M7→M8) |
| WP-BENCH-001 | DN-RES-BENCH | 3 | DEP-120 (DN-PLAT-CLEANREPRO, FREEZE, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE, FREEZE, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF, FREEZE, need-by M7 (S12)) |
| WP-BENCH-002 | DN-RES-BENCH | 3 | DEP-120 (DN-PLAT-CLEANREPRO, FREEZE, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE, FREEZE, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF, FREEZE, need-by M7 (S12)) |
| WP-BENCH-003 | DN-RES-BENCH | 3 | DEP-120 (DN-PLAT-CLEANREPRO, FREEZE, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE, FREEZE, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF, FREEZE, need-by M7 (S12)) |
| WP-BENCH-004 | DN-PLAT-CLEANREPRO | 2 | DEP-118 (DN-ART-RELEASE, MILESTONE_EXIT, need-by M6→M7), DEP-119 (DN-ART-HWPROF, MILESTONE_EXIT, need-by M6→M7) |
| WP-BENCH-005 | DN-RES-BENCH | 3 | DEP-120 (DN-PLAT-CLEANREPRO, FREEZE, need-by M7 (S12)), DEP-141 (DN-FRZ-RELEASE, FREEZE, need-by M7 (S12)), DEP-142 (DN-ART-HWPROF, FREEZE, need-by M7 (S12)) |
| WP-DOC-001 | DN-PLAT-TOOLING | 1 | DEP-001 (DN-PLAT-REPO, START, need-by M0 (S1)) |
| WP-DOC-003 | DN-RES-CLAIMS | 1 | DEP-145 (DN-RES-ANALYSIS, MILESTONE_EXIT, need-by M7→M8) |
| WP-DOC-004 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-DOC-005 | DN-PLAT-CLEANREPRO | 2 | DEP-118 (DN-ART-RELEASE, MILESTONE_EXIT, need-by M6→M7), DEP-119 (DN-ART-HWPROF, MILESTONE_EXIT, need-by M6→M7) |
| WP-DOC-006 | DN-RES-CLAIMS | 1 | DEP-145 (DN-RES-ANALYSIS, MILESTONE_EXIT, need-by M7→M8) |
| WP-R2-001 | DN-RAG | 2 | DEP-070 (DN-RAG-CORPUS, START, need-by S3–S4), DEP-071 (DN-RT-QDRANT, INTEGRATION, need-by M4 (S8)) |
| WP-R2-002 | DN-AI-ORCH | 1 | DEP-064 (DN-AI-TOOLCON, START, need-by S2–S3) |
| WP-S-001 | DN-UI-SHELL | 2 | DEP-105 (DN-UI-BFFCON, START, need-by S1–S2), DEP-106 (DN-TWIN-SKELETON, MILESTONE_EXIT, need-by M1 (S2)) |
| WP-X-001 | DN-RES-CLAIMS | 1 | DEP-145 (DN-RES-ANALYSIS, MILESTONE_EXIT, need-by M7→M8) |

Work packages with no inbound HARD edge are the early unlockers that should start first: WP-GOV-001, WP-GOV-002, WP-GOV-004, WP-CORE-001, WP-SIM-001, WP-SIM-002, WP-VDATA-001, WP-VDATA-003, WP-RAG-001, WP-AI-002, WP-AI-005, WP-SCH-001, WP-SCH-003, WP-HITL-001, WP-UI-001, WP-CICD-001, WP-CICD-006, WP-TEST-001, WP-TEST-007, WP-TEST-008, WP-DOC-002, WP-R2-003.
## 12. Mandatory vs Stretch Isolation (R2 / S / X)

Item 68 scope classes are carried verbatim. R2 candidates and stretch enhancements are held in their own packages with no target milestone, no mandatory-path dependency and no capacity allocation.

| Class | Meaning (Item 68) | Work packages | Placement rule enforced here |
|---|---|---|---|
| F0 | product identity mandatory | 26 packages | each F0 requirement has a dedicated package and an integrated scenario (03 View F) |
| F1 | final mandatory | 125 packages | scheduled against M1–M8; NFR-driven packages additionally carry their NFR class |
| R1 | mandatory research/evidence | 23 packages | mechanism must exist and run; outcome direction is free |
| R2 | evidence-gated candidate | WP-R2-001, WP-R2-002, WP-R2-003 | unscheduled; cannot be a HARD predecessor of any mandatory package without formal promotion (05 DEP-RULE-11) |
| S | stretch | WP-S-001 | register only; reviewed at milestone boundaries, never scheduled against mandatory capacity |
| X | out of scope | WP-X-001 (guard rail) | bounded optional documentation/review guardrail work; not delivery of an out-of-scope product capability; remains unscheduled |

| Isolation check | Result |
|---|---|
| R2/S packages with a target milestone | 0 |
| R2/S packages appearing as a gate for a mandatory WP | 0 |
| Mandatory packages whose deliverables assume ColBERT, local LLM, Neo4j, TimescaleDB, Valkey, Kubernetes or cloud | 0 |
| Out-of-scope claims (real-manufacturing-facility control, first-pass yield improvement, autonomous operation, MES/ERP replacement) present in any deliverable | 0 |

## 13. Risk Hooks

Risk identities come from 01 Item 69; priority is not restated here. A work package carrying a risk hook is where the mitigation actually lands — a mitigation link is never evidence (03 §4.2).

| Risk | Work packages carrying mitigation work |
|---|---|
| AI-R01 | WP-AI-003, WP-RES-007 |
| AI-R02 | WP-AI-003, WP-RAG-003, WP-RES-007 |
| AI-R03 | WP-R2-001, WP-RAG-002 |
| AI-R04 | WP-RAG-005 |
| AI-R05 | WP-RAG-004 |
| AI-R06 | WP-AI-002, WP-SEC-004 |
| AI-R07 | WP-AI-006, WP-HITL-001, WP-RES-009, WP-TEST-003 |
| AI-R08 | WP-AI-005, WP-RES-011 |
| AI-R09 | WP-AI-001 |
| AI-R10 | WP-AI-005, WP-SEC-008 |
| AI-R11 | WP-ML-002, WP-ML-003, WP-ML-004, WP-ML-007 |
| AI-R12 | WP-ML-001 |
| ARCH-R01 | WP-AUTO-007, WP-BENCH-002, WP-EVT-001, WP-RES-010, WP-TEST-006, WP-VIS-007 |
| ARCH-R03 | WP-EVT-001, WP-TEST-002 |
| ARCH-R04 | WP-EVT-001 |
| ARCH-R05 | WP-CORE-001, WP-CORE-007, WP-EVT-001, WP-EVT-005, WP-TEST-007 |
| ARCH-R06 | WP-TWIN-001 |
| ARCH-R07 | WP-EVT-005, WP-TEST-007 |
| ARCH-R08 | WP-EVT-004 |
| ARCH-R09 | WP-EVT-002, WP-PERF-003, WP-SIM-004, WP-TEST-005, WP-TWIN-005 |
| ARCH-R10 | WP-EVT-001, WP-TEST-002 |
| AUTO-R01 | WP-AUTO-002, WP-BENCH-003, WP-CORE-003, WP-PERF-005, WP-TEST-004 |
| AUTO-R02 | WP-AUTO-005 |
| AUTO-R03 | WP-AUTO-001, WP-AUTO-002, WP-TEST-004 |
| AUTO-R04 | WP-HITL-003, WP-TEST-003 |
| AUTO-R05 | WP-AUTO-003, WP-HITL-003, WP-RES-009 |
| AUTO-R06 | WP-AUTO-005, WP-RES-008, WP-TEST-003 |
| AUTO-R09 | WP-HITL-004, WP-TEST-006 |
| AUTO-R10 | WP-UI-006 |
| DATA-R02 | WP-VDATA-001 |
| DATA-R03 | WP-VDATA-001, WP-VDATA-003 |
| DATA-R04 | WP-ML-001, WP-RES-002, WP-VDATA-002 |
| DATA-R05 | WP-RES-002, WP-VDATA-002 |
| DATA-R09 | WP-VDATA-002 |
| DEMO-R01 | WP-AUTO-007, WP-BENCH-002, WP-DOC-004, WP-PERF-002 |
| DEMO-R03 | WP-BENCH-004 |
| DEMO-R04 | WP-DOC-004, WP-UI-012 |
| DEMO-R05 | WP-UI-006 |
| DEMO-R07 | WP-DOC-004, WP-UI-009 |
| DOC-R05 | WP-DOC-003, WP-RES-012 |
| DR-R01 | WP-DR-001 |
| DR-R02 | WP-DR-004 |
| DR-R03 | WP-BENCH-003, WP-DR-002 |
| DR-R04 | WP-DR-002 |
| DR-R06 | WP-DR-003, WP-TWIN-004 |
| PERF-R02 | WP-PERF-004 |
| PERF-R03 | WP-PERF-002, WP-TWIN-002, WP-TWIN-003 |
| PERF-R04 | WP-PERF-006, WP-SCH-005 |
| PERF-R05 | WP-AI-007 |
| PERF-R07 | WP-OBS-006 |
| PLAN-R03 | WP-BENCH-002, WP-RES-010, WP-TEST-006, WP-VIS-007 |
| PLAN-R04 | WP-AUTO-007, WP-BENCH-002, WP-TEST-006 |
| PLAT-R01 | WP-PLAT-004 |
| PLAT-R02 | WP-OBJ-002, WP-OBS-006 |
| PLAT-R03 | WP-DR-003, WP-RAG-006 |
| PLAT-R05 | WP-PLAT-007 |
| PLAT-R06 | WP-BENCH-003, WP-DR-002 |
| PLAT-R07 | WP-CICD-006 |
| PLAT-R08 | WP-CICD-001, WP-CICD-002 |
| PLAT-R09 | WP-PLAT-005 |
| PLAT-R10 | WP-BENCH-004 |
| PLAT-R11 | WP-OBS-004 |
| PLAT-R12 | WP-PLAT-007 |
| RES-R01 | WP-ML-001, WP-RES-002, WP-RES-011, WP-SIM-007, WP-VDATA-002 |
| RES-R05 | WP-RES-003 |
| RES-R08 | WP-BENCH-001, WP-RES-001 |
| RES-R12 | WP-DOC-003, WP-RES-012 |
| RES-R13 | WP-RES-004 |
| RES-R14 | WP-RES-003 |
| RES-R15 | WP-BENCH-001, WP-RES-001 |
| SCH-R01 | WP-SCH-003, WP-TEST-006, WP-VALID-001, WP-VALID-002 |
| SCH-R03 | WP-PERF-006, WP-SCH-005 |
| SCH-R04 | WP-SCH-007 |
| SCH-R05 | WP-RES-008, WP-SCH-004 |
| SCH-R06 | WP-RES-006, WP-SCH-001 |
| SCH-R07 | WP-SCH-005, WP-TEST-006, WP-VALID-001 |
| SEC-R01 | WP-DOC-005, WP-SEC-005 |
| SEC-R02 | WP-SEC-003 |
| SEC-R03 | WP-SEC-002 |
| SEC-R04 | WP-SEC-007, WP-SIM-005, WP-TEST-005 |
| SEC-R05 | WP-HITL-007 |
| SEC-R06 | WP-CICD-004 |
| SIM-R01 | WP-SIM-001, WP-SIM-009 |
| SIM-R02 | WP-SIM-001, WP-SIM-009 |
| SIM-R04 | WP-SEC-007, WP-SIM-005, WP-TEST-005, WP-VIS-009 |
| SIM-R06 | WP-SIM-002, WP-SIM-009 |
| SIM-R08 | WP-RES-008, WP-SCH-006, WP-SIM-004 |
| TEAM-R01 | WP-BENCH-003, WP-BENCH-004 |
| VIS-R01 | WP-BENCH-002, WP-RES-010, WP-TEST-006, WP-VIS-002, WP-VIS-003, WP-VIS-007 |
| VIS-R04 | WP-RES-010, WP-VDATA-005, WP-VIS-004 |
| VIS-R05 | WP-VIS-002, WP-VIS-003 |
| VIS-R06 | WP-VIS-008 |
| VIS-R07 | WP-VDATA-004 |

## 14. Findings Register

| ID | Class | Finding | Required resolution | Severity |
|---|---|---|---|---|
| WBS-GAP-01 | NAMESPACE_COLLISION (inherited GAP-RTM-013) | `WP-<AREA>-NNN` work packages vs Item 82 `WP-SMALL/NORMAL/STRESS` workload profiles. | Pattern-based disambiguation adopted (§2); tooling must match the full pattern `WP-[A-Z0-9]+-[0-9]{3}`, which also covers digit-bearing area segments such as `WP-R2-001`. Alternative (renaming the WBS namespace) rejected because the user-facing convention in 00 §8 uses `WP-CORE-001`. | MINOR — resolved by convention, confirm in review |
| WBS-GAP-02 | RESOLVED | 08 now defines and ratifies the referenced DoR/DoD IDs; lossless many-to-one task mapping is explicit. | Ratify or replace in 08; WP cards reference IDs, not wording, so ratification does not require re-editing every card. | INFO — future implementation evidence remains required |
| WBS-GAP-03 | RESOLVED | 02 append-only existing-service ARCH allocations and03 traces now cover ML, evaluation and dataset capabilities. | 02 registry append via change control before M4/M5 (05 DEP-GAP-08/09). | INFO — future implementation evidence remains required |
| WBS-GAP-04 | RESOLVED | Distinct observation/result and canonical command identities are DECIDED in01/02; contract field/version freeze remains assigned implementation work. | Resolve in the contract registry before S3–S4 so the E2E-01 readiness gate is not the first forcing function. | INFO — governed implementation gates retained |
| WBS-GAP-05 | TIMING (inherited DEP-GAP-04/05) | WP-PLAT-003, WP-SEC-001 and WP-HITL-004 must deliver Keycloak/SeaweedFS by end S4 and Temporal by end S5 — earlier than the Item 66 prose implies; WP-SEC-002 additionally needs an S5 subset for the Oracle negative test. | Roadmaps (06) must schedule these in S3–S5, not M4. | MAJOR |
| WBS-GAP-06 | RESOLVED | MC-2 accountability is Asrın Dündar in01; all179 WP owners remain unchanged. | Assign via change control before M6. | INFO — future implementation evidence remains required |
| WBS-GAP-07 | RESOLVED | 01 final human decision pins the shared-host profile; actual benchmark measurements remain future evidence. | Record profiles in WP-PLAT-005 before M6. | INFO — future implementation evidence remains required |
| WBS-GAP-08 | LOAD_CONCENTRATION | Asrın owns 73 and Yavuz 57 of 179 packages; S9–S11 concentrates Yavuz-owned evidence infrastructure. | 06 roadmaps must sequence contract-first delivery and move research-lane execution to lane owners; not solved by reassigning ownership (Item 62 is fixed). | MAJOR for 06/07 |
| WBS-GAP-09 | SIZING_UNCERTAINTY | Size bands are indicative and derived from deliverable/task counts, not from estimation sessions. | Owners re-band their packages at DoR; bands never become hour commitments. | INFO |
| WBS-GAP-10 | TASKID_ALLOCATION | Major tasks are listed but not individually identified (`TASK-<AREA>-NNN` unallocated) to avoid a micro-task registry before implementation. | Allocate TaskIDs only where a task needs independent tracking (00 §8). | INFO |

## 15. Machine-Readable Companion

| File | Content | Rows |
|---|---|---|
| `04_wbs/work_packages.csv` | full WP registry with owner, scope, milestone, readiness node, requirements, architecture, verification, gates, risks | 179 |
| `04_wbs/requirement_coverage.csv` | requirement → work package mapping | 306 |
| `04_wbs/deliverables.csv` | deliverable register | 553 |
| `04_wbs/tasks.csv` | major task register (no TaskIDs allocated yet) | 624 |

## 16. WBS Maintenance Protocol

| Event | Action | Owner |
|---|---|---|
| Requirement changes or is superseded | update the owning WP source list; re-check coverage (a requirement must never lose its last WP) | requirement PrimaryOwner |
| New capability need discovered | create a WP with source requirements; if no requirement exists, raise a change request instead of a requirement-less WP | capability owner |
| WP starts | DoR check (§4.1); register dependencies in 05 if not already present | WP owner |
| WP completes | DoD check (§4.2); trace edges updated in the same PR | WP owner + reviewer |
| Scope pressure | cut in order: S → R2 → non-critical F1 depth (with change control) — F0, H0 and A1 obligations are never cut silently | team + change control |
| R2 promotion | formal promotion decision, declared dependency-strength change, ADR | capability owner |
| Milestone boundary | review unscheduled register (§12) and load concentration (§9) | team |

## 17. Rejected Alternatives

| Alternative | Rejected because |
|---|---|
| Equal package counts per person | artificial balance (00 §13); ownership follows Item 62 capability boundaries |
| A single "testing" work package at the end | integration and verification must be visible per capability (§10) |
| A single final "documentation" task | documentation is produced alongside capabilities (WP-DOC-001) |
| Hour-level estimates | false precision before implementation; size bands only |
| Micro-task registry for every task | 00 §13 explicitly warns against turning the WBS into a task tracker |
| Requirement-less work packages | every WP carries source requirements; coverage is machine-checked |
| Scheduling R2 candidates alongside F1 work | R2 failure must never make the product incomplete (Item 68 #4) |
| Deferring integration to the last sprint | integration packages sit at M2–M3 with E2E-01 as the forcing function |
| Inventing repository paths or test results to look complete | pre-implementation honesty (00 §7.3, §23) |

## 18. Guide §13 Compliance Check and Audit

| Guide §13 requirement | Status | Where |
|---|---|---|
| Decomposition Program → Capability Area → WP → Deliverable → Task | MET | §3, §6 |
| Full WP schema fields | MET (all 18 fields per card) | §6 |
| All demanded capability families present | MET (24 families + governance + guard rails) | §5, §6 |
| Size discipline 0.5–3 focused days at task level, no hour precision | MET | §3 |
| Every WP bound to a scope class | MET | §5, §6 |
| Stretch never hidden in the mandatory path | MET (0 violations) | §12 |
| Contract / integration / failure-path / observability / acceptance as separate items | MET | §10 |
| No artificial balance across four people | MET (documented unequal load with mitigation) | §9 |
| No requirement-less work packages | MET (0) | §5 |
| Integration not deferred to the final sprint | MET (E2E-01 at S5, integration WPs at M2–M3) | §8 |
| Testing not a single final WP | MET (8 testing WPs + per-capability failure-path work) | §10 |
| Documentation not a single final task | MET (WP-DOC-001 continuous + per-WP runbook obligations) | §16 |
| No hidden manual deployment tasks | MET (WP-CICD-002 forbids host patching; NFR-DEP-003) | §6 |
| R2 candidates not planned as F1 | MET | §12 |

| Automated audit check | Result |
|---|---|
| A-01 every requirement covered by ≥1 WP | PASS (306/306) |
| A-02 every WP has ≥1 source requirement | PASS (0 violations) |
| A-03 every WP has exactly one PrimaryOwner from {Asrın, Selman, Batu, Yavuz} | PASS |
| A-04 every scheduled WP has a target milestone M0–M8 | PASS (unscheduled = R2/S/guard rails only) |
| A-05 every WP references a 05 readiness node that exists | PASS |
| A-06 architecture components resolve to the 02 registry or are flagged | PASS (unanchored flagged in WBS-GAP-03) |
| A-07 verification families resolve to the 03 registry | PASS |
| A-08 no fabricated repository path, test result or evidence ID | PASS (all repository references TBD_BY_IMPLEMENTATION, all statuses NOT_STARTED) |
| A-09 R2/S packages have no milestone and no mandatory dependants | PASS |
| A-10 F0 requirements each have a dedicated F0 package | PASS (17/17) |

### 18.1 Residual limitations

- Size bands are indicative; owners re-band at DoR.
- Major tasks are not individually identified; TaskIDs are allocated only where independent tracking is needed.
- DoR/DoD rule sets are proposals until 08 ratifies them.
- The WBS reflects 01/02/03/05 as of this draft; regenerate and diff `work_packages.csv` if any upstream artifact changes.

---

*End of 04 — Work Breakdown Structure (Draft — Derived from Approved 01/02 Baseline).*

## Final human reconciliation binding — 2026-10-13

01 §Final Human Reconciliation and02 §Final human reconciliation govern this projection. Vision/NDT publishes immutable InspectionObservation (existing EVT-InspectionObservation-v1); Core normalizes separate InspectionResult (existing IC-VIS-002) and owns canonical manufacturing/quality state. PlaceLotOnHold / CMD-PlaceLotOnHold-v1 is the single hold-placement command; ApplyMaterialHold is deprecated terminology, never a second contract. Other protected identities follow the01 action table, with exact approval/revision/freshness/idempotency binding. Simulator/Oracle, Twin/Qdrant projections, AI READ/SIMULATE/PROPOSE, Scheduler candidates, HITL, identity and UI boundaries remain unchanged.

ARCH-AUTO-WORKFLOW (durable Automation/Temporal layer) coordinates GS-01/E2E across Inspection/NDT→Core quality→RCA→recovery→HITL→governed Core commands→verified effect→Twin/Audit. It does not acquire Core authority. MC-2 accountable owner is Asrın Dündar; contributing WP owners remain73/17/32/57. The primary shared-host HardwareProfile and accepted LaneA/B/C portfolio are pinned in01; acquisition/rights/source fields not locally verified are NEEDS_SOURCE_VERIFICATION, not invented facts or performance results. Real/public held-out evaluation and source-specific limitations remain mandatory where claimed.

HARD/SOFT refer to declared work/readiness consumers, not automatic runtime/deployment/import relations. Non-CONTRACT F1 entries DEP-025/045/058/076/094 have no fixture fallback: real producer readiness at the declared stage is required, while development stubs are not satisfaction evidence. DN-VIS-MODELS now declares INTEGRATION_READY for DEP-060/194; operational serving must load promoted required-mode artifacts with provenance. Source-supported deadlines and per-consumer scope are defined in05, without shifting canonical ownership or schedules.

GAP-RTM-004/005 remain ACCEPTED_WITH_RATIONALE for this pre-implementation baseline: missing canonical record metadata is not fabricated. FR-GOV-001/004 and the relevant NFR owners must supply/review actual fields and measurement definitions before their declared gates; projectctl retains nulls/warnings and never grants READY/VERIFIED from planned prose. Owner trace confirmation GAP-RTM-006 and final schema/version/card specifics remain ordinary implementation/review prerequisites, not unresolved choices among the eight approved policy groups.
