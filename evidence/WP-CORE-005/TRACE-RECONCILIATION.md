# WP-CORE-005 — partial implementation trace reconciliation

Assessor: Asrın Dündar's developer agent, 2026-10-23.
Assessed head: `41f90e000bbfa375082e173fa92e420ee3e443c8`.
Fresh live queue/context confirmed Asrın's WP-CORE-005 IN_PROGRESS; Plane unchanged.
This is an engineering artifact inventory, not a new specification, execution
queue or sealed acceptance EvidenceBundle. Product behavior is unchanged.

## Canonical scope and classification limits

01 FR-CORE-014/015 (lines 169862–169863) require accepted state-change emission
and atomic mutation/outgoing persistence. 04 WP-CORE-005 requires schemas per
namespace, atomic writes, relay/retry, real PostgreSQL crash consistency and
outbox-delay instrumentation. 03 FR-CORE-014's EXPOSED_BY names Production,
Equipment, Quality and Schedule. Equipment therefore belongs to full WP coverage;
it is not an additional START gate or permission to invent an accepted transition.

02 Event Catalog (lines 1214–1228) explicitly lists representative families,
not an exhaustive frozen list of accepted Core transitions. Producer authority
must still follow 02 Data/Semantic Authority Map and Service Catalog. These
tables reconcile every representative family/known Core output in that exact
inventory; they do not claim all global events belong to CORE-005.

The four classification labels apply to bounded artifacts, not whole-requirement
acceptance. Existing artifacts below were IMPLEMENTED_NOT_TRACED in FR-CORE-014/015's
REALIZED_BY records before this change; they are now IMPLEMENTED_AND_TRACED for
their stated partial scope. No full requirement has become IMPLEMENTED or VERIFIED.

## Existing Core fact coverage

| Canonical fact / namespace | Current artifact classification | Exact implemented scope / unresolved boundary |
|---|---|---|
| LotReleased / production | IMPLEMENTED_AND_TRACED | LotReleasedV1, lot_id payload, fixture and schema tests; ReleaseLot acceptance/mutation/emission remains UNBOUND_EXTERNAL_CONTRACT |
| MaterialHoldApplied / production | IMPLEMENTED_AND_TRACED | MaterialHoldAppliedV1, material_hold_id payload, fixture and schema tests; hold command/target/effect binding remains UNBOUND_EXTERNAL_CONTRACT |
| QualityExcursionConfirmed / quality | IMPLEMENTED_AND_TRACED | QualityExcursionConfirmedV1, quality_excursion_id payload, fixture and schema tests; quality-governance acceptance/emission remains UNBOUND_EXTERNAL_CONTRACT |
| ScheduleActivated / scheduling | IMPLEMENTED_AND_TRACED | ScheduleActivatedV1, schedule_id payload, fixture and schema tests; governed activation/active-version binding remains UNBOUND_EXTERNAL_CONTRACT |
| Outbox typed record, table, insert/read | IMPLEMENTED_AND_TRACED | FR-CORE-015 partial storage support only; not a domain mutation transaction or relay |
| Pending-age diagnostic | IMPLEMENTED_AND_TRACED | Supporting WP instrumentation; count/oldest age only, not NFR-PERF-003 publication-delay acceptance |

All four existing facts are explicitly named as Core outputs in 02 line 3883.
The combined domain-event schema is a closed four-member union. There is no
equipment.* member, fixture or corresponding schema test in the assessed source.

## Remaining representative inventory and authority bindings

| Canonical family / representative accepted-fact candidates | Classification for additional CORE-005 coverage | Producer/binding boundary |
|---|---|---|
| ProductionOrderCreated/Released; LotCreated/Queued/Dispatched/Split/Merged/Completed/Scrapped; ComponentCreated/Scrapped/FabricationCompleted; MaterialHeld/Released; ReworkRequested/Completed | UNBOUND_EXTERNAL_CONTRACT | Core owns business lifecycle/material governance, but the representative names do not freeze accepted handlers, exact payloads or revision bindings. MaterialHeld/Released are not silently aliased to existing MaterialHoldApplied or ReleaseLot. |
| ProcessingStarted/Completed/Failed/Aborted | UNBOUND_EXTERNAL_CONTRACT | Simulator owns physical execution; Core may record derived business facts. No independent Core physical producer or new event alias is authorized. |
| MachineIsolated | UNBOUND_EXTERNAL_CONTRACT | Event name and machine_id waiting example are explicit (01 line 20832), but 02 Sequence A line 9072 shows Simulator -> Core canonical MachineIsolated, whereas Sequence E line 9163 shows Core -> broker MachineIsolated. Physical effect vs governance publication/canonical producer/payload binding must be made exact; do not invent two producers or resolve the flows in this trace change. |
| MachineReserved/BecameIdle/SetupStarted/SetupCompleted/Failed/Recovered; EquipmentHealthAssessmentUpdated; MaintenanceRequested/Scheduled/Started/Completed | UNBOUND_EXTERNAL_CONTRACT | Equipment family mixes physical Simulator state, assessments and Core business maintenance governance. Names/family membership alone do not authorize Core payloads for all of them. No raw hidden health may become an operational event. |
| InspectionRequested/Started/Completed; DefectDetected/DefectPatternDetected/DefectClusterUpdated; ExcursionSuspected/Confirmed/Rejected/Resolved; QualityDispositionAssigned | UNBOUND_EXTERNAL_CONTRACT | Vision observations and Core quality governance are distinct. Existing QualityExcursionConfirmed is traced above; other names are not automatically aliases or Core-produced facts. Exact normalized-result/transition contracts remain necessary. |
| SchedulingRequested/Started/Completed/Failed; ScheduleProposed/Degraded/Invalidated/Superseded; DispatchDecisionCreated/DispatchRejected | UNBOUND_EXTERNAL_CONTRACT | Scheduler proposes/validates plans; Core owns the activated business fact, with Automation invoking governed actions. Existing ScheduleActivated is traced above; no other Scheduler fact is re-owned here. |
| Automation/recovery, intelligence, simulation families in 02 table | UNBOUND_EXTERNAL_CONTRACT for any proposed Core publication | Workflow/approval/recovery, AI/ML and Simulator authorities retain their facts. Their representative names are not missing Core-owned implementations. Any Core integration requires an explicit consumer/publication binding. |

MISSING_BUT_OWNER_EXECUTABLE product payload additions: **none established by the
exact inspected canonical inventories**. Equipment coverage is genuinely missing
for full WP completion, but no complete unambiguous additional equipment
payload/producer binding was established. This corrects the earlier suggestion
that namespace absence alone established immediately implementable product work.
The MachineIsolated flow ambiguity stops only that affected schema selection;
it does not invalidate the four existing Core-output schema bindings.

## Immutable engineering artifact/test/evidence bindings

Paths below are relative to the repository root, resolved at the listed full
commit. Suite counts are historical executed results from the linked same-revision
evidence, not new runs or per-requirement acceptance counts.

| Requirement / bounded contribution | Commit | Product / contract artifacts | Actual tests and engineering evidence |
|---|---|---|---|
| FR-CORE-014 partial four-fact schemas | `3eb9a96fe874446fad60e8673e2b027524b700e2` | `services/manufacturing-core/src/manufacturing_core/events_v1.py`; `services/manufacturing-core/contracts/v1/domain-event.schema.json`; `domain-event.LotReleased.json`, `domain-event.MaterialHoldApplied.json`, `domain-event.QualityExcursionConfirmed.json`, `domain-event.ScheduleActivated.json` in that contract directory; `domain-events.md` there | `services/manufacturing-core/tests/test_event_contract.py` (TEST-EVT-SCHEMA partial); `test_query_contract.py` in the same tests directory was regression coverage, not extra event acceptance. `evidence/WP-CORE-005/SLICE1.md` records the combined 100 passed result and its initial failures. |
| FR-CORE-015 partial outbox storage | `c2a67aef020c82255c59b4857b5637c8a754f5d5` | `services/manufacturing-core/src/manufacturing_core/outbox.py`; `migrations/0002_outbox.sql` and `migrate.py` under that source directory | `services/manufacturing-core/tests/persistence/test_outbox.py`, `test_persistence.py` there; `evidence/WP-CORE-005/OUTBOX-PRIMITIVES.md` records combined 49 real PostgreSQL tests. Only storage/transaction ownership/constraints/migration support; TEST-CORE-OUTBOX full atomic/crash family remains unexecuted. |
| WP instrumentation supporting future NFR-PERF-003 measurement | `41f90e000bbfa375082e173fa92e420ee3e443c8` | `services/manufacturing-core/src/manufacturing_core/observability.py` (`OutboxPendingAge`, `outbox_pending_age`) | `services/manufacturing-core/tests/persistence/test_outbox_age.py`; existing observability regression paths and 16 combined passing cases documented in `evidence/WP-CORE-005/SLICE4.md`. No broker percentile measurement. |

Exact testcase names are in these immutable files; no future numeric TestID,
RunID, EvidenceID or CURRENT applicability is fabricated. The conceptual
03_traceability companion paths are not present at repository root; this change
updates the actual Markdown trace records instead of creating another registry.

## Trace changes and remaining acceptance

03 View C and the two FR-CORE-014/015 REALIZED_BY records now resolve to existing
product paths, explicitly labeled partial, with this revision/test/evidence map.
VERIFIED_BY family mappings and acceptance boundary/env/EV level are unchanged.
Coverage remains ALLOCATED for the unfulfilled whole requirements, planning stays
VERIFY_PLANNED, and formal execution/sealed-evidence edges remain empty. Existing
engineering runs are documented above but are not sealed acceptance bundles.

Atomic mutation/outbox awaits DEP-022's exact lifecycle binding and
DN-CORE-LIFECYCLE@COMPONENT_READY at INTEGRATION. Relay/retry and publication
completion await canonical NATS routing/publisher/world binding and the real
JetStream path; DEP-023/025 are related spine integration gates, not new Core
START gates. Real crash consistency, RES-BROKER-001, AV-SCEN-01/07, producer/
consumer integration, current-head CI and post-merge consumer acceptance remain
unestablished by these slice counts. NFR-PERF-003 still needs completed commit-to-
durable-publication measurement (p95 <=2s / p99 <=5s under WP-NORMAL); backlog age
is not that measurement. No acceptance criterion or workflow state is completed.

Product implementation executable NOW without inventing one of those bindings:
**NO identified item**. This does not certify owner-work exhaustion or justify
the downstream-integrated-acceptance deferred classification: implementation
remains blocked, and ordinary engineering PR/CI/trace validation is still owner
work. The next smallest task is exact equipment fact/producer/payload resolution
(starting with MachineIsolated's two flows) through canonical authority, followed
by the first explicitly bound schema slice. This document cannot resolve that
architecture question or authorize another WP's execution.

## Checks executed for this trace-only change

- `projectctl validate --json`: exit 0, validation PASS; 306 requirements,
  179 WPs, 217 dependency edges, zero HARD cycles. This is offline canonical
  validation, not live readiness or product acceptance.
- Parsed the before/after FR-CORE-014/015 YAML records: only REALIZED_BY.ref
  changed; all other fields, states, family mappings, acceptance gates and
  formal execution/evidence edges are identical.
- `git cat-file -e <commit>:<path>` verified the pinned product/test/evidence
  paths and all four event fixtures at the listed historical revisions.
- `git diff --check`: passed. Product tests were not rerun because no product
  behavior or tests changed; all previous counts remain historical, scoped claims.
