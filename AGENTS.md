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

Development policy `DEV-REVIEW-2026-10-15-FINAL` / CHG-018: ALL repository development PRs, CR-0 through CR-4 including high-risk security/auth/protected-authority/migration work, require **0 human approvals**. Review, comments, CODEOWNERS and supporting reviewers are advisory; APPROVED/CHANGES_REQUESTED/DISMISSED, reviewer presence, independent quotas, self-approval, owner override and stale/current-head approval mechanisms never gate workflow, merge or DONE. IN_REVIEW means technically reviewable, not waiting for a human. MERGE_READY requires actual correct WP/control scope/branch/head, non-draft PR, required CI/tests/canonical validation, mergeability, trace/evidence, applicable DoR-PR/PR DoD and security/secret/static checks, and no real BLOCKED condition. Actual technical/canonical ambiguity fails closed. DONE still requires all actual DoD/trace/evidence/post-merge validation. Product HITL/protected-action authentication, self-approval prohibition, exact binding and execution authorization remain unchanged.

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

### Execution queue

Plane is the source of truth for execution state, assignment and blockers; GitHub remains engineering-work/review/evidence truth and docs remain specification truth. Read the assignee's live Plane queue first: IN_PROGRESS is the current WP; otherwise READY is the next WP. Normally keep at most one READY WP per person. Multiple IN_PROGRESS or multiple READY candidates, or no IN_PROGRESS/READY task, require planning-owner resolution; never select work independently from BACKLOG. A blocked active WP must be surfaced, not silently replaced.

At the start of every Remote SSH developer session, run `cap-plane-queue` (uses `CAP_PROFILE`) to read the live queue without exposing Plane credentials. Use the canonical WP ID from `current_task` (IN_PROGRESS), otherwise `next_task` (READY), then run `projectctl context <WP-ID>`. Do not start implementation when the live result is UNAVAILABLE, AMBIGUOUS, BLOCKED, NO_TASK, or the task state is not IN_PROGRESS/READY. Do not start implementation directly from BACKLOG or choose arbitrary BACKLOG work. The queue helper remains read-only. As execution actually progresses, use `cap-plane-transition <WP-ID> <TARGET_STATE>` with a reason and evidence references to keep only the assigned canonical WP workflow/BLOCKED projection current. CAP_PROFILE plus canonical owner and live Plane assignee matching are trusted-team operational guards, not a security boundary between processes sharing ailab. Never touch another profile's assignment or other Plane fields.

Before implementation, retrieve `projectctl context <WP-ID>` for that exact canonical WP, inspect dependencies and DoR, and use its WP branch. `projectctl next` gives planning candidates, not permission to start; offline `status` is not the live queue. The assigned developer agent may release BACKLOG to READY only after evidenced canonical DoR and actual dependency/readiness checks; this never authorizes random BACKLOG selection. Move READY to IN_PROGRESS only after implementation actually starts. Every transition must satisfy canonical DoR/DoD/governance and actual GitHub/PR/CI/evidence facts; Plane must never run ahead of reality. Mechanically observable progress uses those actual facts without an additional machine-generated confirmation comment. Accountable DoR/DoD assessments, scope cancellation decisions and blocker reasons/resolutions still require real attributable evidence; no human reviewer presence is required; reuse existing PR, review or repository evidence rather than copying it into a special JSON comment. Missing/ambiguous evidence fails closed. BLOCKED is orthogonal: record a real reason, blocker owner/work or external dependency, and verified resolution before clearing it. CANCELED requires an explicit recorded project-owner decision; agents cannot cancel scope themselves. Merged != Done; Implemented != Tested; Tested != Verified; Demoed != Accepted. UNKNOWN from `check-ready` is not PASS; an applicable accountable owner assessment must have attributable evidence and limitations in GitHub and the transition audit. A Plane state or tool result alone never certifies verification.


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


## AUTO_NEXT — CHG-019 / CTRL-HOST-004 (22 October 2026)

Canonical planning preference lives in `project_control/execution_preferences.yaml`.
Every scheduled owned WP appears exactly once; the five unscheduled WPs stay outside.
Earlier milestone/window comes first, then canonical security/data-integrity,
cross-owner enabling and milestone work, then primary work; the owner's roadmap
section 9 order is the explicit final planning tie-breaker. Current broken-main or
security incidents are not invented from titles; actual repair remains governed
by the Task Priority Rule. This artifact is priority only, never readiness/evidence.

AUTO_NEXT scans preference and skips ineligible work with precise reasons. It uses
canonical node readiness and HARD START gates, not producer-WP DONE. Later-stage
HARD gates retain their actual stage; SOFT gaps are visible. UNKNOWN is not PASS.
Existing attributable current-revision DoR/dependency assessments and exact artifacts
are required; automation never generates confirmations or certifies from planning.

Any READY, IN_PROGRESS, IN_REVIEW, MERGE_READY, MERGED or VALIDATING work prevents
automatic release of another READY. BLOCKED active work is surfaced. This conservative
automatic-release policy does not change the global implementation WIP doctrine.
After VERIFIED DONE, the owner and canonical node consumers are evaluated under the
shared lock. Only BACKLOG -> READY may be automatically written, through the existing
transition evaluator, durable INTENT, one PATCH and fresh verified readback. External
writer races fail closed and require recomputation; timeout is never blindly retried.
No assignment, cycle, module, label, title, description or dependency backfill occurs.

Run `cap-plane-queue` in the real account/profile. JSON compatibility is retained;
`display_status` explains CURRENT/READY/NO_TASK/BLOCKED. NO_TASK includes fresh
eligibility reasons; never choose BACKLOG yourself. `projectctl next` remains
planning-only. Recovery: `cap-plane-advance` for own profile; root administration:
`sudo cap-plane-advance --all`. Both use the same resolver and guards. Offline
`projectctl execution-preferences` validates coverage; `queue-preview` reads explicit
live/evidence snapshots and never authorizes or performs a transition.

Separate Linux accounts asrin/selman/batuhan/yavuz and private workspaces/profiles
are authoritative. The helper drops GitHub reads to the matching account; root-only
installed code/policy is used, never writable repository imports. CAP_PROFILE must
match the real sudo caller. Historical shared-ailab descriptions are superseded for
this workflow; no workspace permissions, SSH or profile paths are changed.
CHG-018 zero-development-approval policy remains; product HITL stays unchanged.

Deploy only merged reference source. The dedicated AUTO_NEXT installer creates a
root-only timestamped `/root` backup and rollback script before replacing helper
files, refreshes source/helper hashes, verifies sudoers and preserves audit. Rollback
restores deployment only; never replay a stale Plane DB or state snapshot. No service
restart is required. Missing evidence results in NO_TASK, never synthetic READY.


## Automatic preparation — CHG-021 / CTRL-HOST-006

CHG-021 supersedes CHG-019's blanket prohibition on generated START assessments
only for exact, mechanically derived canonical governance. Product/DoD evidence,
semantic assessments and dependency-owner attribution remain mandatory.
`preparation.py` consumes existing resolver diagnostics; it does not select work.
AUTO_PREPARABLE means all required START facts can be derived. REAL_WORK_REQUIRED
means actual contract/consumer/design/research evidence or implementation is
missing. WAITING_DEP requires real HARD START producer evidence. UNAVAILABLE
means trusted input cannot be read. UNKNOWN never becomes PASS or PREPARED.

The bounded complete recipe requires no canonical START prerequisite, explicit
canonical input scope and precise later-stage consumer/evidence obligations,
non-R1 requirements, canonical outcome/tasks/deliverables/verification/architecture
and deterministic advisory owner/reviewer evidence routing. The first canonical
task is the initial slice; the remainder is an explicit workstream. Acceptance is
planned, tests NOT_EXECUTED, artifacts NOT_PRODUCED. Preparation source SHA is
recorded; every use regenerates all facts at current main, checks ancestor binding,
input digest and actual artifact/routing presence. These are machine-derived
assessments authorized here, not fabricated owner comments or DONE evidence.

`cap-plane-prepare --all` is root-only. Its 15-minute systemd oneshot may create
minimal branch/commit/PR preparation as Asrin's real UID/GitHub identity, and merge
only after current-head required CI and clean current-main mergeability. One PR
per WP, stable canonical-input branch, existing equivalent artifact detection and
closed-PR no-retry prevent spam. Changed/ambiguous inputs fail closed. No daemon.
All Plane writes still pass existing AUTO_NEXT with fresh full state/evidence
revalidation. Current work excludes another READY. PREPARED remains derived;
later-cycle eligibility is allowed. VERIFIED lifecycle writes nonblockingly request
replenishment after releasing the shared lock; timer is the recovery path.

Recovery: `sudo systemctl start cap-plane-prepare.service`; inspect
`sudo journalctl -u cap-plane-prepare.service` and root-only
`/var/lib/cap-plane-prepare/{latest,before,after,failure}.json` plus per-WP results.
The controller has a 720-second alarm, 750-second service timeout, nonblocking
global lock and per-WP locks. Failures do not undo or interrupt developer work.
Health remains GET-only and does not call this writer. Installer creates root-only
backup/rollback before deploying merged helpers/policy/units. No unrelated service
restart or credential copying. Real consumer/readiness/product blockers remain.

## Deferred downstream acceptance — CHG-022 / CTRL-HOST-007

CHG-022 narrowly supersedes the blanket active-work slot prohibition for verified
`VALIDATING + BLOCKED` work classified exactly
`WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE`. It requires an existing
attributable owner assessment that no owner-executable implementation work remains,
a root verified blocker audit, actual merged WP PR and successful post-merge CI,
and unchanged canonical scope/architecture/DoD. Missing or ambiguous proof keeps
occupying the slot. All other active states, ordinary VALIDATING and implementation
blockers still prevent release. The deferred WP stays visible, open and blocked;
it is never considered DONE for dependency readiness. Existing canonical preference,
AUTO_NEXT guards, fresh rechecks, one READY and all actual DONE gates are unchanged.
