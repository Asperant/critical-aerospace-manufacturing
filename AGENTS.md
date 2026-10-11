# AGENTS.md

## 1. Purpose

This repository implements the graduation project:

**Intelligent Manufacturing Operations Platform for Critical Aerospace Components**

Turkish title:

**Kritik Havacılık ve Uzay Komponentleri için Akıllı Üretim Operasyon Platformu**

This file is the mandatory operating contract for AI coding agents working in this repository.

The AI agent is an implementer, not the product owner and not the architecture authority.

Do not silently redesign the project.

---

## 2. Source of Truth

Canonical project decisions live in repository documentation.

Precedence order:

1. `docs/01_*` — product scope, requirements, governance
2. `docs/02_*` — system architecture
3. stable IDs, invariants, schemas, contracts
4. `docs/03_*` — requirements traceability
5. `docs/04_*` through `docs/07_*` — planning and execution projections
6. `docs/08_*` — Definition of Ready / Definition of Done
7. `docs/09_*` — Change Control
8. `docs/10_*` — Pre-Implementation Red-Team Review
9. `docs/00_*` — guide/meta documentation only

If two sources conflict, do not guess.

Report the conflict and stop the affected implementation until it is resolved.

---

## 3. Work Package Discipline

Implementation must be performed against an explicit canonical Work Package ID.

Examples:

- `WP-CORE-001`
- `WP-VIS-001`
- `WP-SIM-001`
- `WP-AI-001`

Do not start implementation from vague instructions such as:

- "improve backend"
- "add AI"
- "fix architecture"
- "make simulator better"

Every implementation task must have an explicit WP or approved control-item identifier.

Before changing code, obtain context using:

    projectctl context <WP-ID>

when `projectctl` is available.

The agent must respect:

- scope
- owner
- requirements
- architectural surfaces
- dependencies
- readiness conditions
- verification requirements
- expected evidence
- DoR
- DoD

of the active WP.

---

## 4. Workflow

Canonical workflow:

    BACKLOG
    -> READY
    -> IN_PROGRESS
    -> IN_REVIEW
    -> MERGE_READY
    -> MERGED
    -> VALIDATING
    -> DONE

`CANCELED` is terminal.

`BLOCKED` is orthogonal and must not be modeled as a workflow state.

Important:

    Merged != Done
    Implemented != Tested
    Tested != Verified
    Demoed != Accepted

A merged change must not be considered complete until required post-merge validation and evidence are complete.

---

## 5. Git Rules

Default branch:

    main

Work branches:

    wp/<WP-ID>-<short-slug>

Example:

    wp/WP-CORE-003-command-validation

Pull request title:

    [WP-CORE-003] Implement command validation

Do not implement unrelated Work Packages in the same branch.

Do not mix large refactoring with feature implementation unless explicitly required by the WP.

Do not commit:

- secrets
- credentials
- API keys
- `.env` files containing secrets
- generated datasets
- model weights
- large binary artifacts
- local IDE state
- benchmark outputs unless explicitly designated as evidence

---

## 6. Architecture Authority

Authority boundaries are mandatory.

### Core

Core is the canonical authority for manufacturing and business state.

Only Core may own authoritative manufacturing state transitions.

### Simulator

Simulator owns simulated physical execution and hidden Oracle state.

Simulator truth must never be presented as real-factory truth.

Oracle labels must never become runtime model inputs.

### Digital Twin

Digital Twin is a rebuildable projection.

It must not become an independent competing source of legal manufacturing truth.

### Vision / NDT

Vision produces perception and inspection observations/results.

Vision must not directly mutate canonical manufacturing state.

### AI / RCA / RAG

AI may:

    READ
    SIMULATE
    PROPOSE

AI must not independently execute protected manufacturing actions.

Recommendation is not execution.

### Scheduler

Scheduler produces candidate plans and counterfactual recovery alternatives.

A generated schedule is not automatically active.

### HITL

Protected actions require human approval where specified.

No self-approval.

### Automation

Automation coordinates approved and policy-valid actions.

It must verify:

- exact approved proposal/plan binding
- freshness
- policy
- authorization
- expected canonical effects

HTTP acceptance is not sufficient evidence of execution.

### Identity

Keycloak owns authentication/identity.

Business authorization remains application-governed.

---

## 7. Domain Model

Core hierarchy:

    ProductionOrder
    -> ProductionBatch / Lot
    -> SerializedComponent

Component identity is immutable.

Split or merge operations must not clone serialized component identity.

Scrapped components retain genealogy and history.

Important first-class concepts include:

- MaterialHold
- ReworkDirective
- ManufacturingRoute
- ProcessPlan
- ManufacturingOperationExecution
- InspectionObservation
- InspectionResult
- ComponentInspectionMap
- QualityExcursion
- Nonconformance
- maintenance and resource eligibility state

Do not collapse independent state dimensions.

In particular:

    lifecycle != execution
    hold != lifecycle
    priority != lifecycle
    plan != execution
    current state != history
    batch != serialized component
    rework != route-pointer reset

---

## 8. Manufacturing Flow

Primary reference flow:

    rough / multi-axis CNC machining
    -> intermediate metrology
    -> special process / heat treatment
    -> finish CNC machining
    -> visual inspection / NDT
    -> rework when required
    -> reinspection
    -> final quality acceptance

The route is re-entrant.

The system must preserve that semantics.

---

## 9. Golden Scenario

GS-01 is the primary end-to-end scenario.

Expected flow:

    Normal Production
    -> Tool Wear / Vibration / Degradation Trend
    -> Inspection or NDT Anomaly
    -> Quality Excursion
    -> RCA
    -> Counterfactual Recovery
    -> HITL Approval
    -> Governed Automation
    -> Canonical State Change
    -> Effect Verification
    -> Twin / Audit Update

RCA should use heterogeneous evidence such as:

- component genealogy
- telemetry
- tool history
- process history
- inspections
- similar incidents
- technical documentation

Outputs should rank evidence-backed hypotheses and preserve uncertainty.

Scheduler alternatives may include:

- continue
- hold
- alternate qualified CNC
- maintenance
- rework

with effects on:

- delay
- WIP
- throughput
- cycle time

---

## 10. Vision / NDT Scope

Do not reduce the Vision subsystem to a single classifier.

The intended scope includes, where assigned by WPs:

- image ingestion
- spatial inspection maps
- localization
- segmentation
- classification
- anomaly detection
- open-set / unknown handling
- component spatial pattern recognition
- cross-component clustering
- structured InspectionResult generation
- embeddings and similarity
- dataset versioning
- synthetic data
- leakage-aware splitting
- class imbalance handling
- confidence and calibration
- human review
- active-learning candidates
- data drift
- model drift
- preprocessing provenance
- model provenance
- service inference
- asynchronous/batch inference
- deployable optimized artifacts
- task-specific evaluation
- per-class and slice error analysis
- quality-event integration
- real/public held-out evaluation

A VLM must not silently replace the Vision subsystem.

Synthetic-only evaluation must not be presented as real/public held-out evaluation.

---

## 11. Data Doctrine

The project does not depend on proprietary aerospace factory data.

Data strategy:

### Lane A

Open real experimental data for:

- machining
- tool wear
- machine health
- inspection
- NDT

### Lane B

Literature and technical-source-grounded process models for:

- manufacturing routes
- resources
- process assumptions

### Lane C

Controlled simulator-generated operational data for:

- orders
- batches
- components
- queues
- WIP
- failures
- maintenance
- quality events
- scheduling
- recovery
- end-to-end execution

Never describe simulated data as real factory data.

Never infer real-factory production performance solely from simulation.

Do not relabel datasets into another industrial domain.

Examples of prohibited semantic relabeling:

- wafer-map data must not be described as aerospace serialized-component inspection data
- semiconductor manufacturing datasets must not be presented as aerospace factory datasets

Cross-domain datasets may only be used when explicitly documented as methodological or legacy baselines.

---

## 12. Technical Baseline

The approved baseline is Python-first with a TypeScript frontend.

Expected technologies include:

- Python
- TypeScript
- PostgreSQL
- Qdrant
- NATS JetStream
- Temporal
- SeaweedFS
- Keycloak
- Valkey where useful
- OpenTelemetry
- OpenTelemetry Collector
- OpenObserve
- MLflow
- OR-Tools CP-SAT
- deterministic Python discrete-event simulation
- Docker
- Docker Compose
- GitHub
- GitHub Actions
- GitHub Container Registry

Do not introduce a new database, broker, orchestration platform, graph database, Kubernetes dependency, or major infrastructure product without explicit architectural approval.

The platform is designed for a shared Linux development host.

Avoid unnecessary infrastructure expansion.

---

## 13. AI Provider Rules

AI provider integration must remain abstracted.

Supported architectural intent:

- remote provider
- local provider
- deterministic/test-double provider

The platform should be local-first/on-premise-capable with controlled egress.

Do not claim the system is air-gapped unless that property is explicitly validated.

---

## 14. Safety and Scope Boundaries

This project is a research and simulation platform.

It is not:

- a certified aerospace manufacturing system
- a certified safety system
- a commercial MES replacement
- a commercial QMS replacement
- a commercial ERP replacement
- real CNC control
- PLC control
- physical equipment control
- autonomous real-factory control

Do not write code or documentation that implies otherwise.

---

## 15. Change Control

Ordinary implementation inside an approved requirement and architecture does not require a ChangeRequest.

However, semantic changes may require formal change control.

Relevant change classes:

- C0 Editorial
- C1 Compatible
- C2 Behavior-Affecting
- C3 Protocol / Scope / Architecture

Before making a change that affects:

- requirement semantics
- architecture
- service boundaries
- protocol
- canonical schemas
- authority boundaries
- external contracts
- governance
- verification expectations

check `docs/09_*`.

Silent architecture changes are prohibited.

Change is allowed.

Silent change is not.

---

## 16. Testing and Evidence

Every WP must implement the verification required by its canonical specification.

Depending on the WP this may include:

- unit tests
- integration tests
- contract tests
- end-to-end tests
- negative-path tests
- failure injection
- deterministic replay
- performance measurements
- security checks
- research evaluation
- reproducibility evidence

Evidence belongs under:

    evidence/

or an explicitly approved artifact location.

Do not fabricate evidence.

Do not mark tests as passing without running them.

Do not mark a WP DONE merely because code compiles.

---

## 17. Research Integrity

Preserve:

- baselines
- ablations
- reproducibility
- uncertainty
- statistical reporting
- negative results
- experiment configuration
- dataset provenance
- model provenance

Do not cherry-pick favorable runs.

Do not overwrite failed experimental evidence.

---

## 18. Implementation Behaviour

Before coding:

1. identify the active WP
2. read its canonical scope
3. inspect relevant architecture and contracts
4. inspect existing implementation
5. inspect dependencies
6. state the implementation plan
7. identify affected tests and evidence

While coding:

- prefer the smallest compliant implementation
- preserve existing contracts unless explicitly authorized
- keep changes localized
- avoid speculative abstractions
- avoid premature frameworks
- avoid duplicate sources of truth
- use typed interfaces where practical
- make failure states explicit
- maintain deterministic behavior where required

After coding:

1. run relevant tests
2. run negative-path tests where required
3. inspect failures
4. update evidence
5. report exactly what changed
6. report what was not completed
7. report any discovered architecture or specification conflict

---

## 19. Prohibited Agent Behaviour

The coding agent must not:

- invent requirements
- silently reinterpret requirements
- mark Plane work items DONE without validation
- weaken tests to make them pass
- delete failing tests without approval
- bypass HITL
- bypass authorization
- directly mutate canonical state from UI, AI, Vision, or Scheduler
- replace exact proposal binding with loose textual matching
- treat an accepted HTTP request as verified execution
- commit secrets
- fabricate production data
- fabricate evidence
- create hidden technical debt to satisfy a demo
- refactor unrelated systems during a scoped WP
- create alternative project-management truth inside code or markdown
- automatically change canonical documentation to match an implementation mistake

---

## 20. Project Management Boundary

`docs/` is the canonical specification and governance truth.

GitHub is the code, pull-request, review, engineering-work and evidence truth.

Plane is the execution planning, coordination and status view. It must not replace GitHub as engineering-work truth.

`projectctl` is the deterministic validation and synchronization bridge.

Canonical Work Package IDs are stable and must not be replaced by Plane-generated IDs such as `CAP-42`.

Plane state must not redefine canonical project or WP semantics.

The project-control tooling may synchronize approved static metadata into Plane.

Execution fields may live in Plane.

---

## 21. Team Ownership

Primary ownership areas:

### Asrın Dündar

Manufacturing Intelligence & Core Systems

Typical responsibility:

- Core
- Digital Twin
- AI / RCA / RAG
- predictive ML
- backend intelligence
- evaluation
- authority-policy semantics

### Selman Özdemir

Visual Perception & Inspection Intelligence

Typical responsibility:

- Computer Vision
- NDT
- visual inspection
- vision datasets
- vision inference and evaluation

### Batuhan Kaya

Manufacturing Control, Simulation & Recovery

Typical responsibility:

- Simulator
- scheduling
- CP-SAT
- schedule validation
- durable automation
- Temporal workflows
- recovery
- effect verification

### Yavuz Gümüş

Platform Engineering, Delivery & Reliability

Typical responsibility:

- runtime/platform
- security infrastructure
- observability
- CI/CD
- release
- reliability
- evidence/research infrastructure

Ownership does not override architecture authority or dependency rules.

---

## 22. Resource Constraints

Shared development host resources must be respected.

Do not assume unlimited:

- CPU
- RAM
- GPU VRAM
- disk I/O

Avoid launching the entire platform for tests that require only one service.

Canonical benchmark runs must not be contaminated by unrelated infrastructure load.

Plane itself is management infrastructure and may be stopped during controlled benchmark campaigns if required.

---

## 23. Response Format for Coding Tasks

For substantial implementation tasks, the coding agent should finish with:

    WP:
    Implemented:
    Files changed:
    Tests run:
    Tests passed:
    Evidence produced:
    Known limitations:
    Spec conflicts:
    Recommended next action:

Do not claim success when required verification has not completed.

---

## 24. Final Rule

When uncertain:

Do not improvise architecture.

Read the canonical documentation.

If the documentation is insufficient or contradictory, surface the ambiguity explicitly.
