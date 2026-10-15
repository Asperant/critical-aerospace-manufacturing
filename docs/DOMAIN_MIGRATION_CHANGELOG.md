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


## 15 October 2026 — Final owner development review policy (CHG-017)

DEV-REVIEW-2026-10-15 supersedes the historical 14 October normal-risk one-approval rule: **normal-risk required approvals = 0; actual high-risk required approvals = 2**. Optional review remains available; unresolved CHANGES_REQUESTED blocks merge. CI and owner overrides never replace either high-risk approval. Canonical 01/08/09, static companion, change records, helper and tests move together. Product HITL, requirements/IDs/counts, WP ownership/scope, scheduling and actual acceptance/freeze obligations do not change. Historical decisions and reviews remain attributed to their original dates/revisions.


## Final advisory development review policy — CHG-018, 15 October 2026

Policy ID: `DEV-REVIEW-2026-10-15-FINAL`. CHG-018 explicitly supersedes CHG-017; CHG-017 and its intermediate 0/2 decision remain historical, unchanged. Active companion: `09_change/development_review_policy.json`; previous companion archived under `09_change/history/CHG-017-development_review_policy.json`.

| Policy ID | Scope | Required human approvals |
|---|---|---|
| DEV-REVIEW-2026-10-15-FINAL | ALL_DEVELOPMENT | 0 |

Every repository development PR, CR-0 through CR-4, normal/high risk, security/auth, protected-action-authority code, destructive migration, secrets/infrastructure, authority boundaries, platform, tooling, docs, product and research implementation has zero required human approvals. Review, requests, comments, suggestions and security advice are ADVISORY. No independent/qualified reviewer quota, self-approval rule, owner override, current-head approval or stale-approval mechanism governs development workflow. GitHub APPROVED, CHANGES_REQUESTED, COMMENTED and DISMISSED are not workflow, merge or DONE gates, and reviewer presence/absence never blocks progress. CODEOWNERS and supporting-reviewer metadata are advisory routing/domain context only.

IN_REVIEW means a real non-draft technically reviewable PR, not waiting for a human. MERGE_READY requires correct canonical WP/approved control scope and branch/PR/head binding, required actual CI/tests/canonical validation, mergeability/no conflict against current main, no out-of-scope changes, applicable DoR-PR/PR DoD, trace/evidence and applicable security/secret/static checks, and no real BLOCKED condition. Actual technical/canonical failures or ambiguity fail closed; a review state alone neither proves nor disproves these facts. Material revisions re-run technical checks/evidence. Rework follows actual revision/technical evidence, not approval invalidation.

MERGED requires an actual GitHub merge. VALIDATING requires actual post-merge validation started. DONE requires all applicable DoD, trace/evidence and actual successful post-merge validation; accountable owner assessment and real artifacts remain required, another person's review/confirmation does not. Development peer/methodology review is advisory even for closure; real protocol, scientific reproducibility, measured acceptance and product-authority evidence remain required. Merged != Done; Implemented != Tested; Tested != Verified; Demoed != Accepted.

This changes ONLY development/GitHub/repository governance. Product HITL, protected-action approval, AuthorityPolicy, authenticated approvers, runtime self-approval prohibition, exact proposal/plan binding and execution authorization are unchanged. Project-owner scope/cancellation decisions and real product acceptance artifacts are not GitHub review approvals and are not fabricated or waived. No Plane test mutation, merge, commit or push is authorized in this pass. Existing historical approvals remain history, never requirements for a current transition.
