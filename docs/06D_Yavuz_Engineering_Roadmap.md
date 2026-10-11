# 06D — Yavuz Engineering Roadmap
## Platform Engineering, Delivery & Reliability Owner

| Field | Value |
|---|---|
| Document | `06D_Yavuz_Engineering_Roadmap.md` |
| Status | **Draft — Derived from Approved 01/02 Baseline** (requires the owner's own review) |
| Version | v0.1.0-draft |
| Generated | 17 Eylül 2026 (pre-implementation) |
| Canonical role (01 Item 62) | Platform Engineering, Delivery & Reliability Owner |
| Owned work packages | 57 of 179 (2 F0 · 46 F1-class · 8 R1 · 1 R2/S) |
| Owned requirements | 106 (32 FR · 74 NFR) |
| Owned dependency nodes (05) | 24 |
| Upstream cross-owner HARD gates | 2 |
| Downstream cross-owner consumers | 13 HARD edges |
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

Own the ability of the Manufacturing Operations Platform to exist, run, survive and be reproduced by someone else. That means the monorepo platform baseline and Compose profiles, the shared 16 GiB Integration host, CI tiers and CD promotion of immutable artifacts, identity and platform security, observability, backup/restore and failure validation, the resource envelope everything must fit into, the experiment runtime that makes research runs reproducible, and the tooling (`mfgctl`) that makes all of it usable by a teammate on day one. This role is not 'the person who does Docker and CI' — it owns operability, recovery and reproducibility as product capabilities.

## 2. Removal-Test Statement

Remove Yavuz and the system becomes a set of demos on someone's laptop. There is no shared Integration environment, so the closed loop is never proven across real service boundaries; no immutable release identity, so no result can be attributed to a version; no observability, so failures are invisible and GS-01's correlation chain cannot be inspected; no identity runtime, so HITL approvals cannot bind to a real human; no backup, restore or failure validation, so the reliability requirements have no evidence at all; and no experiment runner or clean-host reproduction, so the research claims become unverifiable assertions. Two entire critical paths (CP-3 reproducibility, and the runtime half of CP-1) disappear with this role.

**Removal test in numbers.** Removing this role removes 2 F0 work packages (WP-PLAT-001, WP-CICD-002), 106 owned requirements and 24 owned dependency nodes, including 10 nodes that other owners depend on through 13 HARD edges.

### 2.1 Boundaries this role may not cross

Ownership is bounded in both directions: these rules protect other roles from this one, and are enforced by tests rather than by convention.

| Boundary | Source | How it is enforced in the plan |
|---|---|---|
| Runtime ownership ≠ business semantic ownership | Item 62 #101 | Operating PostgreSQL does not confer authority over LotStatus meaning. |
| NATS runtime ≠ event meaning | Item 62 #103 | Event semantics belong to the canonical producer. |
| OpenObserve ownership ≠ domain metric meaning | Item 62 #104 | Telemetry is diagnostic; business truth lives in application data. |
| Keycloak admin ≠ manufacturing approver | Item 62 #105 | Identity administration grants no operational approval authority. |
| Infrastructure privilege ≠ operational business authority | Item 62 #106 | Platform access never becomes a shortcut around the authority policy. |
| Platform cannot mutate manufacturing state directly | Item 62 #107 | No platform tooling writes to domain tables; recovery uses application paths. |
| Platform cannot alter domain semantics for operational convenience | Item 62 #128 | Resource pressure is reported as a constraint, not resolved by changing meaning. |

## 3. Owned Architecture Surfaces

Architecture components (02 registry) reached through this role's work packages, and the 05 readiness nodes that carry them.

| Readiness node (05) | Surface | Type | 02 ARCH anchor | Final readiness required |
|---|---|---|---|---|
| DN-ART-HWPROF | HardwareProfile records (EVALUATION host, CPU baseline, Vision GPU/CPU) | ARTIFACT | ARCH-PLAT-RELEASE | FROZEN |
| DN-ART-RELEASE | ReleaseManifest + EnvironmentManifest (stable release) | ARTIFACT | ARCH-PLAT-RELEASE | FROZEN |
| DN-FRZ-RELEASE | Stable release / environment freeze for formal runs | FREEZE | ARCH-PLAT-RELEASE | FROZEN |
| DN-PLAT-BACKUP | Backup / restore / rebuild automation | CAPABILITY | ARCH-PLAT-BACKUP | EVALUATION_READY |
| DN-PLAT-CD | CD to INTEGRATION (immutable GHCR artifacts, DeploymentRecord) | CAPABILITY | ARCH-PLAT-CICD, ARCH-PLAT-RELEASE | INTEGRATION_READY |
| DN-PLAT-CLEANREPRO | Clean reproduction (clean host, non-owner rerun) | EVIDENCE | ARCH-PLAT-RELEASE | EVALUATION_READY |
| DN-PLAT-COMPOSE | Docker Compose local capability profiles | RUNTIME | ARCH-PLAT-COMPOSE | EVALUATION_READY |
| DN-PLAT-FAILVAL | Failure validation (resilience drills, AV-SCEN-05…12) | EVIDENCE | ARCH-OBS-HEALTH | EVALUATION_READY |
| DN-PLAT-INTEG | Integration runtime (shared Linux host bootstrap) | RUNTIME | ARCH-PLAT-COMPOSE | EVALUATION_READY |
| DN-PLAT-REPO | Repository, protected main, CI baseline | CAPABILITY | ARCH-PLAT-CICD | INTEGRATION_READY |
| DN-PLAT-RUNNER | Experiment runner (manifest binding, BenchmarkRun registry) | CAPABILITY | — (no 02 ARCH ID,  GAP-RTM-002) | FROZEN |
| DN-PLAT-TOOLING | Runtime language/tooling baseline + mfgctl | CAPABILITY | ARCH-PLAT-CLI | COMPONENT_READY |
| DN-RES-BENCH | Final Benchmark Campaign FBC-01 (sealed evidence) | EVIDENCE | ARCH-PLAT-RELEASE, ARCH-DATA-OBJ | FROZEN |
| DN-RES-HARNESS | Evaluation harnesses (per lane) | CAPABILITY | — (GAP-RTM-002) | FROZEN |
| DN-RT-IDP | Keycloak identity runtime | RUNTIME | ARCH-SEC-IDP | EVALUATION_READY |
| DN-RT-MLFLOW | MLflow tracking/registry support tooling | RUNTIME | — (no 02 ARCH ID,  GAP-RTM-001) | EVALUATION_READY |
| DN-RT-NATS | NATS JetStream runtime | RUNTIME | ARCH-EVT-BROKER | EVALUATION_READY |
| DN-RT-OBJ | SeaweedFS object storage | RUNTIME | ARCH-DATA-OBJ | EVALUATION_READY |
| DN-RT-OBS | OTel SDK + Collector + OpenObserve | RUNTIME | ARCH-OBS-TELEMETRY, ARCH-OBS-STORE, ARCH-OBS-TRACE | EVALUATION_READY(reliability telemetry, M5) |
| DN-RT-PG | PostgreSQL runtime | RUNTIME | ARCH-DATA-PG | EVALUATION_READY |
| DN-RT-QDRANT | Qdrant runtime | RUNTIME | ARCH-DATA-VECTOR | EVALUATION_READY |
| DN-RT-TEMPORAL | Temporal server runtime | RUNTIME | ARCH-AUTO-WORKFLOW | EVALUATION_READY |
| DN-RT-VALKEY | Valkey (optional cache; R2/S, correctness-independent) | RUNTIME | ARCH-DATA-CACHE | SKELETON_READY |
| DN-SEC-BASE | Security baseline: service identities, secrets sourcing, backend authz enforcement points | CAPABILITY | ARCH-SEC-SECRET, ARCH-SEC-AUTHZ | EVALUATION_READY |

**ARCH components touched:** `ARCH-AI-ORCH`, `ARCH-AI-PROVIDER`, `ARCH-AI-RAG`, `ARCH-AI-TOOLS`, `ARCH-AUTO-IDEMPOTENCY`, `ARCH-AUTO-VERIFY`, `ARCH-AUTO-WORKFLOW`, `ARCH-CORE-CMD`, `ARCH-CORE-DB`, `ARCH-CORE-DOMAIN`, `ARCH-CORE-OUTBOX`, `ARCH-CTR-API`, `ARCH-CTR-VERSIONING`, `ARCH-DATA-CACHE`, `ARCH-DATA-LINEAGE`, `ARCH-DATA-OBJ`, `ARCH-DATA-PG`, `ARCH-DATA-VECTOR`, `ARCH-EDGE-AUTH`, `ARCH-EDGE-BFF`, `ARCH-EDGE-NOTIFY`, `ARCH-EDGE-WEB`, `ARCH-EVT-BROKER`, `ARCH-EVT-CONSUMER`, `ARCH-EVT-OUTBOX`, `ARCH-EVT-REPLAY`, `ARCH-HITL-APPROVAL`, `ARCH-HITL-POLICY`, `ARCH-OBS-AUDIT`, `ARCH-OBS-HEALTH`, `ARCH-OBS-STORE`, `ARCH-OBS-TELEMETRY`, `ARCH-OBS-TRACE`, `ARCH-PLAT-BACKUP`, `ARCH-PLAT-CICD`, `ARCH-PLAT-CLI`, `ARCH-PLAT-COMPOSE`, `ARCH-PLAT-RELEASE`, `ARCH-SCH-ENGINE`, `ARCH-SEC-AUTHZ`, `ARCH-SEC-BREAKGLASS`, `ARCH-SEC-IDP`, `ARCH-SEC-SECRET`, `ARCH-SEC-SUPPLYCHAIN`, `ARCH-SIM-ORACLE`, `ARCH-TWIN-API`, `ARCH-TWIN-FRESHNESS`, `ARCH-TWIN-PROJECTOR`, `ARCH-TWIN-REBUILD`, `ARCH-VIS-ARTIFACT`, `ARCH-VIS-INFER`, `ARCH-WORLD-EVALZONE`.

## 4. Owned FR/NFR Families

Ownership here means PrimaryOwner in the 01 catalogue: this role is accountable for the requirement's correctness, its trace mapping (03) and its final disposition.

### 4.FEVAL FR-EVAL (6)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-EVAL-001 | R1 | WP-RES-001, WP-BENCH-001 | TEST-EVAL-RUNNER, REPRO-NONOWNER-001, BENCH-FBC-001 |
| FR-EVAL-003 | R1 | WP-RES-003, WP-BENCH-001 | TEST-EVAL-RUNRECORD, BENCH-FBC-001 |
| FR-EVAL-004 | R1 | WP-RES-003 | TEST-EVAL-RUNRECORD, TEST-DATA-ACCOUNTING, BENCH-FBC-001 |
| FR-EVAL-005 | R1 | WP-RES-003 | TEST-EVAL-RUNRECORD, BENCH-FBC-001 |
| FR-EVAL-007 | R1 | WP-RES-005, WP-BENCH-005 | INSP-EVAL-SEAL, TEST-DATA-REFINTEGRITY, BENCH-FBC-001 |
| FR-EVAL-008 | R1 | WP-DR-004 | RESTORE-EVID-001, INSP-REC-BACKUP |

### 4.FEVT FR-EVT (2)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-EVT-009 | F1 | WP-EVT-004 | TEST-EVT-REPLAY-DLQ, RES-BROKER-001 |
| FR-EVT-010 | F1 | WP-EVT-004 | TEST-EVT-REPLAY-DLQ, RES-DEPFAIL-001 |

### 4.FGOV FR-GOV (3)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-GOV-005 | F1 | WP-GOV-002, WP-TEST-007 | TEST-GOV-TRACELINT |
| FR-GOV-006 | F1 | WP-GOV-003, WP-BENCH-005 | TEST-GOV-TRACELINT, INSP-GOV-ACCEPT |
| FR-GOV-009 | F1 | WP-GOV-002 | TEST-GOV-TRACELINT, INSP-GOV-ACCEPT |

### 4.FHITL FR-HITL (2)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-HITL-007 | F1 | WP-HITL-004, WP-TEST-006 | TEST-SEC-AUTHN, AV-SCEN-01, E2E-01 |
| FR-HITL-010 | F1 | WP-HITL-007 | TEST-SEC-BREAKGLASS, TEST-SEC-AUDIT |

### 4.FPLAT FR-PLAT (10)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-PLAT-001 | F0 | WP-PLAT-001, WP-PLAT-003 | TEST-PLAT-COMPOSE, TEST-DEP-PLATFORM, E2E-01, AV-SCEN-12, BENCH-E2E-001 |
| FR-PLAT-002 | F1 | WP-PLAT-001 | TEST-PLAT-COMPOSE, BENCH-DX-001 |
| FR-PLAT-003 | F1 | WP-PLAT-002 | TEST-PLAT-FABCTL, BENCH-DX-001 |
| FR-PLAT-004 | F1 | WP-CICD-001, WP-CICD-002 | TEST-PLAT-CD, INSP-DEP-HOST |
| FR-PLAT-005 | F1 | WP-PLAT-005, WP-CICD-002 | TEST-PLAT-CD, INSP-DEP-HOST |
| FR-PLAT-006 | F1 | WP-OBS-001 | TEST-OBS-TELEMETRY, AV-SCEN-01 |
| FR-PLAT-007 | F1 | WP-OBS-002 | TEST-OBS-TRACEPROP, AV-SCEN-01, BENCH-E2E-001 |
| FR-PLAT-008 | F1 | WP-DR-001 | RESTORE-PG-001, RESTORE-HOST-001, INSP-REC-BACKUP |
| FR-PLAT-009 | F1 | WP-DR-003 | RES-TWINREBUILD-001, RES-IDXREBUILD-001, AV-SCEN-08 |
| FR-PLAT-010 | F1 | WP-PLAT-005, WP-RES-001 | TEST-EVAL-RUNNER, DEMO-GS01-001, INSP-GOV-ACCEPT, BENCH-FBC-001 |

### 4.FSEC FR-SEC (8)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-SEC-001 | F1 | WP-SEC-001 | TEST-SEC-AUTHN, E2E-01, AV-SCEN-01 |
| FR-SEC-002 | F1 | WP-SEC-002 | TEST-SEC-SVCID, TEST-AUTH-NEG |
| FR-SEC-004 | F1 | WP-AI-002, WP-SEC-004 | TEST-SEC-AISURFACE, TEST-AUTH-NEG |
| FR-SEC-005 | F1 | WP-AI-002, WP-SEC-004 | TEST-SEC-AISURFACE, TEST-AUTH-NEG |
| FR-SEC-006 | F1 | WP-SEC-005 | TEST-SEC-SECRETS, INSP-DEP-HOST |
| FR-SEC-007 | F1 | WP-OBS-004 | TEST-SEC-AUDIT, TEST-OBS-AUDITSEP |
| FR-SEC-008 | F1 | WP-SEC-006 | TEST-SEC-TESTAUTH-NEG, E2E-01, DEMO-GS01-001 |
| FR-SEC-010 | F1 | WP-SIM-005, WP-SEC-007 | TEST-SEC-ORACLE-NEG, AV-SCEN-11, BENCH-RQ3-001 |

### 4.FUI FR-UI (1)

| Requirement | Class | Owning work packages | Verification families (03) |
|---|---|---|---|
| FR-UI-009 | F1 | WP-UI-009, WP-DOC-004 | TEST-UI-DIAG, DEMO-GS01-001 |

### 4.NCAP NFR-CAP (3)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-CAP-004 | A1 | durable application messages/s sustained; loss and duplicate protected effects | 100 msg/s × 10 min; loss = 0; duplicates = 0 | WP-EVT-006, WP-PERF-003 |
| NFR-CAP-009 | S2 | concurrent authenticated interactive sessions without correctness degradation | ≥ 8 sessions | WP-PLAT-004, WP-PERF-003 |
| NFR-CAP-010 | S2 | simultaneously existing isolated WorldIDs; cross-world leakage | ≥ 5 WorldIDs; leakage = 0 | WP-TWIN-005, WP-PERF-003 |

### 4.NDATA NFR-DATA (5)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-DATA-001 | H0 | final critical immutable artifacts with verified checksum/content identity | 100% | WP-OBJ-001 |
| NFR-DATA-003 | H0 | accepted final BenchmarkRunRecords with 100% mandatory provenance fields | 100% | WP-RES-003, WP-BENCH-005 |
| NFR-DATA-004 | H0 | unresolved mandatory artifact/run/evidence references in sealed evidence | = 0 | WP-RES-005, WP-BENCH-005 |
| NFR-DATA-007 | H0 | planned FBC experimental units reconciled to one documented disposition | 100% | WP-RES-003 |
| NFR-DATA-008 | H0 | persisted formal evidence fields with ambiguous UTC-vs-simulation time | = 0 | WP-EVT-002 |

### 4.NDEP NFR-DEP (6)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-DEP-001 | A1 | mandatory runtime deploys on documented x86-64 Linux + Docker/Compose without VM/K8s | PASS | WP-PLAT-001, WP-PLAT-003 |
| NFR-DEP-002 | S2 | startup → healthy or explicit known-degraded with images local | ≤ 10 min | WP-PLAT-001 |
| NFR-DEP-003 | H0 | manual source-code patches on target host for formal deployment | = 0 | WP-CICD-002 |
| NFR-DEP-004 | A1 | release-required migrations executed outside versioned automated tooling | = 0; status inspectable | WP-CORE-007, WP-CICD-003 |
| NFR-DEP-005 | H0 | private filesystem state / undocumented endpoints / hidden services in formal/public reproduction | = 0 | WP-BENCH-004 |
| NFR-DEP-006 | H0 | mandatory Kubernetes / paid cloud / mandatory VM dependencies in v1 baseline | = 0 | WP-PLAT-001 |

### 4.NDX NFR-DX (8)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-DX-001 | S2 | `mfgctl doctor` duration on healthy bootstrapped machine | ≤ 30 s | WP-PLAT-002 |
| NFR-DX-002 | S2 | high-value local lint/type/static validation duration | ≤ 90 s | WP-PLAT-002 |
| NFR-DX-003 | S2 | capability smoke duration (excl. first downloads) | ≤ 2 min | WP-PLAT-002 |
| NFR-DX-004 | S2 | normal capability profile ready time with images present | ≤ 5 min | WP-PLAT-002 |
| NFR-DX-005 | S2 | non-author clone→bootstrap→doctor→subsystem smoke | ≈ one focused hour (excl. bulk downloads) | WP-PLAT-006 |
| NFR-DX-006 | H0 | known unresolved unquarantined flaky tests in final release/benchmark gates | = 0 | WP-CICD-001, WP-TEST-001, WP-TEST-008 |
| NFR-DX-007 | A1 | quickstart/reproduction/runbook commands validated against applicable release | 100% before M8 | WP-PLAT-006, WP-DOC-001 |
| NFR-DX-008 | S2 | diagnostic-bundle generation duration; unredacted secrets | ≤ 2 min; secrets = 0 | WP-PLAT-006, WP-OBS-005 |

### 4.NGOV NFR-GOV (4)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-GOV-004 | H0 | quantitative NFRs lacking metric+measurement context | 0 | WP-GOV-003, WP-PERF-001 |
| NFR-GOV-005 | H0 | hardware-dependent final results without HardwareProfile | 0 | WP-GOV-003, WP-PERF-001 |
| NFR-GOV-006 | H0 | load-dependent final results without WorkloadProfile | 0 | WP-GOV-003, WP-PERF-001 |
| NFR-GOV-009 | H0 | VERIFIED NFRs without durable measurement evidence | 0 | WP-GOV-002, WP-DOC-006 |

### 4.NOBS NFR-OBS (9)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-OBS-001 | A1 | mandatory deployables exposing inspectable health/readiness | 100% | WP-OBS-001 |
| NFR-OBS-002 | A1 | team-owned mandatory services emitting structured logs with service/environment/correlation | 100% where applicable | WP-OBS-001 |
| NFR-OBS-003 | A1 | formal GS-01/E2E acceptance runs with complete traceable path across mandatory boundaries | 100% of acceptance runs | WP-OBS-002, WP-BENCH-002 |
| NFR-OBS-004 | A1 | hard failure → observable health/alert telemetry | ≤ 60 s | WP-OBS-003 |
| NFR-OBS-005 | H0 | formal evidence telemetry lacking EnvironmentID/WorldID/release/CorrelationID-TraceID | = 0 | WP-OBS-002 |
| NFR-OBS-006 | H0 | known plaintext secrets in final logs/evidence | = 0 | WP-OBS-005 |
| NFR-OBS-007 | H0 | protected-action audit records lost after telemetry loss/rotation | = 0; distinct stores/lifecycles | WP-OBS-004 |
| NFR-OBS-008 | S2 | overhead vs instrumentation-disabled diagnostic baseline | ≈ ≤10% p95 latency; ≤15% mean CPU (larger disclosed) | WP-OBS-006 |
| NFR-OBS-009 | A1 | retained useful Integration logs/metrics/traces under quota | ≥ 7 days | WP-OBJ-002, WP-OBS-006 |

### 4.NPERF NFR-PERF (1)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-PERF-012 | S2 | authenticated approve/reject submission → durable approval record | p95 ≤ 2 s | WP-HITL-004, WP-PERF-002 |

### 4.NREC NFR-REC (8)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REC-001 | A1 | recovery point age for canonical Integration mutable data | RPO ≤ 24 h | WP-DR-001 |
| NFR-REC-002 | H0 | EvidenceSeal → verified off-host copy of critical RC-B evidence | ≤ 30 min | WP-DR-004 |
| NFR-REC-003 | A1 | PostgreSQL restore + application smoke validation duration | ≤ 2 h | WP-DR-002 |
| NFR-REC-004 | A1 | simulated host loss → mandatory Integration reconstructed | ≤ 4 h | WP-DR-002 |
| NFR-REC-005 | S2 | rollback decision → known-good compatible release verified | ≤ 20 min where technically safe | WP-CICD-005 |
| NFR-REC-006 | H0 | acceptance/DR-critical backup artifacts failing checksum/integrity verification | = 0 (100% verified) | WP-DR-001 |
| NFR-REC-007 | H0 | full-host-loss reconstruction/restore drill result before M8 | ≥ 1 PASS | WP-DR-002, WP-BENCH-003 |
| NFR-REC-010 | H0 | formal restore drills missing backup source/target release/EnvironmentID/timestamps/result | = 0 | WP-DR-001 |

### 4.NREL NFR-REL (6)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REL-003 | A1 | intentional crash → healthy | ≤ 2 min | WP-PERF-004 |
| NFR-REL-005 | A1 | reboot with intact volumes → healthy or accepted known-degraded | ≤ 10 min | WP-TEST-005, WP-PERF-004 |
| NFR-REL-006 | A1 | 5-min broker interruption → backlog drain; committed Core effect loss | drain ≤ 15 min; loss = 0 | WP-TEST-004, WP-PERF-004 |
| NFR-REL-007 | A1 | unhandled crash loops / data corruption / effect duplication over soak | 8 h; all = 0 | WP-PERF-005 |
| NFR-REL-008 | A1 | duration of unbounded monotonic queue/backlog growth | ≤ 15 min (else capacity exceeded) | WP-PERF-004 |
| NFR-REL-009 | A1 | dependency loss → DEGRADED/UNAVAILABLE/MANUAL_REQUIRED visibility time | ≤ 60 s where observable | WP-OBS-003, WP-PERF-004 |

### 4.NREP NFR-REP (6)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-REP-003 | A1 | clean compatible host deploys exact ReleaseManifest without private state | PASS | WP-PLAT-005, WP-BENCH-004 |
| NFR-REP-004 | A1 | non-owner teammate reproductions of selected final environment/scenario | ≥ 1 PASS before M8 | WP-BENCH-003, WP-BENCH-004 |
| NFR-REP-005 | H0 | known stale generated runtime-required clients/contracts in formal release | = 0 | WP-CICD-004 |
| NFR-REP-006 | H0 | unlocked/unpinned mandatory dependencies; unbounded latest in formal identity | = 0 | WP-CICD-004 |
| NFR-REP-007 | H0 | formal deployments referencing mutable artifact/image identities | = 0 | WP-PLAT-005 |
| NFR-REP-008 | A1 | OSR-3 clean-clone hero reproduction of v1 public (or sanitized) package | PASS | WP-BENCH-004, WP-DOC-005 |

### 4.NRES NFR-RES (8)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-RES-001 | A1 | p95 cgroup-accounted combined mandatory container memory over 30-min steady window | ≤ 12 GiB | WP-PLAT-004 |
| NFR-RES-002 | A1 | combined mandatory container memory during accepted short peaks; OOM kills | ≤ 14 GiB; OOM = 0 | WP-PLAT-004 |
| NFR-RES-003 | H0 | OOM kills during final 8-hour normal soak | = 0 | WP-PLAT-004 |
| NFR-RES-004 | A1 | free persistent-filesystem capacity at Benchmark/Demo preflight | ≥ 20% (or explicit allocated headroom) | WP-PLAT-007 |
| NFR-RES-005 | H0 | undeclared concurrent training/bulk indexing/heavy CI during formal benchmark/performance/demo | = 0 | WP-PLAT-007 |
| NFR-RES-006 | A1 | storage classes without explicit retention/quota limit | = 0 | WP-OBJ-002 |
| NFR-RES-007 | A1 | GPU requirement in mandatory quickstart / CPU smoke path | none required | WP-VIS-008 |
| NFR-RES-008 | C3 | mean CPU, p95 CPU, saturation behavior | C3 — characterize | WP-PLAT-004 |

### 4.NSEC NFR-SEC (10)

| Requirement | Class | Metric (index form, 03 View G) | Threshold | Owning work packages |
|---|---|---|---|---|
| NFR-SEC-001 | H0 | known live secrets/credentials in release + publishable Git history | = 0 | WP-SEC-005, WP-DOC-005 |
| NFR-SEC-002 | H0 | known unmitigated Critical vulnerabilities in mandatory deployed components | = 0 (High → documented disposition) | WP-CICD-004 |
| NFR-SEC-003 | A1 | browser ingress without TLS in INTEGRATION/EVALUATION/DEMO | = 0 endpoints | WP-SEC-001 |
| NFR-SEC-005 | H0 | accepted protected approvals not mapping to exactly one authenticated authorized human | = 0 | WP-HITL-004 |
| NFR-SEC-006 | H0 | uses of bounded test-auth bypass in accepted formal runs | = 0 | WP-SEC-006 |
| NFR-SEC-007 | H0 | team-owned mandatory containers running privileged | = 0 (infra exceptions reviewed) | WP-SEC-002 |
| NFR-SEC-008 | A1 | team-owned application containers running as root without approved exception | = 0 | WP-SEC-002 |
| NFR-SEC-010 | H0 | audit coverage of proposal/plan binding, actor, approval, command, effect verification | 100% | WP-HITL-005, WP-SEC-008 |
| NFR-SEC-011 | H0 | privileged credentials / sensitive runners available to untrusted fork/PR jobs | = 0 | WP-CICD-006 |
| NFR-SEC-012 | H0 | break-glass invocations generating explicit high-risk audit records | 100% (if enabled) | WP-HITL-007 |

## 5. Critical Contracts

_This role produces no cross-service contract node of its own; it consumes contracts owned by others (see §6)._

### 5.1 Contracts this role consumes

_No cross-owner contract consumption._

### 5.2 Verification assets owned by this role

Planned verification families whose semantic correctness belongs to this role (03 §9.X). Asset identities are planning-level; numeric TestIDs are allocated when the assets are created.

| Family | Kind | Scope | Lane / tier | Min environment | Work packages relying on it |
|---|---|---|---|---|---|
| TEST-GOV-CATALOG | TEST | Machine-readable requirement catalog lint: ID pattern/uniqueness/non-reuse, single PrimaryOwner, class, source-ref presence | ENG-A | CI | WP-GOV-001 |
| TEST-GOV-TRACELINT | TEST | Trace-registry linter (Item 83 CI Trace Validation checks 1–10) incl. VERIFIED-without-evidence rejection | ENG-A | CI | WP-BENCH-005, WP-DOC-002, WP-DOC-006, WP-GOV-001, WP-GOV-002, WP-GOV-003 |
| INSP-GOV-ACCEPT | INSP | Generated AcceptanceCoverageReport + ReleaseAcceptanceRecord reproducibility review | ENG-A | EVALUATION | WP-BENCH-005, WP-DOC-006, WP-GOV-002, WP-GOV-003, WP-PLAT-005, WP-RES-001 |
| TEST-EVT-REPLAY-DLQ | TEST | Replay side-effect protection + poison/DLQ discoverability | ENG-D | CI | WP-EVT-004 |
| TEST-SEC-BREAKGLASS | TEST | Break-glass path distinction, audit emission, no hard-invariant bypass | ENG-C | INTEGRATION | WP-HITL-007 |
| TEST-UI-DIAG | TEST | Environment/release/world diagnostic surface | ENG-A | INTEGRATION | WP-DOC-004, WP-UI-009 |
| AV-SCEN-07 | SCENARIO | Architecture validation scenario: Broker interruption and backlog recovery | AVG | INTEGRATION | WP-CORE-005, WP-PERF-004, WP-TEST-004, WP-TWIN-002, WP-UI-008 |
| AV-SCEN-11 | SCENARIO | Architecture validation scenario: Oracle-access negative validation | AVG | INTEGRATION | WP-AI-005, WP-SEC-007, WP-SEC-008, WP-SIM-005, WP-SIM-006, WP-TEST-005 |
| AV-SCEN-12 | SCENARIO | Architecture validation scenario: Shared-host reboot and controlled recovery | AVG | INTEGRATION | WP-PERF-004, WP-PLAT-001, WP-PLAT-003, WP-TEST-005 |
| BENCH-FBC-001 | BENCH | FBC-01 campaign-level execution: BenchmarkCampaignManifest, preflight, run registry, sealing across all lanes (R1 mechanisms exercised formally) | FBC | EVALUATION | WP-BENCH-001, WP-BENCH-005, WP-DOC-003, WP-PLAT-005, WP-RES-001, WP-RES-002 |
| BENCH-E2E-001 | BENCH | FBC-01 final statistical E2E matrix: 4 frozen scenario definitions × 20 seeds (80 base instances) | E2E | EVALUATION | WP-AI-001, WP-AUTO-001, WP-AUTO-005, WP-AUTO-007, WP-BENCH-002, WP-CORE-001 |
| TEST-PLAT-COMPOSE | TEST | Compose profile render/validation + mandatory runtime composition on accepted Linux host | ENG-G | CI | WP-PLAT-001, WP-PLAT-003 |
| TEST-PLAT-FABCTL | TEST | mfgctl bootstrap/doctor/profile/scenario/smoke command contract tests | ENG-G | CI | WP-PLAT-002 |
| TEST-PLAT-CD | TEST | Main-derived immutable artifact deploy to INTEGRATION without host source patch; DeploymentRecord emission | ENG-G | INTEGRATION | WP-CICD-001, WP-CICD-002, WP-PLAT-005 |
| TEST-OBS-TELEMETRY | TEST | Centralized OTel → Collector → OpenObserve ingestion for logs/metrics/traces | ENG-D | INTEGRATION | WP-OBS-001 |
| TEST-OBS-TRACEPROP | TEST | CorrelationID/trace-context propagation across closed-loop async boundaries | ENG-D | INTEGRATION | WP-BENCH-002, WP-EVT-002, WP-OBS-002 |
| TEST-OBS-HEALTH | TEST | Health/readiness surface inventory for 100% mandatory deployables + failure-detection latency | ENG-D | INTEGRATION | WP-OBS-001, WP-OBS-003 |
| TEST-OBS-LOGS | TEST | Structured log field coverage (service, environment, correlation) | ENG-D | CI | WP-OBS-001 |
| TEST-OBS-REDACTION | TEST | Plaintext-secret scan over logs, diagnostic bundles and evidence | ENG-C | EVALUATION | WP-OBS-005, WP-PLAT-006 |
| TEST-OBS-AUDITSEP | TEST | Audit vs telemetry separation: telemetry rotation does not erase protected audit | ENG-C | INTEGRATION | WP-OBS-004 |
| BENCH-OBS-OVERHEAD | BENCH | Instrumentation overhead vs instrumentation-disabled diagnostic baseline (p95 latency, mean CPU) | PERF | EVALUATION | WP-OBS-006 |
| INSP-OBS-RETENTION | INSP | Telemetry retention/quota configuration + 7-day window inspection | ENG-D | INTEGRATION | WP-OBJ-002, WP-OBS-006 |
| TEST-SEC-AUTHN | TEST | Keycloak interactive authentication for formal flows; approval ↔ authenticated identity | ENG-C | INTEGRATION | WP-HITL-004, WP-SEC-001, WP-TEST-006 |
| TEST-SEC-SVCID | TEST | Declared service identities; anonymous mutation rejected; no universal super-credential | ENG-C | INTEGRATION | WP-AI-006, WP-CORE-001, WP-CORE-007, WP-EVT-005, WP-RES-009, WP-SEC-002 |
| TEST-SEC-AISURFACE | TEST | AI-reachable capability inventory: no shell / no arbitrary SQL surface | ENG-C | CI | WP-AI-002, WP-SEC-004 |
| TEST-SEC-SECRETS | TEST | Secret scanning of Git history, images, manifests; non-Git secret sourcing | ENG-C | CI | WP-DOC-005, WP-SEC-005 |
| TEST-SEC-AUDIT | TEST | Protected-action audit coverage: proposal/plan binding, actor, approval, command, effect verification | ENG-C | INTEGRATION | WP-AUTO-006, WP-HITL-005, WP-HITL-007, WP-OBS-004, WP-SEC-008 |
| TEST-SEC-TESTAUTH-NEG | TEST | Formal runtime rejects bounded test-auth bypass; run evidence shows 0 uses | ENG-C | EVALUATION | WP-SEC-006 |
| TEST-SEC-ORACLE-NEG | TEST | Oracle/evaluator-only data inaccessible to normal service identities (runtime denial) | ENG-C | EVALUATION | WP-SEC-007, WP-SIM-005, WP-TEST-005 |
| TEST-SEC-SUPPLYCHAIN | TEST | Vulnerability scan + disposition, lock/pin/digest verification, SBOM presence | ENG-C | CI | WP-CICD-004 |
| TEST-SEC-CONTAINER | TEST | Container runtime posture: no privileged mode, non-root with approved exceptions | ENG-C | INTEGRATION | WP-SEC-002 |
| TEST-SEC-TLS | TEST | TLS on browser ingress for INTEGRATION/EVALUATION/DEMO | ENG-C | INTEGRATION | WP-SEC-001 |
| TEST-SEC-CIISOLATION | TEST | Untrusted fork/PR jobs receive no privileged credentials and no sensitive runner | ENG-C | CI | WP-CICD-006 |
| TEST-EVAL-RUNNER | TEST | Experiment runner binds release/environment/hardware/data/scenario/seed identities | ENG-G | CI | WP-BENCH-001, WP-PLAT-005, WP-RES-001 |
| TEST-EVAL-RUNRECORD | TEST | BenchmarkRunID/status record; failed/invalid attempts retained; RetryOf/disposition provenance | ENG-G | EVALUATION | WP-BENCH-001, WP-RES-003 |
| INSP-EVAL-SEAL | INSP | EvidenceSeal + FinalBenchmarkEvidenceBundle completeness and immutability | RQ* | EVALUATION | WP-BENCH-005, WP-RES-005 |
| RESTORE-EVID-001 | DRILL | Off-host copy + restore test of FinalBenchmarkEvidenceBundle | ENG-F | EVALUATION | WP-DR-004 |
| BENCH-CAP-EVT | BENCH | Application event pipeline sustained 100 msg/s × 10 min | PERF | EVALUATION | WP-EVT-006, WP-PERF-003, WP-PERF-004 |
| BENCH-CAP-ENV | BENCH | Interactive session concurrency and isolated-WorldID capacity | PERF | EVALUATION | WP-PERF-003, WP-PLAT-004, WP-TWIN-005 |
| BENCH-RES-FOOTPRINT | BENCH | cgroup memory steady/peak and CPU mean/p95/saturation under WP-NORMAL and stress | PERF | EVALUATION | WP-PERF-003, WP-PLAT-004, WP-SIM-008 |
| RES-PROCESS-001 | DRILL | Stateless team-owned service crash → healthy within bound | ENG-D | INTEGRATION | WP-OBS-003, WP-PERF-004 |
| RES-BROKER-001 | DRILL | 5-minute broker interruption under WP-NORMAL → backlog drain, no committed-effect loss (AV-SCEN-07 execution) | ENG-D | INTEGRATION | WP-CORE-005, WP-EVT-004, WP-PERF-004, WP-TEST-004 |
| RES-REBOOT-001 | DRILL | Host reboot with intact volumes → healthy/known-degraded (AV-SCEN-12 execution) | ENG-D | INTEGRATION | WP-PERF-004, WP-TEST-005 |
| RES-SOAK-001 | DRILL | 8-hour WP-NORMAL soak: crash loops, corruption, duplication, OOM, queue growth, memory | ENG-D | EVALUATION | WP-PERF-003, WP-PERF-004, WP-PERF-005, WP-PLAT-004, WP-SIM-008 |
| RES-DEPFAIL-001 | DRILL | Mandatory dependency loss → DEGRADED/UNAVAILABLE/MANUAL_REQUIRED visibility within bound | ENG-D | INTEGRATION | WP-EVT-004, WP-OBS-003, WP-PERF-004 |
| RESTORE-PG-001 | DRILL | PostgreSQL restore from accepted backup + application-level smoke validation | ENG-F | INTEGRATION | WP-DR-001, WP-DR-002 |
| RESTORE-HOST-001 | DRILL | Full-host-loss reconstruction from Git + manifests + registry + off-host backups | ENG-F | EVALUATION | WP-BENCH-003, WP-DR-001, WP-DR-002 |
| RESTORE-ROLLBACK-001 | DRILL | Known-good compatible release rollback where migration state permits | ENG-F | INTEGRATION | WP-CICD-005 |
| INSP-REC-BACKUP | INSP | BackupSet checksum/integrity, off-host copy timing, RPO schedule and drill provenance fields | ENG-F | EVALUATION | WP-DR-001, WP-DR-004 |
| TEST-REP-CODEGEN | TEST | Generated client/contract drift detection (CI-detectable, DX-INV-21) | ENG-G | CI | WP-CICD-004 |
| TEST-REP-LOCKS | TEST | Lockfile/pin/digest resolution; unbounded latest prohibited; immutable deployment identity | ENG-G | CI | WP-CICD-004, WP-PLAT-005 |
| REPRO-CLEANHOST-001 | DRILL | Clean compatible host deploys exact ReleaseManifest without private developer state | ENG-G | EVALUATION | WP-BENCH-004, WP-PLAT-005 |
| REPRO-NONOWNER-001 | DRILL | Non-owner teammate reproduction of selected final environment/scenario (ENG-G) | ENG-G | EVALUATION | WP-BENCH-001, WP-BENCH-003, WP-BENCH-004, WP-RES-001, WP-SIM-002, WP-SIM-009 |
| REPRO-OSR3-001 | DRILL | v1 public (or sanitized embargoed) package OSR-3 clean-clone hero reproduction | ENG-I | PUBLIC_REPRO | WP-BENCH-004, WP-DOC-005 |
| TEST-RES-PREFLIGHT | TEST | Benchmark/Demo preflight: disk headroom, undeclared heavy workload exclusion | ENG-E | EVALUATION | WP-PLAT-007 |
| INSP-RES-RETENTION | INSP | Explicit retention/quota limits for logs/metrics/traces/caches/derived artifacts | ENG-D | INTEGRATION | WP-OBJ-002 |
| TEST-RES-CPUONLY | TEST | Quickstart + CPU smoke path on GPU-less host | ENG-G | CI | WP-VIS-008 |
| TEST-DEP-PLATFORM | TEST | x86-64 Linux + Docker/Compose deployment without VM/Kubernetes/paid cloud | ENG-G | INTEGRATION | WP-PLAT-001, WP-PLAT-003 |
| BENCH-DEP-STARTUP | BENCH | Full Integration profile startup-to-healthy with pre-pulled images | ENG-G | INTEGRATION | WP-PLAT-001 |
| TEST-DEP-MIGRATION | TEST | Versioned automated migration execution with inspectable status (CD path) | ENG-B | INTEGRATION | WP-CICD-003, WP-CORE-007 |
| INSP-DEP-HOST | INSP | DeploymentRecord audit: zero host source patches, no hidden runtime dependency, no mandatory cloud/K8s/VM | ENG-G | EVALUATION | WP-BENCH-004, WP-CICD-001, WP-CICD-002, WP-PLAT-001, WP-PLAT-005, WP-PLAT-007 |
| BENCH-DX-001 | BENCH | DX timing suite: doctor, static validation, capability smoke, local profile startup, diagnostic bundle | ENG-G | DEV | WP-OBS-005, WP-PLAT-001, WP-PLAT-002, WP-PLAT-006 |
| INSP-DX-ONBOARD | INSP | Non-author onboarding walk-through record (clone→bootstrap→doctor→smoke) | ENG-G | DEV | WP-PLAT-006 |
| TEST-DX-FLAKE | TEST | Flaky-test registry/quarantine gate for release/benchmark gates (no retry-until-green) | ENG-G | CI | WP-CICD-001, WP-TEST-001, WP-TEST-008 |
| TEST-DX-DOCS | TEST | Executable documentation validation of quickstart/reproduction/runbook commands against release | ENG-G | EVALUATION | WP-DOC-001, WP-PLAT-006 |
| TEST-DATA-CHECKSUM | TEST | Checksum/content identity verification for final critical immutable artifacts | ENG-B | EVALUATION | WP-DR-001, WP-OBJ-001, WP-VDATA-004 |
| TEST-DATA-REFINTEGRITY | TEST | Sealed evidence: BenchmarkRunRecord mandatory-field completeness + zero unresolved references | RQ* | EVALUATION | WP-BENCH-005, WP-GOV-003, WP-OBS-002, WP-PERF-001, WP-RES-003, WP-RES-005 |
| TEST-DATA-ACCOUNTING | TEST | FBC planned-experimental-unit reconciliation to RunDispositionRegister | RQ* | EVALUATION | WP-RES-003 |
| TEST-DATA-TIME | TEST | UTC wall-clock vs simulation-time field semantics in persisted formal evidence | ENG-B | CI | WP-EVT-002 |

## 6. Upstream Dependencies

What this role must receive from others before it can pass a stage. Fixture-satisfiable rows are marked; the rest require the real upstream capability.

| DEP | Predecessor (owner) | Feeds node | Kind | Strength | Stage | Required readiness | Need-by | Fallback | Unblock evidence |
|---|---|---|---|---|---|---|---|---|---|
| DEP-125 | DN-RES-BASELINES (Asrın) | DN-RES-HARNESS | EVIDENCE | HARD | INTEGRATION | EVALUATION_READY | M5 (S10) | — | harness reproduces baseline numbers |
| DEP-139 | DN-FRZ-PROTOCOL (Asrın) | DN-FRZ-RELEASE | FREEZE | HARD | FREEZE | FROZEN | M6 (S11) | — | ExperimentProtocolFreeze recorded |

## 7. Downstream Consumers

What others cannot do until this role delivers. Every row is a commitment with a need-by point.

| DEP | Delivered node | Consumer (owner) | Kind | Strength | Stage | Required readiness | Need-by | Unblock evidence |
|---|---|---|---|---|---|---|---|---|
| DEP-019 | DN-RT-PG | DN-CORE-LIFECYCLE (Asrın) | RUNTIME | HARD | INTEGRATION | SKELETON_READY | M1 (S2) | Core migrations apply on PostgreSQL |
| DEP-025 | DN-RT-NATS | DN-EVT-SPINE (Asrın) | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | M1 (S2) | real JetStream in CI + INTEGRATION (no fake bus, CI-INV-07) |
| DEP-033 | DN-RT-PG | DN-TWIN-SKELETON (Asrın) | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | M1 (S2) | `twin` schema migrated |
| DEP-045 | DN-RT-OBJ | DN-SIM-SNAPFORK (Batu) | RUNTIME | SOFT | INTEGRATION | INTEGRATION_READY | M2 (S4) | snapshot checkpoints stored as object artifacts |
| DEP-090 | DN-RT-IDP | DN-HITL-APPROVAL (Asrın) | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 readiness (end S4) | authenticated approval bound to actor |
| DEP-108 | DN-RT-IDP | DN-UI-APPROVAL (Asrın) | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 readiness (end S4) | real login in Approval Center |
| DEP-047 | DN-SEC-BASE | DN-SIM-ORACLE (Batu) | CAPABILITY | HARD | MILESTONE_EXIT | INTEGRATION_READY | E2E-01 (end S5) | normal runtime credentials denied Oracle access (negative test) |
| DEP-058 | DN-RT-OBJ | DN-VIS-SERVING (Selman) | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 (end S5) | artifact read via ArtifactRef on SeaweedFS |
| DEP-095 | DN-RT-TEMPORAL | DN-AUTO-DURABLE (Batu) | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | E2E-01 formal run (end S5) | workflow persists through worker restart on real Temporal |
| DEP-055 | DN-RT-MLFLOW | DN-VIS-MODELS (Selman) | RUNTIME | HARD | MILESTONE_EXIT | INTEGRATION_READY | M4/M5 | ModelPackage promotion recorded in MLflow + artifact store |
| DEP-071 | DN-RT-QDRANT | DN-RAG (Asrın) | RUNTIME | HARD | INTEGRATION | INTEGRATION_READY | M4 (S8) | RAG retrieval served from Qdrant on INTEGRATION |
| DEP-075 | DN-RT-MLFLOW | DN-ML (Asrın) | RUNTIME | HARD | MILESTONE_EXIT | INTEGRATION_READY | M4/M5 | ML ModelPackage governance in MLflow |
| DEP-127 | DN-RES-HARNESS | DN-RES-CALIB (Asrın) | EVIDENCE | HARD | FREEZE | EVALUATION_READY | M5→M6 | calibration on CAL partition recorded |
| DEP-143 | DN-RES-BENCH | DN-RES-ANALYSIS (Asrın) | EVIDENCE | HARD | FREEZE | FROZEN | M7 (S12) | sealed FBC-01 evidence |

**Delivery load by consumer:** Asrın: 9 HARD edges, Batu: 2 HARD edges, Selman: 2 HARD edges.

## 8. Milestone-by-Milestone Engineering Objectives

### 8.M0 M0 — Engineering Foundation Ready (End S1 / Week 2)

M0 is Yavuz's milestone to deliver, not just support: repository with protected main, CI entrypoint, container tooling baseline, Compose profiles and the Integration bootstrap. Everyone else's ability to start in parallel depends on this window closing on time (Item 66 #94–#95).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-CICD-001 | CI pipeline and required gates | F1 | 3 | M |

**Owned requirements reaching their target in this window (2):** FR-PLAT-004, NFR-DX-006

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

M1 brings the runtime spine up: PostgreSQL and NATS healthy on the Integration host, CD promoting main-derived immutable images to GHCR and deploying without host patches, basic health instrumentation and log/metric collection, and the first DeploymentRecords. The `mfgctl` bootstrap/doctor path should already make a fresh machine usable.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-PLAT-001 | Compose profiles and mandatory runtime composition | F0 | 4 | M |
| WP-PLAT-002 | mfgctl developer and operator CLI | F1 | 4 | M |
| WP-CICD-002 | CD to INTEGRATION with immutable artifacts | F0 | 3 | M |
| WP-OBS-001 | Telemetry pipeline (OTel → Collector → OpenObserve) | F1 | 4 | M |
| WP-TEST-001 | Test strategy, tiers and boundary-mode policy | F1 | 3 | M |

**Owned requirements reaching their target in this window (17):** FR-PLAT-001, FR-PLAT-002, FR-PLAT-003, FR-PLAT-004, FR-PLAT-005, FR-PLAT-006, NFR-DEP-001, NFR-DEP-002, NFR-DEP-003, NFR-DEP-006, NFR-DX-001, NFR-DX-002, NFR-DX-003, NFR-DX-004, NFR-DX-006, NFR-OBS-001, NFR-OBS-002

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (3):** DEP-019 → Asrın, DEP-025 → Asrın, DEP-033 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M2 M2 — Operational Manufacturing Alpha (End S4 / Week 8)

M2 adds the artifact and identity layers the closed loop needs: SeaweedFS for inspection artifacts and snapshots, Keycloak realm configuration with real login, migration automation in the deployment path, and the readiness staging that the E2E-01 gate demands by end S4. Temporal must be ready for the formal E2E run by end S5 (05 DEP-GAP-04).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-GOV-002 | Trace registry, edges and trace linter | F1 | 4 | L |
| WP-OBJ-001 | Artifact service: ArtifactRef contract and object storage integration | F1 | 4 | M |
| WP-PLAT-003 | Runtime service bring-up on the shared host | F1 | 3 | M |
| WP-CICD-003 | Automated migration execution in the deployment path | F1 | 3 | S |
| WP-TEST-007 | Architecture rules and trace validation in CI | F1 | 3 | S |

**Owned requirements reaching their target in this window (7):** FR-GOV-005, FR-GOV-009, FR-PLAT-001, NFR-DATA-001, NFR-DEP-001, NFR-DEP-004, NFR-GOV-009

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (2):** DEP-090 → Asrın, DEP-108 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M3 M3 — Closed-Loop Alpha (End S6 / Week 12)

M3 is where platform quality becomes visible in the product: distributed trace propagation across HTTP, NATS and Temporal so an incident is inspectable end to end, per-capability health states, and the environment/release/world identity surface in the Command Center. Yavuz reviews deployment, reproducibility and evidence capture before the E2E-01 formal run (Item 67 #218).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-HITL-004 | Identity-bound approvals | F1 | 3 | S |
| WP-OBS-002 | Distributed trace propagation across the closed loop | F1 | 3 | S |
| WP-SEC-001 | Keycloak realm, clients and interactive authentication | F1 | 3 | M |

**Owned requirements reaching their target in this window (8):** FR-HITL-007, FR-PLAT-007, FR-SEC-001, NFR-OBS-003, NFR-OBS-005, NFR-PERF-012, NFR-SEC-003, NFR-SEC-005

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (3):** DEP-047 → Batu, DEP-058 → Selman, DEP-095 → Batu

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M4 M4 — Mandatory Core Feature Complete (End S8 / Week 16)

M4 completes the mandatory platform and security surface: service identities and least-privilege credentials, secret sourcing outside Git, container posture, audit store separation, the AI capability-surface restriction checks, Qdrant and MLflow in the runtime, and resource profiles that keep everything inside the 16 GiB envelope.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-UI-009 | System health and environment diagnostics view | F1 | 3 | S |
| WP-OBS-003 | Health, readiness and degradation states | F1 | 3 | S |
| WP-OBS-004 | Audit store separation from telemetry | F1/H0 | 3 | S |
| WP-SEC-002 | Service identities and least-privilege credentials | F1/H0 | 3 | M |
| WP-SEC-004 | AI-reachable capability surface restriction | F1/H0 | 3 | S |
| WP-SEC-005 | Secret sourcing and hygiene | F1/H0 | 3 | M |
| WP-SEC-007 | Oracle access denial at runtime | F1/H0 | 3 | S |

**Owned requirements reaching their target in this window (13):** FR-SEC-002, FR-SEC-004, FR-SEC-005, FR-SEC-006, FR-SEC-007, FR-SEC-010, FR-UI-009, NFR-OBS-004, NFR-OBS-007, NFR-REL-009, NFR-SEC-001, NFR-SEC-007, NFR-SEC-008

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (3):** DEP-055 → Selman, DEP-071 → Asrın, DEP-075 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M5 M5 — Reliability & Evaluation Ready (End S10 / Week 20)

M5 is the reliability and evaluation-readiness milestone and it is dominated by this role: supply-chain scanning and pinning, backup automation with integrity verification, restore drills, failure injection and resilience drills, telemetry at evaluation grade, preflight tooling, and the experiment runner that binds every run to release, environment, hardware, data, scenario and seed identities.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-GOV-003 | Coverage reports and release acceptance record generation | F1 | 3 | M |
| WP-EVT-004 | Replay, poison message and DLQ operations | F1 | 3 | S |
| WP-OBJ-002 | Artifact lifecycle, retention and quota policy | F1 | 3 | S |
| WP-HITL-007 | Break-glass path with mandatory audit | F1 | 3 | S |
| WP-PLAT-004 | Resource profiles and footprint control | F1/A1 | 3 | M |
| WP-PLAT-005 | Environment, release and world manifests | F1 | 3 | M |
| WP-CICD-004 | Supply chain: pinning, scanning and SBOM | F1/H0 | 4 | M |
| WP-CICD-005 | Release rollback capability | F1/A1 | 3 | S |
| WP-CICD-006 | CI isolation for untrusted contributions | F1/H0 | 3 | S |
| WP-OBS-005 | Redaction and diagnostic bundles | F1/H0 | 3 | S |
| WP-SEC-006 | Test-auth prohibition in formal environments | F1/H0 | 3 | S |
| WP-SEC-008 | Security negative suite and external egress audit | F1/H0 | 3 | S |
| WP-DR-001 | Backup automation and integrity verification | F1/H0 | 4 | M |
| WP-DR-003 | Derived-state rebuild paths | F1 | 3 | S |
| WP-TEST-004 | Integration scenarios AV-SCEN-05…08 | F1 | 3 | M |
| WP-PERF-001 | Benchmark definitions, workload profiles and measurement protocol | F1 | 4 | M |
| WP-RES-001 | Experiment runner and run manifest binding | R1 | 3 | M |

**Owned requirements reaching their target in this window (36):** FR-EVAL-001, FR-EVT-009, FR-EVT-010, FR-GOV-006, FR-HITL-010, FR-PLAT-005, FR-PLAT-008, FR-PLAT-009, FR-PLAT-010, FR-SEC-008, NFR-CAP-009, NFR-DX-008, NFR-GOV-004, NFR-GOV-005, NFR-GOV-006, NFR-OBS-006, NFR-OBS-009, NFR-REC-001, NFR-REC-005, NFR-REC-006, NFR-REC-010, NFR-REL-006, NFR-REP-003, NFR-REP-005, NFR-REP-006, NFR-REP-007, NFR-RES-001, NFR-RES-002, NFR-RES-003, NFR-RES-006, NFR-RES-008, NFR-SEC-002, NFR-SEC-006, NFR-SEC-010, NFR-SEC-011, NFR-SEC-012

**Upstream gates that must close in this window (1):** DEP-125 from Asrın

**Commitments owed to others in this window (1):** DEP-127 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M6 M6 — Research Freeze (End S11 / Week 22)

M6 freezes the environment and release profile and confirms that every measurement context — hardware profiles, workload profiles, benchmark definitions — is complete. A performance number without its HardwareProfile is not admissible after this point (Item 66 #92).

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-PLAT-007 | Benchmark and demo preflight tooling | F1/H0 | 3 | S |
| WP-DR-002 | Restore drills: database and full host | F1/H0 | 3 | M |
| WP-TEST-008 | Flake control and release-gate hygiene | F1/S2 | 3 | S |
| WP-PERF-004 | Resilience drill execution | F1/H0 | 3 | S |
| WP-RES-003 | Benchmark run registry and disposition accounting | R1 | 3 | S |
| WP-DOC-001 | Engineering documentation set | F1 | 3 | S |

**Owned requirements reaching their target in this window (17):** FR-EVAL-003, FR-EVAL-004, FR-EVAL-005, NFR-DATA-003, NFR-DATA-007, NFR-DX-006, NFR-DX-007, NFR-REC-003, NFR-REC-004, NFR-REC-007, NFR-REL-003, NFR-REL-005, NFR-REL-006, NFR-REL-008, NFR-REL-009, NFR-RES-004, NFR-RES-005

**Upstream gates that must close in this window (1):** DEP-139 from Asrın

**Commitments owed to others in this window (0):** —

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M7 M7 — Final Benchmark Complete (End S12 / Week 24)

During the campaign Yavuz runs the campaign infrastructure: preflight gates, lane orchestration, run registry and disposition accounting, evidence sealing and off-host preservation, plus the performance, resilience, recovery and reproduction lanes themselves.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-EVT-006 | Event spine throughput and delivery characterization | F1/A1 | 3 | S |
| WP-OBS-006 | Telemetry retention, quota and instrumentation overhead | F1/S2 | 3 | S |
| WP-DR-004 | Evidence protection and off-host preservation | F1/H0 | 3 | S |
| WP-PERF-002 | Latency and throughput measurement execution | F1/A1 | 3 | M |
| WP-PERF-005 | Soak testing and resource behaviour under sustained load | F1/H0 | 3 | S |
| WP-RES-005 | Evidence sealing and bundle assembly | R1 | 3 | S |
| WP-BENCH-001 | Campaign manifest, preflight and lane orchestration | R1 | 3 | S |
| WP-BENCH-003 | Engineering lanes execution (ENG-A…I) | R1 | 3 | S |

**Owned requirements reaching their target in this window (13):** FR-EVAL-001, FR-EVAL-003, FR-EVAL-007, FR-EVAL-008, NFR-CAP-004, NFR-DATA-004, NFR-OBS-008, NFR-OBS-009, NFR-PERF-012, NFR-REC-002, NFR-REC-007, NFR-REL-007, NFR-REP-004

**Upstream gates that must close in this window (0):** —

**Commitments owed to others in this window (1):** DEP-143 → Asrın

**Milestone exit checklist for this role.**
- every listed work package meets 04 DoD (real repository references, trace edges updated in the same PR)
- every upstream gate listed above is satisfied with real unblock evidence — not a development fixture (05 DEP-RULE-04)
- every commitment owed to another owner is delivered at the declared readiness, with the consumer confirming usability (Item 66 #140)
- negative and failure paths for the capabilities in this window are tested, not deferred
- observability exists for every runtime capability delivered in this window
- owned requirements reaching this milestone have their trace state updated in 03


### 8.M8 M8 — Final Release Candidate (End S13 / Week 26)

M8 closes with the reproduction proofs — clean-host deployment from the exact ReleaseManifest, a non-owner reproduction, and the public package hero reproduction — plus the final restore drill, evidence preservation and the generated acceptance artifacts that make the release defensible.

| Work package | Title | Scope | Deliverable count | Size band |
|---|---|---|---|---|
| WP-PLAT-006 | Onboarding, executable documentation and diagnostics | F1/S2 | 3 | M |
| WP-BENCH-004 | Reproduction lanes: clean host, non-owner and public | R1 | 3 | M |
| WP-BENCH-005 | Evidence bundle finalization and acceptance reporting | R1 | 3 | S |
| WP-DOC-005 | Public release package (v1) | R1 | 3 | S |

**Owned requirements reaching their target in this window (12):** FR-EVAL-007, FR-GOV-006, NFR-DATA-003, NFR-DATA-004, NFR-DEP-005, NFR-DX-005, NFR-DX-007, NFR-DX-008, NFR-REP-003, NFR-REP-004, NFR-REP-008, NFR-SEC-001

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
| WP-R2-003 | R2 infrastructure candidates (Neo4j, TimescaleDB, Valkey optimization, GPU/distributed simulator) | R2 | no milestone, no mandatory dependant, cut first under pressure |

## 9. Work Package Mapping

Each package below is owned by this role. Deliverables and tasks are the 04 definitions; the execution context (gates, consumers, verification, evidence) is projected here so the package can be picked up without cross-reading four documents.

### 9.WP-CICD-001 — CI pipeline and required gates

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M0 · S1 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-004, NFR-DX-006 |
| Architecture | ARCH-PLAT-CICD, ARCH-PLAT-RELEASE |
| Gating edges | none — early unlocker |
| Verification families | INSP-DEP-HOST, TEST-DX-FLAKE, TEST-PLAT-CD |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- CI workflows (lint, type, unit, contract, integration tiers)
- required-check configuration
- flaky-test registry and quarantine policy

**Major tasks.**
- define pipeline stages and runtimes
- wire real PostgreSQL/NATS services for integration tier
- implement quarantine registry with expiry
- prohibit retry-until-green on release gates

**Cut/fallback.** No cut (M0 foundation).


### 9.WP-CICD-002 — CD to INTEGRATION with immutable artifacts

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-PLAT-CD |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-004, FR-PLAT-005, NFR-DEP-003 |
| Architecture | ARCH-PLAT-CICD, ARCH-PLAT-RELEASE |
| Gating edges | DEP-002 (DN-PLAT-REPO, M0→M1), DEP-005 (DN-PLAT-INTEG, M1 (S2)) |
| Verification families | INSP-DEP-HOST, TEST-PLAT-CD |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- build-and-publish workflow to GHCR
- deploy workflow with DeploymentRecord emission
- no-host-patch enforcement

**Major tasks.**
- implement image build with provenance and digest pinning
- implement deploy job and rollback hook
- emit DeploymentRecord with release/environment identity
- verify zero manual source patches on host

**Cut/fallback.** No cut (F0 reproducible platform).


### 9.WP-OBS-001 — Telemetry pipeline (OTel → Collector → OpenObserve)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M1 · S2 |
| Readiness node | DN-RT-OBS |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-006, NFR-OBS-001, NFR-OBS-002 |
| Architecture | ARCH-OBS-HEALTH, ARCH-OBS-STORE, ARCH-OBS-TELEMETRY |
| Gating edges | DEP-011 (DN-PLAT-INTEG, M1 (S2)), DEP-109 (DN-PLAT-CD, M3 (S6)) |
| Verification families | AV-SCEN-01, TEST-OBS-HEALTH, TEST-OBS-LOGS, TEST-OBS-TELEMETRY |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut; M1 requires health/basic instrumentation, M5 requires evaluation-grade telemetry.


### 9.WP-PLAT-001 — Compose profiles and mandatory runtime composition

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F0 · M1 · S2 |
| Readiness node | DN-PLAT-COMPOSE |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-001, FR-PLAT-002, NFR-DEP-001, NFR-DEP-002, NFR-DEP-006 |
| Architecture | ARCH-OBS-HEALTH, ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE |
| Gating edges | DEP-003 (DN-PLAT-TOOLING, M0 (S1)) |
| Verification families | AV-SCEN-12, BENCH-DEP-STARTUP, BENCH-DX-001, BENCH-E2E-001, E2E-01, INSP-DEP-HOST, TEST-DEP-PLATFORM, TEST-PLAT-COMPOSE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut (F0 reproducible platform). Kubernetes and cloud remain explicitly out of scope.


### 9.WP-PLAT-002 — mfgctl developer and operator CLI

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M1 · S2 |
| Readiness node | DN-PLAT-TOOLING |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-003, NFR-DX-001, NFR-DX-002, NFR-DX-003, NFR-DX-004 |
| Architecture | ARCH-PLAT-CICD, ARCH-PLAT-CLI, ARCH-PLAT-COMPOSE |
| Gating edges | DEP-001 (DN-PLAT-REPO, M0 (S1)) |
| Verification families | BENCH-DX-001, TEST-PLAT-FABCTL |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut; onboarding and reproducibility depend on it.


### 9.WP-TEST-001 — Test strategy, tiers and boundary-mode policy

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M1 · S2 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Asrın |
| Source requirements | NFR-DX-006 |
| Architecture | ARCH-PLAT-CICD |
| Gating edges | none — early unlocker |
| Verification families | TEST-DX-FLAKE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- test tier definition and CI mapping
- boundary-mode policy (REAL / FIXTURE_ALLOWED / STUB_ALLOWED)
- test naming and TestID allocation convention

**Major tasks.**
- define tiers and their runtimes
- document where fixtures are allowed and where they are forbidden
- allocate TestID namespace against 03 verification families
- wire tiers into CI gates

**Cut/fallback.** No cut; a single final "testing" work package is explicitly rejected.


### 9.WP-CICD-003 — Automated migration execution in the deployment path

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-PLAT-CD |
| Supporting reviewer | Asrın |
| Source requirements | NFR-DEP-004 |
| Architecture | ARCH-DATA-PG, ARCH-PLAT-CICD |
| Gating edges | DEP-002 (DN-PLAT-REPO, M0→M1), DEP-005 (DN-PLAT-INTEG, M1 (S2)) |
| Verification families | TEST-DEP-MIGRATION |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- migration stage in CD
- migration status surface
- failure handling and halt semantics

**Major tasks.**
- wire migration runner into deploy
- implement pre/post checks
- test failed-migration handling

**Cut/fallback.** No cut; manual SQL on the host is forbidden.


### 9.WP-GOV-002 — Trace registry, edges and trace linter

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Asrın |
| Source requirements | FR-GOV-004, FR-GOV-005, FR-GOV-009, NFR-GOV-009 |
| Architecture | ARCH-DATA-OBJ, ARCH-PLAT-CICD, ARCH-PLAT-CLI |
| Gating edges | none — early unlocker |
| Verification families | INSP-GOV-ACCEPT, TEST-GOV-TRACELINT |
| Size band / status | L (≈7–12 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut for F0/F1 coverage checks; advanced query surface (`impacted`, `stale`) may follow M5.


### 9.WP-OBJ-001 — Artifact service: ArtifactRef contract and object storage integration

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-RT-OBJ |
| Supporting reviewer | Selman |
| Source requirements | FR-VIS-001, NFR-DATA-001 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-VIS-ARTIFACT, ARCH-VIS-INFER |
| Gating edges | DEP-009 (DN-PLAT-INTEG, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, E2E-01, TEST-DATA-CHECKSUM, TEST-VIS-PIPELINE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut; local files may unblock development only (05 DEP-GAP-17).


### 9.WP-PLAT-003 — Runtime service bring-up on the shared host

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-PLAT-INTEG |
| Supporting reviewer | Batu |
| Source requirements | FR-PLAT-001, NFR-DEP-001 |
| Architecture | ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE |
| Gating edges | DEP-004 (DN-PLAT-COMPOSE, M0 (S1)) |
| Verification families | AV-SCEN-12, BENCH-E2E-001, E2E-01, TEST-DEP-PLATFORM, TEST-PLAT-COMPOSE |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- per-service configuration and health checks
- dependency-ordered startup (02 Sequence I)
- runtime readiness checklist per E2E-01 gate

**Major tasks.**
- provision each runtime with persistent volumes and limits
- configure Keycloak realm/clients and Temporal namespaces
- verify startup order avoids deadlocks
- stage readiness per 05 need-by dates (S4/S5)

**Cut/fallback.** No cut; Valkey is optional (F3) and never correctness-bearing.


### 9.WP-TEST-007 — Architecture rules and trace validation in CI

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M2 · S3–S4 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Asrın |
| Source requirements | FR-EVT-007, FR-GOV-005 |
| Architecture | ARCH-CORE-DB, ARCH-CTR-API, ARCH-PLAT-CICD |
| Gating edges | none — early unlocker |
| Verification families | TEST-ARCH-BOUNDARY, TEST-GOV-TRACELINT, TEST-SEC-SVCID |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- architecture rule checks
- trace linter integration
- violation reporting

**Major tasks.**
- wire boundary and trace checks as required CI gates
- define exception process
- report violations with requirement context

**Cut/fallback.** No cut.


### 9.WP-HITL-004 — Identity-bound approvals

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-RT-IDP |
| Supporting reviewer | Asrın |
| Source requirements | FR-HITL-007, NFR-SEC-005, NFR-PERF-012 |
| Architecture | ARCH-EDGE-AUTH, ARCH-EDGE-BFF, ARCH-HITL-APPROVAL, ARCH-SEC-IDP |
| Gating edges | DEP-010 (DN-PLAT-INTEG, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, BENCH-PERF-WF, E2E-01, TEST-HITL-RECORD, TEST-SEC-AUTHN |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- Keycloak-backed session propagation into approvals
- authorization check for approver role
- approval persistence latency measurement

**Major tasks.**
- wire OIDC session to BFF and approval service
- implement approver authorization
- measure submission → durable record latency

**Cut/fallback.** No cut; real HITL requires the identity runtime (05 DEP-GAP-04 timing).


### 9.WP-OBS-002 — Distributed trace propagation across the closed loop

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-RT-OBS |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-007, NFR-OBS-003, NFR-OBS-005 |
| Architecture | ARCH-OBS-TELEMETRY, ARCH-OBS-TRACE |
| Gating edges | DEP-011 (DN-PLAT-INTEG, M1 (S2)), DEP-109 (DN-PLAT-CD, M3 (S6)) |
| Verification families | AV-SCEN-01, BENCH-E2E-001, DEMO-GS01-001, TEST-DATA-REFINTEGRITY, TEST-OBS-TRACEPROP |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- context propagation adapters
- correlation chain verification test
- trace-completeness check for acceptance runs

**Major tasks.**
- propagate trace context through async boundaries
- verify GS-01 chain is inspectable end to end
- assert required identity fields on formal-evidence telemetry

**Cut/fallback.** No cut; M3 requires distributed traceability (05 §7).


### 9.WP-SEC-001 — Keycloak realm, clients and interactive authentication

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M3 · S5–S6 |
| Readiness node | DN-RT-IDP |
| Supporting reviewer | Asrın |
| Source requirements | FR-SEC-001, NFR-SEC-003 |
| Architecture | ARCH-EDGE-AUTH, ARCH-EDGE-BFF, ARCH-SEC-AUTHZ, ARCH-SEC-IDP |
| Gating edges | DEP-010 (DN-PLAT-INTEG, E2E-01 readiness (end S4)) |
| Verification families | AV-SCEN-01, E2E-01, TEST-SEC-AUTHN, TEST-SEC-TLS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- realm/client configuration as code
- OIDC integration in BFF/UI
- TLS on browser ingress for formal environments

**Major tasks.**
- configure realm, clients, roles and users
- implement login/session handling
- enable TLS termination for INTEGRATION/EVALUATION/DEMO
- verify real login before E2E-01

**Cut/fallback.** No cut; E2E-01 requires actual login (05 DEP-GAP-04).


### 9.WP-OBS-003 — Health, readiness and degradation states

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-RT-OBS |
| Supporting reviewer | Batu |
| Source requirements | NFR-OBS-004, NFR-REL-009 |
| Architecture | ARCH-OBS-HEALTH, ARCH-OBS-STORE |
| Gating edges | DEP-011 (DN-PLAT-INTEG, M1 (S2)), DEP-109 (DN-PLAT-CD, M3 (S6)) |
| Verification families | RES-DEPFAIL-001, RES-PROCESS-001, TEST-OBS-HEALTH |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- health/readiness endpoints per deployable
- capability-level health model
- failure-detection latency measurement

**Major tasks.**
- define capability health semantics per service
- implement endpoints and aggregation
- measure detection latency under injected failures

**Cut/fallback.** No cut; resilience evidence depends on observable degradation.


### 9.WP-OBS-004 — Audit store separation from telemetry

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M4 · S7–S8 |
| Readiness node | DN-RT-OBS |
| Supporting reviewer | Asrın |
| Source requirements | FR-SEC-007, NFR-OBS-007 |
| Architecture | ARCH-OBS-AUDIT, ARCH-OBS-STORE, ARCH-SEC-AUTHZ |
| Gating edges | DEP-011 (DN-PLAT-INTEG, M1 (S2)), DEP-109 (DN-PLAT-CD, M3 (S6)) |
| Verification families | TEST-OBS-AUDITSEP, TEST-SEC-AUDIT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- audit store and schema
- separation test (telemetry rotation does not erase audit)
- audit query surface

**Major tasks.**
- define audit record model and retention
- implement write path from protected actions
- test rotation/purge independence

**Cut/fallback.** No cut (H0).


### 9.WP-SEC-002 — Service identities and least-privilege credentials

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M4 · S7–S8 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Asrın |
| Source requirements | FR-SEC-002, NFR-SEC-007, NFR-SEC-008 |
| Architecture | ARCH-PLAT-COMPOSE, ARCH-SEC-AUTHZ, ARCH-SEC-IDP, ARCH-SEC-SECRET, ARCH-SEC-SUPPLYCHAIN |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | TEST-AUTH-NEG, TEST-SEC-CONTAINER, TEST-SEC-SVCID |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- service identity matrix (DB roles, broker accounts, client credentials)
- container runtime posture (non-root, non-privileged)
- anonymous-mutation negative tests

**Major tasks.**
- define identity per deployable and data plane
- implement credential issuance and rotation approach
- verify container posture and exceptions
- test anonymous and cross-service access denial

**Cut/fallback.** No cut (H0 family).


### 9.WP-SEC-004 — AI-reachable capability surface restriction

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M4 · S7–S8 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Asrın |
| Source requirements | FR-SEC-004, FR-SEC-005 |
| Architecture | ARCH-AI-TOOLS, ARCH-SEC-AUTHZ |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | TEST-AUTH-NEG, TEST-SEC-AISURFACE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- capability inventory for the AI service
- static/dynamic checks
- negative tests

**Major tasks.**
- inventory tools and libraries reachable by the AI identity
- implement checks that fail on shell/SQL capability introduction
- document accepted exceptions (none expected)

**Cut/fallback.** No cut (H0; Item 68 X-289 forbids arbitrary shell-executing agents).


### 9.WP-SEC-005 — Secret sourcing and hygiene

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M4 · S7–S8 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Asrın |
| Source requirements | FR-SEC-006, NFR-SEC-001 |
| Architecture | ARCH-SEC-SECRET, ARCH-SEC-SUPPLYCHAIN |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | INSP-DEP-HOST, TEST-SEC-SECRETS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- runtime secret injection mechanism
- secret scanning of history, images and manifests
- rotation procedure

**Major tasks.**
- select non-Git secret sourcing for the Integration host
- implement injection in Compose/CD
- scan repository history and images
- document rotation and incident handling

**Cut/fallback.** No cut (H0: zero known live secrets in the final release).


### 9.WP-SEC-007 — Oracle access denial at runtime

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M4 · S7–S8 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Batu |
| Source requirements | FR-SEC-010 |
| Architecture | ARCH-SEC-AUTHZ, ARCH-SIM-ORACLE, ARCH-WORLD-EVALZONE |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | AV-SCEN-11, BENCH-RQ3-001, TEST-SEC-ORACLE-NEG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- credential/network separation for the evaluation zone
- runtime denial tests (AV-SCEN-11)
- evidence of denial in formal runs

**Major tasks.**
- implement separation mechanism (identity and/or network)
- test denial from each operational service identity
- record results as part of benchmark evidence

**Cut/fallback.** No cut (H0 research-validity gate).


### 9.WP-UI-009 — System health and environment diagnostics view

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M4 · S7–S8 |
| Readiness node | DN-UI-SHELL |
| Supporting reviewer | Asrın |
| Source requirements | FR-UI-009 |
| Architecture | ARCH-EDGE-WEB, ARCH-OBS-HEALTH, ARCH-PLAT-RELEASE |
| Gating edges | DEP-105 (DN-UI-BFFCON, S1–S2), DEP-106 (DN-TWIN-SKELETON, M1 (S2)) |
| Verification families | DEMO-GS01-001, TEST-UI-DIAG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- diagnostics panel
- release/environment/world identity display
- capability health presentation

**Major tasks.**
- surface ReleaseManifest/EnvironmentManifest through BFF
- render per-capability health states
- link to diagnostic bundle generation

**Cut/fallback.** No cut; demo and debugging integrity depend on it.


### 9.WP-CICD-004 — Supply chain: pinning, scanning and SBOM

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M5 · S9–S10 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Asrın |
| Source requirements | NFR-SEC-002, NFR-REP-005, NFR-REP-006 |
| Architecture | ARCH-CTR-VERSIONING, ARCH-PLAT-CICD, ARCH-SEC-SUPPLYCHAIN |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | TEST-REP-CODEGEN, TEST-REP-LOCKS, TEST-SEC-SUPPLYCHAIN |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut (H0: no known unmitigated Critical vulnerabilities in the final release).


### 9.WP-CICD-005 — Release rollback capability

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M5 · S9–S10 |
| Readiness node | DN-PLAT-CD |
| Supporting reviewer | Asrın |
| Source requirements | NFR-REC-005 |
| Architecture | ARCH-PLAT-CICD, ARCH-PLAT-RELEASE |
| Gating edges | DEP-002 (DN-PLAT-REPO, M0→M1), DEP-005 (DN-PLAT-INTEG, M1 (S2)) |
| Verification families | RESTORE-ROLLBACK-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- rollback procedure and tooling
- compatibility rules for migrations
- rollback drill record

**Major tasks.**
- define rollback-safe migration policy
- implement rollback command path
- drill rollback on INTEGRATION and measure duration

**Cut/fallback.** A1 timing target; rollback may be impossible for irreversible migrations — that constraint is documented, not hidden.


### 9.WP-CICD-006 — CI isolation for untrusted contributions

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M5 · S9–S10 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Asrın |
| Source requirements | NFR-SEC-011 |
| Architecture | ARCH-PLAT-CICD, ARCH-SEC-SUPPLYCHAIN |
| Gating edges | none — early unlocker |
| Verification families | TEST-SEC-CIISOLATION |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- workflow permission model
- secret scoping rules
- negative test for fork PR

**Major tasks.**
- separate trusted and untrusted workflow paths
- scope tokens to least privilege
- verify no secret exposure on fork PRs

**Cut/fallback.** No cut (H0).


### 9.WP-DR-001 — Backup automation and integrity verification

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M5 · S9–S10 |
| Readiness node | DN-PLAT-BACKUP |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-008, NFR-REC-001, NFR-REC-006, NFR-REC-010 |
| Architecture | ARCH-DATA-OBJ, ARCH-DATA-PG, ARCH-PLAT-BACKUP |
| Gating edges | DEP-111 (DN-SEC-BASE, M5 (S10)) |
| Verification families | INSP-REC-BACKUP, RESTORE-HOST-001, RESTORE-PG-001, TEST-DATA-CHECKSUM |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut (H0 family).


### 9.WP-DR-003 — Derived-state rebuild paths

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-PLAT-BACKUP |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-009, NFR-REC-008, NFR-REC-009 |
| Architecture | ARCH-AI-RAG, ARCH-DATA-VECTOR, ARCH-PLAT-BACKUP, ARCH-TWIN-REBUILD |
| Gating edges | DEP-111 (DN-SEC-BASE, M5 (S10)) |
| Verification families | AV-SCEN-08, RES-IDXREBUILD-001, RES-TWINREBUILD-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- RecoveryDependencyGraph
- Twin rebuild drill (AV-SCEN-08)
- index rebuild drill

**Major tasks.**
- document which stores are canonical vs derived
- implement rebuild orchestration
- measure rebuild durations at benchmark scale

**Cut/fallback.** No cut.


### 9.WP-EVT-004 — Replay, poison message and DLQ operations

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-EVT-SPINE |
| Supporting reviewer | Asrın |
| Source requirements | FR-EVT-009, FR-EVT-010 |
| Architecture | ARCH-EVT-CONSUMER, ARCH-EVT-REPLAY, ARCH-OBS-HEALTH |
| Gating edges | DEP-023 (DN-EVT-CONTRACTS, M1 (S2)), DEP-024 (DN-CORE-OUTBOX, M1 (S2)), DEP-025 (DN-RT-NATS, M1 (S2)) |
| Verification families | RES-BROKER-001, RES-DEPFAIL-001, TEST-EVT-REPLAY-DLQ |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- replay procedure + tooling
- DLQ/quarantine path with alerting
- runbook entry

**Major tasks.**
- define replay guards (world, revision, idempotency)
- implement quarantine and operator visibility
- drill replay on INTEGRATION with verification of no duplicate effects

**Cut/fallback.** No cut; ties to resilience evidence (RES-BROKER-001).


### 9.WP-GOV-003 — Coverage reports and release acceptance record generation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-PLAT-RUNNER |
| Supporting reviewer | Asrın |
| Source requirements | FR-GOV-006, FR-GOV-010, NFR-GOV-004, NFR-GOV-005, NFR-GOV-006, NFR-GOV-010 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-PLAT-CICD, ARCH-PLAT-RELEASE |
| Gating edges | DEP-114 (DN-PLAT-FAILVAL, M5 (S10)), DEP-115 (DN-PLAT-CD, M5 (S10)) |
| Verification families | INSP-GOV-ACCEPT, INSP-GOV-NFR, TEST-DATA-REFINTEGRITY, TEST-GOV-TRACELINT |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- AcceptanceCoverageReport generator
- ReleaseAcceptanceRecord generator
- evidence applicability resolver (Release/Env/HW/Workload binding)

**Major tasks.**
- define evidence binding rules per NFR class
- implement VERIFIED derivation only from CURRENT applicable evidence
- implement composite-score prohibition check
- dry-run report against empty evidence set to prove the pipeline

**Cut/fallback.** No cut: M8 acceptance depends on it. May start as read-only report before full automation.


### 9.WP-HITL-007 — Break-glass path with mandatory audit

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-HITL-APPROVAL |
| Supporting reviewer | Asrın |
| Source requirements | FR-HITL-010, NFR-SEC-012 |
| Architecture | ARCH-OBS-AUDIT, ARCH-SEC-BREAKGLASS |
| Gating edges | DEP-090 (DN-RT-IDP, E2E-01 readiness (end S4)), DEP-091 (DN-HITL-POLICY, E2E-01 (end S5)), DEP-092 (DN-SCH-PLANCON, E2E-01 readiness (end S4)), DEP-093 (DN-UI-APPROVAL, E2E-01 (end S5)) |
| Verification families | TEST-SEC-AUDIT, TEST-SEC-BREAKGLASS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- break-glass procedure and flag
- high-risk audit record emission
- drill test

**Major tasks.**
- define what break-glass may and may not do
- implement flagging and alerting
- drill on INTEGRATION and verify audit completeness

**Cut/fallback.** No cut; if break-glass is enabled it must be auditable — hard invariants remain non-bypassable.


### 9.WP-OBJ-002 — Artifact lifecycle, retention and quota policy

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-RT-OBJ |
| Supporting reviewer | Batu |
| Source requirements | NFR-RES-006, NFR-OBS-009 |
| Architecture | ARCH-DATA-CACHE, ARCH-DATA-OBJ, ARCH-OBS-STORE |
| Gating edges | DEP-009 (DN-PLAT-INTEG, E2E-01 readiness (end S4)) |
| Verification families | INSP-OBS-RETENTION, INSP-RES-RETENTION |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- retention/quota policy per artifact class
- cleanup automation
- storage headroom check used by benchmark preflight

**Major tasks.**
- classify artifact families and lifetimes
- implement retention enforcement
- expose storage usage metrics

**Cut/fallback.** No cut; benchmark preflight (NFR-RES-004) depends on measurable headroom.


### 9.WP-OBS-005 — Redaction and diagnostic bundles

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M5 · S9–S10 |
| Readiness node | DN-RT-OBS |
| Supporting reviewer | Asrın |
| Source requirements | NFR-OBS-006, NFR-DX-008 |
| Architecture | ARCH-OBS-TELEMETRY, ARCH-PLAT-CLI, ARCH-SEC-SECRET |
| Gating edges | DEP-011 (DN-PLAT-INTEG, M1 (S2)), DEP-109 (DN-PLAT-CD, M3 (S6)) |
| Verification families | BENCH-DX-001, TEST-OBS-REDACTION |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- redaction rules
- secret scanning over logs and bundles
- bundle generation timing

**Major tasks.**
- implement redaction at emission and bundle assembly
- scan logs/bundles/evidence in CI and before sealing
- measure bundle generation duration

**Cut/fallback.** No cut (H0).


### 9.WP-PERF-001 — Benchmark definitions, workload profiles and measurement protocol

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-PLAT-RUNNER |
| Supporting reviewer | Asrın |
| Source requirements | NFR-GOV-004, NFR-GOV-005, NFR-GOV-006 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-PLAT-RELEASE |
| Gating edges | DEP-114 (DN-PLAT-FAILVAL, M5 (S10)), DEP-115 (DN-PLAT-CD, M5 (S10)) |
| Verification families | INSP-GOV-NFR, TEST-DATA-REFINTEGRITY |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

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

**Cut/fallback.** No cut; without this, NFR results are unusable (03 GAP-RTM-004).


### 9.WP-PLAT-004 — Resource profiles and footprint control

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M5 · S9–S10 |
| Readiness node | DN-PLAT-INTEG |
| Supporting reviewer | Asrın |
| Source requirements | NFR-RES-001, NFR-RES-002, NFR-RES-003, NFR-RES-008, NFR-CAP-009 |
| Architecture | ARCH-EDGE-BFF, ARCH-PLAT-COMPOSE, ARCH-SEC-IDP |
| Gating edges | DEP-004 (DN-PLAT-COMPOSE, M0 (S1)) |
| Verification families | BENCH-CAP-ENV, BENCH-RES-FOOTPRINT, RES-SOAK-001 |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- per-container resource limits (ResourceProfiles)
- cgroup-based measurement harness
- concurrency validation for interactive sessions

**Major tasks.**
- assign limits per service class
- implement memory/CPU sampling over steady windows
- run soak measurement and record peaks/OOM counts
- verify ≥8 concurrent authenticated sessions

**Cut/fallback.** A1 memory envelope; CPU characterization is C3. Exceeding the envelope is a finding, not a silent limit raise.


### 9.WP-PLAT-005 — Environment, release and world manifests

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-ART-RELEASE |
| Supporting reviewer | Asrın |
| Source requirements | FR-PLAT-005, FR-PLAT-010, NFR-REP-003, NFR-REP-007 |
| Architecture | ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE |
| Gating edges | DEP-116 (DN-PLAT-RUNNER, M6 (S11)) |
| Verification families | BENCH-FBC-001, DEMO-GS01-001, INSP-DEP-HOST, INSP-GOV-ACCEPT, REPRO-CLEANHOST-001, TEST-EVAL-RUNNER, TEST-PLAT-CD, TEST-REP-LOCKS |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- EnvironmentManifest / ReleaseManifest formats
- HardwareProfile records
- manifest binding in runner and demo tooling

**Major tasks.**
- define manifest fields and generation points
- emit manifests from CD and runner
- record hardware profiles for evaluation, CPU baseline and Vision hosts (03 GAP-RTM-021)
- verify immutable artifact identities

**Cut/fallback.** No cut; every quantitative claim depends on this binding.


### 9.WP-RES-001 — Experiment runner and run manifest binding

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M5 · S9–S10 |
| Readiness node | DN-PLAT-RUNNER |
| Supporting reviewer | Asrın |
| Source requirements | FR-EVAL-001, FR-PLAT-010 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE |
| Gating edges | DEP-114 (DN-PLAT-FAILVAL, M5 (S10)), DEP-115 (DN-PLAT-CD, M5 (S10)) |
| Verification families | BENCH-FBC-001, DEMO-GS01-001, INSP-GOV-ACCEPT, REPRO-NONOWNER-001, TEST-EVAL-RUNNER |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- experiment runner CLI/service
- ExperimentDefinition format
- run manifest emission

**Major tasks.**
- define experiment definition schema
- implement execution with identity capture
- implement non-owner reproducible invocation
- dry-run all lanes before M6

**Cut/fallback.** No cut (R1). Architecture anchor pending (03 GAP-RTM-002).


### 9.WP-SEC-006 — Test-auth prohibition in formal environments

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M5 · S9–S10 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Asrın |
| Source requirements | FR-SEC-008, NFR-SEC-006 |
| Architecture | ARCH-PLAT-RELEASE, ARCH-SEC-IDP |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | DEMO-GS01-001, E2E-01, TEST-SEC-TESTAUTH-NEG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- environment-mode enforcement
- startup refusal in formal profiles
- usage counter in run evidence

**Major tasks.**
- define where test-auth is permitted (DEV/CI only)
- implement refusal on formal profiles
- record zero-usage assertion in run evidence

**Cut/fallback.** No cut (H0).


### 9.WP-SEC-008 — Security negative suite and external egress audit

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M5 · S9–S10 |
| Readiness node | DN-SEC-BASE |
| Supporting reviewer | Asrın |
| Source requirements | NFR-SEC-004, NFR-SEC-009, NFR-SEC-010 |
| Architecture | ARCH-AI-PROVIDER, ARCH-AUTO-VERIFY, ARCH-CORE-CMD, ARCH-HITL-APPROVAL, ARCH-HITL-POLICY, ARCH-OBS-AUDIT, ARCH-SEC-AUTHZ, ARCH-WORLD-EVALZONE |
| Gating edges | DEP-016 (DN-RT-IDP, M4 (S8)), DEP-017 (DN-PLAT-CD, M4 (S8)) |
| Verification families | AV-SCEN-01, AV-SCEN-04, AV-SCEN-11, BENCH-RQ3-001, TEST-AUTH-NEG, TEST-SEC-AUDIT, TEST-SEC-AUTHZ-NEG, TEST-SEC-EGRESS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- negative suite covering authority, identity, injection and replay
- external LLM payload audit
- audit coverage verification

**Major tasks.**
- assemble suite from HITL/AI/RAG/Core negative cases
- implement egress payload inspection for secrets/oracle/rights-prohibited data
- run before each formal campaign

**Cut/fallback.** No cut (H0 family; feeds RQ-3 adversarial share).


### 9.WP-TEST-004 — Integration scenarios AV-SCEN-05…08

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M5 · S9–S10 |
| Readiness node | DN-PLAT-FAILVAL |
| Supporting reviewer | Batu |
| Source requirements | FR-EVT-005, FR-AUTO-006, FR-TWIN-006, NFR-REL-006 |
| Architecture | ARCH-AUTO-IDEMPOTENCY, ARCH-AUTO-WORKFLOW, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-PLAT-COMPOSE, ARCH-TWIN-REBUILD |
| Gating edges | DEP-110 (DN-RT-OBS, M5 (S10)), DEP-113 (DN-PLAT-BACKUP, M5 (S10)) |
| Verification families | AV-SCEN-05, AV-SCEN-06, AV-SCEN-07, AV-SCEN-08, RES-BROKER-001, RES-DUP-001, RES-TWINREBUILD-001, RES-WORKER-001, TEST-AUTO-RESTART-001, TEST-EVT-CONSUMER-IDEMP, TEST-TWIN-PROJECTION |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- scenario drivers for AV-SCEN-05…08
- fault injection tooling
- execution reports with correctness counters

**Major tasks.**
- implement duplicate/out-of-order delivery injection
- implement worker crash/restart drill
- implement 5-minute broker interruption drill
- implement Twin projection loss and rebuild drill

**Cut/fallback.** No cut; reliability evidence at M5/M7 depends on these.

**Integration checkpoint.** AV-SCEN-05…08


### 9.WP-DOC-001 — Engineering documentation set

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 · M6 · S11 |
| Readiness node | DN-PLAT-TOOLING |
| Supporting reviewer | Asrın |
| Source requirements | NFR-DX-007 |
| Architecture | ARCH-PLAT-CLI, ARCH-PLAT-RELEASE |
| Gating edges | DEP-001 (DN-PLAT-REPO, M0 (S1)) |
| Verification families | TEST-DX-DOCS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- architecture overview and service docs
- runbooks (deploy, restore, replay, incident)
- quickstart and reproduction guides

**Major tasks.**
- write docs alongside each capability WP
- validate documented commands against the release
- keep ownership per document

**Cut/fallback.** No cut; a single final documentation task is explicitly rejected.


### 9.WP-DR-002 — Restore drills: database and full host

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M6 · S11 |
| Readiness node | DN-PLAT-BACKUP |
| Supporting reviewer | Asrın |
| Source requirements | NFR-REC-003, NFR-REC-004, NFR-REC-007 |
| Architecture | ARCH-DATA-PG, ARCH-PLAT-BACKUP, ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE |
| Gating edges | DEP-111 (DN-SEC-BASE, M5 (S10)) |
| Verification families | RESTORE-HOST-001, RESTORE-PG-001 |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- PostgreSQL restore drill (RESTORE-PG-001)
- full-host reconstruction drill (RESTORE-HOST-001)
- drill evidence records

**Major tasks.**
- script restore from accepted backups
- execute application-level smoke validation after restore
- execute host reconstruction from Git + manifests + registry + backups
- record durations against bounds

**Cut/fallback.** No cut; at least one full-host drill must PASS before M8.


### 9.WP-PERF-004 — Resilience drill execution

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M6 · S11 |
| Readiness node | DN-PLAT-FAILVAL |
| Supporting reviewer | Batu |
| Source requirements | NFR-REL-003, NFR-REL-004, NFR-REL-005, NFR-REL-006, NFR-REL-008, NFR-REL-009 |
| Architecture | ARCH-AUTO-WORKFLOW, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-OBS-HEALTH, ARCH-OBS-TELEMETRY, ARCH-PLAT-COMPOSE |
| Gating edges | DEP-110 (DN-RT-OBS, M5 (S10)), DEP-113 (DN-PLAT-BACKUP, M5 (S10)) |
| Verification families | AV-SCEN-06, AV-SCEN-07, AV-SCEN-12, BENCH-CAP-EVT, RES-BROKER-001, RES-DEPFAIL-001, RES-PROCESS-001, RES-REBOOT-001, RES-SOAK-001, RES-WORKER-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- drill scripts (process crash, worker crash, broker interruption, reboot, dependency loss)
- recovery timing measurement
- drill evidence records

**Major tasks.**
- implement injection and recovery measurement
- execute each drill on INTEGRATION
- record recovery times and any committed-effect loss (must be zero)

**Cut/fallback.** No cut; reliability claims require executed drills, not design arguments.

**Integration checkpoint.** AV-SCEN-06, AV-SCEN-07, AV-SCEN-12


### 9.WP-PLAT-007 — Benchmark and demo preflight tooling

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M6 · S11 |
| Readiness node | DN-PLAT-RUNNER |
| Supporting reviewer | Batu |
| Source requirements | NFR-RES-004, NFR-RES-005 |
| Architecture | ARCH-PLAT-CICD, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE |
| Gating edges | DEP-114 (DN-PLAT-FAILVAL, M5 (S10)), DEP-115 (DN-PLAT-CD, M5 (S10)) |
| Verification families | INSP-DEP-HOST, TEST-RES-PREFLIGHT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- preflight check implementation
- undeclared-workload detection
- preflight record attached to runs

**Major tasks.**
- define preflight checks and thresholds
- implement host-state inspection
- block run start on failure and record the reason

**Cut/fallback.** No cut; a benchmark started on a contended host produces unusable evidence.


### 9.WP-RES-003 — Benchmark run registry and disposition accounting

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M6 · S11 |
| Readiness node | DN-PLAT-RUNNER |
| Supporting reviewer | Asrın |
| Source requirements | FR-EVAL-003, FR-EVAL-004, FR-EVAL-005, NFR-DATA-003, NFR-DATA-007 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-PG |
| Gating edges | DEP-114 (DN-PLAT-FAILVAL, M5 (S10)), DEP-115 (DN-PLAT-CD, M5 (S10)) |
| Verification families | BENCH-FBC-001, TEST-DATA-ACCOUNTING, TEST-DATA-REFINTEGRITY, TEST-EVAL-RUNRECORD |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- BenchmarkRunRecord store
- RunDispositionRegister
- planned-vs-executed reconciliation report

**Major tasks.**
- define record fields and append-only semantics
- implement RetryOf/disposition provenance
- implement reconciliation against planned experimental units

**Cut/fallback.** No cut; silent disappearance of runs is a hard-gate failure.


### 9.WP-TEST-008 — Flake control and release-gate hygiene

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (S2) · M6 · S11 |
| Readiness node | DN-PLAT-REPO |
| Supporting reviewer | Asrın |
| Source requirements | NFR-DX-006 |
| Architecture | ARCH-PLAT-CICD |
| Gating edges | none — early unlocker |
| Verification families | TEST-DX-FLAKE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- flaky-test registry
- quarantine policy with expiry
- gate policy prohibiting retry-until-green

**Major tasks.**
- implement registry and reporting
- define quarantine entry/exit rules
- audit gates before M6

**Cut/fallback.** No cut for gate integrity; the timing target itself is S2.


### 9.WP-BENCH-001 — Campaign manifest, preflight and lane orchestration

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M7 · S12 |
| Readiness node | DN-RES-BENCH |
| Supporting reviewer | Asrın |
| Source requirements | FR-EVAL-001, FR-EVAL-003 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-PG, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE |
| Gating edges | DEP-120 (DN-PLAT-CLEANREPRO, M7 (S12)), DEP-141 (DN-FRZ-RELEASE, M7 (S12)), DEP-142 (DN-ART-HWPROF, M7 (S12)) |
| Verification families | BENCH-FBC-001, REPRO-NONOWNER-001, TEST-EVAL-RUNNER, TEST-EVAL-RUNRECORD |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- BenchmarkCampaignManifest
- lane orchestration scripts (ENG-A…I, RQ lanes)
- preflight gate integration

**Major tasks.**
- define campaign structure and lane order
- implement orchestration with run registry integration
- enforce preflight before each lane

**Cut/fallback.** No cut (R1).


### 9.WP-BENCH-003 — Engineering lanes execution (ENG-A…I)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M7 · S12 |
| Readiness node | DN-RES-BENCH |
| Supporting reviewer | Asrın |
| Source requirements | NFR-REL-001, NFR-SEC-004, NFR-REC-007, NFR-REP-004 |
| Architecture | ARCH-AUTO-IDEMPOTENCY, ARCH-CORE-CMD, ARCH-EVT-CONSUMER, ARCH-HITL-POLICY, ARCH-PLAT-BACKUP, ARCH-PLAT-CLI, ARCH-PLAT-RELEASE, ARCH-SEC-AUTHZ |
| Gating edges | DEP-120 (DN-PLAT-CLEANREPRO, M7 (S12)), DEP-141 (DN-FRZ-RELEASE, M7 (S12)), DEP-142 (DN-ART-HWPROF, M7 (S12)) |
| Verification families | AV-SCEN-04, AV-SCEN-05, AV-SCEN-06, BENCH-RQ3-001, REPRO-NONOWNER-001, RES-DUP-001, RESTORE-HOST-001, TEST-AUTH-NEG, TEST-AUTO-RESTART-001, TEST-SEC-AUTHZ-NEG |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- lane execution scripts
- evidence capture per lane
- lane completion report

**Major tasks.**
- map each lane to its verification assets
- execute in campaign order
- record dispositions including MISS/FAIL

**Cut/fallback.** No cut (R1).


### 9.WP-DR-004 — Evidence protection and off-host preservation

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M7 · S12 |
| Readiness node | DN-PLAT-BACKUP |
| Supporting reviewer | Asrın |
| Source requirements | FR-EVAL-008, NFR-REC-002 |
| Architecture | ARCH-DATA-OBJ, ARCH-PLAT-BACKUP |
| Gating edges | DEP-111 (DN-SEC-BASE, M5 (S10)) |
| Verification families | INSP-REC-BACKUP, RESTORE-EVID-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- evidence copy job after EvidenceSeal
- restore test of the evidence bundle
- preservation record for M8

**Major tasks.**
- implement post-seal copy with timing target
- test restore of the bundle
- verify completeness against the run registry

**Cut/fallback.** No cut (H0).


### 9.WP-EVT-006 — Event spine throughput and delivery characterization

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M7 · S12 |
| Readiness node | DN-EVT-SPINE |
| Supporting reviewer | Asrın |
| Source requirements | NFR-PERF-003, NFR-CAP-004 |
| Architecture | ARCH-CORE-OUTBOX, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX |
| Gating edges | DEP-023 (DN-EVT-CONTRACTS, M1 (S2)), DEP-024 (DN-CORE-OUTBOX, M1 (S2)), DEP-025 (DN-RT-NATS, M1 (S2)) |
| Verification families | BENCH-CAP-EVT, BENCH-PERF-CORE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- event pipeline load driver
- measurement definitions
- recorded results with loss/duplicate counts

**Major tasks.**
- build sustained 100 msg/s × 10 min driver
- instrument outbox → broker delay
- verify zero committed-effect loss and zero duplicate protected effects

**Cut/fallback.** A1 class: threshold must PASS or be formally rebaselined.


### 9.WP-OBS-006 — Telemetry retention, quota and instrumentation overhead

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (S2) · M7 · S12 |
| Readiness node | DN-RT-OBS |
| Supporting reviewer | Asrın |
| Source requirements | NFR-OBS-008, NFR-OBS-009 |
| Architecture | ARCH-OBS-STORE, ARCH-OBS-TELEMETRY |
| Gating edges | DEP-011 (DN-PLAT-INTEG, M1 (S2)), DEP-109 (DN-PLAT-CD, M3 (S6)) |
| Verification families | BENCH-OBS-OVERHEAD, INSP-OBS-RETENTION |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- retention/quota configuration
- overhead measurement protocol (instrumented vs diagnostic baseline)
- recorded overhead results

**Major tasks.**
- configure retention windows and quotas
- implement overhead benchmark with instrumentation disabled baseline
- record p95 latency and CPU deltas

**Cut/fallback.** S2: measured overhead above the guideline is disclosed, not suppressed.


### 9.WP-PERF-002 — Latency and throughput measurement execution

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (A1) · M7 · S12 |
| Readiness node | DN-PLAT-RUNNER |
| Supporting reviewer | Asrın |
| Source requirements | NFR-PERF-001, NFR-PERF-002, NFR-PERF-003, NFR-PERF-004, NFR-PERF-005, NFR-PERF-006, NFR-PERF-011, NFR-PERF-012, NFR-PERF-013, NFR-PERF-014 |
| Architecture | ARCH-AI-ORCH, ARCH-AI-RAG, ARCH-AUTO-VERIFY, ARCH-AUTO-WORKFLOW, ARCH-CORE-CMD, ARCH-CORE-DOMAIN, ARCH-CORE-OUTBOX, ARCH-DATA-VECTOR, ARCH-EDGE-BFF, ARCH-EDGE-NOTIFY, ARCH-EDGE-WEB, ARCH-EVT-BROKER, ARCH-EVT-CONSUMER, ARCH-EVT-OUTBOX, ARCH-HITL-APPROVAL, ARCH-SCH-ENGINE, ARCH-TWIN-API, ARCH-TWIN-FRESHNESS, ARCH-TWIN-PROJECTOR, ARCH-VIS-INFER |
| Gating edges | DEP-114 (DN-PLAT-FAILVAL, M5 (S10)), DEP-115 (DN-PLAT-CD, M5 (S10)) |
| Verification families | BENCH-E2E-001, BENCH-PERF-AI, BENCH-PERF-CORE, BENCH-PERF-UI, BENCH-PERF-WF |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- performance lane execution scripts
- recorded distributions per metric
- disposition table (PASS/FAIL/MISS) per NFR

**Major tasks.**
- run each benchmark definition on the evaluation host
- record raw samples and derived percentiles
- attach measurement context to every result
- report failures without post-hoc threshold changes

**Cut/fallback.** A1/S2 mix: A1 thresholds must PASS or be formally rebaselined; S2 misses are recorded with analysis.


### 9.WP-PERF-005 — Soak testing and resource behaviour under sustained load

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (H0) · M7 · S12 |
| Readiness node | DN-PLAT-FAILVAL |
| Supporting reviewer | Asrın |
| Source requirements | NFR-REL-007, NFR-REL-001 |
| Architecture | ARCH-AUTO-IDEMPOTENCY, ARCH-CORE-CMD, ARCH-EVT-CONSUMER, ARCH-OBS-HEALTH, ARCH-PLAT-COMPOSE |
| Gating edges | DEP-110 (DN-RT-OBS, M5 (S10)), DEP-113 (DN-PLAT-BACKUP, M5 (S10)) |
| Verification families | AV-SCEN-05, AV-SCEN-06, RES-DUP-001, RES-SOAK-001, TEST-AUTO-RESTART-001 |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- soak harness and monitoring
- soak report with counters
- memory/queue trend analysis

**Major tasks.**
- configure WP-NORMAL sustained load
- monitor crash loops, corruption, duplicate effects, OOM, queue growth
- record and analyse trends

**Cut/fallback.** No cut (H0).


### 9.WP-RES-005 — Evidence sealing and bundle assembly

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M7 · S12 |
| Readiness node | DN-RES-BENCH |
| Supporting reviewer | Asrın |
| Source requirements | FR-EVAL-007, NFR-DATA-004 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-OBJ |
| Gating edges | DEP-120 (DN-PLAT-CLEANREPRO, M7 (S12)), DEP-141 (DN-FRZ-RELEASE, M7 (S12)), DEP-142 (DN-ART-HWPROF, M7 (S12)) |
| Verification families | BENCH-FBC-001, INSP-EVAL-SEAL, TEST-DATA-REFINTEGRITY |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- EvidenceSeal mechanism
- FinalBenchmarkEvidenceBundle assembly
- completeness and reference-integrity checks

**Major tasks.**
- define bundle contents per lane
- implement sealing with content identity
- verify zero unresolved references before sealing

**Cut/fallback.** No cut (R1).


### 9.WP-BENCH-004 — Reproduction lanes: clean host, non-owner and public

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M8 · S13 |
| Readiness node | DN-PLAT-CLEANREPRO |
| Supporting reviewer | Asrın |
| Source requirements | NFR-REP-003, NFR-REP-004, NFR-REP-008, NFR-DEP-005 |
| Architecture | ARCH-PLAT-CLI, ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE |
| Gating edges | DEP-118 (DN-ART-RELEASE, M6→M7), DEP-119 (DN-ART-HWPROF, M6→M7) |
| Verification families | INSP-DEP-HOST, REPRO-CLEANHOST-001, REPRO-NONOWNER-001, REPRO-OSR3-001 |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- clean-host deployment run
- non-owner reproduction run
- public/sanitized package reproduction (OSR-3)

**Major tasks.**
- execute clean-host deploy from the exact ReleaseManifest
- have a non-owner reproduce a selected final scenario
- execute the public package hero reproduction
- record hidden-dependency findings if any

**Cut/fallback.** No cut (R1/H0 mix: NFR-REP-003 is H0-grade reproducibility evidence).


### 9.WP-BENCH-005 — Evidence bundle finalization and acceptance reporting

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M8 · S13 |
| Readiness node | DN-RES-BENCH |
| Supporting reviewer | Asrın |
| Source requirements | FR-GOV-006, FR-EVAL-007, NFR-DATA-003, NFR-DATA-004 |
| Architecture | ARCH-DATA-LINEAGE, ARCH-DATA-OBJ, ARCH-PLAT-CICD |
| Gating edges | DEP-120 (DN-PLAT-CLEANREPRO, M7 (S12)), DEP-141 (DN-FRZ-RELEASE, M7 (S12)), DEP-142 (DN-ART-HWPROF, M7 (S12)) |
| Verification families | BENCH-FBC-001, INSP-EVAL-SEAL, INSP-GOV-ACCEPT, TEST-DATA-REFINTEGRITY, TEST-GOV-TRACELINT |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- sealed FinalBenchmarkEvidenceBundle
- AcceptanceCoverageReport
- ReleaseAcceptanceRecord

**Major tasks.**
- assemble and seal bundles per lane
- generate coverage and acceptance artifacts from the trace registry
- verify off-host preservation

**Cut/fallback.** No cut.


### 9.WP-DOC-005 — Public release package (v1)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R1 · M8 · S13 |
| Readiness node | DN-PLAT-CLEANREPRO |
| Supporting reviewer | Asrın |
| Source requirements | NFR-REP-008, NFR-SEC-001 |
| Architecture | ARCH-PLAT-RELEASE, ARCH-SEC-SECRET, ARCH-SEC-SUPPLYCHAIN |
| Gating edges | DEP-118 (DN-ART-RELEASE, M6→M7), DEP-119 (DN-ART-HWPROF, M6→M7) |
| Verification families | REPRO-OSR3-001, TEST-SEC-SECRETS |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- public repository structure and licence review
- sanitized artifacts and documentation
- OSR-3 hero reproduction verification

**Major tasks.**
- review code, data and evidence for rights and secrets
- prepare public quickstart and reproduction instructions
- execute clean-clone reproduction

**Cut/fallback.** R1/stretch-adjacent: scope may be reduced to a sanitized subset; reduction is declared, not silent.


### 9.WP-PLAT-006 — Onboarding, executable documentation and diagnostics

| Field | Value |
|---|---|
| Scope / milestone / sprint window | F1 (S2) · M8 · S13 |
| Readiness node | DN-PLAT-TOOLING |
| Supporting reviewer | Asrın |
| Source requirements | NFR-DX-005, NFR-DX-007, NFR-DX-008 |
| Architecture | ARCH-PLAT-CLI, ARCH-PLAT-RELEASE, ARCH-SEC-SECRET |
| Gating edges | DEP-001 (DN-PLAT-REPO, M0 (S1)) |
| Verification families | BENCH-DX-001, INSP-DX-ONBOARD, TEST-DX-DOCS, TEST-OBS-REDACTION |
| Size band / status | M (≈4–7 focused days) · NOT_STARTED |

**Deliverables.**
- quickstart and runbook set
- executable documentation validation
- diagnostic bundle with redaction

**Major tasks.**
- write quickstart/reproduction/runbook docs against the real release
- implement doc command validation in CI
- implement diagnostics bundle generation and secret redaction
- run a non-author onboarding walk-through and record it

**Cut/fallback.** S2 timing targets; the validation itself (NFR-DX-007) is required before M8.


### 9.WP-R2-003 — R2 infrastructure candidates (Neo4j, TimescaleDB, Valkey optimization, GPU/distributed simulator)

| Field | Value |
|---|---|
| Scope / milestone / sprint window | R2 · — · unscheduled |
| Readiness node | DN-RT-VALKEY |
| Supporting reviewer | Batu |
| Source requirements | NFR-PERF-001 |
| Architecture | ARCH-CORE-DOMAIN, ARCH-EDGE-BFF, ARCH-TWIN-API |
| Gating edges | none — early unlocker |
| Verification families | BENCH-PERF-CORE |
| Size band / status | S (≈1–3 focused days) · NOT_STARTED |

**Deliverables.**
- bottleneck analysis
- prototype measurements
- adopt/reject record

**Major tasks.**
- identify measured bottlenecks from performance lanes
- prototype narrowly
- compare against the mandatory baseline cost

**Cut/fallback.** Cut first. Adoption would require a declared dependency change and an ADR; none is assumed.


### 9.SUP Supporting-reviewer packages (49)

Packages owned by others where this role is the named reviewer — review capacity must be planned, not improvised.

| Work package | Title | Owner | Milestone |
|---|---|---|---|
| WP-GOV-001 | Machine-readable requirement catalog and ID lint | Asrın | M0 |
| WP-GOV-004 | Change control and freeze-impact tooling | Asrın | M6 |
| WP-CORE-005 | Domain events and transactional outbox | Asrın | M1 |
| WP-CORE-006 | Core and Twin read/command performance profile | Asrın | M7 |
| WP-CORE-007 | Core database migrations and role separation | Asrın | M1 |
| WP-EVT-002 | Message envelope, correlation and world scoping | Asrın | M1 |
| WP-EVT-005 | Architecture rules as code (boundaries and ownership) | Asrın | M2 |
| WP-TWIN-001 | Twin projection engine | Asrın | M1 |
| WP-TWIN-004 | Twin rebuild and catch-up | Asrın | M5 |
| WP-SIM-002 | Determinism, replay and event-hash equivalence | Batu | M2 |
| WP-SIM-004 | Snapshot, fork and world isolation | Batu | M4 |
| WP-SIM-005 | Oracle isolation and evaluator-only data plane | Batu | M3 |
| WP-SIM-008 | Simulator capacity and scale validation | Batu | M7 |
| WP-VIS-003 | Segmentation and anomaly detection | Selman | M4 |
| WP-VIS-008 | CPU smoke inference path | Selman | M2 |
| WP-VIS-010 | Vision inference performance characterization | Selman | M7 |
| WP-VDATA-004 | ModelPackage governance and MLflow promotion | Selman | M5 |
| WP-ML-005 | Common prediction contract and publication | Asrın | M4 |
| WP-ML-007 | ML evaluation lanes (M1/M2/M3) for the final campaign | Asrın | M6 |
| WP-RAG-001 | Documentary corpus governance and ingestion | Asrın | M4 |
| WP-RAG-002 | Retrieval profiles: sparse, dense and hybrid | Asrın | M4 |
| WP-RAG-004 | Rights filtering and prompt-injection resistance | Asrın | M4 |
| WP-RAG-006 | Index rebuild and recovery | Asrın | M5 |
| WP-RAG-007 | Retrieval ablation lane for RQ-1 | Asrın | M6 |
| WP-AI-001 | Deterministic orchestrator and execution budgets | Asrın | M3 |
| WP-AI-002 | Typed tool registry and authority-tagged tool access | Asrın | M3 |
| WP-AI-003 | Structured evidence-grounded RCA output | Asrın | M3 |
| WP-AI-005 | Provider abstraction, behavior bundle and deterministic baseline | Asrın | M4 |
| WP-AI-006 | AI authority boundary and negative suite | Asrın | M3 |
| WP-AI-007 | RCA path performance characterization | Asrın | M7 |
| WP-SCH-005 | Decision budget, fallback and explicit failure state | Batu | M5 |
| WP-AUTO-001 | Durable workflow bundle and approval wait | Batu | M3 |
| WP-HITL-005 | Approval record, audit trail and protected-action coverage | Asrın | M4 |
| WP-UI-001 | Command Center shell and BFF contract | Asrın | M1 |
| WP-UI-010 | Incident and decision timeline | Asrın | M5 |
| WP-UI-011 | Browser E2E harness and compatibility validation | Asrın | M8 |
| WP-UI-012 | Presenter mode integrity | Asrın | M8 |
| WP-SEC-003 | Backend authorization enforcement | Asrın | M3 |
| WP-TEST-005 | Integration scenarios AV-SCEN-09…12 | Batu | M5 |
| WP-PERF-003 | Capacity and stress execution | Batu | M7 |
| WP-PERF-006 | Scheduler performance frontier measurement | Batu | M7 |
| WP-RES-004 | AnalysisPackage and deterministic result regeneration | Asrın | M6 |
| WP-RES-007 | RQ-1 lane: evidence-grounded RCA evaluation | Asrın | M6 |
| WP-RES-011 | Freeze execution for M6 | Asrın | M6 |
| WP-DOC-002 | ADR backfill and decision index | Asrın | M2 |
| WP-DOC-004 | Demo infrastructure and GS-01 rehearsal | Asrın | M8 |
| WP-DOC-006 | Final red-team review execution | Asrın | M8 |
| WP-R2-001 | R2 retrieval candidates (ColBERT, cross-encoder reranking, alternative embeddings) | Asrın | — |
| WP-X-001 | Out-of-scope boundary maintenance | Asrın | — |

## 10. Sprint-Level Execution Projection

Sprint character follows Item 66 §"Sprint-Level Parallelization"; the packages are this role's. This is a projection for planning conversations, not a commitment schedule — 07 owns milestone planning.

| Sprint | Character (Item 66) | Work packages in flight | Upstream gates due | Commitments owed | Milestone |
|---|---|---|---|---|---|
| S1 | maximum independent foundational work | WP-CICD-001 | 0 | 0 | M0 |
| S2 | first Core/event/Twin/platform convergence | WP-PLAT-001, WP-PLAT-002, WP-CICD-002, WP-OBS-001, WP-TEST-001 | 0 | 3 | M1 |
| S3 | independent depth: Simulator, Vision, Scheduler, AI fixtures | WP-GOV-002, WP-OBJ-001, WP-PLAT-003, WP-CICD-003, WP-TEST-007 | 0 | 0 | M2 |
| S4 | depth continues; E2E-01 contract readiness gate closes | WP-GOV-002, WP-OBJ-001, WP-PLAT-003, WP-CICD-003, WP-TEST-007 | 0 | 2 | M2 |
| S5 | highest integration density; E2E-01 dry run and formal run | WP-HITL-004, WP-OBS-002, WP-SEC-001 | 0 | 3 | M3 |
| S6 | highest integration density; M3 closed-loop alpha | WP-HITL-004, WP-OBS-002, WP-SEC-001 | 0 | 0 | M3 |
| S7 | independent capability depth increases again | WP-UI-009, WP-OBS-003, WP-OBS-004, WP-SEC-002, WP-SEC-004, WP-SEC-005, WP-SEC-007 | 0 | 0 | M4 |
| S8 | depth continues; M4 mandatory feature complete | WP-UI-009, WP-OBS-003, WP-OBS-004, WP-SEC-002, WP-SEC-004, WP-SEC-005, WP-SEC-007 | 0 | 3 | M4 |
| S9 | cross-cutting quality and evaluation dependencies dominate | WP-GOV-003, WP-EVT-004, WP-OBJ-002, WP-HITL-007, WP-PLAT-004, WP-PLAT-005, WP-CICD-004, WP-CICD-005, WP-CICD-006, WP-OBS-005, WP-SEC-006, WP-SEC-008, WP-DR-001, WP-DR-003, WP-TEST-004, WP-PERF-001, WP-RES-001 | 0 | 0 | M5 |
| S10 | quality/evaluation continues; M5 reliability & evaluation ready | WP-GOV-003, WP-EVT-004, WP-OBJ-002, WP-HITL-007, WP-PLAT-004, WP-PLAT-005, WP-CICD-004, WP-CICD-005, WP-CICD-006, WP-OBS-005, WP-SEC-006, WP-SEC-008, WP-DR-001, WP-DR-003, WP-TEST-004, WP-PERF-001, WP-RES-001 | 1 | 1 | M5 |
| S11 | freeze convergence; highest freeze-risk window; M6 | WP-PLAT-007, WP-DR-002, WP-TEST-008, WP-PERF-004, WP-RES-003, WP-DOC-001 | 1 | 0 | M6 |
| S12 | graph effectively immutable, formal execution only; M7 | WP-EVT-006, WP-OBS-006, WP-DR-004, WP-PERF-002, WP-PERF-005, WP-RES-005, WP-BENCH-001, WP-BENCH-003 | 0 | 1 | M7 |
| S13 | evidence, release and documentation convergence; M8 | WP-PLAT-006, WP-BENCH-004, WP-BENCH-005, WP-DOC-005 | 0 | 0 | M8 |

Two windows deserve explicit attention for this role: **S5–S6** (highest integration density — avoid unrelated refactoring) and **S11** (freeze convergence — avoid casual experimental changes).

### 10.1 Interface ledger with each teammate

**Yavuz ↔ Asrın**

| Direction | Count | Edges / packages |
|---|---|---|
| Yavuz receives from Asrın | 2 | DEP-125 (DN-RES-BASELINES, by M5 (S10)), DEP-139 (DN-FRZ-PROTOCOL, by M6 (S11)) |
| Yavuz delivers to Asrın | 9 | DEP-019 (DN-CORE-LIFECYCLE, by M1 (S2)), DEP-025 (DN-EVT-SPINE, by M1 (S2)), DEP-033 (DN-TWIN-SKELETON, by M1 (S2)), DEP-071 (DN-RAG, by M4 (S8)), DEP-075 (DN-ML, by M4/M5), DEP-090 (DN-HITL-APPROVAL, by E2E-01 readiness (end S4)), DEP-108 (DN-UI-APPROVAL, by E2E-01 readiness (end S4)), DEP-127 (DN-RES-CALIB, by M5→M6), DEP-143 (DN-RES-ANALYSIS, by M7 (S12)) |
| shared packages (owner/reviewer) | 84 | WP-GOV-001, WP-GOV-002, WP-GOV-003, WP-GOV-004, WP-CORE-005, WP-CORE-006, WP-CORE-007, WP-EVT-002, WP-EVT-004, WP-EVT-005, WP-EVT-006, WP-TWIN-001, WP-TWIN-004, WP-ML-005, WP-ML-007, WP-RAG-001, WP-RAG-002, WP-RAG-004, WP-RAG-006, WP-RAG-007, WP-AI-001, WP-AI-002, WP-AI-003, WP-AI-005, WP-AI-006, WP-AI-007, WP-HITL-004, WP-HITL-005, WP-HITL-007, WP-UI-001, WP-UI-009, WP-UI-010, WP-UI-011, WP-UI-012, WP-PLAT-001, WP-PLAT-002, WP-PLAT-004, WP-PLAT-005, WP-PLAT-006, WP-CICD-001, WP-CICD-002, WP-CICD-003, WP-CICD-004, WP-CICD-005, WP-CICD-006, WP-OBS-001, WP-OBS-002, WP-OBS-004, WP-OBS-005, WP-OBS-006, WP-SEC-001, WP-SEC-002, WP-SEC-003, WP-SEC-004, WP-SEC-005, WP-SEC-006, WP-SEC-008, WP-DR-001, WP-DR-002, WP-DR-003, WP-DR-004, WP-TEST-001, WP-TEST-007, WP-TEST-008, WP-PERF-001, WP-PERF-002, WP-PERF-005, WP-RES-001, WP-RES-003, WP-RES-004, WP-RES-005, WP-RES-007, WP-RES-011, WP-BENCH-001, WP-BENCH-003, WP-BENCH-004, WP-BENCH-005, WP-DOC-001, WP-DOC-002, WP-DOC-004, WP-DOC-005, WP-DOC-006, WP-R2-001, WP-X-001 |

**Yavuz ↔ Selman**

| Direction | Count | Edges / packages |
|---|---|---|
| Yavuz receives from Selman | 0 | — |
| Yavuz delivers to Selman | 2 | DEP-055 (DN-VIS-MODELS, by M4/M5), DEP-058 (DN-VIS-SERVING, by E2E-01 (end S5)) |
| shared packages (owner/reviewer) | 5 | WP-OBJ-001, WP-VIS-003, WP-VIS-008, WP-VIS-010, WP-VDATA-004 |

**Yavuz ↔ Batu**

| Direction | Count | Edges / packages |
|---|---|---|
| Yavuz receives from Batu | 0 | — |
| Yavuz delivers to Batu | 3 | DEP-045 (DN-SIM-SNAPFORK, by M2 (S4)), DEP-047 (DN-SIM-ORACLE, by E2E-01 (end S5)), DEP-095 (DN-AUTO-DURABLE, by E2E-01 formal run (end S5)) |
| shared packages (owner/reviewer) | 17 | WP-SIM-002, WP-SIM-004, WP-SIM-005, WP-SIM-008, WP-OBJ-002, WP-SCH-005, WP-AUTO-001, WP-PLAT-003, WP-PLAT-007, WP-OBS-003, WP-SEC-007, WP-TEST-004, WP-TEST-005, WP-PERF-003, WP-PERF-004, WP-PERF-006, WP-R2-003 |

## 11. Integration Checkpoints

| Checkpoint | Work packages | What this role must prove |
|---|---|---|
| E2E-01 (end S5, Item 67) | — | contract readiness by end S4 and real-boundary behaviour in the formal run; review obligation before the run (Item 67 #215–#218) |
| AV-SCEN-01…12 (Item 84) | WP-TEST-004, WP-PERF-004 | architecture validation scenarios executed on the Integration environment |
| GS-01 demo (DEMO-GS01-001) | — | the hero path works from a pinned release without presentation shortcuts |
| FBC-01 E2E matrix (BENCH-E2E-001) | — | the role's part of the 4×20 statistical matrix executes unattended |

## 12. Failure and Negative Tests

Negative and failure-path verification owned or co-owned by this role. Happy-path evidence alone can never satisfy an H0 requirement (03 §4.4).

| Verification family | Kind | Scope | Family owner | Minimum environment |
|---|---|---|---|---|
| RES-DUP-001 | DRILL | Duplicate/retry/restart protected-effect suite aggregation (AV-SCEN-05/06 + TEST-AUTO-RESTART-001) | Batu | EVALUATION |
| TEST-ARCH-BOUNDARY | TEST | Architecture-rules-as-code: import boundaries, schema ownership, forbidden cross-service credentials, contract producer uniqueness | Asrın | CI |
| TEST-AUTH-NEG | TEST | Cross-cutting authority negative suite: AI mutation/self-approval/credential/bypass attempts (AUTH-INV family) | Asrın | CI |
| TEST-AUTO-RESTART-001 | TEST | Worker crash / restart-before-command / duplicate delivery / restart-after-effect / restart-before-verification | Batu | CI |
| TEST-EVT-CONSUMER-IDEMP | TEST | At-least-once consumer idempotency with real NATS JetStream (no fake bus, CI-INV-07) | Asrın | CI |
| TEST-EVT-REPLAY-DLQ | TEST | Replay side-effect protection + poison/DLQ discoverability | Yavuz | CI |
| TEST-SEC-AISURFACE | TEST | AI-reachable capability inventory: no shell / no arbitrary SQL surface | Yavuz | CI |
| TEST-SEC-AUTHN | TEST | Keycloak interactive authentication for formal flows; approval ↔ authenticated identity | Yavuz | INTEGRATION |
| TEST-SEC-AUTHZ-NEG | TEST | Backend authorization negative suite (UI visibility ≠ authorization; unknown permission ≠ allow) | Asrın | INTEGRATION |
| TEST-SEC-BREAKGLASS | TEST | Break-glass path distinction, audit emission, no hard-invariant bypass | Yavuz | INTEGRATION |
| TEST-SEC-CIISOLATION | TEST | Untrusted fork/PR jobs receive no privileged credentials and no sensitive runner | Yavuz | CI |
| TEST-SEC-CONTAINER | TEST | Container runtime posture: no privileged mode, non-root with approved exceptions | Yavuz | INTEGRATION |
| TEST-SEC-EGRESS | TEST | External LLM request payload audit: no secrets / Oracle truth / rights-prohibited data | Asrın | EVALUATION |
| TEST-SEC-ORACLE-NEG | TEST | Oracle/evaluator-only data inaccessible to normal service identities (runtime denial) | Yavuz | EVALUATION |
| TEST-SEC-SECRETS | TEST | Secret scanning of Git history, images, manifests; non-Git secret sourcing | Yavuz | CI |
| TEST-SEC-SVCID | TEST | Declared service identities; anonymous mutation rejected; no universal super-credential | Yavuz | INTEGRATION |
| TEST-SEC-TESTAUTH-NEG | TEST | Formal runtime rejects bounded test-auth bypass; run evidence shows 0 uses | Yavuz | EVALUATION |

**Owned H0 (hard-gate) requirements requiring hard/negative evidence (33):** NFR-DATA-001, NFR-DATA-003, NFR-DATA-004, NFR-DATA-007, NFR-DATA-008, NFR-DEP-003, NFR-DEP-005, NFR-DEP-006, NFR-DX-006, NFR-GOV-004, NFR-GOV-005, NFR-GOV-006, NFR-GOV-009, NFR-OBS-005, NFR-OBS-006, NFR-OBS-007, NFR-REC-002, NFR-REC-006, NFR-REC-007, NFR-REC-010, NFR-REP-005, NFR-REP-006, NFR-REP-007, NFR-RES-003, NFR-RES-005, NFR-SEC-001, NFR-SEC-002, NFR-SEC-005, NFR-SEC-006, NFR-SEC-007, NFR-SEC-010, NFR-SEC-011, NFR-SEC-012.

## 13. Research / Evaluation Responsibilities

Yavuz's research contribution is systems-research, not a support role (Item 58 #257): reproducible ExperimentRuns, failure-aware validation, evidence packaging, environment integrity and performance/resilience measurement. Concretely this role owns the experiment runner, the run registry with disposition accounting (including failed and invalid attempts), evidence sealing, the reproduction lanes (clean host, non-owner, public OSR-3) and the measurement discipline that binds every quantitative result to Release/Environment/HardwareProfile/WorkloadProfile. If this work is weak, every other research claim becomes unverifiable regardless of its content.

| R1 work package | Title | Milestone | Evidence lane |
|---|---|---|---|
| WP-RES-001 | Experiment runner and run manifest binding | M5 | BENCH-FBC-001 |
| WP-RES-003 | Benchmark run registry and disposition accounting | M6 | BENCH-FBC-001 |
| WP-RES-005 | Evidence sealing and bundle assembly | M7 | BENCH-FBC-001, INSP-EVAL-SEAL |
| WP-BENCH-001 | Campaign manifest, preflight and lane orchestration | M7 | BENCH-FBC-001 |
| WP-BENCH-003 | Engineering lanes execution (ENG-A…I) | M7 | BENCH-RQ3-001 |
| WP-BENCH-004 | Reproduction lanes: clean host, non-owner and public | M8 | FBC-01 lane |
| WP-BENCH-005 | Evidence bundle finalization and acceptance reporting | M8 | BENCH-FBC-001, INSP-EVAL-SEAL |
| WP-DOC-005 | Public release package (v1) | M8 | FBC-01 lane |

## 14. Documentation and ADR Obligations

Own the platform, environment and runbook documentation (deploy, restore, replay, incident, benchmark execution), the quickstart and reproduction guides, the executable-documentation validation, and the ADRs for Compose/runtime, CI/CD, observability stack, identity and backup design.

## 15. Risks and Bottlenecks

| Risk (Item 69) | Exposure for this role | Mitigation carried in this roadmap |
|---|---|---|
| PLAT-R01 | The 16 GiB host cannot hold the full runtime under benchmark load. | Resource profiles per service, measured steady/peak footprint, preflight isolation, early stress measurement rather than late discovery. |
| PLAT-R06 | Host loss destroys the project. | Backup automation with off-host copies, full-host reconstruction drill before M8, evidence preservation after sealing. |
| PLAT-R08 | Manual host patching makes releases unreproducible. | CD-only deployment with DeploymentRecords and a zero-host-patch audit. |
| TEAM-R04 | Yavuz becomes the support queue and the platform evidence slips. | Research lane execution stays with lane owners; platform work is scheduled as packages with milestones, not as ad hoc requests. |
| DR-R02 | Sealed evidence exists only on the Integration host. | Post-seal off-host copy with a restore test. |
| RES-R15 | Runs cannot be attributed to a release/environment/hardware identity. | Experiment runner binds manifests at run start; runs without binding are invalid by construction. |

## 16. Cross-Review Responsibilities

Yavuz reviews every change that touches runtime, deployment, resource consumption, secrets or evidence capture, and is the required reviewer for anything that would add infrastructure technology (no application team adds infrastructure unilaterally, Item 62 #127). Conversely Yavuz may not alter domain semantics for operational convenience (#128) — platform ownership stops at meaning.

Named reviewer on 49 work packages owned by others (§9.SUP). Cross-review is an Item 63 obligation, not a courtesy: a dependency handshake counts as complete only when both sides have validated contract usability (Item 66 #140).

## 17. Final Benchmark Contribution

| Lane / asset | Kind | Scope | Role's obligation |
|---|---|---|---|
| BENCH-CAP-ENV | BENCH | Interactive session concurrency and isolated-WorldID capacity | execute and record dispositions, including failures |
| BENCH-CAP-EVT | BENCH | Application event pipeline sustained 100 msg/s × 10 min | execute and record dispositions, including failures |
| BENCH-DEP-STARTUP | BENCH | Full Integration profile startup-to-healthy with pre-pulled images | execute and record dispositions, including failures |
| BENCH-DX-001 | BENCH | DX timing suite: doctor, static validation, capability smoke, local profile startup, diagnostic bundle | execute and record dispositions, including failures |
| BENCH-E2E-001 | BENCH | FBC-01 final statistical E2E matrix: 4 frozen scenario definitions × 20 seeds (80 base instances) | execute and record dispositions, including failures |
| BENCH-FBC-001 | BENCH | FBC-01 campaign-level execution: BenchmarkCampaignManifest, preflight, run registry, sealing across all lanes (R1 mechanisms exercised formally) | execute and record dispositions, including failures |
| BENCH-OBS-OVERHEAD | BENCH | Instrumentation overhead vs instrumentation-disabled diagnostic baseline (p95 latency, mean CPU) | execute and record dispositions, including failures |
| BENCH-PERF-AI | BENCH | RAG top-k retrieval latency and RCA path latency decomposition (provider context retained) | execute and record dispositions, including failures |
| BENCH-PERF-CORE | BENCH | Core/Twin read latency, command decision latency, outbox delay, Twin freshness, Core command throughput | execute and record dispositions, including failures |
| BENCH-PERF-UI | BENCH | Command Center state visibility and initial actionable load on accepted LAN/client profile | execute and record dispositions, including failures |
| BENCH-PERF-WF | BENCH | Workflow control-plane overhead, approval persistence, GS-01 system-controlled duration, workflow concurrency | execute and record dispositions, including failures |
| BENCH-RES-FOOTPRINT | BENCH | cgroup memory steady/peak and CPU mean/p95/saturation under WP-NORMAL and stress | execute and record dispositions, including failures |
| BENCH-RQ3-001 | BENCH | RQ-3 governed AI-to-action (150 cases, L0–L4 × 30, ≥40% adversarial) | execute and record dispositions, including failures |
| REPRO-CLEANHOST-001 | DRILL | Clean compatible host deploys exact ReleaseManifest without private developer state | execute and record dispositions, including failures |
| REPRO-NONOWNER-001 | DRILL | Non-owner teammate reproduction of selected final environment/scenario (ENG-G) | execute and record dispositions, including failures |
| REPRO-OSR3-001 | DRILL | v1 public (or sanitized embargoed) package OSR-3 clean-clone hero reproduction | execute and record dispositions, including failures |
| RES-BROKER-001 | DRILL | 5-minute broker interruption under WP-NORMAL → backlog drain, no committed-effect loss (AV-SCEN-07 execution) | execute and record dispositions, including failures |
| RES-DEPFAIL-001 | DRILL | Mandatory dependency loss → DEGRADED/UNAVAILABLE/MANUAL_REQUIRED visibility within bound | execute and record dispositions, including failures |
| RES-DUP-001 | DRILL | Duplicate/retry/restart protected-effect suite aggregation (AV-SCEN-05/06 + TEST-AUTO-RESTART-001) | execute and record dispositions, including failures |
| RES-IDXREBUILD-001 | DRILL | Qdrant/RAG index rebuild from canonical corpus artifacts | execute and record dispositions, including failures |
| RES-PROCESS-001 | DRILL | Stateless team-owned service crash → healthy within bound | execute and record dispositions, including failures |
| RES-REBOOT-001 | DRILL | Host reboot with intact volumes → healthy/known-degraded (AV-SCEN-12 execution) | execute and record dispositions, including failures |
| RES-SOAK-001 | DRILL | 8-hour WP-NORMAL soak: crash loops, corruption, duplication, OOM, queue growth, memory | execute and record dispositions, including failures |
| RES-TWINREBUILD-001 | DRILL | Twin projection loss → deterministic rebuild from retained canonical sources (AV-SCEN-08 execution) | execute and record dispositions, including failures |
| RES-WORKER-001 | DRILL | Workflow-worker crash/restart resumption without duplicate verified effect (AV-SCEN-06 execution) | execute and record dispositions, including failures |
| RESTORE-EVID-001 | DRILL | Off-host copy + restore test of FinalBenchmarkEvidenceBundle | execute and record dispositions, including failures |
| RESTORE-HOST-001 | DRILL | Full-host-loss reconstruction from Git + manifests + registry + off-host backups | execute and record dispositions, including failures |
| RESTORE-PG-001 | DRILL | PostgreSQL restore from accepted backup + application-level smoke validation | execute and record dispositions, including failures |
| RESTORE-ROLLBACK-001 | DRILL | Known-good compatible release rollback where migration state permits | execute and record dispositions, including failures |

Campaign discipline that binds this role: run only what was frozen at M6; record every attempted run with a disposition; never adjust a threshold, rubric or scenario after seeing results; a MISS or a NOT_SUPPORTED outcome is a result, not a failure to conceal.

## 18. Demo Contribution

Yavuz owns demo integrity infrastructure: the pinned DemoManifest and release, the clean world provisioning, the evidence capture, and the abort conditions (wrong release, test-auth enabled, oracle violation, unverified effect). The demo runs on the real platform or it does not run.

## 19. Thesis / Portfolio Evidence

Portfolio and thesis material: the reproducible multi-service platform on a single constrained host, the CI/CD and release-identity model, the observability and audit separation design, the backup/restore and failure-validation evidence, the experiment runtime and evidence-sealing approach, and the reproduction results (clean host, non-owner, public package). These are exactly the artifacts that make the rest of the project credible rather than anecdotal.

| Evidence artifact | Produced by | Status today |
|---|---|---|
| Owned requirement dispositions (106) | 03 trace registry at M8 | NOT_YET_EXECUTED |
| Sealed lane results for owned research lanes | FBC-01 bundle at M7 | NOT_YET_EXECUTED |
| Architecture/design record (ADRs, contracts) | continuous from M1 | NOT_STARTED |
| Negative/failure evidence (17 families) | M5–M7 | NOT_YET_EXECUTED |

## 19.1 Requirement Execution Dossier

One block per owned requirement: what must be built, what proves it, where the evidence must come from, and which milestone carries it. This is the checklist the owner works through between M1 and M8.

```yaml
FR-EVAL-001:
  class: R1
  area: EVAL
  work_packages: [WP-RES-001, WP-BENCH-001]
  target_milestone: M5
  architecture: [ARCH-PLAT-RELEASE, ARCH-DATA-LINEAGE, ARCH-PLAT-CLI]
  planned_surface: "ExperimentRun manifest binding + runner CLI"
  boundary_mode_final: REAL
  verification: [TEST-EVAL-RUNNER, REPRO-NONOWNER-001, BENCH-FBC-001]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-003:
  class: R1
  area: EVAL
  work_packages: [WP-RES-003, WP-BENCH-001]
  target_milestone: M6
  architecture: [ARCH-DATA-LINEAGE, ARCH-DATA-PG]
  planned_surface: "BenchmarkRunRecord persistence"
  boundary_mode_final: REAL
  verification: [TEST-EVAL-RUNRECORD, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-004:
  class: R1
  area: EVAL
  work_packages: [WP-RES-003]
  target_milestone: M6
  architecture: [ARCH-DATA-LINEAGE]
  planned_surface: "append-only run status incl. failed/invalid attempts"
  boundary_mode_final: REAL
  verification: [TEST-EVAL-RUNRECORD, TEST-DATA-ACCOUNTING, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-005:
  class: R1
  area: EVAL
  work_packages: [WP-RES-003]
  target_milestone: M6
  architecture: [ARCH-DATA-LINEAGE]
  planned_surface: "RetryOf + disposition provenance"
  boundary_mode_final: REAL
  verification: [TEST-EVAL-RUNRECORD, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-007:
  class: R1
  area: EVAL
  work_packages: [WP-RES-005, WP-BENCH-005]
  target_milestone: M7
  architecture: [ARCH-DATA-OBJ, ARCH-DATA-LINEAGE]
  planned_surface: "EvidenceSeal + FinalBenchmarkEvidenceBundle assembly"
  boundary_mode_final: REAL
  verification: [INSP-EVAL-SEAL, TEST-DATA-REFINTEGRITY, BENCH-FBC-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVAL-008:
  class: R1
  area: EVAL
  work_packages: [WP-DR-004]
  target_milestone: M7
  architecture: [ARCH-PLAT-BACKUP, ARCH-DATA-OBJ]
  planned_surface: "off-host evidence copy + restore test job"
  boundary_mode_final: REAL
  verification: [RESTORE-EVID-001, INSP-REC-BACKUP]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-009:
  class: F1
  area: EVT
  work_packages: [WP-EVT-004]
  target_milestone: M5
  architecture: [ARCH-EVT-REPLAY, ARCH-EVT-CONSUMER]
  planned_surface: "replay procedure with World/revision/idempotency guards"
  boundary_mode_final: REAL
  verification: [TEST-EVT-REPLAY-DLQ, RES-BROKER-001]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-EVT-010:
  class: F1
  area: EVT
  work_packages: [WP-EVT-004]
  target_milestone: M5
  architecture: [ARCH-EVT-REPLAY, ARCH-OBS-HEALTH]
  planned_surface: "poison-message quarantine/DLQ path + alert (policy choice OD-FAIL-01)"
  boundary_mode_final: REAL
  verification: [TEST-EVT-REPLAY-DLQ, RES-DEPFAIL-001]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-005:
  class: F1
  area: GOV
  work_packages: [WP-GOV-002, WP-TEST-007]
  target_milestone: M2
  architecture: [ARCH-PLAT-CICD]
  planned_surface: "VERIFIED_BY edge completeness rule (M5 gate)"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-GOV-TRACELINT]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-006:
  class: F1
  area: GOV
  work_packages: [WP-GOV-003, WP-BENCH-005]
  target_milestone: M5
  architecture: [ARCH-PLAT-CICD, ARCH-DATA-OBJ]
  planned_surface: "EVIDENCED_BY edge rule bound to immutable EvidenceIDs"
  boundary_mode_final: REAL
  verification: [TEST-GOV-TRACELINT, INSP-GOV-ACCEPT]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-GOV-009:
  class: F1
  area: GOV
  work_packages: [WP-GOV-002]
  target_milestone: M2
  architecture: [ARCH-PLAT-CICD, ARCH-PLAT-CLI]
  planned_surface: "trace_edges registry + `mfgctl trace` generated views"
  boundary_mode_final: REAL
  verification: [TEST-GOV-TRACELINT, INSP-GOV-ACCEPT]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-007:
  class: F1
  area: HITL
  work_packages: [WP-HITL-004, WP-TEST-006]
  target_milestone: M3
  architecture: [ARCH-SEC-IDP, ARCH-EDGE-AUTH, ARCH-HITL-APPROVAL]
  planned_surface: "authenticated principal propagated into approval record"
  boundary_mode_final: REAL
  verification: [TEST-SEC-AUTHN, AV-SCEN-01, E2E-01]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-HITL-010:
  class: F1
  area: HITL
  work_packages: [WP-HITL-007]
  target_milestone: M5
  architecture: [ARCH-SEC-BREAKGLASS, ARCH-OBS-AUDIT]
  planned_surface: "break-glass path flag + high-risk audit record"
  boundary_mode_final: REAL
  verification: [TEST-SEC-BREAKGLASS, TEST-SEC-AUDIT]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-001:
  class: F0
  area: PLAT
  work_packages: [WP-PLAT-001, WP-PLAT-003]
  target_milestone: M1
  architecture: [ARCH-PLAT-COMPOSE, ARCH-PLAT-RELEASE]
  planned_surface: "Compose-based INTEGRATION composition of 9 deployables + infrastructure (backfill ADR 11)"
  boundary_mode_final: REAL
  verification: [TEST-PLAT-COMPOSE, TEST-DEP-PLATFORM, E2E-01, AV-SCEN-12, BENCH-E2E-001]
  evidence_env: "CI + INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-002:
  class: F1
  area: PLAT
  work_packages: [WP-PLAT-001]
  target_milestone: M1
  architecture: [ARCH-PLAT-COMPOSE]
  planned_surface: "capability-group Compose profiles"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-PLAT-COMPOSE, BENCH-DX-001]
  evidence_env: "DEV + CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-003:
  class: F1
  area: PLAT
  work_packages: [WP-PLAT-002]
  target_milestone: M1
  architecture: [ARCH-PLAT-CLI]
  planned_surface: "bootstrap/doctor/profile/scenario/smoke commands"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-PLAT-FABCTL, BENCH-DX-001]
  evidence_env: "DEV + CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-004:
  class: F1
  area: PLAT
  work_packages: [WP-CICD-001, WP-CICD-002]
  target_milestone: M0
  architecture: [ARCH-PLAT-CICD, ARCH-PLAT-RELEASE]
  planned_surface: "main-derived immutable artifact promotion to INTEGRATION"
  boundary_mode_final: REAL
  verification: [TEST-PLAT-CD, INSP-DEP-HOST]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-005:
  class: F1
  area: PLAT
  work_packages: [WP-PLAT-005, WP-CICD-002]
  target_milestone: M5
  architecture: [ARCH-PLAT-RELEASE]
  planned_surface: "ReleaseManifest/DeploymentRecord emission (format OD-CICD-01)"
  boundary_mode_final: REAL
  verification: [TEST-PLAT-CD, INSP-DEP-HOST]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-006:
  class: F1
  area: PLAT
  work_packages: [WP-OBS-001]
  target_milestone: M1
  architecture: [ARCH-OBS-TELEMETRY, ARCH-OBS-STORE]
  planned_surface: "centralized telemetry pipeline (backfill ADR 10)"
  boundary_mode_final: REAL
  verification: [TEST-OBS-TELEMETRY, AV-SCEN-01]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-007:
  class: F1
  area: PLAT
  work_packages: [WP-OBS-002]
  target_milestone: M3
  architecture: [ARCH-OBS-TRACE, ARCH-OBS-TELEMETRY]
  planned_surface: "trace-context propagation adapters"
  boundary_mode_final: REAL
  verification: [TEST-OBS-TRACEPROP, AV-SCEN-01, BENCH-E2E-001]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-008:
  class: F1
  area: PLAT
  work_packages: [WP-DR-001]
  target_milestone: M5
  architecture: [ARCH-PLAT-BACKUP, ARCH-DATA-PG, ARCH-DATA-OBJ]
  planned_surface: "BackupSet jobs (PostgreSQL logical/physical, critical objects) + off-host copy"
  boundary_mode_final: REAL
  verification: [RESTORE-PG-001, RESTORE-HOST-001, INSP-REC-BACKUP]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-009:
  class: F1
  area: PLAT
  work_packages: [WP-DR-003]
  target_milestone: M5
  architecture: [ARCH-PLAT-BACKUP, ARCH-TWIN-REBUILD, ARCH-DATA-VECTOR]
  planned_surface: "RecoveryDependencyGraph-driven rebuild runbooks"
  boundary_mode_final: REAL
  verification: [RES-TWINREBUILD-001, RES-IDXREBUILD-001, AV-SCEN-08]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-PLAT-010:
  class: F1
  area: PLAT
  work_packages: [WP-PLAT-005, WP-RES-001]
  target_milestone: M5
  architecture: [ARCH-PLAT-RELEASE]
  planned_surface: "EvaluationRunManifest/DemoManifest binding of Environment/Release/HardwareProfile"
  boundary_mode_final: REAL
  verification: [TEST-EVAL-RUNNER, DEMO-GS01-001, INSP-GOV-ACCEPT, BENCH-FBC-001]
  evidence_env: "CI + EVALUATION + DEMO"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-001:
  class: F1
  area: SEC
  work_packages: [WP-SEC-001]
  target_milestone: M3
  architecture: [ARCH-SEC-IDP, ARCH-EDGE-AUTH]
  planned_surface: "OIDC login/session for formal environments (backfill ADR 9)"
  boundary_mode_final: REAL
  verification: [TEST-SEC-AUTHN, E2E-01, AV-SCEN-01]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-002:
  class: F1
  area: SEC
  work_packages: [WP-SEC-002]
  target_milestone: M4
  architecture: [ARCH-SEC-IDP, ARCH-SEC-AUTHZ, ARCH-SEC-SECRET]
  planned_surface: "per-service client credentials / DB roles / broker accounts"
  boundary_mode_final: REAL
  verification: [TEST-SEC-SVCID, TEST-AUTH-NEG]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-004:
  class: F1
  area: SEC
  work_packages: [WP-AI-002, WP-SEC-004]
  target_milestone: M3
  architecture: [ARCH-AI-TOOLS, ARCH-SEC-AUTHZ]
  planned_surface: "tool inventory without shell execution capability"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-SEC-AISURFACE, TEST-AUTH-NEG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-005:
  class: F1
  area: SEC
  work_packages: [WP-AI-002, WP-SEC-004]
  target_milestone: M3
  architecture: [ARCH-AI-TOOLS, ARCH-SEC-AUTHZ]
  planned_surface: "tool inventory without arbitrary SQL; typed queries only"
  boundary_mode_final: FIXTURE_ALLOWED
  verification: [TEST-SEC-AISURFACE, TEST-AUTH-NEG]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-006:
  class: F1
  area: SEC
  work_packages: [WP-SEC-005]
  target_milestone: M4
  architecture: [ARCH-SEC-SECRET]
  planned_surface: "non-Git secret injection for formal runtime"
  boundary_mode_final: REAL
  verification: [TEST-SEC-SECRETS, INSP-DEP-HOST]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-007:
  class: F1
  area: SEC
  work_packages: [WP-OBS-004]
  target_milestone: M4
  architecture: [ARCH-OBS-AUDIT, ARCH-SEC-AUTHZ]
  planned_surface: "protected-action audit record with authn/authz identity"
  boundary_mode_final: REAL
  verification: [TEST-SEC-AUDIT, TEST-OBS-AUDITSEP]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-008:
  class: F1
  area: SEC
  work_packages: [WP-SEC-006]
  target_milestone: M5
  architecture: [ARCH-SEC-IDP, ARCH-PLAT-RELEASE]
  planned_surface: "test-auth mode flag rejected by formal runtime profile"
  boundary_mode_final: REAL
  verification: [TEST-SEC-TESTAUTH-NEG, E2E-01, DEMO-GS01-001]
  evidence_env: "INTEGRATION + EVALUATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-SEC-010:
  class: F1
  area: SEC
  work_packages: [WP-SIM-005, WP-SEC-007]
  target_milestone: M3
  architecture: [ARCH-WORLD-EVALZONE, ARCH-SIM-ORACLE, ARCH-SEC-AUTHZ]
  planned_surface: "EVALUATOR_ONLY credential/network separation (mechanism OD-AI-03)"
  boundary_mode_final: REAL
  verification: [TEST-SEC-ORACLE-NEG, AV-SCEN-11, BENCH-RQ3-001]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
FR-UI-009:
  class: F1
  area: UI
  work_packages: [WP-UI-009, WP-DOC-004]
  target_milestone: M4
  architecture: [ARCH-EDGE-WEB, ARCH-PLAT-RELEASE, ARCH-OBS-HEALTH]
  planned_surface: "environment/release/world diagnostic panel"
  boundary_mode_final: REAL
  verification: [TEST-UI-DIAG, DEMO-GS01-001]
  evidence_env: "INTEGRATION + DEMO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-004:
  class: A1
  area: CAP
  work_packages: [WP-EVT-006, WP-PERF-003]
  target_milestone: M7
  metric: "durable application messages/s sustained; loss and duplicate protected effects"
  threshold: "100 msg/s × 10 min; loss = 0; duplicates = 0"
  workload_profile: "application event pipeline load"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-CAP-EVT]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-009:
  class: S2
  area: CAP
  work_packages: [WP-PLAT-004, WP-PERF-003]
  target_milestone: M5
  metric: "concurrent authenticated interactive sessions without correctness degradation"
  threshold: "≥ 8 sessions"
  workload_profile: "Integration profile"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-CAP-ENV]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-CAP-010:
  class: S2
  area: CAP
  work_packages: [WP-TWIN-005, WP-PERF-003]
  target_milestone: M4
  metric: "simultaneously existing isolated WorldIDs; cross-world leakage"
  threshold: "≥ 5 WorldIDs; leakage = 0"
  workload_profile: "Integration/Evaluation runtime"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-CAP-ENV, AV-SCEN-10]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-001:
  class: H0
  area: DATA
  work_packages: [WP-OBJ-001]
  target_milestone: M2
  metric: "final critical immutable artifacts with verified checksum/content identity"
  threshold: "100%"
  workload_profile: "final critical artifacts"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DATA-CHECKSUM]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-003:
  class: H0
  area: DATA
  work_packages: [WP-RES-003, WP-BENCH-005]
  target_milestone: M6
  metric: "accepted final BenchmarkRunRecords with 100% mandatory provenance fields"
  threshold: "100%"
  workload_profile: "FBC-01 run set"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DATA-REFINTEGRITY]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-004:
  class: H0
  area: DATA
  work_packages: [WP-RES-005, WP-BENCH-005]
  target_milestone: M7
  metric: "unresolved mandatory artifact/run/evidence references in sealed evidence"
  threshold: "= 0"
  workload_profile: "FinalBenchmarkEvidenceBundle"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DATA-REFINTEGRITY, INSP-EVAL-SEAL]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-007:
  class: H0
  area: DATA
  work_packages: [WP-RES-003]
  target_milestone: M6
  metric: "planned FBC experimental units reconciled to one documented disposition"
  threshold: "100%"
  workload_profile: "FBC-01"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DATA-ACCOUNTING]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DATA-008:
  class: H0
  area: DATA
  work_packages: [WP-EVT-002]
  target_milestone: M1
  metric: "persisted formal evidence fields with ambiguous UTC-vs-simulation time"
  threshold: "= 0"
  workload_profile: "formal persisted evidence"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DATA-TIME]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DEP-001:
  class: A1
  area: DEP
  work_packages: [WP-PLAT-001, WP-PLAT-003]
  target_milestone: M1
  metric: "mandatory runtime deploys on documented x86-64 Linux + Docker/Compose without VM/K8s"
  threshold: "PASS"
  workload_profile: "mandatory Integration profile"
  hardware_profile: "HP: x86-64 Linux host (distro OD-PLAT-01)"
  verification: [TEST-DEP-PLATFORM]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DEP-002:
  class: S2
  area: DEP
  work_packages: [WP-PLAT-001]
  target_milestone: M1
  metric: "startup → healthy or explicit known-degraded with images local"
  threshold: "≤ 10 min"
  workload_profile: "full mandatory Integration profile"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-DEP-STARTUP]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DEP-003:
  class: H0
  area: DEP
  work_packages: [WP-CICD-002]
  target_milestone: M1
  metric: "manual source-code patches on target host for formal deployment"
  threshold: "= 0"
  workload_profile: "formal deployments"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-DEP-HOST, TEST-PLAT-CD]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DEP-004:
  class: A1
  area: DEP
  work_packages: [WP-CORE-007, WP-CICD-003]
  target_milestone: M1
  metric: "release-required migrations executed outside versioned automated tooling"
  threshold: "= 0; status inspectable"
  workload_profile: "release deployments"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DEP-MIGRATION]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DEP-005:
  class: H0
  area: DEP
  work_packages: [WP-BENCH-004]
  target_milestone: M8
  metric: "private filesystem state / undocumented endpoints / hidden services in formal/public reproduction"
  threshold: "= 0"
  workload_profile: "formal + public reproduction paths"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-DEP-HOST, REPRO-CLEANHOST-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DEP-006:
  class: H0
  area: DEP
  work_packages: [WP-PLAT-001]
  target_milestone: M1
  metric: "mandatory Kubernetes / paid cloud / mandatory VM dependencies in v1 baseline"
  threshold: "= 0"
  workload_profile: "v1 mandatory baseline"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-DEP-HOST, TEST-DEP-PLATFORM]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-001:
  class: S2
  area: DX
  work_packages: [WP-PLAT-002]
  target_milestone: M1
  metric: "`mfgctl doctor` duration on healthy bootstrapped machine"
  threshold: "≤ 30 s"
  workload_profile: "—"
  hardware_profile: "HP: documented normal developer hardware (TBD, Item 82 open)"
  verification: [BENCH-DX-001]
  evidence_env: "DEV"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-002:
  class: S2
  area: DX
  work_packages: [WP-PLAT-002]
  target_milestone: M1
  metric: "high-value local lint/type/static validation duration"
  threshold: "≤ 90 s"
  workload_profile: "—"
  hardware_profile: "HP: documented normal developer hardware"
  verification: [BENCH-DX-001]
  evidence_env: "DEV"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-003:
  class: S2
  area: DX
  work_packages: [WP-PLAT-002]
  target_milestone: M1
  metric: "capability smoke duration (excl. first downloads)"
  threshold: "≤ 2 min"
  workload_profile: "per capability smoke"
  hardware_profile: "HP: documented normal developer hardware"
  verification: [BENCH-DX-001]
  evidence_env: "DEV"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-004:
  class: S2
  area: DX
  work_packages: [WP-PLAT-002]
  target_milestone: M1
  metric: "normal capability profile ready time with images present"
  threshold: "≤ 5 min"
  workload_profile: "capability profile"
  hardware_profile: "HP: documented normal developer hardware"
  verification: [BENCH-DX-001]
  evidence_env: "DEV"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-005:
  class: S2
  area: DX
  work_packages: [WP-PLAT-006]
  target_milestone: M8
  metric: "non-author clone→bootstrap→doctor→subsystem smoke"
  threshold: "≈ one focused hour (excl. bulk downloads)"
  workload_profile: "onboarding walk-through"
  hardware_profile: "HP: documented normal developer hardware"
  verification: [INSP-DX-ONBOARD]
  evidence_env: "DEV"
  evidence_target: EV-L1
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-006:
  class: H0
  area: DX
  work_packages: [WP-CICD-001, WP-TEST-001, WP-TEST-008]
  target_milestone: M0
  metric: "known unresolved unquarantined flaky tests in final release/benchmark gates"
  threshold: "= 0"
  workload_profile: "final required gates"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DX-FLAKE]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-007:
  class: A1
  area: DX
  work_packages: [WP-PLAT-006, WP-DOC-001]
  target_milestone: M8
  metric: "quickstart/reproduction/runbook commands validated against applicable release"
  threshold: "100% before M8"
  workload_profile: "applicable release"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-DX-DOCS]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-DX-008:
  class: S2
  area: DX
  work_packages: [WP-PLAT-006, WP-OBS-005]
  target_milestone: M8
  metric: "diagnostic-bundle generation duration; unredacted secrets"
  threshold: "≤ 2 min; secrets = 0"
  workload_profile: "normal host conditions"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-DX-001, TEST-OBS-REDACTION]
  evidence_env: "DEV + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-004:
  class: H0
  area: GOV
  work_packages: [WP-GOV-003, WP-PERF-001]
  target_milestone: M5
  metric: "quantitative NFRs lacking metric+measurement context"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-GOV-NFR, TEST-DATA-REFINTEGRITY]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-005:
  class: H0
  area: GOV
  work_packages: [WP-GOV-003, WP-PERF-001]
  target_milestone: M5
  metric: "hardware-dependent final results without HardwareProfile"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-GOV-NFR, TEST-DATA-REFINTEGRITY]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-006:
  class: H0
  area: GOV
  work_packages: [WP-GOV-003, WP-PERF-001]
  target_milestone: M5
  metric: "load-dependent final results without WorkloadProfile"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-GOV-NFR, TEST-DATA-REFINTEGRITY]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-GOV-009:
  class: H0
  area: GOV
  work_packages: [WP-GOV-002, WP-DOC-006]
  target_milestone: M2
  metric: "VERIFIED NFRs without durable measurement evidence"
  threshold: "0"
  workload_profile: "—"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-GOV-TRACELINT, INSP-GOV-ACCEPT]
  evidence_env: "CI + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-001:
  class: A1
  area: OBS
  work_packages: [WP-OBS-001]
  target_milestone: M1
  metric: "mandatory deployables exposing inspectable health/readiness"
  threshold: "100%"
  workload_profile: "mandatory runtime"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-OBS-HEALTH]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-002:
  class: A1
  area: OBS
  work_packages: [WP-OBS-001]
  target_milestone: M1
  metric: "team-owned mandatory services emitting structured logs with service/environment/correlation"
  threshold: "100% where applicable"
  workload_profile: "mandatory runtime"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-OBS-LOGS]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-003:
  class: A1
  area: OBS
  work_packages: [WP-OBS-002, WP-BENCH-002]
  target_milestone: M3
  metric: "formal GS-01/E2E acceptance runs with complete traceable path across mandatory boundaries"
  threshold: "100% of acceptance runs"
  workload_profile: "GS-01 + FBC-01 E2E matrix"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-OBS-TRACEPROP, BENCH-E2E-001, DEMO-GS01-001]
  evidence_env: "INTEGRATION + EVALUATION + DEMO"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-004:
  class: A1
  area: OBS
  work_packages: [WP-OBS-003]
  target_milestone: M4
  metric: "hard failure → observable health/alert telemetry"
  threshold: "≤ 60 s"
  workload_profile: "mandatory service hard-failure injection"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [TEST-OBS-HEALTH, RES-DEPFAIL-001, RES-PROCESS-001]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-005:
  class: H0
  area: OBS
  work_packages: [WP-OBS-002]
  target_milestone: M3
  metric: "formal evidence telemetry lacking EnvironmentID/WorldID/release/CorrelationID-TraceID"
  threshold: "= 0"
  workload_profile: "formal evidence telemetry"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-OBS-TRACEPROP, TEST-DATA-REFINTEGRITY]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-006:
  class: H0
  area: OBS
  work_packages: [WP-OBS-005]
  target_milestone: M5
  metric: "known plaintext secrets in final logs/evidence"
  threshold: "= 0"
  workload_profile: "final log/evidence redaction check"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-OBS-REDACTION]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-007:
  class: H0
  area: OBS
  work_packages: [WP-OBS-004]
  target_milestone: M4
  metric: "protected-action audit records lost after telemetry loss/rotation"
  threshold: "= 0; distinct stores/lifecycles"
  workload_profile: "telemetry rotation test"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-OBS-AUDITSEP]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-008:
  class: S2
  area: OBS
  work_packages: [WP-OBS-006]
  target_milestone: M7
  metric: "overhead vs instrumentation-disabled diagnostic baseline"
  threshold: "≈ ≤10% p95 latency; ≤15% mean CPU (larger disclosed)"
  workload_profile: "representative controlled workload"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-OBS-OVERHEAD]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-OBS-009:
  class: A1
  area: OBS
  work_packages: [WP-OBJ-002, WP-OBS-006]
  target_milestone: M5
  metric: "retained useful Integration logs/metrics/traces under quota"
  threshold: "≥ 7 days"
  workload_profile: "Integration storage quota"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [INSP-OBS-RETENTION]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-PERF-012:
  class: S2
  area: PERF
  work_packages: [WP-HITL-004, WP-PERF-002]
  target_milestone: M3
  metric: "authenticated approve/reject submission → durable approval record"
  threshold: "p95 ≤ 2 s"
  workload_profile: "Integration/Evaluation profile"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-PERF-WF]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-001:
  class: A1
  area: REC
  work_packages: [WP-DR-001]
  target_milestone: M5
  metric: "recovery point age for canonical Integration mutable data"
  threshold: "RPO ≤ 24 h"
  workload_profile: "Integration backup schedule"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-REC-BACKUP, RESTORE-PG-001]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-002:
  class: H0
  area: REC
  work_packages: [WP-DR-004]
  target_milestone: M7
  metric: "EvidenceSeal → verified off-host copy of critical RC-B evidence"
  threshold: "≤ 30 min"
  workload_profile: "final evidence sealing"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-REC-BACKUP, RESTORE-EVID-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-003:
  class: A1
  area: REC
  work_packages: [WP-DR-002]
  target_milestone: M6
  metric: "PostgreSQL restore + application smoke validation duration"
  threshold: "≤ 2 h"
  workload_profile: "accepted backup"
  hardware_profile: "HP: compatible restore hardware (recorded)"
  verification: [RESTORE-PG-001]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-004:
  class: A1
  area: REC
  work_packages: [WP-DR-002]
  target_milestone: M6
  metric: "simulated host loss → mandatory Integration reconstructed"
  threshold: "≤ 4 h"
  workload_profile: "Git + manifests + registry + off-host backups"
  hardware_profile: "HP: compatible replacement hardware (recorded)"
  verification: [RESTORE-HOST-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-005:
  class: S2
  area: REC
  work_packages: [WP-CICD-005]
  target_milestone: M5
  metric: "rollback decision → known-good compatible release verified"
  threshold: "≤ 20 min where technically safe"
  workload_profile: "rollback-safe migration state"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RESTORE-ROLLBACK-001]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-006:
  class: H0
  area: REC
  work_packages: [WP-DR-001]
  target_milestone: M5
  metric: "acceptance/DR-critical backup artifacts failing checksum/integrity verification"
  threshold: "= 0 (100% verified)"
  workload_profile: "final/DR BackupSets"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-REC-BACKUP, TEST-DATA-CHECKSUM]
  evidence_env: "EVALUATION"
  evidence_target: EV-L5
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-007:
  class: H0
  area: REC
  work_packages: [WP-DR-002, WP-BENCH-003]
  target_milestone: M6
  metric: "full-host-loss reconstruction/restore drill result before M8"
  threshold: "≥ 1 PASS"
  workload_profile: "full host loss"
  hardware_profile: "HP: compatible replacement hardware (recorded)"
  verification: [RESTORE-HOST-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REC-010:
  class: H0
  area: REC
  work_packages: [WP-DR-001]
  target_milestone: M5
  metric: "formal restore drills missing backup source/target release/EnvironmentID/timestamps/result"
  threshold: "= 0"
  workload_profile: "every formal drill"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-REC-BACKUP, RESTORE-PG-001, RESTORE-HOST-001]
  evidence_env: "INTEGRATION + EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-003:
  class: A1
  area: REL
  work_packages: [WP-PERF-004]
  target_milestone: M6
  metric: "intentional crash → healthy"
  threshold: "≤ 2 min"
  workload_profile: "normal restart policy"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-PROCESS-001]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-005:
  class: A1
  area: REL
  work_packages: [WP-TEST-005, WP-PERF-004]
  target_milestone: M5
  metric: "reboot with intact volumes → healthy or accepted known-degraded"
  threshold: "≤ 10 min"
  workload_profile: "mandatory Integration runtime"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-REBOOT-001, AV-SCEN-12]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-006:
  class: A1
  area: REL
  work_packages: [WP-TEST-004, WP-PERF-004]
  target_milestone: M5
  metric: "5-min broker interruption → backlog drain; committed Core effect loss"
  threshold: "drain ≤ 15 min; loss = 0"
  workload_profile: "WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-BROKER-001, AV-SCEN-07]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-007:
  class: A1
  area: REL
  work_packages: [WP-PERF-005]
  target_milestone: M7
  metric: "unhandled crash loops / data corruption / effect duplication over soak"
  threshold: "8 h; all = 0"
  workload_profile: "WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-SOAK-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-008:
  class: A1
  area: REL
  work_packages: [WP-PERF-004]
  target_milestone: M6
  metric: "duration of unbounded monotonic queue/backlog growth"
  threshold: "≤ 15 min (else capacity exceeded)"
  workload_profile: "sustained WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-SOAK-001, BENCH-CAP-EVT]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REL-009:
  class: A1
  area: REL
  work_packages: [WP-OBS-003, WP-PERF-004]
  target_milestone: M4
  metric: "dependency loss → DEGRADED/UNAVAILABLE/MANUAL_REQUIRED visibility time"
  threshold: "≤ 60 s where observable"
  workload_profile: "mandatory observable dependencies"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-DEPFAIL-001]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-003:
  class: A1
  area: REP
  work_packages: [WP-PLAT-005, WP-BENCH-004]
  target_milestone: M5
  metric: "clean compatible host deploys exact ReleaseManifest without private state"
  threshold: "PASS"
  workload_profile: "exact accepted ReleaseManifest"
  hardware_profile: "HP: clean compatible host (recorded)"
  verification: [REPRO-CLEANHOST-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-004:
  class: A1
  area: REP
  work_packages: [WP-BENCH-003, WP-BENCH-004]
  target_milestone: M7
  metric: "non-owner teammate reproductions of selected final environment/scenario"
  threshold: "≥ 1 PASS before M8"
  workload_profile: "selected final scenario"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [REPRO-NONOWNER-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-005:
  class: H0
  area: REP
  work_packages: [WP-CICD-004]
  target_milestone: M5
  metric: "known stale generated runtime-required clients/contracts in formal release"
  threshold: "= 0"
  workload_profile: "formal release"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-REP-CODEGEN]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-006:
  class: H0
  area: REP
  work_packages: [WP-CICD-004]
  target_milestone: M5
  metric: "unlocked/unpinned mandatory dependencies; unbounded latest in formal identity"
  threshold: "= 0"
  workload_profile: "formal runtime identity"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-REP-LOCKS]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-007:
  class: H0
  area: REP
  work_packages: [WP-PLAT-005]
  target_milestone: M5
  metric: "formal deployments referencing mutable artifact/image identities"
  threshold: "= 0"
  workload_profile: "formal deployments"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-REP-LOCKS, TEST-PLAT-CD]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-REP-008:
  class: A1
  area: REP
  work_packages: [WP-BENCH-004, WP-DOC-005]
  target_milestone: M8
  metric: "OSR-3 clean-clone hero reproduction of v1 public (or sanitized) package"
  threshold: "PASS"
  workload_profile: "public/sanitized package"
  hardware_profile: "HP: clean public-repro host (recorded)"
  verification: [REPRO-OSR3-001]
  evidence_env: "PUBLIC_REPRO"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-001:
  class: A1
  area: RES
  work_packages: [WP-PLAT-004]
  target_milestone: M5
  metric: "p95 cgroup-accounted combined mandatory container memory over 30-min steady window"
  threshold: "≤ 12 GiB"
  workload_profile: "WP-NORMAL"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-RES-FOOTPRINT, RES-SOAK-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-002:
  class: A1
  area: RES
  work_packages: [WP-PLAT-004]
  target_milestone: M5
  metric: "combined mandatory container memory during accepted short peaks; OOM kills"
  threshold: "≤ 14 GiB; OOM = 0"
  workload_profile: "accepted operational peaks"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-RES-FOOTPRINT]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-003:
  class: H0
  area: RES
  work_packages: [WP-PLAT-004]
  target_milestone: M5
  metric: "OOM kills during final 8-hour normal soak"
  threshold: "= 0"
  workload_profile: "WP-NORMAL 8 h soak"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [RES-SOAK-001]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-004:
  class: A1
  area: RES
  work_packages: [WP-PLAT-007]
  target_milestone: M6
  metric: "free persistent-filesystem capacity at Benchmark/Demo preflight"
  threshold: "≥ 20% (or explicit allocated headroom)"
  workload_profile: "preflight"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [TEST-RES-PREFLIGHT]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-005:
  class: H0
  area: RES
  work_packages: [WP-PLAT-007]
  target_milestone: M6
  metric: "undeclared concurrent training/bulk indexing/heavy CI during formal benchmark/performance/demo"
  threshold: "= 0"
  workload_profile: "formal benchmark/demo windows"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [TEST-RES-PREFLIGHT, INSP-DEP-HOST]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-006:
  class: A1
  area: RES
  work_packages: [WP-OBJ-002]
  target_milestone: M5
  metric: "storage classes without explicit retention/quota limit"
  threshold: "= 0"
  workload_profile: "Integration runtime"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [INSP-RES-RETENTION]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-007:
  class: A1
  area: RES
  work_packages: [WP-VIS-008]
  target_milestone: M2
  metric: "GPU requirement in mandatory quickstart / CPU smoke path"
  threshold: "none required"
  workload_profile: "GPU-less host"
  hardware_profile: "HP: GPU-less CPU host (recorded)"
  verification: [TEST-RES-CPUONLY, TEST-VIS-CPUSMOKE]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-RES-008:
  class: C3
  area: RES
  work_packages: [WP-PLAT-004]
  target_milestone: M5
  metric: "mean CPU, p95 CPU, saturation behavior"
  threshold: "C3 — characterize"
  workload_profile: "WP-NORMAL + selected stress"
  hardware_profile: "HP: accepted 16 GiB shared Linux host (EVALUATION HardwareProfile)"
  verification: [BENCH-RES-FOOTPRINT]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-001:
  class: H0
  area: SEC
  work_packages: [WP-SEC-005, WP-DOC-005]
  target_milestone: M4
  metric: "known live secrets/credentials in release + publishable Git history"
  threshold: "= 0"
  workload_profile: "final accepted release"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-SECRETS]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-002:
  class: H0
  area: SEC
  work_packages: [WP-CICD-004]
  target_milestone: M5
  metric: "known unmitigated Critical vulnerabilities in mandatory deployed components"
  threshold: "= 0 (High → documented disposition)"
  workload_profile: "final accepted release"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-SUPPLYCHAIN]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-003:
  class: A1
  area: SEC
  work_packages: [WP-SEC-001]
  target_milestone: M3
  metric: "browser ingress without TLS in INTEGRATION/EVALUATION/DEMO"
  threshold: "= 0 endpoints"
  workload_profile: "formal environments"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-TLS]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-005:
  class: H0
  area: SEC
  work_packages: [WP-HITL-004]
  target_milestone: M3
  metric: "accepted protected approvals not mapping to exactly one authenticated authorized human"
  threshold: "= 0"
  workload_profile: "formal approvals"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-AUTHN, TEST-HITL-RECORD]
  evidence_env: "CI + INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-006:
  class: H0
  area: SEC
  work_packages: [WP-SEC-006]
  target_milestone: M5
  metric: "uses of bounded test-auth bypass in accepted formal runs"
  threshold: "= 0"
  workload_profile: "formal Integration/Evaluation/Demo runs"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-TESTAUTH-NEG]
  evidence_env: "EVALUATION"
  evidence_target: EV-L4
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-007:
  class: H0
  area: SEC
  work_packages: [WP-SEC-002]
  target_milestone: M4
  metric: "team-owned mandatory containers running privileged"
  threshold: "= 0 (infra exceptions reviewed)"
  workload_profile: "mandatory runtime"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-CONTAINER]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-008:
  class: A1
  area: SEC
  work_packages: [WP-SEC-002]
  target_milestone: M4
  metric: "team-owned application containers running as root without approved exception"
  threshold: "= 0"
  workload_profile: "mandatory runtime"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-CONTAINER]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-010:
  class: H0
  area: SEC
  work_packages: [WP-HITL-005, WP-SEC-008]
  target_milestone: M4
  metric: "audit coverage of proposal/plan binding, actor, approval, command, effect verification"
  threshold: "100%"
  workload_profile: "formal protected actions"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-AUDIT, AV-SCEN-01]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-011:
  class: H0
  area: SEC
  work_packages: [WP-CICD-006]
  target_milestone: M5
  metric: "privileged credentials / sensitive runners available to untrusted fork/PR jobs"
  threshold: "= 0"
  workload_profile: "CI configuration"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-CIISOLATION]
  evidence_env: "CI"
  evidence_target: EV-L2
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
NFR-SEC-012:
  class: H0
  area: SEC
  work_packages: [WP-HITL-007]
  target_milestone: M5
  metric: "break-glass invocations generating explicit high-risk audit records"
  threshold: "100% (if enabled)"
  workload_profile: "break-glass drills"
  hardware_profile: "N/A (not hardware-bound)"
  verification: [TEST-SEC-BREAKGLASS]
  evidence_env: "INTEGRATION"
  evidence_target: EV-L3
  state: {implementation: NOT_STARTED, verification: NOT_BUILT, evidence: NOT_YET_EXECUTED}
```

## 20. Definition of Final Role Completion

This role is complete at M8 when every line below is true and demonstrable from generated artifacts — not when the owner believes the work is done.

| # | Completion criterion |
|---|---|
| C-1 | All 57 owned work packages are at DoD (04 §4.2), with real repository references replacing `TBD_BY_IMPLEMENTATION` |
| C-2 | All 106 owned requirements have a final disposition in 03 — VERIFIED, or an explicitly recorded FAIL/MISS/REBASELINED with analysis |
| C-3 | Every owned F0 requirement is verified on a real integrated path (FR-PLAT-001) |
| C-4 | Every owned H0 requirement (33) has hard/negative evidence with zero-count assertions satisfied |
| C-5 | Every owned A1/S2/C3 requirement has a measurement executed in the correct environment with its HardwareProfile/WorkloadProfile bound |
| C-6 | Every downstream commitment (13 HARD edges) was delivered at its required readiness with unblock evidence |
| C-7 | All owned contracts are versioned, documented and consumed by their real consumers — no consumer still runs on fixtures in the acceptance path |
| C-8 | Owned ADRs exist for the decisions listed in §14, and 03 trace edges are current |
| C-9 | Owned research lanes executed from frozen artifacts with dispositions recorded; claims traced to sealed evidence |
| C-10 | Owned red-team findings are resolved or explicitly accepted before release |
| C-11 | No owned capability depends on a development fixture, a manual host step or an unrecorded configuration |
| C-12 | A teammate who is not this owner can run the owned capability from documentation alone (cross-familiarity, TEAM-R01) |

---

*End of 06D_Yavuz_Engineering_Roadmap.md (Draft — Derived from Approved 01/02 Baseline).*