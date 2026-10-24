# ADR-0007: A custom Python discrete-event simulator, not a generic DES framework

- **ADR-ID**: ADR-0007
- **Title**: A custom Python discrete-event simulator, not a generic DES framework
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Batu, Yavuz Gümüş
- **DecisionLevel**: ADR-L3
- **AffectedCapabilities**: Simulator kernel (ARCH-SIM-ENGINE, ARCH-SIM-CLOCK, ARCH-SIM-SNAPSHOT, ARCH-SIM-ORACLE)
- **AffectedRequirements**: FR-SIM-001 (DECIDED_BY edge in the RTM; a decision link, never verification)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Item 61 and the Simulator items) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

The Manufacturing Simulator needs a deterministic kernel that supports replay, snapshots, forks and counterfactual worlds, while keeping a hidden Oracle isolated and calling an external Scheduler through a decision interface.

## Decision Drivers

Deterministic replay, snapshot, fork, counterfactual worlds, named RNG streams, a hidden Oracle, and an external Scheduler decision interface.

## Constraints/Assumptions

- A logically single authoritative DES kernel per simulation world; a distributed DES design is rejected. Scale comes from independent parallel runs or branches.
- The Simulator implements behavior; Core defines legality of manufacturing semantics.
- Oracle isolation is safety and research-integrity critical (`ARCH-INV-042`, Oracle Access Negative Test, Item 67).

## Considered Options

- Custom deterministic Python DES kernel: **selected**.
- SimPy: not the primary engine; it may be referenced or used experimentally only.
- Distributed DES across nodes: rejected (clock-synchronization, causality and rollback complexity).

## Decision

The simulator kernel is a custom deterministic Python discrete-event simulation kernel, not a generic DES framework.

## Rationale

The required properties (deterministic replay, snapshot and fork, named RNG streams, hidden Oracle isolation, external Scheduler decisions) are owned by the kernel itself rather than adapted from a generic framework.

## Positive Consequences

The kernel can guarantee the replay, fork and Oracle-isolation properties directly.

## Negative Consequences

The specification does not enumerate negative consequences. The record author notes the cost of owning a simulation kernel; this is an observation, not a specification statement.

## Risks

Loss of the kernel blocks all scenario generation, RCA evidence generation and Scheduler evaluation.

## Operational Impact

Owner: Batu (Operational Simulator primary). The kernel is stateful per world or run, and snapshot and fork artifacts are persisted for reproducibility. It can be rebuilt from GeneratorVersion and ScenarioVersion lineage (Item 56).

## Security/Authority Impact

Medium, with Oracle isolation flagged as safety and research-integrity critical. The Oracle is enforced at the permission, network or service-boundary level, and Oracle-derived data keeps an explicit taint marker (`ARCH-INV-042`, `ARCH-INV-043`).

## Research/Evidence Impact

Determinism, named RNG streams and replay underpin reproducible scenario generation and evaluation evidence.

## Migration/Rollback

Reversibility class: `COSTLY_TO_REVERSE` (assigned by this record's author, because scenarios, snapshots and evaluation evidence are bound to the kernel). A change of simulation engine is a mandatory ADR trigger. A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Validation evidence is attached when determinism, replay, fork and Oracle-isolation negative tests exist.

## Revisit Triggers

If the kernel can no longer deliver deterministic replay, snapshot or fork, or if the Item 61 promotion and exit policy for the simulator engine is triggered.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Manufacturing Simulator Architecture; Single authoritative kernel per world; `ARCH-INV-042`, `ARCH-INV-043`; The Backfill ADR Set.
- [ADR index](README.md)
