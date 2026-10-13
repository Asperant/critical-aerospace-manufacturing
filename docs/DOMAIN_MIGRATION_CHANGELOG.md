# Domain migration changelog — source reconstruction

## Record scope and authority

CTRL-DOC-006 / CHG-013 reconstructs the migration description from the current01 migration notice,02 Known Source Defect/R-001 and repository history. The original canonical baseline is Git commit `fb294d9` (`chore: establish canonical project baseline`); the completed setup parent is `644e380`. No prior semiconductor source snapshot or historical approval record is reconstructed from these commits. Existing source notices claim an approved migration; this file records what those sources say, not an invented approval date/reviewer. The current human reconciliation policy is identified by the request SHA256 in `evidence/documentation-reconciliation/inventory.json`.

## Current product-name reconciliation

CTRL-DOC-002 replaces obsolete final `Autonomous Critical-Component Manufacturing Facility Operating System` branding with **Intelligent Manufacturing Operations Platform for Critical Aerospace Components**. Turkish name: **Kritik Havacılık ve Uzay Komponentleri için Akıllı Üretim Operasyon Platformu**. Governed autonomy remains explicitly human/policy bounded. Research/simulation scope is preserved; this is not real CNC/PLC or autonomous factory control, a certified safety/QMS/aerospace process, or a commercial MES/QMS/ERP replacement.

## Project-domain semantic mappings

These mappings describe the intended project domain only. They never relabel external datasets or establish command/schema aliases.

| Legacy project concept | Preserved/new-domain concept |
|---|---|
| Fab | Critical-component manufacturing facility/environment |
| Wafer | Serialized Critical Component / SerializedComponent |
| Lot | Production Batch / Lot |
| Wafer Genealogy | Component / Manufacturing Genealogy |
| Process Route | Manufacturing Route / Process Plan |
| Lithography / Etch | CNC / precision machining |
| Deposition | Special process / heat treatment / surface process |
| Recipe | NC Program + Process Recipe / ParameterSet |
| ProcessExecution | Manufacturing Operation Execution |
| Wafer Inspection | Component Visual/NDT Inspection |
| Wafer Map | Component Inspection Map / Surface/NDT Defect Map |
| Yield | FPY / conformance / scrap-rework rate |
| Quality Hold | Canonically governed quality/material hold semantics |

Reentrant rough/multi-axis CNC→metrology→heat/special process→finish CNC→Vision/NDT→rework/reinspection→final acceptance is preserved. ProductionOrder→ProductionBatch/Lot→SerializedComponent, immutable identity, genealogy, split/merge conservation, scrap history, MaterialHold and ReworkDirective remain distinct.

## Preserved architecture and scientific boundaries

Core owns canonical manufacturing/business state; Simulator owns simulated physical execution and hidden Oracle; Twin and Qdrant are rebuildable projections; Vision owns perception observations; AI READ/SIMULATE/PROPOSE; Scheduler candidates; HITL authenticated approval; Automation approved coordination; Keycloak authentication; UI no direct DB/broker mutation. Exact proposal/plan binding, freshness/expiry, no self-approval and effect verification remain mandatory. Oracle labels never become runtime inputs. No technology/infrastructure, RQ1–RQ4, requirement/classification, ownership, dependency count or milestone is changed.

Semiconductor-fab process examples are not the current aerospace process model. Wafer die/photomask meanings are not component inspection/segmentation-mask meanings. Proprietary-factory realism and certified-process claims are excluded.

## Dataset-domain correction

CTRL-DOC-003 / CHG-002 corrects false source-domain relabeling: SECOM remains semiconductor process data; WM-811K and MixedWM38 remain semiconductor wafer-map data. Retention is optional legacy/cross-domain methodological comparison only, outside the primary aerospace evaluation portfolio. Original rights/redistribution gates are preserved. MVTec AD/AD2 remain auxiliary industrial anomaly data. Lane A real/public experimental machining/health/inspection/NDT, Lane B literature/process assumptions and Lane C explicitly simulated operational scenarios remain distinct. Candidate directions are not frozen licensed DatasetVersions or accepted results.

## Intentionally not mechanically renamed

`WL-INV-*`, `FAB-01…FAB-NN`, `TEST-PLAT-FABCTL` remain stable legacy IDs. Historical findings, external dataset names, bibliographic titles, comparison sections and migration mappings retain their actual meaning. Segmentation mask is not a photomask; a component inspection map is not a semiconductor wafer map. Item43's identical copies remain one logical item under02 R-001.

The01 notice describes docs-only deployable mappings `fab-core`→`manufacturing-core`, `fab-simulator`→`manufacturing-simulator`, `fab-bff`→`operations-bff`, `fabctl`→`mfgctl`. Repository bootstrap currently implements projectctl and management support, not those product deployables. A current code/config scan is recorded in the final audit; it cannot prove deployment of absent product services.

## Historical pending semantics and acceptance — superseded by the final decisions

InspectionObservation/InspectionResult transformation/schema acceptance, protected hold/dispatch aliases, new ARCH allocations, graph readiness/fallback/precision/need-by decisions, MC-2 ownership, hardware pinning, E2E coordinator and final dataset selection remain pending where no unique approved decision exists. Current CHG peer reviews remain outstanding. Documentation repair is not executed verification, release acceptance, or a READY/DONE transition.


## Final approved semantic reconciliation — 2026-10-13

The eight final human decisions are DECIDED and applied normatively in01/02 and the downstream03–08 projections. InspectionObservation and InspectionResult remain distinct; IC-VIS-002 and EVT-InspectionObservation-v1 are retained. CMD-PlaceLotOnHold-v1 is the canonical hold identity, while ApplyMaterialHold is deprecated rather than another contract; ActivateScheduleCommand/RequestMaintenance likewise resolve to existing canonical actions. No lifecycle-as-hold or route-pointer-as-rework substitution.

Existing-service component allocations are appended in02 (ML/MLOps, experiment/evidence, scheduling evaluation, Vision data) and traced in03; no new infrastructure. DN-VIS-MODELS gains a genuine operational-serving INTEGRATION_READY predicate for DEP-060/194; five non-CONTRACT F1 fallbacks are removed in table/YAML/aggregate mirrors. Topology remains100nodes/217edges/208HARD/9SOFT/0HARDcycles. Consumer field-level unknowns and raw deadline windows remain diagnostic-visible with explicit per-consumer/§18 interpretation, never automatic authorization.

MC-2 accountable owner is Asrın; WP owners73/17/32/57 unchanged. Shared-host hardware is pinned without performance claims or a mandatory secondaryNVMe. Durable Automation/Temporal coordinates GS-01 with Core authority intact. The accepted real/public+literature+simulator portfolio is explicit; semiconductor references remain optional legacy/cross-domain only and unverified source metadata is NEEDS_SOURCE_VERIFICATION.

The DoR mapping is lossless but may be many-to-one (DOR-WP-03/04→DOR-TASK-04). WP-X-001 remains an optional unscheduled boundary-maintenance documentation/claim guardrail, not implementation of an excluded product capability. All306requirement IDs and179WP IDs remain stable. Item43 duplicate copies remain one logical item under02R-001; they are not competing contracts.

This is docs-only branch reconciliation pending independent qualified change review and integration. No Plane/setup/product state mutation, scientific result, dataset acquisition or runtime verification is claimed. Existing setup evidence remains bound to its original source hashes and observed events; changed canonical source hashes do not rewrite that history.


##14 October2026 — owner-approved development review policy migration

Former REVIEW-INV-07 blanket two-review and owner-pair rules replaced by normal-risk one independent approval / actual high-risk two. High-risk triggers: auth/authorization, protected-action authority, destructive migration, security-sensitive infra/secrets and major authority-boundary changes. Batuhan is not a mandatory reviewer for every PR. Self-approval remains prohibited. No product HITL change. CHG-002 retains research scrutiny with one qualified reviewer for this normal-risk documentation scope; CHG-010 and other historical blanket CR-3 documentation classifications become CR-2 with original values recorded. Owner expressly authorizes PR#4 policy commit and closure without a new review request; historical approval is never relabeled current-head approval. Counts, IDs, scheduling and ownership unchanged.
