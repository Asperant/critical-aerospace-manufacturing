# 06C — Batu Engineering Roadmap
## Manufacturing Control, Simulation & Recovery Owner

| Field | Value |
|---|---|
| Document | `06C_Batu_Engineering_Roadmap.md` |
| Status | **Draft — Derived from Approved 01/02 Baseline** (requires the owner's own review) |
| Version | v0.1.0-draft |
| Generated | 17 Eylül 2026 (pre-implementation) |
| Canonical role (01 Item 62) | Manufacturing Control, Simulation & Recovery Owner |
| Owned work packages | 32 of 179 (10 F0 · 20 F1-class · 2 R1 · 0 R2/S) |
| Owned requirements | 57 (45 FR · 12 NFR) |
| Owned dependency nodes (05) | 20 |
| Upstream cross-owner HARD gates | 17 |
| Downstream cross-owner consumers | 10 HARD edges |
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

Own the manufacturing control capability family as one coherent system: the simulated world in which production actually happens, the planning intelligence that decides what should happen next, and the durable execution machinery that makes an approved decision take effect exactly once and provably. Simulator, Scheduler and Automation are not three side projects — they are the world, the decision and the hand. Their shared property is that they must behave correctly under disruption, restart, duplication and counterfactual branching.

## 2. Removal-Test Statement

Remove Batu and there is no operational world and no recovery. Without the Simulator there is nothing to observe, no reentrant routing, no failures or rework, no snapshots to fork and therefore no counterfactual evaluation and no RQ-2. Without the Scheduler and its independent validator, RCA proposals end in text nobody can act on safely. Without durable Automation and effect verification, the loop stops at 'the system suggested something': no workflow survives a restart, no duplicate is suppressed, and success would be measured by an HTTP 200 instead of a verified manufacturing effect. In short: without this role the Manufacturing Operations Platform observes and reasons but never closes the loop.

**Removal test in numbers.** Removing this role removes 10 F0 work packages (WP-SIM-001, WP-SIM-003, WP-SIM-005, WP-SIM-006, WP-SCH-002, WP-VALID-001, WP-AUTO-001, WP-AUTO-005, WP-AUTO-007, WP-TEST-006), 57 owned requirements and 20 owned dependency nodes, including 7 nodes that other owners depend on through 10 HARD edges.

### 2.1 Boundaries this role may not cross

Ownership is bounded in both directions: these rules protect other roles from this one, and are enforced by tests rather than by convention.

| Boundary | Source | How it is enforced in the plan |
|---|---|---|
| Simulator implements domain semantics; Core defines business legality | Item 62 #72–#73 | Simulated execution follows Core-validated commands; the Simulator never invents legality. |
| Scheduler cannot mutate manufacturing truth | Item 62 #75 | A plan is not a command; state changes happen only through Core. |
| Automation cannot authorize its own action | Item 62 #78 | Execution requires an external approval per the authority policy. |
| Approval timeout cannot become implicit approval | Item 62 #79 | Timeouts fail closed; the workflow ends in an explicit non-success state. |
| Automation cannot bypass Core validation | Item 62 #80–#81 | All effects are dispatched as typed Core commands, never direct database writes. |
| Scheduler cannot assume unlimited compute | Item 62 #133 | The decision budget and resource profile are platform-enforced constraints. |

## 3. Owned Architecture Surfaces

Architecture components (02 registry) reached through this role's work packages, and the 05 readiness nodes that carry them.

| Readiness node (05) | Surface | Type | 02 ARCH anchor | Final readiness required |
|---|---|---|---|---|
| DN-AUTO-DESIGN | Workflow design with stub activities | CAPABILITY | ARCH-AUTO-WORKFLOW | COMPONENT_READY |
| DN-AUTO-DURABLE | Durable workflows on real Temporal (approval wait, restart safety) | CAPABILITY | ARCH-AUTO-WORKFLOW, ARCH-AUTO-IDEMPOTENCY | FROZEN |
| DN-AUTO-EXEC | Protected execution via Core typed commands (final revalidation) | CAPABILITY | ARCH-AUTO-ACTIONCAT, ARCH-CORE-CMD | FROZEN |
| DN-AUTO-VERIFY | Effect verification (ACK ≠ effect; UNKNOWN_VERIFY_REQUIRED) | CAPABILITY | ARCH-AUTO-VERIFY | FROZEN |
| DN-FRZ-DATA | Data / scenario / seed freeze (SplitManifests, ScenarioSet, SeedSet) | FREEZE | ARCH-DATA-LINEAGE, ARCH-SIM-SCENARIO | FROZEN |
| DN-FRZ-SCENSET | Scenario set (FBC-01 scenario families) | FREEZE | ARCH-SIM-SCENARIO | FROZEN |
| DN-SCH-CF | Counterfactual schedule evaluation | CAPABILITY | ARCH-SCH-ENGINE, ARCH-WORLD-FORK | FROZEN |
| DN-SCH-CPSAT | CP-SAT recovery scheduling | CAPABILITY | ARCH-SCH-ENGINE | FROZEN |
| DN-SCH-DYN | Dynamic / event-triggered rescheduling on real state | CAPABILITY | ARCH-SCH-ENGINE | FROZEN |
| DN-SCH-HEUR | Heuristic/baseline dispatch (FIFO/EDD/CR/SPT/SRPT) over generated instances | CAPABILITY | ARCH-SCH-HEURISTIC | FROZEN |
| DN-SCH-PLANCON | RecoveryPlan contract | CONTRACT | ARCH-SCH-PLAN, ARCH-CTR-EVTSCHEMA | FROZEN |
| DN-SCH-VALID | Independent ScheduleValidator | CAPABILITY | ARCH-SCH-VALIDATOR | FROZEN |
| DN-SIM-COREINT | Simulator/Core integration (Core-validated physical commands, events) | CAPABILITY | ARCH-SIM-ENGINE, ARCH-CTR-CMDSCHEMA | FROZEN |
| DN-SIM-DISPIF | Simulator dispatch-decision interface + deterministic baseline dispatch | CONTRACT | ARCH-SIM-ENGINE, ARCH-CTR-CMDSCHEMA | FROZEN |
| DN-SIM-KERNEL | DES kernel (event queue, clock, named RNG) | CAPABILITY | ARCH-SIM-ENGINE, ARCH-SIM-CLOCK | FROZEN |
| DN-SIM-OPSEM | Operational semantics (reentrant routing, queues, failures, maintenance, rework) | CAPABILITY | ARCH-SIM-ENGINE | FROZEN |
| DN-SIM-ORACLE | Oracle isolation (evaluator-only stream/credentials) | CAPABILITY | ARCH-SIM-ORACLE, ARCH-WORLD-EVALZONE | FROZEN |
| DN-SIM-REALISM | Simulation validation evidence (RL-3, RealismBenchmarkSuite) | EVIDENCE | ARCH-SIM-ENGINE | FROZEN |
| DN-SIM-SNAPFORK | Snapshot / Fork / counterfactual worlds | CAPABILITY | ARCH-SIM-SNAPSHOT, ARCH-WORLD-FORK | FROZEN |
| DN-SIM-SYNTH | Synthetic operational data / generated history (ScenarioInstances) | DATA | ARCH-SIM-SCENARIO | FROZEN |

**ARCH components touched:** `ARCH-AI-ORCH`, `ARCH-AI-PROPOSAL`, `ARCH-AI-TOOLS`, `ARCH-AUTO-ACTIONCAT`, `ARCH-AUTO-IDEMPOTENCY`, `ARCH-AUTO-VERIFY`, `ARCH-AUTO-WORKFLOW`, `ARCH-CORE-CMD`, `ARCH-CORE-DOMAIN`, `ARCH-CTR-CMDSCHEMA`, `ARCH-CTR-EVTSCHEMA`, `ARCH-DATA-LINEAGE`, `ARCH-EDGE-AUTH`, `ARCH-EDGE-BFF`, `ARCH-EDGE-WEB`, `ARCH-EVT-BROKER`, `ARCH-EVT-CONSUMER`, `ARCH-EVT-OUTBOX`, `ARCH-HITL-APPROVAL`, `ARCH-HITL-EXPIRY`, `ARCH-HITL-POLICY`, `ARCH-OBS-AUDIT`, `ARCH-OBS-HEALTH`, `ARCH-PLAT-COMPOSE`, `ARCH-SCH-ENGINE`, `ARCH-SCH-HEURISTIC`, `ARCH-SCH-PLAN`, `ARCH-SCH-VALIDATOR`, `ARCH-SEC-AUTHZ`, `ARCH-SEC-IDP`, `ARCH-SIM-CLOCK`, `ARCH-SIM-ENGINE`, `ARCH-SIM-ORACLE`, `ARCH-SIM-SCENARIO`, `ARCH-SIM-SNAPSHOT`, `ARCH-TWIN-API`, `ARCH-TWIN-FRESHNESS`, `ARCH-TWIN-PROJECTOR`, `ARCH-TWIN-STATE`, `ARCH-VIS-EVAL`, `ARCH-VIS-INFER`, `ARCH-WORLD-EVALZONE`, `ARCH-WORLD-FORK`, `ARCH-WORLD-ISOLATION`, `ARCH-WORLD-REGISTRY`, `ARCH-WORLD-SCOPE`.

## 4. Owned FR/NFR Families

Ownership here means PrimaryOwner in the 01 catalogue: this role is accountable for the requirement's correctness, its trace mapping (03) and its final disposition.

### 4.FAUTO FR-AUTO (14)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-AUTO-001 | F0 | WP-AUTO-001 | TEST-AUTO-WORKFLOW, E2E-01, AV-SCEN-01, BENCH-AUTO-001, BENCH-E2E-001 |
| FR-AUTO-002 | F1 | WP-AUTO-001 | TEST-AUTO-WORKFLOW, E2E-01, AV-SCEN-01 |
| FR-AUTO-003 | F1 | WP-AUTO-001 | TEST-AUTO-WORKFLOW, TEST-AUTO-RESTART-001, AV-SCEN-06 |
| FR-AUTO-004 | F1 | WP-AUTO-003, WP-RES-009 | TEST-AUTO-FRESHNESS, AV-SCEN-04, AV-SCEN-01 |
| FR-AUTO-005 | F1 | WP-AUTO-002 | TEST-AUTO-RESTART-001, RES-DUP-001 |
| FR-AUTO-006 | F1 | WP-AUTO-002, WP-TEST-004 | TEST-AUTO-RESTART-001, RES-WORKER-001, AV-SCEN-06 |
| FR-AUTO-007 | F1 | WP-AUTO-005 | TEST-AUTO-OUTCOME, AV-SCEN-01 |
| FR-AUTO-008 | F1 | WP-AUTO-005, WP-TEST-003, WP-RES-008 | AV-SCEN-01, RES-WORKER-001, BENCH-E2E-001 |
| FR-AUTO-009 | F1 | WP-AUTO-005 | TEST-AUTO-OUTCOME, RES-DUP-001 |
| FR-AUTO-010 | F1 | WP-AUTO-003 | TEST-AUTO-FRESHNESS, AV-SCEN-10 |
| FR-AUTO-011 | F1 | WP-AUTO-006 | TEST-AUTO-ACTIONCAT, TEST-SEC-AUDIT |
| FR-AUTO-012 | F1 | WP-AUTO-004 | TEST-AUTO-ACTIONCAT, TEST-AUTH-NEG |
| FR-AUTO-013 | F1 | WP-AUTO-004 | TEST-AUTO-ACTIONCAT, TEST-AUTH-NEG, AV-SCEN-04 |
| FR-AUTO-014 | F0 | WP-AUTO-007, WP-TEST-006, WP-BENCH-002 | E2E-01, AV-SCEN-01, DEMO-GS01-001, BENCH-E2E-001 |

### 4.FSCH FR-SCH (15)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-SCH-001 | F0 | WP-SCH-002 | TEST-SCH-CONSTRAINTS, E2E-01, AV-SCEN-02, BENCH-SCH-001, BENCH-E2E-001 |
| FR-SCH-002 | F1 | WP-SCH-004 | TEST-SCH-REPLAN, BENCH-SCH-001 |
| FR-SCH-003 | F1 | WP-SCH-004, WP-RES-008 | TEST-SCH-REPLAN, AV-SCEN-02, BENCH-RQ2-001 |
| FR-SCH-004 | F1 | WP-SCH-003 | TEST-SCH-CONSTRAINTS, BENCH-SCH-001 |
| FR-SCH-005 | F0 | WP-VALID-001, WP-TEST-006 | TEST-SCH-VALIDATOR, E2E-01, AV-SCEN-01, AV-SCEN-02, BENCH-SCH-001, BENCH-E2E-001 |
| FR-SCH-006 | F1 | WP-VALID-002 | TEST-SCH-VALIDATOR, AV-SCEN-01 |
| FR-SCH-007 | F1 | WP-SCH-002 | TEST-SCH-PLAN, TEST-AUTO-FRESHNESS |
| FR-SCH-008 | F1 | WP-SCH-002 | TEST-SCH-PLAN, AV-SCEN-01 |
| FR-SCH-009 | F1 | WP-SCH-003, WP-R2-002 | TEST-SCH-CONSTRAINTS, BENCH-SCH-001, BENCH-PERF-SCH |
| FR-SCH-010 | F1 | WP-SCH-001, WP-RES-006 | BENCH-SCH-001, BENCH-RQ2-001 |
| FR-SCH-011 | F1 | WP-SCH-007 | BENCH-SCH-001, BENCH-RQ2-001 |
| FR-SCH-012 | F1 | WP-SCH-005 | TEST-SCH-FALLBACK, BENCH-PERF-SCH |
| FR-SCH-013 | F1 | WP-SCH-006, WP-RES-008 | TEST-SCH-COUNTERFACTUAL, AV-SCEN-09, BENCH-RQ2-001 |
| FR-SCH-014 | F1 | WP-VALID-002 | TEST-SCH-VALIDATOR, TEST-AUTH-NEG, AV-SCEN-01, BENCH-RQ3-001 |
| FR-SCH-015 | F1 | WP-SCH-002 | TEST-SCH-PLAN, TEST-UI-PLAN, AV-SCEN-01 |

### 4.FSIM FR-SIM (14)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-SIM-001 | F0 | WP-SIM-001, WP-SIM-009 | TEST-SIM-KERNEL, E2E-01, AV-SCEN-01, BENCH-SIMVAL-001 |
| FR-SIM-002 | F0 | WP-SIM-003 | TEST-SIM-KERNEL, E2E-01, AV-SCEN-02, BENCH-SIMVAL-001 |
| FR-SIM-003 | F1 | WP-SIM-003 | TEST-SIM-KERNEL, AV-SCEN-02, BENCH-SIMVAL-001 |
| FR-SIM-004 | F1 | WP-SIM-003 | TEST-SIM-KERNEL, AV-SCEN-02, BENCH-RQ2-001 |
| FR-SIM-005 | F1 | WP-SIM-003 | TEST-SIM-KERNEL, BENCH-SIMVAL-001, AV-SCEN-02, BENCH-E2E-001 |
| FR-SIM-006 | F1 | WP-SIM-003 | TEST-SIM-KERNEL, BENCH-SIMVAL-001, BENCH-E2E-001 |
| FR-SIM-007 | F1 | WP-SIM-001, WP-SIM-007 | TEST-SIM-DETERMINISM, BENCH-SIMVAL-001 |
| FR-SIM-008 | F1 | WP-SIM-002 | TEST-SIM-DETERMINISM, BENCH-SIMVAL-001, REPRO-NONOWNER-001 |
| FR-SIM-009 | F1 | WP-SIM-004 | TEST-SIM-SNAPSHOT, AV-SCEN-09 |
| FR-SIM-010 | F1 | WP-SIM-004 | TEST-SIM-SNAPSHOT, AV-SCEN-09, BENCH-RQ2-001 |
| FR-SIM-011 | F1 | WP-SIM-004, WP-TEST-005 | TEST-SIM-ISOLATION, AV-SCEN-09, AV-SCEN-10 |
| FR-SIM-012 | F1 | WP-SIM-005, WP-TEST-005 | TEST-SIM-ISOLATION, AV-SCEN-11, TEST-SEC-ORACLE-NEG, BENCH-RQ3-001 |
| FR-SIM-013 | F1 | WP-SIM-006 | TEST-SIM-DECISIONIF, AV-SCEN-02, BENCH-RQ2-001 |
| FR-SIM-014 | F1 | WP-SIM-006 | TEST-SIM-DECISIONIF, TEST-SIM-ISOLATION, AV-SCEN-01, AV-SCEN-11 |

### 4.FUI FR-UI (2)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-UI-005 | F1 | WP-UI-005 | TEST-UI-PLAN, AV-SCEN-01, DEMO-GS01-001 |
| FR-UI-007 | F1 | WP-UI-007 | TEST-UI-PLAN, AV-SCEN-01, DEMO-GS01-001 |

### 4.NCAP NFR-CAP (6)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-CAP-001 | A1 | sustained operation without semantic degradation | ≥100 tools / 1,000 active lots | WP-SIM-008, WP-PERF-003 |
| NFR-CAP-002 | A1 | corruption / cross-world leakage / invalid transition / OOM counts | all = 0 at 200 tools / 2,000 lots | WP-SIM-008, WP-PERF-003 |
| NFR-CAP-003 | A1 | discrete events processed without correctness failure | ≥ 250,000 events | WP-SIM-008 |
| NFR-CAP-006 | A1 | NFR-PERF-008 satisfaction at normal scheduling scale | ≤100 eligible lots / ≤50 tools within 30 s | WP-SCH-005, WP-PERF-006 |
| NFR-CAP-007 | C3 | feasibility rate, solve time, solution quality, fallback rate | C3 — characterize | WP-SCH-005, WP-PERF-006 |
| NFR-CAP-008 | A1 | simultaneously active/waiting workflows; lost state; duplicate effects | 50 workflows; lost = 0; duplicates = 0 | WP-AUTO-007, WP-PERF-003 |

### 4.NPERF NFR-PERF (3)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-PERF-008 | A1 | wall-clock to validator-feasible candidate / accepted fallback / explicit failure | ≤ 30 s for every instance | WP-SCH-005, WP-PERF-006 |
| NFR-PERF-011 | S2 | authorization-ready step → verified Core/Twin effect overhead (human wait excluded) | p95 ≤ 10 s | WP-AUTO-007, WP-PERF-002 |
| NFR-PERF-013 | S2 | inspection evidence available → verified final recovery state (system-controlled) | p95 ≤ 120 s (excl. human, sim waits, provider outage) | WP-AUTO-007, WP-PERF-002, WP-BENCH-002, WP-DOC-004 |

### 4.NREL NFR-REL (2)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REL-001 | H0 | duplicate protected manufacturing effects across duplicate/retry/restart suites | = 0 | WP-AUTO-002, WP-PERF-005, WP-BENCH-003 |
| NFR-REL-004 | A1 | worker crash/restart → durable processing resumed; duplicate verified effects | ≤ 5 min; duplicates = 0 | WP-AUTO-002, WP-PERF-004 |

### 4.NREP NFR-REP (1)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REP-001 | H0 | final state + deterministic event sequence/hash equality for same release/scenario/state/seed | identical | WP-SIM-002, WP-SIM-009 |

## 5. Critical Contracts

| Node | Contract surface | Readiness deadline | Consumers (owner, edge) |
|---|---|---|---|
| DN-SIM-DISPIF | Simulator dispatch-decision interface + deterministic baseline dispatch | CONTRACT_READY by M2 (S4) | DN-SCH-DYN (Batu, DEP-088) |
| DN-SCH-PLANCON | RecoveryPlan contract | CONTRACT_READY by E2E-01 readiness (end S4) | DN-HITL-APPROVAL (Asrın, DEP-092); DN-AUTO-EXEC (Batu, DEP-101); CK-E2E01 (N/A — no single owner (Item 67 #213), DEP-180) |

Contract obligations follow 05 DEP-RULE-04: a fixture satisfies development-stage consumption only; milestone and final evidence require the real capability behind the contract.

### 5.1 Contracts this role consumes

| DEP | Contract node (owner) | Consumed by | Required readiness | Need-by | Precise requirement declared (05 DEP-RULE-06) |
|---|---|---|---|---|---|
| DEP-038 | DN-CORE-CONTRACTS (Asrın) | DN-SIM-OPSEM | CONTRACT_READY | S2 | reentrant lifecycle, hold/rework semantics |
| DEP-079 | DN-CORE-SNAPCON (Asrın) | DN-SCH-DYN | CONTRACT_READY | E2E-01 readiness (end S4) | to be completed at WorkItem READY |
| DEP-096 | DN-AI-ACTCON (Asrın) | DN-AUTO-EXEC | CONTRACT_READY | E2E-01 readiness (end S4) | to be completed at WorkItem READY |
| DEP-097 | DN-CORE-CMDCON (Asrın) | DN-AUTO-EXEC | CONTRACT_READY | E2E-01 readiness (end S4) | Automation cannot invent command semantics (#43) |

### 5.2 Verification assets owned by this role

Planned verification families whose semantic correctness belongs to this role (03 §9.X). Asset identities are planning-level; numeric TestIDs are allocated when the assets are created.

| Family | Kind | Scope | Lane / tier | Min environment | Work packages relying on it |
|---|---|---|---|---|---|
| TEST-SIM-KERNEL | TEST | DES kernel mechanics: reentrant routing, queues, availability/failure/repair, maintenance, rework | ENG-A | CI | WP-SIM-001, WP-SIM-003, WP-SIM-009 |
| TEST-SIM-DETERMINISM | TEST | Named seeded RNG streams + same-seed replay state/event-hash equivalence | ENG-G | CI | WP-SIM-001, WP-SIM-002, WP-SIM-007, WP-SIM-008, WP-SIM-009 |
| TEST-SIM-SNAPSHOT | TEST | Snapshot, restore and fork into new WorldID | ENG-B | CI | WP-SIM-004 |
| TEST-SIM-ISOLATION | TEST | Counterfactual non-mutation of primary world + Oracle stream/namespace inaccessibility (negative) | ENG-C | CI | WP-SIM-004, WP-SIM-005, WP-SIM-006, WP-TEST-005 |
| TEST-SIM-DECISIONIF | TEST | External dispatch/planning decision contract acceptance + operational state/event exposure without Oracle fields | ENG-B | CI | WP-SIM-006 |
| BENCH-SIMVAL-001 | BENCH | SimulationValidationRun / RealismBenchmarkSuite: V-MICRO-01..06, RV-01..15, IndependentKPIRecalculator, RL-3 target | RQ2 | EVALUATION | WP-SIM-001, WP-SIM-002, WP-SIM-003, WP-SIM-007, WP-SIM-009 |
| TEST-SCH-CONSTRAINTS | TEST | Property-based hard-constraint feasibility (not golden snapshots only, TEST-INV-17) | ENG-B | CI | WP-R2-002, WP-SCH-002, WP-SCH-003 |
| TEST-SCH-VALIDATOR | TEST | Independent ScheduleValidator: infeasible plan rejection, eligibility blocking, AI-origin plans included | ENG-C | CI | WP-TEST-006, WP-VALID-001, WP-VALID-002 |
| TEST-SCH-PLAN | TEST | RecoveryPlan contract: snapshot revision binding, assignments, rationale/objective fields | ENG-B | CI | WP-SCH-002 |
| TEST-SCH-REPLAN | TEST | Rolling-horizon + event-triggered rescheduling for accepted disruption classes | ENG-A | CI | WP-RES-008, WP-SCH-004 |
| TEST-SCH-FALLBACK | TEST | Bounded fallback / explicit failure state when CP-SAT cannot return valid plan | ENG-D | CI | WP-PERF-006, WP-SCH-005 |
| TEST-SCH-COUNTERFACTUAL | TEST | Counterfactual plan evaluation in isolated fork WorldID | ENG-C | CI | WP-RES-008, WP-SCH-006 |
| BENCH-SCH-001 | BENCH | Scheduler component benchmark (8 families × 30 paired seeds) incl. baselines and churn/stability metrics | SCHEDULER | EVALUATION | WP-R2-002, WP-RES-006, WP-SCH-001, WP-SCH-002, WP-SCH-003, WP-SCH-004 |
| BENCH-RQ2-001 | BENCH | RQ-2 dynamic closed-loop recovery (4 families × 20 paired seeds, realized execution outcome) | RQ2 | EVALUATION | WP-RES-006, WP-RES-008, WP-SCH-001, WP-SCH-004, WP-SCH-006, WP-SCH-007 |
| TEST-AUTO-WORKFLOW | TEST | Temporal workflow semantics: durable approval wait, timers, activity boundaries | ENG-A | CI | WP-AUTO-001 |
| TEST-AUTO-FRESHNESS | TEST | Pre-execution revalidation of proposal/plan/state freshness, WorldID and action identity | ENG-C | CI | WP-AUTO-003, WP-RES-009, WP-SCH-002 |
| TEST-AUTO-RESTART-001 | TEST | Worker crash / restart-before-command / duplicate delivery / restart-after-effect / restart-before-verification | ENG-D | CI | WP-AUTO-001, WP-AUTO-002, WP-BENCH-003, WP-PERF-005, WP-TEST-004 |
| TEST-AUTO-OUTCOME | TEST | ACK ≠ effect; lost/ambiguous response → UNKNOWN_VERIFY_REQUIRED; Core/Twin effect verification | ENG-B | CI | WP-AUTO-005, WP-CORE-003, WP-CORE-008 |
| TEST-AUTO-ACTIONCAT | TEST | ActionCatalog-only execution; no self-authorization; inspectable history | ENG-C | CI | WP-AUTO-004, WP-AUTO-006 |
| BENCH-AUTO-001 | BENCH | Automation/workflow evaluation lane (durability/effect result) | AUTOMATION | EVALUATION | WP-AUTO-001 |
| TEST-UI-PLAN | TEST | Plan/validation-status and workflow progress views | ENG-A | INTEGRATION | WP-SCH-002, WP-UI-005, WP-UI-007 |
| AV-SCEN-02 | SCENARIO | Architecture validation scenario: Equipment disruption → dynamic rescheduling | AVG | INTEGRATION | WP-CORE-001, WP-RES-008, WP-SCH-002, WP-SCH-004, WP-SIM-003, WP-SIM-006 |
| AV-SCEN-06 | SCENARIO | Architecture validation scenario: Workflow worker crash and restart | AVG | INTEGRATION | WP-AUTO-001, WP-AUTO-002, WP-BENCH-003, WP-PERF-004, WP-PERF-005, WP-TEST-004 |
| AV-SCEN-09 | SCENARIO | Architecture validation scenario: Counterfactual fork isolation | AVG | INTEGRATION | WP-EVT-002, WP-RES-008, WP-SCH-006, WP-SIM-004, WP-TEST-005, WP-TWIN-002 |
| BENCH-PERF-SCH | BENCH | SP-NORMAL decision budget and SP-STRESS frontier (feasibility, solve time, quality, fallback rate) | PERF | EVALUATION | WP-PERF-006, WP-R2-002, WP-SCH-003, WP-SCH-005 |
| BENCH-PERF-WF | BENCH | Workflow control-plane overhead, approval persistence, GS-01 system-controlled duration, workflow concurrency | PERF | EVALUATION | WP-AUTO-007, WP-BENCH-002, WP-DOC-004, WP-HITL-004, WP-PERF-002, WP-PERF-003 |
| BENCH-CAP-WORLD | BENCH | WP-NORMAL / WP-STRESS operational world and ≥250,000-event simulator stress | PERF | EVALUATION | WP-PERF-003, WP-SIM-008 |
| RES-WORKER-001 | DRILL | Workflow-worker crash/restart resumption without duplicate verified effect (AV-SCEN-06 execution) | ENG-D | INTEGRATION | WP-AUTO-002, WP-AUTO-005, WP-PERF-004, WP-RES-008, WP-TEST-003, WP-TEST-004 |
| RES-DUP-001 | DRILL | Duplicate/retry/restart protected-effect suite aggregation (AV-SCEN-05/06 + TEST-AUTO-RESTART-001) | ENG-D | EVALUATION | WP-AUTO-002, WP-AUTO-005, WP-AUTO-007, WP-BENCH-003, WP-CORE-003, WP-EVT-003 |

## 6. Upstream Dependencies

What this role must receive from others before it can pass a stage. Fixture-satisfiable rows are marked; the rest require the real upstream capability.

| DEP | Predecessor (owner) | Feeds node | Kind | Strength | Stage | Required readiness | Need-by | Fallback | Unblock evidence |
|---|---|---|---|---|---|---|---|---|---|
| DEP-038 | DN-CORE-CONTRACTS (Asrın) | DN-SIM-OPSEM | CONTRACT | HARD | START | CONTRACT_READY | S2 | F1 | contract merged + contract tests green + example fixture published (reviewed by Batu) |
| DEP-039 | DN-CORE-TRANSITIONS (Asrın) | DN-SIM-OPSEM | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M2 (S4) | — | Simulator manufacturing-validity checks against Core legality |
| DEP-041 | DN-CORE-CMDEXEC (Asrın) | DN-SIM-COREINT | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | M2 (S4) | — | Core-validated physical commands executed by Simulator |
| DEP-042 | DN-EVT-SPINE (Asrın) | DN-SIM-COREINT | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | M2 (S4) | — | real cross-boundary integration test green on INTEGRATION |
| DEP-045 | DN-RT-OBJ (Yavuz) | DN-SIM-SNAPFORK | RUNTIME | SOFT | INTEGRATION | INTEGRATION_READY | M2 (S4) | F1 | snapshot checkpoints stored as object artifacts |
| DEP-079 | DN-CORE-SNAPCON (Asrın) | DN-SCH-DYN | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | F1 | contract merged + contract tests green + example fixture published |
| DEP-080 | DN-TWIN-PROJ (Asrın) | DN-SCH-DYN | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | M2 (S4) | — | SchedulingSnapshot exported from real Twin |
| DEP-096 | DN-AI-ACTCON (Asrın) | DN-AUTO-EXEC | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | F1 | contract merged + contract tests green + example fixture published |
| DEP-097 | DN-CORE-CMDCON (Asrın) | DN-AUTO-EXEC | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | F1 | contract merged + contract tests green + example fixture published (typed command client) |
| DEP-098 | DN-CORE-CMDEXEC (Asrın) | DN-AUTO-EXEC | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 readiness (end S4) | — | Core applies approved command idempotently and emits result (#187) |
| DEP-047 | DN-SEC-BASE (Yavuz) | DN-SIM-ORACLE | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | E2E-01 (end S5) | F0 | normal runtime credentials denied Oracle access (negative test) |
| DEP-082 | DN-CORE-TRANSITIONS (Asrın) | DN-SCH-VALID | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | — | validator uses canonical domain rules (no unilateral legality) |
| DEP-095 | DN-RT-TEMPORAL (Yavuz) | DN-AUTO-DURABLE | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 formal run (end S5) | — | workflow persists through worker restart on real Temporal |
| DEP-099 | DN-HITL-APPROVAL (Asrın) | DN-AUTO-EXEC | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | F0 | valid approval required for protected execution — no fallback |
| DEP-103 | DN-TWIN-VERIFY (Asrın) | DN-AUTO-VERIFY | CAPABILITY | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | F0 | verified Core/Twin effect (HTTP success insufficient) |
| DEP-089 | DN-AI-RCA (Asrın) | DN-SCH-DYN | CAPABILITY | SOFT | INTEGRATION | COMPONENT_READY | M3 (S6) | F2 | trigger/objective context may come from AI, human or policy |
| DEP-104 | DN-AI-RCA (Asrın) | DN-AUTO-EXEC | CAPABILITY | SOFT | INTEGRATION | COMPONENT_READY | M3 (S6) | F2 | deterministic/human proposals allowed for testing |
| DEP-081 | DN-EVT-SPINE (Asrın) | DN-SCH-DYN | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M4 (S8) | — | event-triggered replanning on failures/holds/excursions |
| DEP-129 | DN-RES-CALIB (Asrın) | DN-FRZ-DATA | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | — | calibration closed before freeze |
| DEP-131 | DN-FRZ-RQ4SPLIT (Selman) | DN-FRZ-DATA | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | — | Vision split frozen before final RQ-4 training/evaluation |

## 7. Downstream Consumers

What others cannot do until this role delivers. Every row is a commitment with a need-by point.

| DEP | Delivered node | Consumer (owner) | Kind | Strength | Stage | Required readiness | Need-by | Unblock evidence |
|---|---|---|---|---|---|---|---|---|
| DEP-035 | DN-SIM-COREINT | DN-TWIN-PROJ (Asrın) | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | M2 (S4) | Twin reflects simulated reentrant world |
| DEP-092 | DN-SCH-PLANCON | DN-HITL-APPROVAL (Asrın) | CONTRACT | HARD | INTEGRATION | CONTRACT_READY | E2E-01 readiness (end S4) | contract merged + contract tests green + example fixture published |
| DEP-074 | DN-SIM-SYNTH | DN-ML (Asrın) | DATA | HARD | MILESTONE_EXIT | EVALUATION_READY | M4 (S8) | sufficient historical data/features/labels generated |
| DEP-062 | DN-SIM-COREINT | DN-VIS-EPISODES (Selman) | DATA | HARD | MILESTONE_EXIT | INTEGRATION_READY | M5 | ScenarioEpisodes with genealogy/state generated |
| DEP-121 | DN-SIM-SYNTH | DN-RES-DATASCEN (Asrın) | DATA | HARD | MILESTONE_EXIT | EVALUATION_READY | M5 (S10) | evaluation-ready scenarios/data with partitions |
| DEP-132 | DN-FRZ-DATA | DN-FRZ-MODEL (Asrın) | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | model/policy selection on frozen data |
| DEP-135 | DN-FRZ-DATA | DN-FRZ-PROTOCOL (Asrın) | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | dataset/scenario selection before protocol freeze |
| DEP-138 | DN-SIM-REALISM | DN-FRZ-PROTOCOL (Asrın) | EVIDENCE | HARD | FREEZE | EVALUATION_READY | M6 (S11) | Simulation validation before final RQ-2 claim |
| DEP-153 | DN-SCH-CPSAT | DN-FRZ-MODEL (Asrın) | CAPABILITY | HARD | FREEZE | EVALUATION_READY | M6 | SchedulerPolicy selected |
| DEP-154 | DN-SCH-CF | DN-FRZ-PROTOCOL (Asrın) | CAPABILITY | HARD | FREEZE | EVALUATION_READY | M6 | counterfactual recovery evaluation ready (CRN) |

**Delivery load by consumer:** Asrın: 9 HARD edges, Selman: 1 HARD edges.

## 8. Milestone-by-Milestone Engineering Objectives

### 8.M0 M0 — Engineering Foundation Ready (End S1 / Week 2)

Batu's work is the least blocked in the programme (Item 66 #47): the DES kernel, clock and named RNG streams can start immediately. The only external need in this window is the reviewed Core domain contract draft, which arrives as fixtures rather than as a finished Core.

_No work package of this role targets M0; the role contributes through review, support and preparation in this window._


### 8.M1 M1 — Integrated Spine (End S2 / Week 4)

During M1 the kernel becomes a usable simulation: deterministic replay, scenario-driven world initialization, and the first baseline dispatch policies operating on generated instances. Nothing here needs the integration environment yet — but everything here must be deterministic, because the paired-seed research design later depends on it.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-SIM-001 | Deterministic DES kernel | F0 | 3 | M |

**Owned requirements reaching their target in this window (2):** FR-SIM-001, FR-SIM-007

**Upstream gates that must close in this window (1):** DEP-038 from Asrın

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M2 M2 — Operational Manufacturing Alpha (End S4 / Week 8)

M2 is the operational world milestone: reentrant routing aligned to Core legality, queues, equipment failure/repair, maintenance, rework, and the Simulator/Core integration in which Core-validated commands produce simulated effects that flow back through the event spine into the Twin. The Scheduler starts consuming real snapshots and produces plans with rationale.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-SIM-002 | Determinism, replay and event-hash equivalence | F1 | 3 | M |
| WP-SIM-003 | Operational semantics: reentrant routing, queues, failures, maintenance, rework | F0 | 4 | L |
| WP-SIM-006 | External dispatch decision interface and operational telemetry | F0 | 3 | M |
| WP-SCH-001 | Dispatch baselines and scheduling instance model | F1 | 3 | S |

**Owned requirements reaching their target in this window (10):** FR-SCH-010, FR-SIM-002, FR-SIM-003, FR-SIM-004, FR-SIM-005, FR-SIM-006, FR-SIM-008, FR-SIM-013, FR-SIM-014, NFR-REP-001

**Upstream gates that must close in this window (8):** DEP-039 from Asrın, DEP-041 from Asrın, DEP-042 from Asrın, DEP-079 from Asrın, DEP-080 from Asrın, DEP-096 from Asrın, DEP-097 from Asrın, DEP-098 from Asrın

**Commitments owed to others in this window (2):** DEP-035 → Asrın, DEP-092 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M3 M3 — Closed-Loop Alpha (End S6 / Week 12)

M3 closes the loop through Batu's hand: the independent ScheduleValidator gates execution eligibility, the Temporal workflow waits durably for approval, revalidates freshness, dispatches Core commands with idempotency keys and verifies the effect against Core/Twin. Batu reviews the scenario/Scheduler/Automation path before E2E-01 and owns the scenario semantics of the checkpoint (Item 67 #214, #217).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-SIM-005 | Oracle isolation and evaluator-only data plane | F0 | 3 | M |
| WP-SCH-002 | Snapshot consumption and recovery plan contract | F0 | 3 | M |
| WP-VALID-001 | Independent schedule validator | F0 | 3 | M |
| WP-VALID-002 | Execution eligibility gate and AI-origin plan routing | F1 | 3 | S |
| WP-AUTO-001 | Durable workflow bundle and approval wait | F0 | 4 | M |
| WP-AUTO-003 | Pre-execution revalidation and command identity | F1 | 3 | S |
| WP-AUTO-004 | ActionCatalog and authorization gate | F1 | 3 | S |
| WP-AUTO-005 | Outcome model and effect verification | F0 | 3 | M |
| WP-TEST-006 | E2E-01 checkpoint execution | F0 | 3 | M |

**Owned requirements reaching their target in this window (19):** FR-AUTO-001, FR-AUTO-002, FR-AUTO-003, FR-AUTO-004, FR-AUTO-007, FR-AUTO-008, FR-AUTO-009, FR-AUTO-010, FR-AUTO-012, FR-AUTO-013, FR-AUTO-014, FR-SCH-001, FR-SCH-005, FR-SCH-006, FR-SCH-007, FR-SCH-008, FR-SCH-014, FR-SCH-015, FR-SIM-012

**Upstream gates that must close in this window (5):** DEP-047 from Yavuz, DEP-082 from Asrın, DEP-095 from Yavuz, DEP-099 from Asrın, DEP-103 from Asrın

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M4 M4 — Mandatory Core Feature Complete (End S8 / Week 16)

M4 completes mandatory control capability: CP-SAT recovery scheduling within the decision budget, rolling-horizon and event-triggered replanning, counterfactual evaluation on forked worlds, the full ActionCatalog with risk classes, restart-safe idempotent execution, and the GS-01 recovery workflow end to end. Snapshot/fork must be solid because RQ-2 depends on it.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-SIM-004 | Snapshot, fork and world isolation | F1 | 3 | M |
| WP-SIM-007 | Scenario versioning and synthetic operational history | F1 | 3 | M |
| WP-SCH-003 | CP-SAT model and hard constraints | F1 | 3 | M |
| WP-SCH-004 | Rolling horizon and event-triggered rescheduling | F1 | 3 | M |
| WP-SCH-006 | Counterfactual schedule evaluation on forked worlds | F1 | 3 | S |
| WP-AUTO-002 | Idempotency and restart safety for protected effects | F1 | 3 | M |
| WP-AUTO-007 | GS-01 recovery workflow and closed-loop timing | F0 | 3 | S |
| WP-UI-005 | Planning and validation views | F1 | 3 | S |
| WP-UI-007 | Workflow progress and verification view | F1 | 3 | S |

**Owned requirements reaching their target in this window (19):** FR-AUTO-005, FR-AUTO-006, FR-AUTO-014, FR-SCH-002, FR-SCH-003, FR-SCH-004, FR-SCH-009, FR-SCH-013, FR-SIM-007, FR-SIM-009, FR-SIM-010, FR-SIM-011, FR-UI-005, FR-UI-007, NFR-CAP-008, NFR-PERF-011, NFR-PERF-013, NFR-REL-001, NFR-REL-004

**Upstream gates that must close in this window (1):** DEP-081 from Asrın

**Commitments owed to others in this window (1):** DEP-074 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M5 M5 — Reliability & Evaluation Ready (End S10 / Week 20)

M5 hardens and prepares evidence: fallback and explicit failure states under budget pressure, churn/stability metrics, worker-crash and duplicate-delivery drills, scheduler performance at SP-NORMAL, and the scenario families and seeds that the research lanes will freeze. Simulation realism validation starts in earnest here.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-SCH-005 | Decision budget, fallback and explicit failure state | F1 | 3 | S |
| WP-SCH-007 | Schedule churn and stability metrics | F1 | 3 | S |
| WP-AUTO-006 | Workflow history and audit surface | F1 | 3 | S |
| WP-TEST-005 | Integration scenarios AV-SCEN-09…12 | F1 | 3 | M |

**Owned requirements reaching their target in this window (8):** FR-AUTO-011, FR-SCH-011, FR-SCH-012, FR-SIM-011, FR-SIM-012, NFR-CAP-006, NFR-CAP-007, NFR-PERF-008

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (2):** DEP-062 → Selman, DEP-121 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M6 M6 — Research Freeze (End S11 / Week 22)

M6 freezes Batu's research inputs: scenario set, seeds, scheduler policy and workflow versions, plus the realism evidence (RL-3 target) that is a hard precondition for any strong RQ-2 claim (Item 66 #87). A late scheduler tweak after this point is a protocol violation, not an optimization.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-SIM-009 | Simulation realism validation suite (RL-3) | R1 | 4 | M |
| WP-RES-008 | RQ-2 lane: dynamic recovery evaluation | R1 | 3 | M |

**Owned requirements reaching their target in this window (5):** FR-AUTO-008, FR-SCH-003, FR-SCH-013, FR-SIM-001, NFR-REP-001

**Upstream gates that must close in this window (2):** DEP-129 from Asrın, DEP-131 from Selman

**Commitments owed to others in this window (5):** DEP-132 → Asrın, DEP-135 → Asrın, DEP-138 → Asrın, DEP-153 → Asrın, DEP-154 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M7 M7 — Final Benchmark Complete (End S12 / Week 24)

During the campaign Batu executes the RQ-2 lanes (component 8×30 and full recovery 4×20 with realized execution outcomes), the scheduler component benchmark and the automation/workflow lane, and contributes the control-plane half of the MC-1 matrix.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-SIM-008 | Simulator capacity and scale validation | F1/A1 | 3 | S |
| WP-PERF-003 | Capacity and stress execution | F1/A1 | 3 | S |
| WP-PERF-006 | Scheduler performance frontier measurement | F1/A1 | 3 | S |

**Owned requirements reaching their target in this window (7):** NFR-CAP-001, NFR-CAP-002, NFR-CAP-003, NFR-CAP-006, NFR-CAP-007, NFR-CAP-008, NFR-PERF-008

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

M8 closes with RQ-2 claim classification bounded by the achieved realism level, thesis material on execution-aware dynamic recovery, and confirmation that every Batu-owned requirement — including the hard-gate idempotency and verification requirements — has a final disposition.

_No work package of this role targets M8; the role contributes through review, support and preparation in this window._


## 9. Work Package Mapping

Each package below is owned by this role. Deliverables and tasks are the 04 definitions; the execution context (gates, consumers, verification, evidence) is projected here so the package can be picked up without cross-reading four documents.

### 9.WP-SIM-001 — Deterministic DES kernel

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-SIM-KERNEL |
| Supporting reviewer | Asrın |
| Source requirements | FR-SIM-001, FR-SIM-007 |
| Architecture | ARCH-SIM-CLOCK, ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO |
| Gating edges | none — early unlocker |
| Verification families | AV-SCEN-01, BENCH-SIMVAL-001, E2E-01, TEST-SIM-DETERMINISM, TEST-SIM-KERNEL |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- DES kernel module
- named RNG stream registry
- kernel unit/property test suite

**Major tasks.**
- implement event queue and clock advance
- implement per-concern RNG streams (arrival, processing, failure, repair, quality, inspection)
- expose scenario-driven world initialization
- property tests for event ordering and time monotonicity

**Cut/fallback.** No cut (F0). Custom Python kernel per backfill ADR 7; no external DES framework dependency.


### 9.WP-SCH-001 — Dispatch baselines and scheduling instance model

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-SCH-HEUR |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-010 |
| Architecture | ARCH-SCH-HEURISTIC, ARCH-VIS-EVAL |
| Gating edges | none — early unlocker |
| Verification families | BENCH-RQ2-001, BENCH-SCH-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- FIFO/EDD/CR/SPT/SRPT implementations
- BaselineDefinition records
- instance generator for offline testing

**Major tasks.**
- implement policies over a common decision interface
- validate against generated instances
- record baseline definitions for later comparison

**Cut/fallback.** F2 role: baselines are the approved fallback if CP-SAT integration slips, and are required as research baselines anyway.


### 9.WP-SIM-002 — Determinism, replay and event-hash equivalence

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-SIM-KERNEL |
| Supporting reviewer | Yavuz |
| Source requirements | FR-SIM-008, NFR-REP-001 |
| Architecture | ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO |
| Gating edges | none — early unlocker |
| Verification families | BENCH-SIMVAL-001, REPRO-NONOWNER-001, TEST-SIM-DETERMINISM |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- replay harness
- event-sequence hash computation
- determinism regression test

**Major tasks.**
- define canonical serialization for hashing
- implement replay from scenario+seed
- detect nondeterminism sources (dict ordering, time, threads)
- wire determinism check into CI

**Cut/fallback.** No cut; RQ-2 paired-seed design and reproducibility claims depend on it.


### 9.WP-SIM-003 — Operational semantics: reentrant routing, queues, failures, maintenance, rework

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M2 · S3–S4 |
| Readiness node | DN-SIM-OPSEM |
| Supporting reviewer | Asrın |
| Source requirements | FR-SIM-002, FR-SIM-003, FR-SIM-004, FR-SIM-005, FR-SIM-006 |
| Architecture | ARCH-SIM-ENGINE |
| Gating edges | DEP-037 (DN-SIM-KERNEL, S2), DEP-038 (DN-CORE-CONTRACTS, S2), DEP-039 (DN-CORE-TRANSITIONS, M2 (S4)) |
| Verification families | AV-SCEN-02, BENCH-E2E-001, BENCH-RQ2-001, BENCH-SIMVAL-001, E2E-01, TEST-SIM-KERNEL |
| Size band / status | L (≈7–12 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut (F0 world identity).


### 9.WP-SIM-006 — External dispatch decision interface and operational telemetry

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M2 · S3–S4 |
| Readiness node | DN-SIM-DISPIF |
| Supporting reviewer | Asrın |
| Source requirements | FR-SIM-013, FR-SIM-014 |
| Architecture | ARCH-CTR-CMDSCHEMA, ARCH-SIM-ENGINE, ARCH-WORLD-EVALZONE |
| Gating edges | DEP-043 (DN-SIM-KERNEL, S2) |
| Verification families | AV-SCEN-01, AV-SCEN-02, AV-SCEN-11, BENCH-RQ2-001, TEST-SIM-DECISIONIF, TEST-SIM-ISOLATION |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- dispatch decision contract + baseline policy implementation
- operational event/telemetry publication without oracle fields
- Simulator↔Core command acceptance path

**Major tasks.**
- define decision request/response contract
- implement deterministic baseline dispatch so Scheduler can plug in later (05 CYC-03)
- publish operational events through the spine
- verify no oracle field leaks into published data

**Cut/fallback.** No cut (F0).


### 9.WP-AUTO-001 — Durable workflow bundle and approval wait

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-AUTO-DURABLE |
| Supporting reviewer | Yavuz |
| Source requirements | FR-AUTO-001, FR-AUTO-002, FR-AUTO-003 |
| Architecture | ARCH-AUTO-ACTIONCAT, ARCH-AUTO-WORKFLOW, ARCH-HITL-APPROVAL |
| Gating edges | DEP-094 (DN-AUTO-DESIGN, S3), DEP-095 (DN-RT-TEMPORAL, E2E-01 formal run (end S5)) |
| Verification families | AV-SCEN-01, AV-SCEN-06, BENCH-AUTO-001, BENCH-E2E-001, E2E-01, TEST-AUTO-RESTART-001, TEST-AUTO-WORKFLOW |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut (F0). Stub activities unblock development before the runtime exists (05 CYC-04).


### 9.WP-AUTO-003 — Pre-execution revalidation and command identity

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-AUTO-EXEC |
| Supporting reviewer | Asrın |
| Source requirements | FR-AUTO-004, FR-AUTO-010 |
| Architecture | ARCH-AUTO-WORKFLOW, ARCH-HITL-EXPIRY, ARCH-WORLD-SCOPE |
| Gating edges | DEP-096 (DN-AI-ACTCON, E2E-01 readiness (end S4)), DEP-097 (DN-CORE-CMDCON, E2E-01 readiness (end S4)), DEP-098 (DN-CORE-CMDEXEC, E2E-01 readiness (end S4)), DEP-099 (DN-HITL-APPROVAL, E2E-01 (end S5)), DEP-100 (DN-AUTO-DURABLE, E2E-01 (end S5)), DEP-101 (DN-SCH-PLANCON, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, AV-SCEN-04, AV-SCEN-10, TEST-AUTO-FRESHNESS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- revalidation activity
- command identity fields (WorldID, revision, ActionID)
- stale-rejection tests (AV-SCEN-04)

**Major tasks.**
- define revalidation predicates per action
- implement fail-closed behaviour
- test stale plan/approval/state paths

**Cut/fallback.** No cut (hard gate).


### 9.WP-AUTO-004 — ActionCatalog and authorization gate

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-AI-ACTCON |
| Supporting reviewer | Asrın |
| Source requirements | FR-AUTO-012, FR-AUTO-013 |
| Architecture | ARCH-AUTO-ACTIONCAT, ARCH-HITL-POLICY |
| Gating edges | DEP-076 (DN-HITL-POLICY, S3–S4) |
| Verification families | AV-SCEN-04, TEST-AUTH-NEG, TEST-AUTO-ACTIONCAT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- ActionCatalog registry
- authorization gate in the execution path
- self-authorization negative tests

**Major tasks.**
- define catalog entries (risk level, preconditions, idempotency, valid world types)
- implement gate consulting AuthorityPolicy
- test unknown/forbidden/self-approved action attempts

**Cut/fallback.** No cut (F0-adjacent authority boundary).


### 9.WP-AUTO-005 — Outcome model and effect verification

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-AUTO-VERIFY |
| Supporting reviewer | Asrın |
| Source requirements | FR-AUTO-007, FR-AUTO-008, FR-AUTO-009 |
| Architecture | ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-TWIN-API |
| Gating edges | DEP-102 (DN-AUTO-EXEC, E2E-01 (end S5)), DEP-103 (DN-TWIN-VERIFY, E2E-01 (end S5)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, RES-DUP-001, RES-WORKER-001, TEST-AUTO-OUTCOME |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- AutomationOutcome contract (IC-AUTO-004)
- verification activity against Core events/Twin state
- UNKNOWN_VERIFY_REQUIRED path and reconciliation

**Major tasks.**
- define outcome states (ACCEPTED, VERIFIED_SUCCESS, FAILED, UNKNOWN_VERIFY_REQUIRED)
- implement verification queries and retry/backoff
- implement reconciliation procedure for ambiguous cases
- test lost-ACK scenarios

**Cut/fallback.** No cut (F0, hard gate DEP-INV-16).

**Integration checkpoint.** AV-SCEN-01, AV-SCEN-06


### 9.WP-SCH-002 — Snapshot consumption and recovery plan contract

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-SCH-PLANCON |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-001, FR-SCH-007, FR-SCH-008, FR-SCH-015 |
| Architecture | ARCH-CTR-EVTSCHEMA, ARCH-EDGE-BFF, ARCH-SCH-ENGINE, ARCH-SCH-HEURISTIC, ARCH-SCH-PLAN, ARCH-TWIN-FRESHNESS |
| Gating edges | DEP-083 (DN-SCH-DYN, E2E-01 (end S5)), DEP-084 (DN-SCH-VALID, E2E-01 (end S5)) |
| Verification families | AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, BENCH-SCH-001, E2E-01, TEST-AUTO-FRESHNESS, TEST-SCH-CONSTRAINTS, TEST-SCH-PLAN, TEST-UI-PLAN |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- snapshot consumption module
- RecoveryPlan contract (IC-SCH-004) + fixtures
- rationale/objective/comparison fields

**Major tasks.**
- implement snapshot → internal instance mapping
- implement plan serialization with source revision binding
- include rationale and objective summary for human review
- contract tests with Automation and HITL consumers

**Cut/fallback.** No cut (F0).


### 9.WP-SIM-005 — Oracle isolation and evaluator-only data plane

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-SIM-ORACLE |
| Supporting reviewer | Yavuz |
| Source requirements | FR-SIM-012, FR-SEC-010 |
| Architecture | ARCH-SEC-AUTHZ, ARCH-SIM-ORACLE, ARCH-WORLD-EVALZONE |
| Gating edges | DEP-046 (DN-SIM-KERNEL, S3), DEP-047 (DN-SEC-BASE, E2E-01 (end S5)) |
| Verification families | AV-SCEN-11, BENCH-RQ3-001, TEST-SEC-ORACLE-NEG, TEST-SIM-ISOLATION |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- Oracle stream/namespace separation
- EVALUATOR_ONLY credential scope
- negative access test (AV-SCEN-11)

**Major tasks.**
- define oracle data plane boundary
- implement separate subjects/schema and credentials
- implement runtime denial for normal service identities
- prove denial in INTEGRATION before E2E-01

**Cut/fallback.** No cut (F0 research validity; hard gate).

**Integration checkpoint.** AV-SCEN-11, E2E-01


### 9.WP-TEST-006 — E2E-01 checkpoint execution

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | CK-E2E01 |
| Supporting reviewer | Asrın |
| Source requirements | FR-VIS-016, FR-AI-001, FR-SCH-005, FR-AUTO-014, FR-HITL-007 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-TOOLS, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-EDGE-AUTH, ARCH-HITL-APPROVAL, ARCH-SCH-VALIDATOR, ARCH-SEC-IDP, ARCH-SIM-ENGINE, ARCH-VIS-INFER |
| Gating edges | DEP-178 (DN-VIS-SERVING, E2E-01 (end S5)), DEP-179 (DN-AI-RCA, E2E-01 (end S5)), DEP-180 (DN-SCH-PLANCON, E2E-01 (end S5)), DEP-181 (DN-SCH-VALID, E2E-01 (end S5)), DEP-182 (DN-HITL-APPROVAL, E2E-01 (end S5)), DEP-183 (DN-AUTO-DURABLE, E2E-01 (end S5)), DEP-184 (DN-AUTO-EXEC, E2E-01 (end S5)), DEP-185 (DN-AUTO-VERIFY, E2E-01 (end S5)), DEP-186 (DN-UI-APPROVAL, E2E-01 (end S5)), DEP-187 (DN-SIM-ORACLE, E2E-01 (end S5)) |
| Verification families | AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, BENCH-RQ1-001, BENCH-SCH-001, DEMO-GS01-001, E2E-01, TEST-AI-OUTPUT, TEST-SCH-VALIDATOR, TEST-SEC-AUTHN |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- E2E-SCENARIO-01 v1 definition
- dry-run report with failure classification
- E2E-RUN-A/B/C formal evidence

**Major tasks.**
- freeze the scenario (two lots, inspection condition, alternative tool)
- execute dry run and classify failures
- execute formal runs from approved main
- include duplicate-input and stale-approval negative gates

**Cut/fallback.** No cut. A manual patch invalidates the formal run (Item 67 #223); failures are expected engineering feedback in the dry run.

**Integration checkpoint.** E2E-01


### 9.WP-VALID-001 — Independent schedule validator

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M3 · S5–S6 |
| Readiness node | DN-SCH-VALID |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-005 |
| Architecture | ARCH-SCH-VALIDATOR |
| Gating edges | DEP-082 (DN-CORE-TRANSITIONS, E2E-01 (end S5)) |
| Verification families | AV-SCEN-01, AV-SCEN-02, BENCH-E2E-001, BENCH-SCH-001, E2E-01, TEST-SCH-VALIDATOR |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- validator module (independent code path)
- hard-constraint check set derived from Core rules
- negative test suite with infeasible plans

**Major tasks.**
- derive validation rules from Core domain legality, not from planner internals
- implement deterministic validation result contract
- build infeasible/illegal plan corpus
- verify planner and validator do not share logic

**Cut/fallback.** No cut (F0). Planner ≠ validator is an architectural invariant (Item 67 #116).


### 9.WP-VALID-002 — Execution eligibility gate and AI-origin plan routing

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-SCH-VALID |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-006, FR-SCH-014 |
| Architecture | ARCH-AI-PROPOSAL, ARCH-AUTO-WORKFLOW, ARCH-SCH-VALIDATOR |
| Gating edges | DEP-082 (DN-CORE-TRANSITIONS, E2E-01 (end S5)) |
| Verification families | AV-SCEN-01, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-SCH-VALIDATOR |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- eligibility flag in plan contract
- Automation-side rejection of ineligible plans
- bypass-attempt negative tests

**Major tasks.**
- define eligibility semantics and lifetime
- implement gate on the Automation consumption path
- test AI-originated plan routing and bypass attempts

**Cut/fallback.** No cut (hard gate: infeasible plan must never reach execution).


### 9.WP-AUTO-002 — Idempotency and restart safety for protected effects

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-AUTO-DURABLE |
| Supporting reviewer | Asrın |
| Source requirements | FR-AUTO-005, FR-AUTO-006, NFR-REL-001, NFR-REL-004 |
| Architecture | ARCH-AUTO-IDEMPOTENCY, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-EVT-CONSUMER |
| Gating edges | DEP-094 (DN-AUTO-DESIGN, S3), DEP-095 (DN-RT-TEMPORAL, E2E-01 formal run (end S5)) |
| Verification families | AV-SCEN-05, AV-SCEN-06, RES-DUP-001, RES-WORKER-001, TEST-AUTO-RESTART-001 |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- idempotency key propagation to Core commands
- verified-effect ledger before re-issue
- restart/duplicate test matrix (TEST-AUTO-RESTART-001)

**Major tasks.**
- align keys with Core command acceptance
- implement pre-issue effect check
- build the five restart/duplicate cases
- execute against real Temporal + Core

**Cut/fallback.** No cut (hard gate: duplicate protected effect count must be zero).


### 9.WP-AUTO-007 — GS-01 recovery workflow and closed-loop timing

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M4 · S7–S8 |
| Readiness node | DN-AUTO-EXEC |
| Supporting reviewer | Asrın |
| Source requirements | FR-AUTO-014, NFR-PERF-011, NFR-PERF-013, NFR-CAP-008 |
| Architecture | ARCH-AI-ORCH, ARCH-AUTO-VERIFY, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-SCH-ENGINE, ARCH-SIM-ENGINE, ARCH-TWIN-API, ARCH-VIS-INFER |
| Gating edges | DEP-096 (DN-AI-ACTCON, E2E-01 readiness (end S4)), DEP-097 (DN-CORE-CMDCON, E2E-01 readiness (end S4)), DEP-098 (DN-CORE-CMDEXEC, E2E-01 readiness (end S4)), DEP-099 (DN-HITL-APPROVAL, E2E-01 (end S5)), DEP-100 (DN-AUTO-DURABLE, E2E-01 (end S5)), DEP-101 (DN-SCH-PLANCON, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, BENCH-PERF-WF, DEMO-GS01-001, E2E-01, RES-DUP-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- GS-01 workflow definition
- workflow concurrency handling
- duration instrumentation excluding human wait

**Major tasks.**
- implement the full recovery sequence against real Core/Simulator
- instrument control-plane overhead and total system-controlled duration
- test 50 concurrent workflows for state integrity

**Cut/fallback.** No cut (F0 + demo path). Presenter-mode shortcuts are forbidden.

**Integration checkpoint.** E2E-01, DEMO-GS01-001, BENCH-E2E-001


### 9.WP-SCH-003 — CP-SAT model and hard constraints

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-SCH-CPSAT |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-004, FR-SCH-009 |
| Architecture | ARCH-SCH-ENGINE |
| Gating edges | none — early unlocker |
| Verification families | BENCH-PERF-SCH, BENCH-SCH-001, TEST-SCH-CONSTRAINTS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- CP-SAT model
- constraint property tests
- solver configuration profile

**Major tasks.**
- encode eligibility, capacity, precedence, maintenance and hold constraints
- implement solve with time budget
- property-based feasibility tests (not golden snapshots)
- tune search parameters within the budget

**Cut/fallback.** F2 fallback exists (heuristics) but F1 requires the CP-SAT candidate at M4.


### 9.WP-SCH-004 — Rolling horizon and event-triggered rescheduling

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-SCH-DYN |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-002, FR-SCH-003 |
| Architecture | ARCH-SCH-ENGINE |
| Gating edges | DEP-078 (DN-SCH-HEUR, S3), DEP-079 (DN-CORE-SNAPCON, E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, M2 (S4)), DEP-081 (DN-EVT-SPINE, M4 (S8)), DEP-086 (DN-SCH-CPSAT, M4 (S8)), DEP-088 (DN-SIM-DISPIF, M2 (S4)) |
| Verification families | AV-SCEN-02, BENCH-RQ2-001, BENCH-SCH-001, TEST-SCH-REPLAN |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- rolling-horizon planner loop
- event-triggered replanning hooks
- disruption class configuration

**Major tasks.**
- define horizon and replan cadence
- subscribe to failure/maintenance/hold/excursion events
- implement replan trigger policy
- integration tests with Simulator disruptions

**Cut/fallback.** No cut (F1, RQ-2 core).


### 9.WP-SCH-006 — Counterfactual schedule evaluation on forked worlds

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-SCH-CF |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-013 |
| Architecture | ARCH-SCH-ENGINE, ARCH-SIM-SNAPSHOT, ARCH-WORLD-FORK |
| Gating edges | DEP-087 (DN-SIM-SNAPFORK, M4 (S8)) |
| Verification families | AV-SCEN-09, BENCH-RQ2-001, TEST-SCH-COUNTERFACTUAL |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- fork-based evaluation harness
- common random number handling
- isolation tests (AV-SCEN-09)

**Major tasks.**
- integrate with Simulator snapshot/fork API
- implement candidate evaluation loop
- ensure exogenous randomness control for paired comparison

**Cut/fallback.** No cut for RQ-2; HARD on Simulator snapshot/fork.


### 9.WP-SIM-004 — Snapshot, fork and world isolation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-SIM-SNAPFORK |
| Supporting reviewer | Yavuz |
| Source requirements | FR-SIM-009, FR-SIM-010, FR-SIM-011 |
| Architecture | ARCH-SIM-SNAPSHOT, ARCH-WORLD-FORK, ARCH-WORLD-ISOLATION |
| Gating edges | DEP-044 (DN-SIM-KERNEL, S3) |
| Verification families | AV-SCEN-09, AV-SCEN-10, BENCH-RQ2-001, TEST-SIM-ISOLATION, TEST-SIM-SNAPSHOT |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- snapshot writer/reader (object-store backed)
- fork API producing new WorldID
- world-scope guard on command/event paths

**Major tasks.**
- define snapshot content and versioning
- implement restore and fork semantics
- implement scope guard + negative tests (AV-SCEN-09/10)
- store snapshots as artifacts with checksums

**Cut/fallback.** No cut for RQ-2; snapshots may use local files during development (F1) but object-store artifacts for evidence.


### 9.WP-SIM-007 — Scenario versioning and synthetic operational history

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-SIM-SYNTH |
| Supporting reviewer | Asrın |
| Source requirements | FR-SIM-007, FR-EVAL-002, FR-ML-007 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO |
| Gating edges | DEP-048 (DN-SIM-OPSEM, S3–S4) |
| Verification families | BENCH-FBC-001, BENCH-ML-M1-001, BENCH-ML-M2-001, BENCH-ML-M3-001, BENCH-SIMVAL-001, INSP-DATA-PROVENANCE, INSP-EVAL-PARTITION, TEST-DATA-SPLITLEAK, TEST-SIM-DETERMINISM |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- ScenarioVersion definitions and registry
- SeedSet management
- generated history export for downstream training/evaluation

**Major tasks.**
- define scenario schema (routes, tools, arrival patterns, disruption profiles)
- implement scenario library covering normal/bottleneck/failure/excursion/rework/hold classes
- implement dataset export with partition metadata
- document provenance of generated data

**Cut/fallback.** No cut; F4 synthetic data is also the fallback that keeps external datasets off the product path.


### 9.WP-UI-005 — Planning and validation views

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Asrın |
| Source requirements | FR-UI-005 |
| Architecture | ARCH-EDGE-WEB, ARCH-SCH-PLAN |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-01, DEMO-GS01-001, TEST-UI-PLAN |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- plan comparison view
- validation status presentation
- objective/rationale display

**Major tasks.**
- design view model from IC-SCH-003/004
- present validator verdicts prominently
- handle no-plan/failure states

**Cut/fallback.** No cut (F1).


### 9.WP-UI-007 — Workflow progress and verification view

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Asrın |
| Source requirements | FR-UI-007 |
| Architecture | ARCH-EDGE-WEB |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | AV-SCEN-01, DEMO-GS01-001, TEST-UI-PLAN |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- workflow progress view
- verification outcome presentation
- failure/unknown state handling

**Major tasks.**
- project workflow state into domain terms
- render ACCEPTED vs VERIFIED_SUCCESS distinctly
- handle UNKNOWN_VERIFY_REQUIRED honestly

**Cut/fallback.** No cut (F1).


### 9.WP-AUTO-006 — Workflow history and audit surface

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-AUTO-DURABLE |
| Supporting reviewer | Asrın |
| Source requirements | FR-AUTO-011 |
| Architecture | ARCH-AUTO-WORKFLOW, ARCH-OBS-AUDIT |
| Gating edges | DEP-094 (DN-AUTO-DESIGN, S3), DEP-095 (DN-RT-TEMPORAL, E2E-01 formal run (end S5)) |
| Verification families | TEST-AUTO-ACTIONCAT, TEST-SEC-AUDIT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- workflow state/history query API
- audit linkage to approval and command records
- UI-facing projection

**Major tasks.**
- define domain-level history projection
- link workflow run to ApprovalRecord/CommandOutcome
- expose through BFF for the workflow view

**Cut/fallback.** No cut; operator trust and audit coverage depend on it.


### 9.WP-SCH-005 — Decision budget, fallback and explicit failure state

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-SCH-DYN |
| Supporting reviewer | Yavuz |
| Source requirements | FR-SCH-012, NFR-PERF-008, NFR-CAP-006, NFR-CAP-007 |
| Architecture | ARCH-SCH-ENGINE, ARCH-SCH-HEURISTIC, ARCH-SCH-VALIDATOR |
| Gating edges | DEP-078 (DN-SCH-HEUR, S3), DEP-079 (DN-CORE-SNAPCON, E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, M2 (S4)), DEP-081 (DN-EVT-SPINE, M4 (S8)), DEP-086 (DN-SCH-CPSAT, M4 (S8)), DEP-088 (DN-SIM-DISPIF, M2 (S4)) |
| Verification families | BENCH-PERF-SCH, TEST-SCH-FALLBACK |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- bounded fallback policy
- explicit failure/no-plan state
- SP-NORMAL/SP-STRESS measurement harness

**Major tasks.**
- implement budget enforcement and graceful degradation
- define failure state semantics for consumers
- measure feasibility rate, solve time, quality and fallback rate

**Cut/fallback.** No cut; silent timeout or an infeasible plan reaching execution is a hard failure.


### 9.WP-SCH-007 — Schedule churn and stability metrics

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-SCH-DYN |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-011 |
| Architecture | ARCH-SCH-ENGINE |
| Gating edges | DEP-078 (DN-SCH-HEUR, S3), DEP-079 (DN-CORE-SNAPCON, E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, M2 (S4)), DEP-081 (DN-EVT-SPINE, M4 (S8)), DEP-086 (DN-SCH-CPSAT, M4 (S8)), DEP-088 (DN-SIM-DISPIF, M2 (S4)) |
| Verification families | BENCH-RQ2-001, BENCH-SCH-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- churn/stability metric calculators
- metric definitions in the analysis package
- regression tests on metric behaviour

**Major tasks.**
- define churn measures (assignment changes, sequence disruption)
- implement calculators independent of the objective function
- validate on controlled replan scenarios

**Cut/fallback.** No cut; stability trade-offs are an explicit RQ-2 dimension.


### 9.WP-TEST-005 — Integration scenarios AV-SCEN-09…12

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-SIM-SNAPFORK |
| Supporting reviewer | Yavuz |
| Source requirements | FR-SIM-011, FR-SIM-012, FR-TWIN-007, NFR-REL-005 |
| Architecture | ARCH-OBS-HEALTH, ARCH-PLAT-COMPOSE, ARCH-SIM-ORACLE, ARCH-SIM-SNAPSHOT, ARCH-TWIN-STATE, ARCH-WORLD-EVALZONE, ARCH-WORLD-ISOLATION |
| Gating edges | DEP-044 (DN-SIM-KERNEL, S3) |
| Verification families | AV-SCEN-09, AV-SCEN-10, AV-SCEN-11, AV-SCEN-12, BENCH-RQ3-001, RES-REBOOT-001, TEST-SEC-ORACLE-NEG, TEST-SIM-ISOLATION, TEST-TWIN-EPISTEMIC |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- scenario drivers for AV-SCEN-09…12
- negative assertions per scenario
- execution reports

**Major tasks.**
- implement fork isolation verification
- implement cross-WorldID mutation rejection test
- implement oracle-access negative validation
- implement host reboot and controlled recovery drill

**Cut/fallback.** No cut.

**Integration checkpoint.** AV-SCEN-09…12


### 9.WP-RES-008 — RQ-2 lane: dynamic recovery evaluation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-SIM-REALISM |
| Supporting reviewer | Asrın |
| Source requirements | FR-SCH-003, FR-SCH-013, FR-AUTO-008 |
| Architecture | ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-SCH-ENGINE, ARCH-SIM-SNAPSHOT, ARCH-TWIN-API, ARCH-WORLD-FORK |
| Gating edges | DEP-049 (DN-SIM-OPSEM, M5→M6) |
| Verification families | AV-SCEN-01, AV-SCEN-02, AV-SCEN-09, BENCH-E2E-001, BENCH-RQ2-001, RES-WORKER-001, TEST-SCH-COUNTERFACTUAL, TEST-SCH-REPLAN |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- RQ-2 experiment definitions
- paired-seed harness with common random numbers
- realized-outcome measurement

**Major tasks.**
- define scenario families and disruption profiles
- implement paired comparison execution
- ensure realism evidence precedes final claims
- execute in FBC-01

**Cut/fallback.** R1; simulation realism (WP-SIM-009) is a HARD evidence precondition.


### 9.WP-SIM-009 — Simulation realism validation suite (RL-3)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-SIM-REALISM |
| Supporting reviewer | Asrın |
| Source requirements | FR-SIM-001, NFR-REP-001 |
| Architecture | ARCH-SIM-CLOCK, ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO |
| Gating edges | DEP-049 (DN-SIM-OPSEM, M5→M6) |
| Verification families | AV-SCEN-01, BENCH-SIMVAL-001, E2E-01, REPRO-NONOWNER-001, TEST-SIM-DETERMINISM, TEST-SIM-KERNEL |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** R1: a lower achieved realism level is a valid recorded outcome that bounds RQ-2 claim wording — it is not hidden.


### 9.WP-PERF-003 — Capacity and stress execution

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M7 · S12 |
| Readiness node | DN-SIM-OPSEM |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-CAP-001, NFR-CAP-002, NFR-CAP-004, NFR-CAP-005, NFR-CAP-008, NFR-CAP-009, NFR-CAP-010 |
| Architecture | ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-SEC-IDP, ARCH-SIM-ENGINE, ARCH-TWIN-PROJECTOR, ARCH-WORLD-ISOLATION, ARCH-WORLD-REGISTRY |
| Gating edges | DEP-037 (DN-SIM-KERNEL, S2), DEP-038 (DN-CORE-CONTRACTS, S2), DEP-039 (DN-CORE-TRANSITIONS, M2 (S4)) |
| Verification families | AV-SCEN-10, BENCH-CAP-ENV, BENCH-CAP-EVT, BENCH-CAP-WORLD, BENCH-PERF-CORE, BENCH-PERF-WF, BENCH-RES-FOOTPRINT, RES-DUP-001, RES-SOAK-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- capacity lane scripts
- stress frontier results
- correctness counters at stress

**Major tasks.**
- execute WP-NORMAL and WP-STRESS runs
- execute event pipeline and workflow concurrency load
- verify zero corruption/leakage/invalid transitions at stress

**Cut/fallback.** A1 for capacity numbers; correctness counters are hard-zero.


### 9.WP-PERF-006 — Scheduler performance frontier measurement

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M7 · S12 |
| Readiness node | DN-SCH-DYN |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-PERF-008, NFR-CAP-006, NFR-CAP-007 |
| Architecture | ARCH-SCH-ENGINE, ARCH-SCH-HEURISTIC, ARCH-SCH-VALIDATOR |
| Gating edges | DEP-078 (DN-SCH-HEUR, S3), DEP-079 (DN-CORE-SNAPCON, E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, M2 (S4)), DEP-081 (DN-EVT-SPINE, M4 (S8)), DEP-086 (DN-SCH-CPSAT, M4 (S8)), DEP-088 (DN-SIM-DISPIF, M2 (S4)) |
| Verification families | BENCH-PERF-SCH, TEST-SCH-FALLBACK |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- scheduler benchmark scripts
- SP-NORMAL results vs 30 s budget
- SP-STRESS characterization

**Major tasks.**
- generate instance sets at both profiles
- measure solve time, feasibility rate, quality and fallback rate
- record frontier behaviour

**Cut/fallback.** A1 at SP-NORMAL; SP-STRESS is C3 characterization.


### 9.WP-SIM-008 — Simulator capacity and scale validation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M7 · S12 |
| Readiness node | DN-SIM-OPSEM |
| Supporting reviewer | Yavuz |
| Source requirements | NFR-CAP-001, NFR-CAP-002, NFR-CAP-003 |
| Architecture | ARCH-CORE-DOMAIN, ARCH-SIM-ENGINE, ARCH-TWIN-PROJECTOR, ARCH-WORLD-ISOLATION |
| Gating edges | DEP-037 (DN-SIM-KERNEL, S2), DEP-038 (DN-CORE-CONTRACTS, S2), DEP-039 (DN-CORE-TRANSITIONS, M2 (S4)) |
| Verification families | BENCH-CAP-WORLD, BENCH-RES-FOOTPRINT, RES-SOAK-001, TEST-SIM-DETERMINISM |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- WP-NORMAL / WP-STRESS world configurations
- ≥250k-event stress run harness
- recorded capacity results

**Major tasks.**
- define workload profile compositions
- instrument correctness counters (corruption, cross-world leakage, invalid transitions, OOM)
- execute and record on the evaluation host

**Cut/fallback.** A1/H0 mix: NFR-CAP-002 counters are hard-zero; the capacity numbers themselves are A1.


### 9.SUP Supporting-reviewer packages (32)

Packages owned by others where this role is the named reviewer — review capacity must be planned, not improvised.

| Work package | Title | Owner | Milestone |
|---|---|---|---|
| WP-CORE-001 | Canonical manufacturing domain model and core schema | Asrın | M1 |
| WP-CORE-002 | Manufacturing lifecycle state machine | Asrın | M2 |
| WP-CORE-003 | Command acceptance: idempotency, revision preconditions, durable outcomes | Asrın | M2 |
| WP-CORE-008 | Core ↔ Simulator ↔ Twin integration and acceptance | Asrın | M3 |
| WP-EVT-003 | Idempotent consumer framework | Asrın | M2 |
| WP-TWIN-003 | Twin query API and scheduling snapshot export | Asrın | M2 |
| WP-TWIN-005 | Counterfactual/what-if stream isolation | Asrın | M4 |
| WP-TWIN-006 | Effect verification view and Core/Twin consistency | Asrın | M3 |
| WP-OBJ-002 | Artifact lifecycle, retention and quota policy | Yavuz | M5 |
| WP-VIS-009 | Oracle-taint guard for Vision inputs | Selman | M3 |
| WP-VDATA-003 | Synthetic Vision data generator | Selman | M4 |
| WP-ML-001 | Feature and label pipeline from operational history | Asrın | M4 |
| WP-ML-003 | M2 — cycle-time / tardiness risk model | Asrın | M4 |
| WP-AI-004 | Action proposal and context binding | Asrın | M3 |
| WP-HITL-001 | Authority policy engine (L0–L4) | Asrın | M3 |
| WP-HITL-002 | Approval binding to exact proposal/plan revision and world | Asrın | M3 |
| WP-HITL-003 | Expiry, replay and staleness rejection | Asrın | M3 |
| WP-HITL-006 | Dual approval for highest-risk actions | Asrın | M4 |
| WP-UI-002 | manufacturing facility state and operational views | Asrın | M2 |
| WP-UI-006 | Approval Center | Asrın | M3 |
| WP-PLAT-003 | Runtime service bring-up on the shared host | Yavuz | M2 |
| WP-PLAT-007 | Benchmark and demo preflight tooling | Yavuz | M6 |
| WP-OBS-003 | Health, readiness and degradation states | Yavuz | M4 |
| WP-SEC-007 | Oracle access denial at runtime | Yavuz | M4 |
| WP-TEST-003 | Integration scenarios AV-SCEN-01…04 | Asrın | M3 |
| WP-TEST-004 | Integration scenarios AV-SCEN-05…08 | Yavuz | M5 |
| WP-PERF-004 | Resilience drill execution | Yavuz | M6 |
| WP-RES-006 | Baseline suite across lanes | Asrın | M5 |
| WP-RES-009 | RQ-3 lane: governed AI-to-action evaluation | Asrın | M6 |
| WP-BENCH-002 | Final E2E matrix execution (MC-1) | Asrın | M7 |
| WP-R2-002 | R2 modelling candidates (local LLM runtime, VLM experiment, advanced causal RCA, RL scheduler, alternative solver formulations) | Asrın | — |
| WP-R2-003 | R2 infrastructure candidates (Neo4j, TimescaleDB, Valkey optimization, GPU/distributed simulator) | Yavuz | — |

## 10. Sprint-Level Execution Projection

Sprint character follows Item 66 §"Sprint-Level Parallelization"; the packages are this role's. This is a projection for planning conversations, not a commitment schedule — 07 owns milestone planning.

| Sprint | Character (Item 66) | Work packages in flight | Upstream gates due | Commitments owed | Milestone |
|---|---|---|---|---|---|
| S1 | maximum independent foundational work | — | 0 | 0 | M0 |
| S2 | first Core/event/Twin/platform convergence | WP-SIM-001 | 1 | 0 | M1 |
| S3 | independent depth: Simulator, Vision, Scheduler, AI fixtures | WP-SIM-002, WP-SIM-003, WP-SIM-006, WP-SCH-001 | 0 | 0 | M2 |
| S4 | depth continues; E2E-01 contract readiness gate closes | WP-SIM-002, WP-SIM-003, WP-SIM-006, WP-SCH-001 | 8 | 2 | M2 |
| S5 | highest integration density; E2E-01 dry run and formal run | WP-SIM-005, WP-SCH-002, WP-VALID-001, WP-VALID-002, WP-AUTO-001, WP-AUTO-003, WP-AUTO-004, WP-AUTO-005, WP-TEST-006 | 5 | 0 | M3 |
| S6 | highest integration density; M3 closed-loop alpha | WP-SIM-005, WP-SCH-002, WP-VALID-001, WP-VALID-002, WP-AUTO-001, WP-AUTO-003, WP-AUTO-004, WP-AUTO-005, WP-TEST-006 | 0 | 0 | M3 |
| S7 | independent capability depth increases again | WP-SIM-004, WP-SIM-007, WP-SCH-003, WP-SCH-004, WP-SCH-006, WP-AUTO-002, WP-AUTO-007, WP-UI-005, WP-UI-007 | 0 | 0 | M4 |
| S8 | depth continues; M4 mandatory feature complete | WP-SIM-004, WP-SIM-007, WP-SCH-003, WP-SCH-004, WP-SCH-006, WP-AUTO-002, WP-AUTO-007, WP-UI-005, WP-UI-007 | 1 | 1 | M4 |
| S9 | cross-cutting quality and evaluation dependencies dominate | WP-SCH-005, WP-SCH-007, WP-AUTO-006, WP-TEST-005 | 0 | 0 | M5 |
| S10 | quality/evaluation continues; M5 reliability & evaluation ready | WP-SCH-005, WP-SCH-007, WP-AUTO-006, WP-TEST-005 | 0 | 2 | M5 |
| S11 | freeze convergence; highest freeze-risk window; M6 | WP-SIM-009, WP-RES-008 | 2 | 5 | M6 |
| S12 | graph effectively immutable, formal execution only; M7 | WP-SIM-008, WP-PERF-003, WP-PERF-006 | 0 | 0 | M7 |
| S13 | evidence, release and documentation convergence; M8 | — | 0 | 0 | M8 |

Two windows deserve explicit attention for this role: **S5–S6** (highest integration density — avoid unrelated refactoring) and **S11** (freeze convergence — avoid casual experimental changes).

### 10.1 Interface ledger with each teammate

**Batu ↔ Asrın**

| Direction | Count | Edges / packages |
|---|---|---|
| Batu receives from Asrın | 16 | DEP-038 (DN-CORE-CONTRACTS, by S2), DEP-039 (DN-CORE-TRANSITIONS, by M2 (S4)), DEP-041 (DN-CORE-CMDEXEC, by M2 (S4)), DEP-042 (DN-EVT-SPINE, by M2 (S4)), DEP-079 (DN-CORE-SNAPCON, by E2E-01 readiness (end S4)), DEP-080 (DN-TWIN-PROJ, by M2 (S4)), DEP-081 (DN-EVT-SPINE, by M4 (S8)), DEP-082 (DN-CORE-TRANSITIONS, by E2E-01 (end S5)), DEP-089 (DN-AI-RCA, by M3 (S6)), DEP-096 (DN-AI-ACTCON, by E2E-01 readiness (end S4)), DEP-097 (DN-CORE-CMDCON, by E2E-01 readiness (end S4)), DEP-098 (DN-CORE-CMDEXEC, by E2E-01 readiness (end S4)), DEP-099 (DN-HITL-APPROVAL, by E2E-01 (end S5)), DEP-103 (DN-TWIN-VERIFY, by E2E-01 (end S5)), DEP-104 (DN-AI-RCA, by M3 (S6)), DEP-129 (DN-RES-CALIB, by M6 (S11)) |
| Batu delivers to Asrın | 9 | DEP-035 (DN-TWIN-PROJ, by M2 (S4)), DEP-074 (DN-ML, by M4 (S8)), DEP-092 (DN-HITL-APPROVAL, by E2E-01 readiness (end S4)), DEP-121 (DN-RES-DATASCEN, by M5 (S10)), DEP-132 (DN-FRZ-MODEL, by M6 (S11)), DEP-135 (DN-FRZ-PROTOCOL, by M6 (S11)), DEP-138 (DN-FRZ-PROTOCOL, by M6 (S11)), DEP-153 (DN-FRZ-MODEL, by M6), DEP-154 (DN-FRZ-PROTOCOL, by M6) |
| shared packages (owner/reviewer) | 45 | WP-CORE-001, WP-CORE-002, WP-CORE-003, WP-CORE-008, WP-EVT-003, WP-TWIN-003, WP-TWIN-005, WP-TWIN-006, WP-SIM-001, WP-SIM-003, WP-SIM-006, WP-SIM-007, WP-SIM-009, WP-ML-001, WP-ML-003, WP-AI-004, WP-SCH-001, WP-SCH-002, WP-SCH-003, WP-SCH-004, WP-SCH-006, WP-SCH-007, WP-VALID-001, WP-VALID-002, WP-AUTO-002, WP-AUTO-003, WP-AUTO-004, WP-AUTO-005, WP-AUTO-006, WP-AUTO-007, WP-HITL-001, WP-HITL-002, WP-HITL-003, WP-HITL-006, WP-UI-002, WP-UI-005, WP-UI-006, WP-UI-007, WP-TEST-003, WP-TEST-006, WP-RES-006, WP-RES-008, WP-RES-009, WP-BENCH-002, WP-R2-002 |

**Batu ↔ Selman**

| Direction | Count | Edges / packages |
|---|---|---|
| Batu receives from Selman | 1 | DEP-131 (DN-FRZ-RQ4SPLIT, by M6 (S11)) |
| Batu delivers to Selman | 1 | DEP-062 (DN-VIS-EPISODES, by M5) |
| shared packages (owner/reviewer) | 2 | WP-VIS-009, WP-VDATA-003 |

**Batu ↔ Yavuz**

| Direction | Count | Edges / packages |
|---|---|---|
| Batu receives from Yavuz | 3 | DEP-045 (DN-RT-OBJ, by M2 (S4)), DEP-047 (DN-SEC-BASE, by E2E-01 (end S5)), DEP-095 (DN-RT-TEMPORAL, by E2E-01 formal run (end S5)) |
| Batu delivers to Yavuz | 0 | — |
| shared packages (owner/reviewer) | 17 | WP-SIM-002, WP-SIM-004, WP-SIM-005, WP-SIM-008, WP-OBJ-002, WP-SCH-005, WP-AUTO-001, WP-PLAT-003, WP-PLAT-007, WP-OBS-003, WP-SEC-007, WP-TEST-004, WP-TEST-005, WP-PERF-003, WP-PERF-004, WP-PERF-006, WP-R2-003 |

## 11. Integration Checkpoints

| Checkpoint | Work packages | What this role must prove |
|---|---|---|
| E2E-01 (end S5, Item 67) | WP-SIM-005, WP-AUTO-007, WP-TEST-006 | contract readiness by end S4 and real-boundary behaviour in the formal run; review obligation before the run (Item 67 #215–#218) |
| AV-SCEN-01…12 (Item 84) | WP-SIM-005, WP-AUTO-005, WP-TEST-005 | architecture validation scenarios executed on the Integration environment |
| GS-01 demo (DEMO-GS01-001) | WP-AUTO-007 | the hero path works from a pinned release without presentation shortcuts |
| FBC-01 E2E matrix (BENCH-E2E-001) | WP-AUTO-007 | the role's part of the 4×20 statistical matrix executes unattended |

## 12. Failure and Negative Tests

Negative and failure-path verification owned or co-owned by this role. Happy-path evidence alone can never satisfy an H0 requirement (03 §4.4).

| Verification family | Kind | Scope | Family owner | Minimum environment |
|---|---|---|---|---|
| RES-DUP-001 | DRILL | Duplicate/retry/restart protected-effect suite aggregation (AV-SCEN-05/06 + TEST-AUTO-RESTART-001) | Batu | EVALUATION |
| TEST-AUTH-NEG | TEST | Cross-cutting authority negative suite: AI mutation/self-approval/credential/bypass attempts (AUTH-INV family) | Asrın | CI |
| TEST-AUTO-ACTIONCAT | TEST | ActionCatalog-only execution; no self-authorization; inspectable history | Batu | CI |
| TEST-AUTO-FRESHNESS | TEST | Pre-execution revalidation of proposal/plan/state freshness, WorldID and action identity | Batu | CI |
| TEST-AUTO-OUTCOME | TEST | ACK ≠ effect; lost/ambiguous response → UNKNOWN_VERIFY_REQUIRED; Core/Twin effect verification | Batu | CI |
| TEST-AUTO-RESTART-001 | TEST | Worker crash / restart-before-command / duplicate delivery / restart-after-effect / restart-before-verification | Batu | CI |
| TEST-DATA-SPLITLEAK | TEST | Frozen partition entity/group overlap detection against SplitManifest policy | Asrın | EVALUATION |
| TEST-SCH-COUNTERFACTUAL | TEST | Counterfactual plan evaluation in isolated fork WorldID | Batu | CI |
| TEST-SCH-FALLBACK | TEST | Bounded fallback / explicit failure state when CP-SAT cannot return valid plan | Batu | CI |
| TEST-SCH-VALIDATOR | TEST | Independent ScheduleValidator: infeasible plan rejection, eligibility blocking, AI-origin plans included | Batu | CI |
| TEST-SEC-AUTHN | TEST | Keycloak interactive authentication for formal flows; approval ↔ authenticated identity | Yavuz | INTEGRATION |
| TEST-SEC-ORACLE-NEG | TEST | Oracle/evaluator-only data inaccessible to normal service identities (runtime denial) | Yavuz | EVALUATION |
| TEST-SIM-ISOLATION | TEST | Counterfactual non-mutation of primary world + Oracle stream/namespace inaccessibility (negative) | Batu | CI |
| TEST-TWIN-EPISTEMIC | TEST | ACTUAL/OBSERVED/INFERRED/PREDICTED/PLANNED/COUNTERFACTUAL separation + counterfactual isolation | Asrın | CI |

**Owned H0 (hard-gate) requirements requiring hard/negative evidence (2):** NFR-REL-001, NFR-REP-001.

## 13. Research / Evaluation Responsibilities

Batu is primary research owner for **RQ-2 (execution-aware dynamic rescheduling and recovery)**, scheduling baselines, counterfactual recovery and stability trade-offs (Item 58), and for the simulation realism evidence that bounds every RQ-2 claim. The design discipline that matters here: paired seeds with common random numbers, realized execution outcomes rather than planned objective values, baselines executed locally rather than cited from literature, and stability measured separately from objective quality so that 'better' is never achieved by thrashing.

| R1 work package | Title | Milestone | Evidence lane |
|---|---|---|---|
| WP-SIM-009 | Simulation realism validation suite (RL-3) | M6 | BENCH-SIMVAL-001 |
| WP-RES-008 | RQ-2 lane: dynamic recovery evaluation | M6 | BENCH-E2E-001, BENCH-RQ2-001 |

## 14. Documentation and ADR Obligations

Own the Simulator, Scheduler and Automation service documentation, the scenario catalogue, the workflow runbooks (including manual reconciliation of UNKNOWN_VERIFY_REQUIRED cases), and the ADRs for the DES kernel, CP-SAT choice and Temporal workflow design.

## 15. Risks and Bottlenecks

| Risk (Item 69) | Exposure for this role | Mitigation carried in this roadmap |
|---|---|---|
| SCH-R01 | Scheduler produces plans that violate manufacturing legality. | Validator implemented independently from the planner, derived from Core rules, with an infeasible-plan corpus. |
| SCH-R03 | Solve time exceeds the decision budget under stress. | Budget enforcement with bounded fallback and explicit failure state; SP-STRESS characterized rather than hidden. |
| AUTO-R01 | A retry or restart causes a duplicate real effect. | Idempotency keys shared with Core, verified-effect ledger, five-case restart matrix, duplicate-delivery drills. |
| AUTO-R06 | Acknowledgement is mistaken for effect. | Outcome model separating ACCEPTED from VERIFIED_SUCCESS, with an UNKNOWN_VERIFY_REQUIRED path and reconciliation. |
| SIM-R06 | Nondeterminism breaks paired-seed experiments. | Named RNG streams, replay hash equivalence, determinism check in CI. |
| SIM-R08 | Counterfactual evaluation contaminates the primary world. | Fork isolation with world-scope guards and cross-world rejection tests. |

## 16. Cross-Review Responsibilities

Batu reviews anything that changes what the world does or how execution happens: Core transition rules and command semantics from an execution perspective, the authority policy from a workflow-feasibility perspective, and platform changes affecting Temporal, resource budgets or the Integration host's behaviour under load. Batu is also the required reviewer for scenario semantics used in evaluation.

Named reviewer on 32 work packages owned by others (§9.SUP). Cross-review is an Item 63 obligation, not a courtesy: a dependency handshake counts as complete only when both sides have validated contract usability (Item 66 #140).

## 17. Final Benchmark Contribution

| Lane / asset | Kind | Scope | Role's obligation |
|---|---|---|---|
| BENCH-AUTO-001 | BENCH | Automation/workflow evaluation lane (durability/effect result) | execute and record dispositions, including failures |
| BENCH-CAP-ENV | BENCH | Interactive session concurrency and isolated-WorldID capacity | execute and record dispositions, including failures |
| BENCH-CAP-EVT | BENCH | Application event pipeline sustained 100 msg/s × 10 min | execute and record dispositions, including failures |
| BENCH-CAP-WORLD | BENCH | WP-NORMAL / WP-STRESS operational world and ≥250,000-event simulator stress | execute and record dispositions, including failures |
| BENCH-E2E-001 | BENCH | FBC-01 final statistical E2E matrix: 4 frozen scenario definitions × 20 seeds (80 base instances) | execute and record dispositions, including failures |
| BENCH-FBC-001 | BENCH | FBC-01 campaign-level execution: BenchmarkCampaignManifest, preflight, run registry, sealing across all lanes (R1 mechanisms exercised formally) | execute and record dispositions, including failures |
| BENCH-ML-M1-001 | BENCH | M1 equipment-risk evaluation (discrimination + calibration separately) | execute and record dispositions, including failures |
| BENCH-ML-M2-001 | BENCH | M2 cycle-time/tardiness evaluation | execute and record dispositions, including failures |
| BENCH-ML-M3-001 | BENCH | M3 pre-inspection quality evaluation | execute and record dispositions, including failures |
| BENCH-PERF-CORE | BENCH | Core/Twin read latency, command decision latency, outbox delay, Twin freshness, Core command throughput | execute and record dispositions, including failures |
| BENCH-PERF-SCH | BENCH | SP-NORMAL decision budget and SP-STRESS frontier (feasibility, solve time, quality, fallback rate) | execute and record dispositions, including failures |
| BENCH-PERF-WF | BENCH | Workflow control-plane overhead, approval persistence, GS-01 system-controlled duration, workflow concurrency | execute and record dispositions, including failures |
| BENCH-RES-FOOTPRINT | BENCH | cgroup memory steady/peak and CPU mean/p95/saturation under WP-NORMAL and stress | execute and record dispositions, including failures |
| BENCH-RQ1-001 | BENCH | RQ-1 evidence-grounded RCA final evaluation (120 FINAL_TEST cases, baselines RCA-B1..PROPOSED) | execute and record dispositions, including failures |
| BENCH-RQ2-001 | BENCH | RQ-2 dynamic closed-loop recovery (4 families × 20 paired seeds, realized execution outcome) | execute and record dispositions, including failures |
| BENCH-RQ3-001 | BENCH | RQ-3 governed AI-to-action (150 cases, L0–L4 × 30, ≥40% adversarial) | execute and record dispositions, including failures |
| BENCH-SCH-001 | BENCH | Scheduler component benchmark (8 families × 30 paired seeds) incl. baselines and churn/stability metrics | execute and record dispositions, including failures |
| BENCH-SIMVAL-001 | BENCH | SimulationValidationRun / RealismBenchmarkSuite: V-MICRO-01..06, RV-01..15, IndependentKPIRecalculator, RL-3 target | execute and record dispositions, including failures |
| REPRO-NONOWNER-001 | DRILL | Non-owner teammate reproduction of selected final environment/scenario (ENG-G) | execute and record dispositions, including failures |
| RES-DUP-001 | DRILL | Duplicate/retry/restart protected-effect suite aggregation (AV-SCEN-05/06 + TEST-AUTO-RESTART-001) | execute and record dispositions, including failures |
| RES-REBOOT-001 | DRILL | Host reboot with intact volumes → healthy/known-degraded (AV-SCEN-12 execution) | execute and record dispositions, including failures |
| RES-SOAK-001 | DRILL | 8-hour WP-NORMAL soak: crash loops, corruption, duplication, OOM, queue growth, memory | execute and record dispositions, including failures |
| RES-WORKER-001 | DRILL | Workflow-worker crash/restart resumption without duplicate verified effect (AV-SCEN-06 execution) | execute and record dispositions, including failures |

Campaign discipline that binds this role: run only what was frozen at M6; record every attempted run with a disposition; never adjust a threshold, rubric or scenario after seeing results; a MISS or a NOT_SUPPORTED outcome is a result, not a failure to conceal.

## 18. Demo Contribution

GS-01's visible action sequence is Batu's: the recovery plan appears with rationale and validation status, the workflow progresses through approval, the command executes and the effect is verified in the Twin. The demo's hard abort conditions — unverified effect, stale plan execution, validator failure — protect exactly this path.

## 19. Thesis / Portfolio Evidence

Portfolio and thesis material: the deterministic reentrant manufacturing simulator with snapshot/fork semantics, the recovery scheduling approach with an independent validator, the counterfactual evaluation method, the durable execution model with effect verification, and the RQ-2 results with their realism caveats stated honestly.

| Evidence artifact | Produced by | Status today |
|---|---|---|
| Owned requirement dispositions (57) | 03 trace registry at M8 | NOT_YET_EXECUTED |
| Sealed lane results for owned research lanes | FBC-01 bundle at M7 | NOT_YET_EXECUTED |
| Architecture/design record (ADRs, contracts) | continuous from M1 | NOT_STARTED |
| Negative/failure evidence (14 families) | M5–M7 | NOT_YET_EXECUTED |

## 19.1 Requirement Execution Dossier

One block per owned requirement: what must be built, what proves it, where the evidence must come from, and which milestone carries it. This is the checklist the owner works through between M1 and M8.

```yaml
FR-AUTO-001:
  class: F0
  area: AUTO
  work_packages: [WP-AUTO-001]
  target_milestone: M3
  architecture: [ARCH-AUTO-WORKFLOW, ARCH-AUTO-ACTIONCAT]
  planned_surface: "durable recovery WorkflowDefinitions (WorkflowBundle)"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-WORKFLOW, E2E-01, AV-SCEN-01, BENCH-AUTO-001, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-002:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-001]
  target_milestone: M3
  architecture: [ARCH-AUTO-WORKFLOW]
  planned_surface: "Temporal workers/workflows (backfill ADR 4)"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-WORKFLOW, E2E-01, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-003:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-001]
  target_milestone: M3
  architecture: [ARCH-AUTO-WORKFLOW, ARCH-HITL-APPROVAL]
  planned_surface: "durable approval-wait signal handling"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-WORKFLOW, TEST-AUTO-RESTART-001, AV-SCEN-06]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-004:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-003, WP-RES-009]
  target_milestone: M3
  architecture: [ARCH-AUTO-WORKFLOW, ARCH-HITL-EXPIRY]
  planned_surface: "final revalidation activity (target state, freshness, validator result, policy)"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-FRESHNESS, AV-SCEN-04, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-005:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-002]
  target_milestone: M4
  architecture: [ARCH-AUTO-IDEMPOTENCY]
  planned_surface: "activity idempotency keys propagated to Core commands"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-RESTART-001, RES-DUP-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-006:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-002, WP-TEST-004]
  target_milestone: M4
  architecture: [ARCH-AUTO-WORKFLOW, ARCH-AUTO-IDEMPOTENCY]
  planned_surface: "restart-safe effect ledger / verified-effect check before re-issue"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-RESTART-001, RES-WORKER-001, AV-SCEN-06]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-007:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-005]
  target_milestone: M3
  architecture: [ARCH-AUTO-VERIFY]
  planned_surface: "outcome state model (ACCEPTED ≠ VERIFIED_SUCCESS)"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-OUTCOME, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-008:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-005, WP-TEST-003, WP-RES-008]
  target_milestone: M3
  architecture: [ARCH-AUTO-VERIFY, ARCH-TWIN-API, ARCH-CORE-CMD]
  planned_surface: "effect-verification activity against Core events/Twin state"
  boundary_mode_final: REAL
  verification: [AV-SCEN-01, RES-WORKER-001, BENCH-E2E-001]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-009:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-005]
  target_milestone: M3
  architecture: [ARCH-AUTO-VERIFY]
  planned_surface: "UNKNOWN_VERIFY_REQUIRED path + reconciliation"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-OUTCOME, RES-DUP-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-010:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-003]
  target_milestone: M3
  architecture: [ARCH-AUTO-WORKFLOW, ARCH-WORLD-SCOPE]
  planned_surface: "command identity (WorldID, revision, ActionID) on every typed command"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-AUTO-FRESHNESS, AV-SCEN-10]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-011:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-006]
  target_milestone: M5
  architecture: [ARCH-AUTO-WORKFLOW, ARCH-OBS-AUDIT]
  planned_surface: "workflow history query surface + audit linkage"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-ACTIONCAT, TEST-SEC-AUDIT]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-012:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-004]
  target_milestone: M3
  architecture: [ARCH-AUTO-ACTIONCAT]
  planned_surface: "ActionCatalog registry (risk level, preconditions, idempotency, valid world types)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-AUTO-ACTIONCAT, TEST-AUTH-NEG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-013:
  class: F1
  area: AUTO
  work_packages: [WP-AUTO-004]
  target_milestone: M3
  architecture: [ARCH-AUTO-ACTIONCAT, ARCH-HITL-POLICY]
  planned_surface: "external-approval gate (no self-authorization)"
  boundary_mode_final: REAL
  verification: [TEST-AUTO-ACTIONCAT, TEST-AUTH-NEG, AV-SCEN-04]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-AUTO-014:
  class: F0
  area: AUTO
  work_packages: [WP-AUTO-007, WP-TEST-006, WP-BENCH-002]
  target_milestone: M4
  architecture: [ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-SIM-ENGINE]
  planned_surface: "GS-01 recovery workflow (isolation, ActivateSchedule, maintenance WO)"
  boundary_mode_final: REAL
  verification: [E2E-01, AV-SCEN-01, DEMO-GS01-001, BENCH-E2E-001]
  evidence_env: "INTEGRATION + EVALUATION + DEMO"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-001:
  class: F0
  area: SCH
  work_packages: [WP-SCH-002]
  target_milestone: M3
  architecture: [ARCH-SCH-ENGINE, ARCH-SCH-HEURISTIC]
  planned_surface: "dispatch/scheduling over SchedulingSnapshot"
  boundary_mode_final: REAL
  verification: [TEST-SCH-CONSTRAINTS, E2E-01, AV-SCEN-02, BENCH-SCH-001, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-002:
  class: F1
  area: SCH
  work_packages: [WP-SCH-004]
  target_milestone: M4
  architecture: [ARCH-SCH-ENGINE]
  planned_surface: "rolling-horizon planning loop (Long/Planning workload class)"
  boundary_mode_final: REAL
  verification: [TEST-SCH-REPLAN, BENCH-SCH-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-003:
  class: F1
  area: SCH
  work_packages: [WP-SCH-004, WP-RES-008]
  target_milestone: M4
  architecture: [ARCH-SCH-ENGINE]
  planned_surface: "event-triggered replanning for accepted disruption classes"
  boundary_mode_final: REAL
  verification: [TEST-SCH-REPLAN, AV-SCEN-02, BENCH-RQ2-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-004:
  class: F1
  area: SCH
  work_packages: [WP-SCH-003]
  target_milestone: M4
  architecture: [ARCH-SCH-ENGINE]
  planned_surface: "CP-SAT hard-constraint model"
  boundary_mode_final: REAL
  verification: [TEST-SCH-CONSTRAINTS, BENCH-SCH-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-005:
  class: F0
  area: SCH
  work_packages: [WP-VALID-001, WP-TEST-006]
  target_milestone: M3
  architecture: [ARCH-SCH-VALIDATOR]
  planned_surface: "deterministic validator module independent of generator"
  boundary_mode_final: REAL
  verification: [TEST-SCH-VALIDATOR, E2E-01, AV-SCEN-01, AV-SCEN-02, BENCH-SCH-001, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-006:
  class: F1
  area: SCH
  work_packages: [WP-VALID-002]
  target_milestone: M3
  architecture: [ARCH-SCH-VALIDATOR, ARCH-AUTO-WORKFLOW]
  planned_surface: "execution-eligibility flag gated by validator result; Automation rejects ineligible"
  boundary_mode_final: REAL
  verification: [TEST-SCH-VALIDATOR, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-007:
  class: F1
  area: SCH
  work_packages: [WP-SCH-002]
  target_milestone: M3
  architecture: [ARCH-SCH-PLAN, ARCH-TWIN-FRESHNESS]
  planned_surface: "plan ↔ SchedulingSnapshot revision binding"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-SCH-PLAN, TEST-AUTO-FRESHNESS]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-008:
  class: F1
  area: SCH
  work_packages: [WP-SCH-002]
  target_milestone: M3
  architecture: [ARCH-SCH-PLAN, ARCH-CTR-EVTSCHEMA]
  planned_surface: "RecoveryPlan schema (Item 83 example: CONTRACT-RecoveryPlan-v1)"
  boundary_mode_final: REAL
  verification: [TEST-SCH-PLAN, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-009:
  class: F1
  area: SCH
  work_packages: [WP-SCH-003, WP-R2-002]
  target_milestone: M4
  architecture: [ARCH-SCH-ENGINE]
  planned_surface: "OR-Tools CP-SAT candidate strategy (backfill ADR 8)"
  boundary_mode_final: REAL
  verification: [TEST-SCH-CONSTRAINTS, BENCH-SCH-001, BENCH-PERF-SCH]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-010:
  class: F1
  area: SCH
  work_packages: [WP-SCH-001, WP-RES-006]
  target_milestone: M2
  architecture: [ARCH-SCH-HEURISTIC, ARCH-VIS-EVAL]
  planned_surface: "FIFO/EDD/CR/SPT/SRPT baseline implementations (BaselineDefinition)"
  boundary_mode_final: REAL
  verification: [BENCH-SCH-001, BENCH-RQ2-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-011:
  class: F1
  area: SCH
  work_packages: [WP-SCH-007]
  target_milestone: M5
  architecture: [ARCH-SCH-ENGINE]
  planned_surface: "churn/stability metric calculators separate from objective"
  boundary_mode_final: REAL
  verification: [BENCH-SCH-001, BENCH-RQ2-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-012:
  class: F1
  area: SCH
  work_packages: [WP-SCH-005]
  target_milestone: M5
  architecture: [ARCH-SCH-HEURISTIC, ARCH-SCH-ENGINE]
  planned_surface: "bounded fallback policy + explicit failure state"
  boundary_mode_final: REAL
  verification: [TEST-SCH-FALLBACK, BENCH-PERF-SCH]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-013:
  class: F1
  area: SCH
  work_packages: [WP-SCH-006, WP-RES-008]
  target_milestone: M4
  architecture: [ARCH-SCH-ENGINE, ARCH-WORLD-FORK, ARCH-SIM-SNAPSHOT]
  planned_surface: "counterfactual candidate evaluation per fork WorldID"
  boundary_mode_final: REAL
  verification: [TEST-SCH-COUNTERFACTUAL, AV-SCEN-09, BENCH-RQ2-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-014:
  class: F1
  area: SCH
  work_packages: [WP-VALID-002]
  target_milestone: M3
  architecture: [ARCH-SCH-VALIDATOR, ARCH-AI-PROPOSAL]
  planned_surface: "AI-originated plan requests routed through validator (no bypass path)"
  boundary_mode_final: REAL
  verification: [TEST-SCH-VALIDATOR, TEST-AUTH-NEG, AV-SCEN-01, BENCH-RQ3-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SCH-015:
  class: F1
  area: SCH
  work_packages: [WP-SCH-002]
  target_milestone: M3
  architecture: [ARCH-SCH-PLAN, ARCH-EDGE-BFF]
  planned_surface: "rationale/objective/comparison fields for review"
  boundary_mode_final: REAL
  verification: [TEST-SCH-PLAN, TEST-UI-PLAN, AV-SCEN-01]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-001:
  class: F0
  area: SIM
  work_packages: [WP-SIM-001, WP-SIM-009]
  target_milestone: M1
  architecture: [ARCH-SIM-ENGINE, ARCH-SIM-CLOCK]
  planned_surface: "custom deterministic Python DES kernel (backfill ADR 7)"
  boundary_mode_final: REAL
  verification: [TEST-SIM-KERNEL, E2E-01, AV-SCEN-01, BENCH-SIMVAL-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-002:
  class: F0
  area: SIM
  work_packages: [WP-SIM-003]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE]
  planned_surface: "reentrant lot routing executor"
  boundary_mode_final: REAL
  verification: [TEST-SIM-KERNEL, E2E-01, AV-SCEN-02, BENCH-SIMVAL-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-003:
  class: F1
  area: SIM
  work_packages: [WP-SIM-003]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE]
  planned_surface: "equipment queue model"
  boundary_mode_final: REAL
  verification: [TEST-SIM-KERNEL, AV-SCEN-02, BENCH-SIMVAL-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-004:
  class: F1
  area: SIM
  work_packages: [WP-SIM-003]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE]
  planned_surface: "equipment availability/failure/repair model"
  boundary_mode_final: REAL
  verification: [TEST-SIM-KERNEL, AV-SCEN-02, BENCH-RQ2-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-005:
  class: F1
  area: SIM
  work_packages: [WP-SIM-003]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE]
  planned_surface: "maintenance effect model"
  boundary_mode_final: REAL
  verification: [TEST-SIM-KERNEL, BENCH-SIMVAL-001, AV-SCEN-02, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-006:
  class: F1
  area: SIM
  work_packages: [WP-SIM-003]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE]
  planned_surface: "rework transition execution"
  boundary_mode_final: REAL
  verification: [TEST-SIM-KERNEL, BENCH-SIMVAL-001, BENCH-E2E-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-007:
  class: F1
  area: SIM
  work_packages: [WP-SIM-001, WP-SIM-007]
  target_milestone: M1
  architecture: [ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO]
  planned_surface: "named RNG stream registry (arrival/processing/failure/repair/quality/inspection)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-SIM-DETERMINISM, BENCH-SIMVAL-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-008:
  class: F1
  area: SIM
  work_packages: [WP-SIM-002]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE, ARCH-SIM-SCENARIO]
  planned_surface: "deterministic replay + event-sequence hash"
  boundary_mode_final: REAL
  verification: [TEST-SIM-DETERMINISM, BENCH-SIMVAL-001, REPRO-NONOWNER-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-009:
  class: F1
  area: SIM
  work_packages: [WP-SIM-004]
  target_milestone: M4
  architecture: [ARCH-SIM-SNAPSHOT]
  planned_surface: "snapshot writer (SNAPSHOT_CHECKPOINT artifacts on SeaweedFS)"
  boundary_mode_final: REAL
  verification: [TEST-SIM-SNAPSHOT, AV-SCEN-09]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-010:
  class: F1
  area: SIM
  work_packages: [WP-SIM-004]
  target_milestone: M4
  architecture: [ARCH-SIM-SNAPSHOT, ARCH-WORLD-FORK]
  planned_surface: "fork/restore into new WorldID"
  boundary_mode_final: REAL
  verification: [TEST-SIM-SNAPSHOT, AV-SCEN-09, BENCH-RQ2-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-011:
  class: F1
  area: SIM
  work_packages: [WP-SIM-004, WP-TEST-005]
  target_milestone: M4
  architecture: [ARCH-WORLD-ISOLATION, ARCH-SIM-SNAPSHOT]
  planned_surface: "world-scope guard on physical command/event paths"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-SIM-ISOLATION, AV-SCEN-09, AV-SCEN-10]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-012:
  class: F1
  area: SIM
  work_packages: [WP-SIM-005, WP-TEST-005]
  target_milestone: M3
  architecture: [ARCH-SIM-ORACLE, ARCH-WORLD-EVALZONE]
  planned_surface: "Oracle stream namespace + EVALUATOR_ONLY credential separation"
  boundary_mode_final: REAL
  verification: [TEST-SIM-ISOLATION, AV-SCEN-11, TEST-SEC-ORACLE-NEG, BENCH-RQ3-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-013:
  class: F1
  area: SIM
  work_packages: [WP-SIM-006]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE, ARCH-CTR-CMDSCHEMA]
  planned_surface: "external dispatch/planning decision interface (Core-validated physical commands)"
  boundary_mode_final: REAL
  verification: [TEST-SIM-DECISIONIF, AV-SCEN-02, BENCH-RQ2-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SIM-014:
  class: F1
  area: SIM
  work_packages: [WP-SIM-006]
  target_milestone: M2
  architecture: [ARCH-SIM-ENGINE, ARCH-WORLD-EVALZONE]
  planned_surface: "operational event/telemetry publication without Oracle fields"
  boundary_mode_final: REAL
  verification: [TEST-SIM-DECISIONIF, TEST-SIM-ISOLATION, AV-SCEN-01, AV-SCEN-11]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-005:
  class: F1
  area: UI
  work_packages: [WP-UI-005]
  target_milestone: M4
  architecture: [ARCH-EDGE-WEB, ARCH-SCH-PLAN]
  planned_surface: "plan comparison + validation status view"
  boundary_mode_final: REAL
  verification: [TEST-UI-PLAN, AV-SCEN-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-007:
  class: F1
  area: UI
  work_packages: [WP-UI-007]
  target_milestone: M4
  architecture: [ARCH-EDGE-WEB]
  planned_surface: "workflow execution/verification progress (domain-level)"
  boundary_mode_final: REAL
  verification: [TEST-UI-PLAN, AV-SCEN-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-001:
  class: A1
  area: CAP
  work_packages: [WP-SIM-008, WP-PERF-003]
  target_milestone: M7
  metric: "sustained operation without semantic degradation"
  threshold: "≥100 tools / 1,000 active lots"
  workload_profile: "WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-CAP-WORLD, RES-SOAK-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-002:
  class: A1
  area: CAP
  work_packages: [WP-SIM-008, WP-PERF-003]
  target_milestone: M7
  metric: "corruption / cross-world leakage / invalid transition / OOM counts"
  threshold: "all = 0 at 200 tools / 2,000 lots"
  workload_profile: "WP-STRESS"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-CAP-WORLD, BENCH-RES-FOOTPRINT]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-003:
  class: A1
  area: CAP
  work_packages: [WP-SIM-008]
  target_milestone: M7
  metric: "discrete events processed without correctness failure"
  threshold: "≥ 250,000 events"
  workload_profile: "simulator stress benchmark"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-CAP-WORLD, TEST-SIM-DETERMINISM]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-006:
  class: A1
  area: CAP
  work_packages: [WP-SCH-005, WP-PERF-006]
  target_milestone: M5
  metric: "NFR-PERF-008 satisfaction at normal scheduling scale"
  threshold: "≤100 eligible lots / ≤50 tools within 30 s"
  workload_profile: "SP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-SCH]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-007:
  class: C3
  area: CAP
  work_packages: [WP-SCH-005, WP-PERF-006]
  target_milestone: M5
  metric: "feasibility rate, solve time, solution quality, fallback rate"
  threshold: "C3 — characterize"
  workload_profile: "SP-STRESS (≤250 lots / ≤100 tools)"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-SCH]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-008:
  class: A1
  area: CAP
  work_packages: [WP-AUTO-007, WP-PERF-003]
  target_milestone: M4
  metric: "simultaneously active/waiting workflows; lost state; duplicate effects"
  threshold: "50 workflows; lost = 0; duplicates = 0"
  workload_profile: "workflow concurrency profile"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-WF, RES-DUP-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-008:
  class: A1
  area: PERF
  work_packages: [WP-SCH-005, WP-PERF-006]
  target_milestone: M5
  metric: "wall-clock to validator-feasible candidate / accepted fallback / explicit failure"
  threshold: "≤ 30 s for every instance"
  workload_profile: "SP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-SCH, TEST-SCH-FALLBACK]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-011:
  class: S2
  area: PERF
  work_packages: [WP-AUTO-007, WP-PERF-002]
  target_milestone: M4
  metric: "authorization-ready step → verified Core/Twin effect overhead (human wait excluded)"
  threshold: "p95 ≤ 10 s"
  workload_profile: "protected actions without deliberate waits"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-WF]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-013:
  class: S2
  area: PERF
  work_packages: [WP-AUTO-007, WP-PERF-002, WP-BENCH-002, WP-DOC-004]
  target_milestone: M4
  metric: "inspection evidence available → verified final recovery state (system-controlled)"
  threshold: "p95 ≤ 120 s (excl. human, sim waits, provider outage)"
  workload_profile: "GS-01 / FBC-01 visual-excursion family"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-WF, BENCH-E2E-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-001:
  class: H0
  area: REL
  work_packages: [WP-AUTO-002, WP-PERF-005, WP-BENCH-003]
  target_milestone: M4
  metric: "duplicate protected manufacturing effects across duplicate/retry/restart suites"
  threshold: "= 0"
  workload_profile: "duplicate-delivery, retry, restart suites"
  hardware_profile: "N/A (count-based; context recorded)"
  verification: [RES-DUP-001, AV-SCEN-05, AV-SCEN-06, TEST-AUTO-RESTART-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-004:
  class: A1
  area: REL
  work_packages: [WP-AUTO-002, WP-PERF-004]
  target_milestone: M4
  metric: "worker crash/restart → durable processing resumed; duplicate verified effects"
  threshold: "≤ 5 min; duplicates = 0"
  workload_profile: "workflow restart scenario"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-WORKER-001, AV-SCEN-06]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-001:
  class: H0
  area: REP
  work_packages: [WP-SIM-002, WP-SIM-009]
  target_milestone: M2
  metric: "final state + deterministic event sequence/hash equality for same release/scenario/state/seed"
  threshold: "identical"
  workload_profile: "deterministic scenarios"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SIM-DETERMINISM, BENCH-SIMVAL-001, REPRO-NONOWNER-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
```

## 20. Definition of Final Role Completion

This role is complete at M8 when every line below is true and demonstrable from generated artifacts — not when the owner believes the work is done.

| # | Completion criterion |
|---|---|
| C-1 | All 32 owned work packages are at DoD (04 §4.2), with real repository references replacing `TBD_BY_IMPLEMENTATION` |
| C-2 | All 57 owned requirements have a final disposition in 03 — VERIFIED, or an explicitly recorded FAIL/MISS/REBASELINED with analysis |
| C-3 | Every owned F0 requirement is verified on a real integrated path (FR-AI-001, FR-AUTO-001, FR-AUTO-014, FR-SCH-001, FR-SCH-005, FR-SIM-001, FR-SIM-002, FR-VIS-016) |
| C-4 | Every owned H0 requirement (2) has hard/negative evidence with zero-count assertions satisfied |
| C-5 | Every owned A1/S2/C3 requirement has a measurement executed in the correct environment with its HardwareProfile/WorkloadProfile bound |
| C-6 | Every downstream commitment (10 HARD edges) was delivered at its required readiness with unblock evidence |
| C-7 | All owned contracts are versioned, documented and consumed by their real consumers — no consumer still runs on fixtures in the acceptance path |
| C-8 | Owned ADRs exist for the decisions listed in §14, and 03 trace edges are current |
| C-9 | Owned research lanes executed from frozen artifacts with dispositions recorded; claims traced to sealed evidence |
| C-10 | Owned red-team findings are resolved or explicitly accepted before release |
| C-11 | No owned capability depends on a development fixture, a manual host step or an unrecorded configuration |
| C-12 | A teammate who is not this owner can run the owned capability from documentation alone (cross-familiarity, TEAM-R01) |

---

*End of 06C_Batu_Engineering_Roadmap.md (Draft — Derived from Approved 01/02 Baseline).*