# Downstream Artifact Production Guide
## Intelligent Manufacturing Operations Platform for Critical Aerospace Components — 01/02 Sonrası Teknik Doküman Üretim Standardı

**Doküman amacı:** Bu rehber, `01_Master_Project_Specification.md` ve tamamlanmış `02_System_Architecture_Specification.md` ile birlikte bir yapay zekâ aracına verilerek the Manufacturing Operations Platform’nin kalan planlama ve execution-artifact dokümanlarının aynı mühendislik disiplini, içerik derinliği ve profesyonellik seviyesinde üretilmesini sağlamak için hazırlanmıştır.

**Kullanım biçimi:** Yapay zekâ aracına her görevde üç temel kaynak verilir:

1. `01_Master_Project_Specification.md`
2. `02_System_Architecture_Specification.md`
3. Bu doküman

Ardından üretilecek hedef dosya açıkça belirtilir.

---

# 1. Ana Üretim Doktrini

Bu projede kalan dokümanlar `01` ve `02`nin özeti değildir.

`01_Master_Project_Specification.md` projenin **normative product constitution / approved decision baseline**’ıdır. Ne yapılacağı, neden yapılacağı, scope, requirement, quality, authority, research, evaluation ve governance kararları burada bulunur.

`02_System_Architecture_Specification.md` kabul edilmiş sistemin **current structural architecture projection**’ıdır. Bounded services, semantic authority, component responsibilities, data/control flows, service boundaries, deployment topology, trust zones, failure domains ve runtime composition burada bulunur.

Kalan dokümanların görevi bu iki kaynaktaki kararları tekrar etmek değil, belirli bir mühendislik amacı için **lossless projection** haline getirmektir.

Canonical yaklaşım:

> **Read Source → Extract Relevant Approved Decisions → Normalize Into Target Artifact Model → Preserve Stable Identities → Add Only Necessary Derived Detail → Cross-Check Against 01/02 → Produce Implementable Artifact**

Her doküman şu soruya cevap vermelidir:

> “Bu dosyanın var olmasının 01 ve 02’den bağımsız mühendislik değeri nedir?”

Cevap yalnız “aynı bilgiyi başka formatta tekrar ediyor” ise doküman yanlış üretilmiştir.

---

# 2. Kaynak Önceliği ve Normative Truth

## 2.1 Canonical source precedence

Her yapay zekâ aracı aşağıdaki önceliği kullanmalıdır:

1. **01 Master Project Specification** — product/scope/requirements/governance açısından en yüksek source of truth.
2. **02 System Architecture Specification** — 01 ile uyumlu current architecture source of truth.
3. **Stable IDs ve approved invariants** — FR/NFR/architecture/benchmark/authority vb. kimlikler.
4. **Hedef artifact’ın kendi derived planning structure’ı.**

01 ile 02 arasında gerçek bir çelişki bulunursa:

- sessizce bir taraf seçilmemeli,
- yeni bir “doğru” icat edilmemeli,
- `SOURCE_CONFLICT` veya `RECONCILIATION_REQUIRED` olarak işaretlenmeli,
- 01’in approved normative kararını override eden yeni karar üretilmemelidir.

Final 02’nin zaten 01 ile reconcile edilmiş olması beklenir; buna rağmen downstream AI bu kontrolü yapmalıdır.

## 2.2 Latest approved refinement controls

01 içinde erken maddelerde candidate/deferred olarak geçen ama daha sonraki approved maddelerde kesinleşen kararlar için **latest approved refinement controls**.

Örnek final technology baseline:

- Python-first + TypeScript frontend
- PostgreSQL canonical relational store
- Qdrant retrieval projection
- NATS + JetStream event backbone
- Temporal durable workflow
- SeaweedFS S3-compatible object storage
- Keycloak identity provider
- Valkey optional/degradable cache
- OpenTelemetry + Collector + OpenObserve observability
- MLflow supporting ML experiment/registry tooling
- OR-Tools CP-SAT scheduling
- custom deterministic Python DES
- Docker/Compose final local/shared-host baseline
- GitHub + Actions + GHCR

Downstream dokümanlar eski candidate’ları yeniden “open decision” yapmamalıdır.

---

# 3. Yeni Karar İcat Etme Yasağı

Kalan artifact’lar execution detail üretmek zorunda olduğu için bazı derived detail’ler kaçınılmazdır. Fakat derived detail ile yeni product decision birbirinden ayrılmalıdır.

## 3.1 İzin verilen derived detail

Aşağıdakiler, 01/02 ile çelişmediği sürece üretilebilir:

- Work Package numaralandırması
- WBS task decomposition
- dependency-edge IDs
- roadmap phase/task ordering
- review/checklist IDs
- planned TestID placeholder families
- internal table/view organization
- Mermaid diagram layout
- document-local section IDs
- implementation sequencing detail
- task-level handoff artifacts
- document generation metadata

Bunlar mümkün olduğunda:

> `Derived Planning Detail`

veya

> `Derived Execution Detail`

olarak düşünülmelidir.

## 3.2 İzin verilmeyen sessiz icatlar

AI aşağıdakileri kaynakta yoksa kendiliğinden belirleyemez:

- yeni F0/F1 requirement
- yeni product capability
- yeni mandatory technology
- yeni database/broker/framework
- farklı service authority
- farklı role ownership
- farklı milestone semantics
- yeni approval level
- yeni benchmark sample size
- yeni research hypothesis
- yeni cloud/Kubernetes requirement
- yeni real-manufacturing-facility claim
- yeni security bypass
- mevcut scope’u genişleten feature

Böyle bir ihtiyaç ortaya çıkarsa:

> `CHANGE_CONTROL_REQUIRED`

olarak işaretlenmelidir.

---

# 4. Claim ve Scope Disiplini

Bütün downstream artifacts aşağıdaki claim boundaries’i korumalıdır.

the Manufacturing Operations Platform:

> **simulated/research-scale critical-component manufacturing critical-component manufacturing operational environment içinde çalışan human-governed autonomous manufacturing operations & intelligence platform**

olarak çerçevelenir.

the Manufacturing Operations Platform şu değildir:

- real manufacturing facility equipment controller
- manufacturing process-physics simulator
- TCAD system
- certified safety system
- production-qualified industrial MES replacement
- real-manufacturing-facility first-pass yield optimization proof
- HA commercial production platform
- guaranteed hard-real-time controller
- packaging/test platform

“Production-grade”, “enterprise-scale”, “real-time”, “causal”, “optimal”, “industry-ready”, “fault tolerant”, “highly available” gibi güçlü ifadeler yalnız 01/02’nin açıkça izin verdiği ve evidence ile sınırlandırdığı biçimde kullanılabilir.

Sentetik/public evidence:

> gerçek manufacturing facility doğrulaması olarak yeniden adlandırılamaz.

---

# 5. Sabit Ownership ve Removal-Test

Downstream AI role ownership’i yeniden dağıtamaz.

## Asrın — Manufacturing Intelligence & Core Systems Owner

Canonical ownership family:

- manufacturing Core/domain semantics
- Digital Twin semantics
- AI/RCA/RAG
- predictive intelligence
- backend/application authority
- action-authority semantics
- architecture coherence

Removal effect:

> **Understand / Govern / Core Intelligence capability family breaks.**

## Selman — Visual Perception & Inspection Intelligence Owner

Canonical ownership family:

- Vision pipeline
- inspection intelligence
- classification
- localization
- segmentation
- anomaly/OOD
- serialized component spatial analysis
- Vision datasets / Vision MLOps
- Vision evaluation

Removal effect:

> **Sense capability breaks.**

## Batu — Manufacturing Control, Simulation & Recovery Owner

Canonical ownership family:

- operational DES Simulator
- scenarios/world execution
- Scheduler
- CP-SAT
- ScheduleValidator
- counterfactual planning
- Temporal workflow semantics
- recovery automation/control plane

Removal effect:

> **Operational world and Decide / Optimize / Execute capability family breaks.**

## Yavuz — Platform Engineering, Delivery & Reliability Owner

Canonical ownership family:

- container/runtime platform
- local/shared environments
- CI/CD
- registry/deployment
- release/environment manifests
- observability
- platform security
- backup/restore
- operational reliability
- experiment reproducibility infrastructure

Removal effect:

> **Operate / Recover / Reproduce capability family breaks.**

Cross-cutting collaboration is encouraged, but primary ownership cannot drift silently.

---

# 6. Architecture Boundaries That Every Artifact Must Preserve

Kalan belgelerde aşağıdaki boundaries hiçbir nedenle yumuşatılamaz:

- **Core** = legal manufacturing/business state authority.
- **Simulator** = simulated physical execution/world authority + hidden Oracle authority.
- **Twin** = rebuildable operational projection; canonical mutation authority değildir.
- **Vision** = inspection/perception observation authority; operational-action authority değildir.
- **AI** = READ / SIMULATE / PROPOSE; canonical manufacturing mutation yapamaz.
- **Scheduler** = plan/candidate generation authority; execution authority değildir.
- **ScheduleValidator** = independent deterministic feasibility gate.
- **HITL** = exact proposal/plan/world/revision-bound approval.
- **Automation/Temporal** = governed durable execution path; Core private DB’sini bypass etmez.
- **NATS** = transport; business truth değildir.
- **Qdrant** = retrieval projection; documentary/canonical truth değildir.
- **MLflow** = supporting MLOps tooling; the Manufacturing Operations Platform governance authority değildir.
- **OpenObserve** = telemetry backend; audit veya manufacturing truth değildir.
- **Valkey** = optional/degradable cache; canonical state değildir.
- **SeaweedFS** = immutable/object bytes; semantic provenance ayrı tutulur.
- **Keycloak** = identity provider; backend authorization policy yine the Manufacturing Operations Platform semantics tarafından enforce edilir.
- **Oracle** = evaluator-only/hidden; operational decision services’ten structurally isolated.
- **WorldID** = formal operational-isolation primitive.
- **ACTUAL / OBSERVED / INFERRED / PREDICTED / PLANNED / COUNTERFACTUAL** state classes birbirine karıştırılmaz.

---

# 7. Doküman Kalite Standardı

Her downstream artifact şu profesyonellik seviyesini hedeflemelidir.

## 7.1 Engineering artifact, not essay

Belge yalnız prose açıklama olmamalıdır. Amacına göre aşağıdakilerin uygun kombinasyonunu içermelidir:

- stable IDs
- structured tables
- ownership matrices
- dependency mappings
- lifecycle/state definitions
- entry/exit gates
- requirement references
- failure semantics
- acceptance criteria
- milestone mappings
- diagrams
- risk/assumption annotations
- traceability references
- explicit rejected alternatives
- unresolved issue registers where legitimate

## 7.2 High information density

Genel/geçiş cümleleri minimumda tutulmalıdır.

Şu tür filler kabul edilmez:

> “Communication is important for team success.”

Bunun yerine:

> “A contract-breaking event-schema change is CR-2/CR-3 reviewed, must identify downstream consumers, update impacted TestIDs and invalidate stale integration evidence.”

gibi project-specific engineering content beklenir.

## 7.3 No fake completeness

Pre-implementation aşamasında henüz var olmayan şeyler varmış gibi yazılmamalıdır.

Örneğin:

- henüz gerçek TestRun yoksa PASS yazma,
- EvidenceBundle yoksa uydurma ID verme,
- implementation path kesin değilse sahte repo path oluşturma,
- benchmark yapılmadıysa observed metric üretme,
- restore drill yapılmadıysa “verified” yazma.

Doğru statüler:

- `PLANNED`
- `DEFINED`
- `TBD_BY_IMPLEMENTATION`
- `EVIDENCE_PENDING`
- `NOT_YET_EXECUTED`

gibi semantik olarak dürüst pre-implementation durumlarıdır.

## 7.4 No false approval

AI tarafından ilk oluşturulan downstream artifact varsayılan olarak:

> **Draft — Derived from Approved 01/02 Baseline**

statüsünde olmalıdır.

İnsan/team review olmadan:

> Approved

yazılmamalıdır.

01 içindeki kararların approved olması, üretilen projection’ın hatasız olduğu anlamına gelmez.

---

# 8. Stable Identity ve Cross-Reference Standardı

Dokümanlar mümkün olduğunca mevcut stable kimlikleri korur:

- `FR-*`
- `NFR-*`
- `ADR-*`
- `ARCH-*`
- `EVT-*`
- `CMD-*`
- `WF-*`
- `POL-*`
- `SCEN-*`
- `TEST-*`
- `BENCH-*`
- `RISK-*`
- `TD-*`
- `M0...M8`
- `CP-1...CP-3`

Yeni doküman-local kimlikler açık namespace kullanmalıdır.

Örnek:

- WBS → `WP-CORE-001`, `TASK-CORE-001`
- Dependency Graph → `DEP-001`
- Roadmap → `RM-ASR-001`
- DoR/DoD rule → `DOR-PR-001`, `DOD-WP-001`
- Change request → `CHG-*`
- Red-team finding → `RTF-*`

ID sistemi gereksiz yere binlerce mikro-ID üretmek için kullanılmamalıdır. Kimlik, gerçek traceability değeri olan bir artifact’a verilmelidir.

---

# 9. Cross-Document Duplication Politikası

Bir kararın bütün prose’unu başka bir dokümana kopyalamayın.

Örneğin 01’deki HITL kararının bütün bölümünü WBS’ye taşımak yanlış olur.

WBS şunu söylemelidir:

> `WP-AUTH-004 — Exact Revision-Bound Approval Enforcement`  
> Source: `FR-HITL-003..006`, architecture authority flow section.

Yani downstream artifact:

- karar metnini yeniden üretmez,
- kendi amacına gereken projection’ı oluşturur,
- canonical source’a referans verir.

Bu disiplin doküman drift’ini önler.

---

# 10. Önerilen Üretim Sırası

Kalan artifact’lar ideal olarak şu sırayla üretilmelidir:

> **03 RTM → 05 Dependency Graph → 04 WBS → 06A–D Roadmaps → 07 Milestone & Release Plan → 08 DoR/DoD → 09 Change Control → 10 RTR-0**

Sebep:

- RTM requirement/architecture coverage modelini netleştirir.
- Dependency Graph implementation ordering’i netleştirir.
- WBS dependency’leri work package’a dönüştürür.
- Roadmaps kişilere göre WBS projection’ı üretir.
- Milestone Plan bunları release gates altında konsolide eder.
- DoR/DoD execution-quality kurallarını tanımlar.
- Change Control freeze/change semantics’i operationalize eder.
- Pre-Implementation Red Team bütün planı son kez adversarial olarak inceler.

Birden fazla ekip üyesi paralel çalışacaksa, `03` ve `05` tamamlanmadan yazılan `04/06/07` dokümanları sonradan reconciliation pass almalıdır.

---

# 11. Dosya 03 — Requirements Traceability Matrix

## Canonical filename

`03_Requirements_Traceability_Matrix.md`

## Amaç

Toplam 306 normative requirement’ın:

> **Requirement → Source Decision → Architecture → Planned Implementation Surface → Verification Asset → Future Evidence → Claim**

zincirini yönetmek.

Bu belge ikinci requirement catalog değildir.

## Zorunlu baseline

- 186 FR
- 120 NFR
- toplam 306 unique normative requirement

AI önce bu sayıların kaynakta gerçekten doğru olduğunu machine-check etmelidir.

Count mismatch varsa belge üretimini sessizce sürdürmek yerine finding açmalıdır.

## İçerik modeli

Belge en az şu focused view’ları içermelidir:

### View A — Requirement Master Index

Her requirement için:

- RequirementID
- Class
- PrimaryOwner
- Source item/invariant
- Current trace state

### View B — Architecture Allocation

Requirement:

> hangi architecture capability/service/boundary tarafından realize edilecek?

### View C — Planned Implementation Coverage

Pre-implementation aşamasında:

- planned service/module/package/workflow/config surface
- kesin değilse `TBD_BY_IMPLEMENTATION`

Sahte path üretilmez.

### View D — Verification Design Coverage

Requirement:

- TestID family
- E2E
- benchmark
- resilience drill
- security negative suite
- inspection/review

hangi verification method ile doğrulanacak?

### View E — Evidence Coverage

Pre-implementation output’ta çoğu:

> `EVIDENCE_PENDING`

olacaktır.

Bu normaldir.

### View F — F0 Integrated Coverage

Her F0 capability:

- hangi real integrated scenario’da görünür?
- hangi closed-loop boundary’ye bağlanır?

### View G — NFR Measurement View

Her NFR için:

- class H0/A1/S2/C3
- metric
- threshold
- HardwareProfile/WorkloadProfile requirement
- planned measurement mechanism
- current evidence state

Observed value uydurulmaz.

### View H — Research Claim Trace

RQ/major future claims:

- planned BenchmarkDefinition
- requirement families
- future EvidenceBundle

ile bağlanır.

### View I — Orphans and Gaps

- orphan requirement
- orphan verification
- unresolved architecture allocation
- unresolved owner
- source conflict

ayrı gösterilir.

## PlanningState baseline

Pre-implementation planning projections only. CoverageState is independently governed by01 Item83: VERIFY_PLANNED in CoverageState requires an existing verification asset; a planned asset is insufficient. BLOCKED is an orthogonal flag, never a workflow state.

Pre-implementation için uygun planning states:

- `UNALLOCATED`
- `ALLOCATED`
- `IMPLEMENTATION_PLANNED`
- `VERIFY_PLANNED`
- `EVIDENCE_PENDING`
- `BLOCKED`
- `SUPERSEDED`

`VERIFIED` yalnız gerçek evidence varsa kullanılmalıdır.

## Machine-readable companion

Mümkünse aynı üretim içinde veya future tooling design olarak:

- trace edge schema
- CSV/JSON/YAML export concept
- generated-report concept

tanımlanmalıdır.

Ancak Markdown artifact’ın amacı tek dev 50-column table olmak değildir.

## Profesyonellik barı

Bu dosyada en kritik kalite göstergesi uzun prose değil:

> **coverage completeness + stable identities + no invented evidence + graph-quality trace semantics**

olacaktır.

## Beklenen ölçek

Yaklaşık:

> **12.000–22.000 satır**

normaldir.

Bu bir quota değildir. 306 requirement’ın gerçek mapping derinliği hedeflenir.

## Kaçınılacak hatalar

- 306 requirement metnini copy-paste etmek
- implementation yapılmış gibi davranmak
- evidence uydurmak
- “GS-01 verifies everything” demek
- tek green unit test’i F0 integration evidence saymak
- S2 MISS’i trace failure saymak
- ADR’yi verification saymak

---

# 12. Dosya 05 — Dependency Graph

## Canonical filename

`05_Dependency_Graph.md`

## Amaç

the Manufacturing Operations Platform’de hangi capability/artifact’ın hangisini:

- başlamadan önce,
- integration öncesi,
- milestone exit öncesi,
- research freeze öncesi

gerektirdiğini açık hale getirmek.

Bu doküman Gantt chart değildir.

## Canonical dependency semantics

Source baseline’da kabul edilmiş dependency dimensions korunmalıdır:

### Kind

- `CONTRACT`
- `CAPABILITY`
- `DATA`
- `RUNTIME`
- `EVIDENCE`
- `FREEZE`

### Strength

- `HARD`
- `SOFT`

### Blocking stage

- `START`
- `INTEGRATION`
- `MILESTONE_EXIT`
- `FREEZE`

### Readiness

- `DEFINED`
- `CONTRACT_READY`
- `SKELETON_READY`
- `COMPONENT_READY`
- `INTEGRATION_READY`
- `EVALUATION_READY`
- `FROZEN`

## Zorunlu içerik

### Dependency Registry

Her meaningful edge:

- dependency ID
- source capability/artifact
- target capability/artifact
- dependency type
- strength
- blocking stage
- readiness required
- owner
- fallback class where approved
- milestone relevance

### Platform dependency spine

Özellikle:

- PostgreSQL
- NATS
- SeaweedFS
- Keycloak
- Temporal
- Qdrant
- OTel/OpenObserve

dependency’leri final technology semantics’e göre modellenmelidir.

### Product integration dependencies

- Core contracts
- event spine
- Simulator
- Twin
- Vision observation
- AI
- Scheduler
- HITL
- Automation
- effect verification

### Research dependencies

- datasets/splits
- baselines
- experiment protocol
- model freeze
- release freeze
- benchmark
- AnalysisPackage
- claims

### Critical Paths

Aynen korunması gereken üç approved path:

#### CP-1 — Product Closed Loop

Platform → Core Contracts → Event Spine → Simulator/Core → Twin → Vision → AI → Scheduler → HITL → Automation → Core Effect → Twin Verification

#### CP-2 — Research Evidence

Operational System → Datasets / Scenarios → Baselines → Evaluation Harnesses → Calibration → Data/Scenario/Seed Freeze → Model/Policy Freeze → ExperimentProtocolFreeze → Stable Release / Environment → Final Benchmark → Statistical Analysis → ResearchClaims

#### CP-3 — Reproducibility

Git / CI → Integration Runtime → CD → Observability / Security → Backup / Recovery → Failure Validation → Experiment Runner → ReleaseManifest / HardwareProfile → Clean Reproduction → Benchmark Execution

### Dependency diagrams

Mermaid/Graphviz benzeri diagramlar kullanılabilir:

- product critical path
- research path
- platform path
- cross-role handoff graph

## Person vs capability dependency

Dependency:

> “Asrın bitirmeden Batu başlayamaz”

şeklinde yazılmamalıdır.

Doğru:

> `Core Snapshot Contract must be CONTRACT_READY before Scheduler Integration`.

Owner ayrı metadata’dır.

## Döngü analizi

Hard dependency cycle bulunursa:

- sessizce graph’a bırakılmamalı,
- `DEPENDENCY_CYCLE_FINDING`
- veya `RECONCILIATION_REQUIRED`

olarak işaretlenmelidir.

## Beklenen ölçek

Yaklaşık:

> **4.000–8.000 satır**

## Kaçınılacak hatalar

- kişi bazlı informal dependency
- her task’ı dependency node yapmak
- soft dependency’yi hard yapmak
- circular waiting planı
- stretch feature’i critical path’e sokmak
- RAG/advanced Vision olmadan M3 mümkün değilmiş gibi architecture’yı kilitlemek

---

# 13. Dosya 04 — Work Breakdown Structure

## Canonical filename

`04_Work_Breakdown_Structure.md`

## Amaç

306 requirement, architecture components ve dependency graph’ı gerçek uygulanabilir engineering work packages’a dönüştürmek.

WBS:

> “Backend yap / Vision yap / AI yap”

seviyesinde olamaz.

## WBS hierarchy

Önerilen decomposition:

> **Program → Capability Area → Work Package → Deliverable → Task / Verification Task**

Micro-task yönetim sistemi haline getirilmemelidir.

## Work Package schema

Her substantial WP mümkün olduğunca şunları içermelidir:

- WorkPackageID
- Title
- PrimaryOwner
- SupportingOwners
- ScopeClass
- Purpose
- Source RequirementIDs
- Architecture Components
- Inputs
- Required Contracts
- Deliverables
- Major Tasks
- Dependencies
- Target Milestone
- DoR references
- DoD references
- Verification strategy
- Integration checkpoint
- Risk refs
- Expected evidence artifact
- Cut/fallback semantics
- Status

## Scope decomposition

WBS en az şu capability families’i kapsamalıdır:

- Core/domain/backend
- Simulator
- Twin
- event/contracts
- object/artifact layer
- Vision
- Vision dataset/MLOps
- predictive ML
- RAG
- AI orchestrator/RCA
- Scheduler
- ScheduleValidator
- Automation/Temporal
- HITL/authority
- Command Center
- platform/runtime
- CI/CD
- observability
- security
- backup/DR
- testing
- performance/resilience
- research/evaluation
- benchmark
- documentation/thesis/demo/public release

## Work sizing

Source workflow doctrine korunmalıdır:

> coherent engineering slices approximately 0.5–3 focused days guideline

ancak WBS bütün sistemi bu mikro seviyeye zorla parçalamamalıdır.

Work Package daha büyük olabilir; iç task’lar bu slice discipline’i takip edebilir.

Saat bazlı sahte precision kullanılmamalıdır.

## Mandatory vs stretch

Her WP açıkça:

- F0
- F1
- R1
- R2
- S

scope class’ına veya bunlardan türetilmiş plan kategorisine bağlanmalıdır.

Stretch hiçbir zaman mandatory path’in içine gizlenmemelidir.

## Integration tasks

Her core capability için yalnız “component implementation” değil:

- contract implementation
- integration
- failure-path verification
- observability
- acceptance tests

ayrı work items olarak görünmelidir.

## Beklenen ölçek

Yaklaşık:

> **8.000–15.000 satır**

## Kaçınılacak hatalar

- dört kişiye eşit sayıda task vererek yapay denge
- requirement’sız work packages
- integration’ı son sprint’e bırakmak
- “testing”i tek final WP yapmak
- documentation’ı tek final görev yapmak
- hidden manual deployment tasks
- R2 research candidate’larını F1 gibi planlamak

---

# 14. Dosyalar 06A–06D — Team Engineering Roadmaps

Canonical files:

- `06A_Asrin_Engineering_Roadmap.md`
- `06B_Selman_Engineering_Roadmap.md`
- `06C_Batu_Engineering_Roadmap.md`
- `06D_Yavuz_Engineering_Roadmap.md`

Bu dört doküman aynı template’in isim değiştirilmiş kopyaları olmamalıdır.

Her roadmap kişinin gerçek capability ownership’inin execution projection’ıdır.

## Ortak roadmap structure

Her biri en az şu bölümleri içermelidir:

1. Role Mission
2. Removal-Test Statement
3. Owned Architecture Surfaces
4. Owned FR/NFR Families
5. Critical Contracts
6. Upstream Dependencies
7. Downstream Consumers
8. Milestone-by-Milestone Engineering Objectives
9. Work Package Mapping
10. Integration Checkpoints
11. Failure/Negative Tests
12. Research/Evaluation Responsibilities
13. Documentation/ADR Obligations
14. Risks and Bottlenecks
15. Cross-Review Responsibilities
16. Final Benchmark Contribution
17. Demo Contribution
18. Thesis/Portfolio Evidence
19. Definition of Final Role Completion

## 06A — Asrın roadmap depth

Özellikle kapsamalı:

- Core/domain model implementation
- business-state authority
- revisions/idempotency/outbox
- genealogy
- Twin semantics
- BFF/backend boundaries
- predictive M1/M2/M3
- RAG/Qdrant integration
- AI orchestrator/tooling
- RCA evidence model
- action proposal contract
- authority policy semantics
- AI evaluation/RQ1
- RQ3 shared authority research
- architecture/RTM semantic stewardship

M3 için Asrın’ın işi final advanced RAG’e bağımlı yapılmamalıdır. Typed tools/fixtures ile early integration yolu görünmelidir.

## 06B — Selman roadmap depth

Özellikle kapsamalı:

- inspection artifact pipeline
- dataset versioning/splits
- synthetic/public data strategy
- baseline Vision models
- classification
- localization
- segmentation
- anomaly detection
- OOD/UNKNOWN
- serialized component spatial analysis
- ModelPackage
- inference serving contract
- InspectionObservation contract
- Vision MLOps
- Vision evaluation
- RQ4 perception-to-operations
- Command Center Vision surfaces

Selman roadmap classification-only bir proje gibi görünmemelidir.

## 06C — Batu roadmap depth

Özellikle kapsamalı:

- deterministic DES kernel
- scenario/world lifecycle
- reentrant routing
- queues/failures/maintenance/rework
- snapshots/forks
- hidden Oracle mechanics
- scheduling baselines
- rolling-horizon scheduler
- OR-Tools CP-SAT
- ScheduleValidator
- dynamic rescheduling
- stability/churn
- counterfactual evaluation
- Temporal workflow
- ActionCatalog execution semantics
- effect verification/idempotency
- workflow crash/recovery
- RQ2 scheduling/recovery
- RQ3 shared governance

Batu roadmap Simulator/Scheduler/Automation’ı üç ayrı mini-project gibi değil, manufacturing control capability family olarak bağlamalıdır.

## 06D — Yavuz roadmap depth

Özellikle kapsamalı:

- monorepo platform baseline
- Docker/Compose profiles
- shared 16 GiB host
- self-hosted runner boundary
- GHCR/release artifacts
- CI T0–T3
- CD promotion/deployment
- EnvironmentManifest
- ReleaseManifest
- resource profiles
- Keycloak runtime
- OTel/Collector/OpenObserve
- platform security
- SBOM/scans/provenance
- backup/restore
- reboot/recovery
- benchmark resource isolation
- reproducibility tooling
- `mfgctl`
- final clean-host reproduction
- platform/reliability evidence

Yavuz yalnız “Docker ve CI yapan kişi” gibi görünmemelidir; final product operability/recovery/reproducibility capability’sinin owner’ıdır.

## Milestone semantics

Her roadmap M0–M8 ile align olmalıdır.

Particularly:

- M1 integrated foundation
- M2 operational spine
- M3 closed-loop alpha
- M4 mandatory feature complete
- M5 reliability/evaluation ready
- M6 freeze
- M7 benchmark
- M8 final release

## Portfolio discipline

Roadmap’te portfolio artifact’ları:

> yapılan gerçek work/evidence’in sonucu

olarak yer almalıdır.

CV için yapay feature eklenmemelidir.

## Beklenen ölçek

Her biri yaklaşık:

> **5.000–9.000 satır**

---

# 15. Dosya 07 — Milestone and Release Plan

## Canonical filename

`07_Milestone_and_Release_Plan.md`

## Amaç

Approved project schedule’i:

- milestone gates
- release semantics
- capability readiness
- freeze rules
- cut policy
- acceptance evidence

ile operational hale getirmek.

## Canonical planning baseline

Reference:

> **26 effective engineering weeks / 13 × 2-week sprint**

Bu bir planning baseline’dır. Gerçek akademik calendar değişirse week/sprint mapping rebaselined olabilir; milestone semantics korunmalıdır.

## Canonical milestones

- M0 — End S1/W2 — Engineering Foundation
- M1 — End S2/W4 — Integrated Spine
- M2 — End S4/W8 — Operational Manufacturing Alpha
- M3 — End S6/W12 — Closed-Loop Alpha
- M4 — End S8/W16 — Mandatory Core Feature Complete
- M5 — End S10/W20 — Reliability & Evaluation Ready
- M6 — End S11/W22 — Research Freeze
- M7 — End S12/W24 — Final Benchmark Complete
- M8 — End S13/W26 — Final Release Candidate

Bu semantics değiştirilmemelidir.

## Zorunlu içerik

### Milestone record

Her milestone:

- purpose
- entry criteria
- required capabilities
- required WPs
- required integration
- exit criteria
- required evidence
- blocking risks
- cut decision
- allowed/unallowed debt
- release artifact
- go/no-go condition

içermelidir.

### Sprint themes

Source baseline’daki S1–S13 progression korunmalıdır.

### Release semantics

- build once
- immutable artifacts
- Integration deployment
- promotion
- migration
- verify
- declare success
- known-good rollback where compatible

### Freeze semantics

M6 sonrası:

- behavior-affecting feature addition default olarak yasak
- benchmark/test tuning yasak
- fixes formal impact review ister
- evidence staleness/rerun scope değerlendirilir

### Cut policy

Schedule pressure altında cut order:

1. cosmetic
2. convenience
3. unpromoted R2
4. non-core breadth
5. semantics-preserving simplification

Safety/correctness/research integrity cut edilmez.

### Demo/benchmark separation

M7 benchmark completion ve M8 demo/release stabilization birbirine karıştırılmamalıdır.

## Fake calendar yasağı

Kaynakta gerçek semester/calendar dates yoksa AI tarih uydurmamalıdır.

Week/Sprint formatı kullanılır.

## Beklenen ölçek

Yaklaşık:

> **5.000–9.000 satır**

---

# 16. Dosya 08 — Definition of Ready and Done

## Canonical filename

`08_Definition_of_Ready_and_Done.md`

## Amaç

the Manufacturing Operations Platform’de:

> “Bu iş başlamaya hazır mı?”

ve

> “Bu iş gerçekten tamamlandı mı?”

sorularına work type ve maturity level bazında kesin cevap vermek.

## Temel doctrine

> **Merged ≠ Done**

> **Implemented ≠ Tested**

> **Tested ≠ Verified**

> **Demoed ≠ Accepted**

## DoR levels

En az aşağıdakiler için ayrı DoR düşünülmelidir:

- Task / Work Package
- PR
- Contract change
- Capability integration
- Dataset/model experiment
- Benchmark experiment
- Milestone
- Release candidate
- Demo
- Architecture change

## Generic DoR dimensions

Uygun olduğunda:

- purpose clear
- RequirementIDs known
- PrimaryOwner known
- dependency readiness satisfied
- contracts ready
- data rights/source ready
- acceptance criteria defined
- verification strategy defined
- environment available
- risk level classified
- architecture decision resolved
- no hidden blocker

## DoD levels

### PR DoD

Examples:

- coherent change
- tests
- static/type checks
- contract/schema update
- docs/trace impact
- risk review as applicable
- required reviewers
- no secret/security violation

### Work Package DoD

Examples:

- deliverable exists
- planned requirements implemented
- integration completed
- negative/failure paths tested
- observability present
- documentation updated
- RTM mapping advanced
- evidence state honest

### Capability DoD

Examples:

- real boundaries
- failure semantics
- service health
- required F0/F1 verification
- no core mocks in formal path
- role-owned evaluation

### Milestone DoD

Use Item 65 gate semantics.

### Final Release DoD

Must align with:

- 100% F0/F1 final disposition
- H0/A1 rules
- architecture valid
- benchmark sealed
- restore/reproduction
- documentation
- red-team defensibility

## Research DoD

A negative result can be DONE if:

- protocol valid
- run accounting complete
- evidence sealed
- analysis complete
- result honestly reported

“Hypothesis supported” is not DoD.

## Beklenen ölçek

Yaklaşık:

> **3.500–6.500 satır**

---

# 17. Dosya 09 — Change Control Process

## Canonical filename

`09_Change_Control_Process.md`

## Amaç

Approved 01/02 baseline’dan implementation sırasında sapılması gerektiğinde:

- neyin değişiklik sayıldığı,
- kimin review edeceği,
- hangi artifact’ların stale olacağı,
- hangi requirement/ADR/benchmark’ın güncelleneceği,
- hangi durumda freeze ihlali olduğu

konusunda lightweight fakat strict governance sağlamak.

## Temel doctrine

> **Change Is Allowed; Silent Change Is Not.**

## Change classes

Project-wide change taxonomy, Item 79’un benchmark change classes’iyle uyumlu olmalıdır.

Önerilen operational classes:

### C0 — Editorial / Nonsemantic

- typo
- formatting
- nonsemantic docs
- diagram clarity

No behavioral rerun by default.

### C1 — Compatible / Analysis or Implementation Correction

Behavioral semantics değişmeden:

- bug fix
- analysis correction
- derived implementation detail

Impact review gerekir.

### C2 — Behavior-Affecting Change

Examples:

- model
- prompt/tool behavior
- scheduler policy
- workflow semantics
- authority policy
- event contract behavior
- data processing

New release identity and affected evidence review/rerun required.

### C3 — Protocol / Scope / Final-Data / Fundamental Architecture Change

Examples:

- requirement semantics
- FINAL split/protocol
- research hypothesis
- canonical authority
- major architecture
- scope

Formal rebaseline required; new benchmark campaign potentially required.

## ChangeRequest schema

Her material change:

- ChangeID
- title
- trigger
- reason
- class
- affected FR/NFR
- affected architecture
- affected contracts
- affected WPs/roadmaps
- affected evidence
- evidence staleness
- security/authority impact
- owner
- reviewers
- decision
- rollout
- rollback
- required rerun
- documentation updates

içermelidir.

## Freeze rules

M6 sonrası behavior-affecting changes:

- default disallowed
- bug/security/integrity fix olabilir
- impact review zorunlu
- benchmark validity değerlendirilir
- no silent mixing of results across releases

## Requirement change

Requirement ID semantics:

- editorial clarification → same ID/revision
- materially different behavior → new ID/supersession preferred
- retired ID reused edilmez

## ADR relation

Material architecture changes:

> ADR/update/supersession

gerektirebilir.

Change Control ADR’nin yerine geçmez.

## Evidence staleness

Change process mutlaka şu soruyu sormalıdır:

> “Which previous evidence is no longer valid?”

Potential stale triggers:

- code
- model
- corpus
- dataset
- workflow
- policy
- contract
- hardware
- analysis package

## Emergency/hotfix

Hotfix:

- Git üzerinden
- auditable
- exact revision
- follow-up reconciliation

olmalıdır.

SSH manual patch accepted source-of-truth değildir.

## Beklenen ölçek

Yaklaşık:

> **3.000–6.000 satır**

---

# 18. Dosya 10 — Pre-Implementation Red-Team Review

## Canonical filename

`10_Pre_Implementation_Red_Team_Review.md`

## Çok önemli ayrım

Bu dosya:

> “Red team nasıl yapılır?”

diye yalnız policy anlatan belge değildir.

Item 85 zaten policy’yi tanımlar.

`10`:

> **01 + final 02 + 03 + 04 + 05 + 06A-D + 07 + 08 + 09 üzerinde gerçekten yürütülmüş RTR-0 adversarial review report**

olmalıdır.

Bu nedenle kalan artifact’ların en sonuncusudur.

## Verdict

Binary:

> `READY_TO_IMPLEMENT`

veya

> `NOT_READY_TO_IMPLEMENT`

Verdict önceden belirlenmez.

## Review baseline

Exact versions/hashes mümkün olduğunda belirtilmelidir.

## Twenty review categories

Item 85’te approved categories eksiksiz kullanılmalıdır:

- RT-01 Product Identity / Scope
- RT-02 Domain Validity
- RT-03 Requirements / Consistency
- RT-04 Architecture / Canonical Truth
- RT-05 Authority / HITL
- RT-06 Simulator / Twin / Counterfactual
- RT-07 Data / Licensing / Provenance
- RT-08 Vision / ML
- RT-09 AI / RAG / RCA
- RT-10 Scheduling
- RT-11 Automation
- RT-12 Security / Supply Chain
- RT-13 Platform / Resource Feasibility
- RT-14 Reliability / Backup / DR
- RT-15 Research / Statistics / Benchmark
- RT-16 Demo
- RT-17 Thesis / Claims
- RT-18 Open Source
- RT-19 Team / Ownership / Schedule
- RT-20 Documentation / Traceability / Change Control

## Finding schema

Her real finding:

- FindingID
- category
- attack question
- weakness
- counterexample
- affected requirements
- severity
- owner
- independent challenger
- required remediation
- evidence to close
- status
- residual limitation

ile kaydedilmelidir.

## Severity

- RT-BLOCKER
- RT-MAJOR
- RT-MINOR
- RT-OBSERVATION

## RTR-0 kill criteria

Source baseline’daki pre-implementation kill criteria özellikle kontrol edilmelidir:

- contradictory closed-loop identity
- role without indispensable capability
- hardware/cost infeasibility
- no rights-safe mandatory data path
- FINAL leakage
- ambiguous canonical authority
- protected-action bypass
- circular M3 dependency
- infeasible F0 scope
- unavailable mandatory paid/cloud dependency

## Real problems bulma zorunluluğu

AI’ın görevi belgeyi “green” göstermek değildir.

Gerçek issue bulursa:

> finding açmalıdır.

Unresolved Blocker/Major varsa:

> `NOT_READY_TO_IMPLEMENT`

vermelidir.

## Known high-risk attack themes

Özellikle:

- 16 GiB host feasibility
- Asrın/Batu workload bottleneck
- hidden mocks
- hidden manual steps
- source contradictions
- rights/licensing
- Oracle leakage
- authority bypass
- fake final evidence
- unfair benchmark
- overclaim
- technology zoo
- critical-path cycles
- documentation drift

aggressively incelenmelidir.

## Existing planning defect handling

Kaynak dosyalarda duplicate section, stale reference, inconsistent count vb. görülürse finding olarak kaydedilmelidir; sessizce unutulmamalıdır.

## Beklenen ölçek

Yaklaşık:

> **7.000–14.000 satır**

Ancak gerçek finding sayısına göre değişebilir.

Kalite metriği uzunluk değil:

> **adversarial depth + evidence + actionable findings + truthful verdict**

olmalıdır.

---

# 19. Ortak Section Template Standardı

Her downstream artifact, uygun olduğu ölçüde aşağıdaki high-level section pattern’i kullanabilir:

1. Document Status and Purpose
2. Canonical Sources
3. Scope and Non-Goals
4. Terminology / Stable IDs
5. Core Model
6. Detailed Registries / Tables
7. Lifecycle / State Semantics
8. Ownership
9. Dependencies / Interfaces
10. Failure / Exception Semantics
11. Verification / Acceptance
12. Milestone or Execution Mapping
13. Risks / Limitations
14. Rejected Alternatives
15. Open Issues / Change-Control Required
16. Success Criteria
17. Source Trace / References

Bu template zorunlu copy-paste değildir. Artifact’ın amacına göre adapte edilir.

---

# 20. Diagram Standardı

Diagram yalnız süs için kullanılmamalıdır.

İyi diagram:

- spesifik bir architectural/planning sorusuna cevap verir,
- text/table ile tutarlı olur,
- stable IDs kullanabilir,
- ownership veya dependency’yi görünür yapar.

Önerilen diagram türleri:

- dependency DAG
- milestone flow
- capability-to-owner map
- closed-loop path
- release lifecycle
- WBS hierarchy
- change lifecycle
- traceability graph
- red-team finding lifecycle

Diagram, normative prose’un yerine geçmez.

---

# 21. Table Standardı

Tablolar özellikle şu bilgilerde tercih edilir:

- requirement mappings
- owners
- milestones
- dependencies
- status
- gates
- DoR/DoD
- change impact
- red-team findings

Ancak 20+ kolonlu okunamaz tablolar üretmek yerine focused views kullanılmalıdır.

---

# 22. Language ve Terminology Standardı

Belge Türkçe/İngilizce karışık teknik vocabulary kullanabilir; 01/02’nin terminolojisi korunmalıdır.

Canonical terms değiştirilmemelidir:

- Core
- Simulator
- Twin
- Vision
- AI / RCA
- Scheduler
- ScheduleValidator
- Automation
- HITL
- Command Center
- WorldID
- ModelPackage
- ReleaseManifest
- EnvironmentManifest
- BenchmarkCampaign
- EvidenceBundle
- F0/F1/R1/R2/S
- H0/A1/S2/C3
- M0–M8
- CP-1/2/3

Aynı kavram farklı dosyada yeni isimle yeniden icat edilmemelidir.

---

# 23. Pre-Implementation Honesty Standardı

Kalan planning docs implementation başlamadan hazırlanıyorsa kesinlikle:

> **planlanan**

ile:

> **gerçekleşmiş**

ayrılmalıdır.

Yanlış:

> “TEST-AUTO-012 passes restart validation.”

Doğru:

> “TEST-AUTO-012 is the planned acceptance verification for restart/idempotency; evidence state: EVIDENCE_PENDING.”

Yanlış:

> “System restores in 3.2 hours.”

Doğru:

> “NFR-REC-004 target is ≤4 hours; planned verification: RESTORE-HOST-001; observed value not yet available.”

Bu ayrım bütün artifact setinin credibility’si için kritiktir.

---

# 24. Requirement ve Evidence Count Discipline

AI her üretimde programatik olarak mümkün olduğunca şunları kontrol etmelidir:

- FR count
- NFR count
- unique IDs
- duplicated IDs
- missing milestone references
- invalid role owner
- stale technology names
- forbidden “production-grade” claims
- contradictory scope classes
- unresolved placeholders
- broken cross references

Machine-check mümkün değilse manual audit section eklenmelidir.

---

# 25. Quality Review Checklist

Bir artifact teslim edilmeden önce AI şu sorulara cevap vermelidir:

### Source Fidelity

- 01/02’ye aykırı yeni karar var mı?
- latest approved technology/authority kullanıldı mı?
- role ownership değişti mi?

### Artifact Purpose

- bu dosya kendi mühendislik sorusuna cevap veriyor mu?
- yoksa 01/02 copy-paste’i mi?

### Completeness

- ilgili F0/F1/R1 kapsamı eksiksiz mi?
- failure/negative paths var mı?
- integration obligations var mı?

### Honesty

- implementation/evidence uyduruldu mu?
- planned vs verified ayrımı doğru mu?
- real-manufacturing-facility overclaim var mı?

### Traceability

- stable IDs korunuyor mu?
- source decisions bulunabilir mi?
- dependencies ve owners explicit mi?

### Professionalism

- filler düşük mü?
- tables/diagrams meaningful mi?
- contradictions görünür mü?
- rejected alternatives veya constraints açıklanmış mı?
- artifact implementasyonda gerçekten kullanılabilir mi?

---

# 26. Yasaklanan AI Davranışları

Kalan belgeleri üreten AI aşağıdakileri yapmamalıdır:

- 01’i “özetleyerek” kısa generic belge üretmek
- 02’yi yeniden yazmak
- tech stack değiştirmek
- cloud/Kubernetes eklemek
- microservice sayısını keyfi artırmak
- role ownership değiştirmek
- fake TestID result üretmek
- fake evidence üretmek
- fake benchmark result üretmek
- fake calendar date üretmek
- gerçek manufacturing facility iddiası eklemek
- consultant-style filler doldurmak
- open-source rights konusunda varsayım yapmak
- requirement’ı “nice to have” diye düşürmek
- stretch’i mandatory yapmak
- authority bypass önermek
- demo convenience için auth/HITL kaldırmak
- “future work” bahanesiyle F0/F1 eksik bırakmak
- unresolved contradiction’ı sessizce çözmek

---

# 27. Hedef Artifact Boyutları

Line count bir kalite metriği değildir; yalnız expected depth indicator’dır.

| Artifact | Healthy Expected Range |
|---|---:|
| 03 Requirements Traceability Matrix | 12k–22k |
| 05 Dependency Graph | 4k–8k |
| 04 Work Breakdown Structure | 8k–15k |
| 06A Asrın Roadmap | 5k–9k |
| 06B Selman Roadmap | 5k–9k |
| 06C Batu Roadmap | 5k–9k |
| 06D Yavuz Roadmap | 5k–9k |
| 07 Milestone & Release Plan | 5k–9k |
| 08 DoR/DoD | 3.5k–6.5k |
| 09 Change Control | 3k–6k |
| 10 Pre-Implementation Red-Team Review | 7k–14k |

Belgeyi aralığa sokmak için yapay padding veya gereksiz tekrar yapılmamalıdır.

---

# 28. Teammate / AI Handoff Prompt Template

Her ekip üyesi kendi AI aracına şu generic instruction’ı hedef dosya adıyla verebilir:

> `01_Master_Project_Specification.md`, `02_System_Architecture_Specification.md` ve `00_Downstream_Artifact_Production_Guide.md` dosyalarını canonical source set olarak kullan. Hedef artifact: `<TARGET_FILENAME>`.
>
> Önce ilgili approved decisions, requirements, architecture boundaries, ownership, dependencies, milestones ve invariants’ı kaynaklardan çıkar. Hedef dokümanı kaynakların özeti olarak değil, Production Guide’da tanımlanan artifact-specific engineering projection olarak üret.
>
> 01 normative product/spec truth’tur; 02 current architecture truth’tur. Yeni product requirement, architecture authority, technology veya scope kararı icat etme. Derived planning detail gerekirse açık biçimde derived olarak tut. Kaynak çatışması bulursan sessizce çözme; `SOURCE_CONFLICT` / `RECONCILIATION_REQUIRED` olarak göster.
>
> Stable IDs, role ownership, M0–M8 milestones, F0/F1/R1 scope semantics, H0/A1/S2/C3 NFR semantics, WorldID/Oracle/authority boundaries ve final technology stack’i değiştirme.
>
> Pre-implementation artifact üretiyorsan henüz gerçekleşmemiş implementation, test, benchmark veya evidence sonucu uydurma. Planned/Defined/Evidence Pending statülerini doğru kullan.
>
> Artifact’ın sonunda source-fidelity ve internal-consistency audit yap. Copy-paste repetition, stale technology decision, contradictory authority, broken reference, fake evidence, unsupported claim veya unfinished authoring note bırakma.
>
> Çıktı `Draft — Derived from Approved 01/02 Baseline` statüsünde, implementation-usable, high-detail ve professional engineering artifact olmalı.

---

# 29. Team Integration Rule

Farklı AI araçları farklı dokümanları hazırlayacağı için final integration pass zorunludur.

Bütün artifact’lar tamamlandıktan sonra en az şu cross-check yapılmalıdır:

- 03 requirement ownership ↔ 06 roadmaps
- 05 dependencies ↔ 04 WBS
- 04 WBS ↔ 07 milestones
- 06 roadmaps ↔ 04/05/07
- 07 milestones ↔ 08 DoR/DoD
- 08 DoR/DoD ↔ 09 change control
- 03/04/05/06/07/08/09 ↔ 10 RTR-0
- bütün dosyalar ↔ 01 scope/requirements
- bütün architecture references ↔ final 02

Bir AI’ın ürettiği local consistency, multi-document consistency garantisi değildir.

---

# 30. Final Artifact Set İçin Acceptance Bar

Bu artifact set ancak aşağıdaki durumda başarılı sayılmalıdır:

1. 01/02 normative baseline korunmuştur.
2. Kalan dokümanlar birbirinin kopyası değildir.
3. Her artifact’ın bağımsız execution value’su vardır.
4. Stable IDs korunmuştur.
5. 306 requirement’ın planning trace’i kaybolmamıştır.
6. Dört role ait removal-test korunmuştur.
7. CP-1/CP-2/CP-3 plansal olarak kapanmaktadır.
8. M0–M8 milestone semantics aynıdır.
9. F0/F1/R1/R2/S separation korunmuştur.
10. H0/A1/S2/C3 quality semantics korunmuştur.
11. Final technology stack drift etmemiştir.
12. WorldID/Oracle/authority boundaries drift etmemiştir.
13. Hidden cloud/Kubernetes requirement eklenmemiştir.
14. Pre-implementation evidence uydurulmamıştır.
15. WBS gerçek work decomposition’dır.
16. Dependency Graph gerçek blocking semantics içerir.
17. Roadmaps gerçekten kişiye özeldir.
18. Milestone plan gerçek gates içerir.
19. DoR/DoD “merged = done” anlayışını reddeder.
20. Change Control freeze/evidence staleness semantics içerir.
21. RTR-0 gerçek adversarial review’dür.
22. Public/research claims evidence seviyesini aşmaz.
23. Cross-document contradictions audit edilmiştir.
24. Artifact set implementasyona başlanırken gerçek bir engineering operating system gibi kullanılabilir.

---

# Nihai İlke

Bu doküman setinin amacı büyük görünmek değildir.

Amaç:

> **85 approved planning decisions’i, 306 normative requirement’ı, dört bağımsız capability ownership’ini ve the Manufacturing Operations Platform closed-loop architecture’sını implementation boyunca kaybetmeden; kim ne yapacak, hangi sırada yapacak, neye bağlı, ne zaman hazır, nasıl doğrulanacak, değişiklik nasıl yönetilecek ve implementation başlamadan önce hangi varsayımların hâlâ savunulamaz olduğu konusunda executable-level clarity sağlamaktır.**

Kalite ölçütü doküman uzunluğu değil:

> **source fidelity + engineering specificity + traceability + implementation utility + evidence honesty + cross-document consistency**

olacaktır.


## Final human reconciliation binding — 2026-10-13

01 §Final Human Reconciliation and02 §Final human reconciliation govern this projection. Vision/NDT publishes immutable InspectionObservation (existing EVT-InspectionObservation-v1); Core normalizes separate InspectionResult (existing IC-VIS-002) and owns canonical manufacturing/quality state. PlaceLotOnHold / CMD-PlaceLotOnHold-v1 is the single hold-placement command; ApplyMaterialHold is deprecated terminology, never a second contract. Other protected identities follow the01 action table, with exact approval/revision/freshness/idempotency binding. Simulator/Oracle, Twin/Qdrant projections, AI READ/SIMULATE/PROPOSE, Scheduler candidates, HITL, identity and UI boundaries remain unchanged.

ARCH-AUTO-WORKFLOW (durable Automation/Temporal layer) coordinates GS-01/E2E across Inspection/NDT→Core quality→RCA→recovery→HITL→governed Core commands→verified effect→Twin/Audit. It does not acquire Core authority. MC-2 accountable owner is Asrın Dündar; contributing WP owners remain73/17/32/57. The primary shared-host HardwareProfile and accepted LaneA/B/C portfolio are pinned in01; acquisition/rights/source fields not locally verified are NEEDS_SOURCE_VERIFICATION, not invented facts or performance results. Real/public held-out evaluation and source-specific limitations remain mandatory where claimed.

HARD/SOFT refer to declared work/readiness consumers, not automatic runtime/deployment/import relations. Non-CONTRACT F1 entries DEP-025/045/058/076/094 have no fixture fallback: real producer readiness at the declared stage is required, while development stubs are not satisfaction evidence. DN-VIS-MODELS now declares INTEGRATION_READY for DEP-060/194; operational serving must load promoted required-mode artifacts with provenance. Source-supported deadlines and per-consumer scope are defined in05, without shifting canonical ownership or schedules.

GAP-RTM-004/005 remain ACCEPTED_WITH_RATIONALE for this pre-implementation baseline: missing canonical record metadata is not fabricated. FR-GOV-001/004 and the relevant NFR owners must supply/review actual fields and measurement definitions before their declared gates; projectctl retains nulls/warnings and never grants READY/VERIFIED from planned prose. Owner trace confirmation GAP-RTM-006 and final schema/version/card specifics remain ordinary implementation/review prerequisites, not unresolved choices among the eight approved policy groups.
