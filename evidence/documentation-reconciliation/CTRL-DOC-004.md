# CTRL-DOC-004 — Contract naming audit

Result: audit complete; affected semantic changes remain pending. Canonical contract locations are untouched. CHG-003/004/010 are deferred. The machine companion traces every matching canonical occurrence with its heading and immediate context.

| Surface | Producer / authority | Consumer / meaning | Deterministic conclusion |
|---|---|---|---|
| InspectionRequest / InspectionRequested | Requesting service/actor; 02 labels request fields derived candidates | Vision serving, artifact retrieval and inference | Do not promote inferred fields to an approved schema |
| InspectionObservation | Vision perception; 01 FR-VIS-009, Items62/83 and 02 perception-fact list | AI evidence, Core/quality integration, inspection UI; 03/05/06B trace | Observation confidence cannot be rewritten by downstream services |
| InspectionResult / IC-VIS-002 | Vision structured perception output; 02 registry and serving sequence | Evidence and quality workflows | The existing architecture also calls this a perception fact; an accepted manufacturing-quality interpretation/transformation is not uniquely established |
| ActivateSchedule / ActivateScheduleCommand | Automation Control Plane, 02 R-003 | Canonical protected command path | Already one logical command under full ActionCatalog gates; no new alias decision necessary |
| PlaceLotOnHold / ApplyMaterialHold | Core authority; Automation approved coordination | Material/lot hold, approval binding and protected effects | No proven identical payload/scope/idempotency binding; keep unresolved |
| DispatchLot / ReleaseLot / ActivateSchedule | Distinct Core lifecycle/dispatch and governed schedule operations | Execution and scheduling consumers | Never conflate these merely because they occur in the same planning chain |
| IsolateMachine / maintenance request/work-order names | Existing resource and protected-action authority boundaries | Resource eligibility and maintenance coordination | Payload/alias reconciliation belongs to the protected-command decision, not textual substitution |

HUMAN_DECISION_REQUIRED: INSPECTION_CONTRACT_CANONICALIZATION

Selman with Asrın review must decide one contract plus explicit aliases, or two contracts with a versioned transformation and acceptance authority. Update API/events, schemas, 01/02/03/04/05/06/07 and binding tests together. This audit does not implement the suggested two-contract interpretation by guesswork.

HUMAN_DECISION_REQUIRED: PROTECTED_COMMAND_NAMING

Asrın with Batu consumer review must freeze exact hold/isolation/maintenance command identities, payloads and approval/idempotency binding. AI remains READ/SIMULATE/PROPOSE, Scheduler generates candidates, HITL approves, Automation coordinates, Core owns authoritative effects. HTTP acceptance is not verified execution.

RTF-025/026: owner-reviewed append-only ARCH allocation remains required for predictive ML/MLOps, experiment runner/evidence sealing, scheduling evaluation harness and Vision dataset pipeline. Existing ARCH-AI/DATA/PLAT/SCH/VIS prefixes are candidate homes from GAP-RTM-001/002/003, not newly minted architecture decisions. No new service or infrastructure is introduced.

No Plane/GitHub/network mutation. No canonical owner, WP, requirement or contract was renamed. Full test/validation evidence is recorded separately before the control-item commit.
