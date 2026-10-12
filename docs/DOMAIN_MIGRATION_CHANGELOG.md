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

## Pending semantics and acceptance

InspectionObservation/InspectionResult transformation/schema acceptance, protected hold/dispatch aliases, new ARCH allocations, graph readiness/fallback/precision/need-by decisions, MC-2 ownership, hardware pinning, E2E coordinator and final dataset selection remain pending where no unique approved decision exists. Current CHG peer reviews remain outstanding. Documentation repair is not executed verification, release acceptance, or a READY/DONE transition.
