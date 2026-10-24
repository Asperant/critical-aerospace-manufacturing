# ADR-0004: Temporal as the durable workflow engine

- **ADR-ID**: ADR-0004
- **Title**: Temporal as the durable workflow engine
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Batu, Yavuz Gümüş
- **DecisionLevel**: ADR-L3
- **AffectedCapabilities**: Durable workflow engine binding (ARCH-AUTO-WORKFLOW); Automation durable execution
- **AffectedRequirements**: FR-AUTO-002 (DECIDED_BY edge in the RTM; a decision link, never verification)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Item 61, Technology Selection, against the Item 18
> capability list) and already incorporated into the architecture specification.
> It does not propose or change anything. The date is the date this record was
> written, not the date of the decision.

## Context

Item 18 deliberately names no workflow-engine technology. It specifies required
capabilities: durable execution, persistent workflow state, timers, event waits,
retries, idempotency support, human tasks and approval, workflow versioning, crash
recovery, visibility, compensation and correlation. Item 61 names the product that
satisfies them.

## Decision Drivers

The Item 18 capability list above, and a self-hosted engine on the single shared
host.

## Constraints/Assumptions

- Temporal provides durability and cannot own the platform's authority semantics
  (`TECH-INV-11`, `ARCH-INV-024`). The Action Catalog, risk classification and
  approval requirements are the platform's own policy.
- The engine orchestrates commands only and does not mutate Core's private
  persistence directly. All Core mutation goes through Core's versioned command
  contracts.
- Workflow completion does not by itself imply manufacturing completion; the effect
  must be independently verified against Core/Twin (`ARCH-INV-051`).
- Self-hosted; PostgreSQL-backed persistence is preferred, with no Cassandra
  requirement. Exact container image versions remain an open decision.

## Considered Options

- Temporal: **selected**.
- Celery: rejected. NATS plus Temporal already cover the async execution patterns.
- The specification notes the Automation architecture is defined by the capability
  list and would be unchanged if a different durable-workflow technology satisfying
  the same list were substituted.

## Decision

Temporal, self-hosted, is the canonical durable workflow engine: durable execution,
activity retry, timers, signals, workflow recovery and waits.

## Rationale

It satisfies the Item 18 capability list, and the platform keeps business workflow
semantics (Action Catalog, approval semantics, risk classification, effect
verification, stale-state validation, compensation policy) in its own definitions.

## Positive Consequences

- Durable-execution mechanics (state persistence, retries, timers, signals,
  recovery) are provided by the engine instead of being rebuilt.
- Authority policy stays outside the engine, which keeps the engine replaceable in
  principle.

## Negative Consequences

High exit cost (Item 61 promotion and exit policy): business workflow semantics
must not exist solely as opaque workflow code; they must be reconstructable from
Batu-owned workflow definitions.

## Risks

Loss of the durable-workflow capability blocks all authorized recovery execution;
Automation and HITL cannot durably progress.

## Operational Impact

Semantic owner of workflow definitions: Batu. Runtime owner: Yavuz. The engine is
stateful (workflow history), self-hosted and PostgreSQL-backed where possible.
Automation typically runs workflow-engine worker processes plus a thin command/API
front that accepts Action-Catalog commands and signals running workflows.

## Security/Authority Impact

High: it executes authorized manufacturing-affecting commands. Approval binding and
revision freshness are enforced at this layer. It must not mutate Core's private
persistence.

## Research/Evidence Impact

None stated in the specification for this decision.

## Migration/Rollback

Reversibility class: `COSTLY_TO_REVERSE` (assigned by this record's author, from
the specification's "high exit cost"). A durable-workflow-engine change is a
mandatory ADR trigger and needs a new superseding ADR following prepare ->
compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1`
(documentation). Validation evidence is attached when real durable-workflow
execution, restart recovery and effect verification evidence exists.

## Revisit Triggers

If business workflow semantics can no longer be reconstructed from the workflow
definitions, or if the Item 61 promotion and exit policy for the workflow engine is
triggered.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Automation Architecture; `TECH-INV-11`; `ARCH-INV-024`;
  `ARCH-INV-051`; The Backfill ADR Set.
- [ADR index](README.md)
