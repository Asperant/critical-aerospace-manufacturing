# ADR-0001: Modular Core + Specialized Bounded Services

- **ADR-ID**: ADR-0001
- **Title**: Modular Core + Specialized Bounded Services
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L3
- **AffectedCapabilities**: Application architecture style; the nine mandatory logical deployables and their authority boundaries
- **AffectedRequirements**: None linked yet (no DECIDED_BY edge uses the placeholder `backfill-01`; GAP-RTM-023)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Items 15, 18 and 22) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

The platform needs an application architecture that can express the AI to
Automation authority law, isolate the Oracle evaluation plane, and give the
subsystem owners independently deployable, independently failing subsystems. The
specification chose a deliberate middle path between two rejected extremes.

## Decision Drivers

- Express the AI to Automation authority law with real boundaries.
- Isolate the Oracle evaluation plane.
- Independently deployable and independently failing subsystems for Selman, Batu
  and Asrın.
- Avoid the "Distributed Monolith" anti-pattern (shared database plus circular
  synchronous calls plus cross-service transactional dependency).

## Constraints/Assumptions

- Governing rule: a service boundary represents a real authority, runtime or
  failure boundary, never an entity name. "Service count is not what matters,
  boundary quality is" (`BE-INV-10`).
- A new service boundary is justified only when the candidate is the sole
  canonical authority for a distinct class of semantic fact, has a materially
  different runtime profile, needs independent failure isolation, needs
  independent security exposure, or needs independent scaling.
- Nine mandatory logical deployables: `command-center-web`, `operations-bff`,
  `manufacturing-core`, `manufacturing-simulator`, `digital-twin-service`,
  `vision-service`, `ai-intelligence-service`, `scheduler-service`,
  `automation-service`.
- A logical deployable is not necessarily one OS process. Exact process and
  container topology is deliberately deferred (a Derived Architecture Detail).
- Cross-service private imports are prohibited (`TECH-INV-04`).

## Considered Options

- Modular Core + Specialized Bounded Services: **selected**.
- One undifferentiated monolith: rejected. It cannot express the authority law,
  cannot isolate the Oracle evaluation plane, and gives no independently failing
  subsystems. Item 15 allows a "modular monolith" for the Backend/Twin cluster
  specifically, but rejects an undifferentiated one.
- Entity-per-microservice decomposition: rejected. It decomposes by entity name
  rather than by authority boundary and produces the Distributed Monolith.

## Decision

The application architecture is Modular Core + Specialized Bounded Services, with
the nine mandatory logical deployables above, each bounded by an authority,
runtime or failure boundary.

## Rationale

The middle path keeps authority boundaries real without splitting by entity. The
five boundary justifications make every additional service defensible against the
governing rule.

## Positive Consequences

- Authority, failure-isolation, security-exposure and scaling boundaries can be
  expressed and enforced.
- Subsystems can be deployed and can fail independently (for example Vision
  inference latency does not block Manufacturing Core transactional commands).
- The Oracle evaluation plane can be network- and identity-isolated from every
  operational service.

## Negative Consequences

The specification does not enumerate negative consequences for this decision. The
record author notes the inherent cost of more than one deployable: cross-service
contracts must be versioned and kept compatible. This is an observation, not a
specification statement.

## Risks

Drawing boundaries by entity name instead of authority would reproduce the
Distributed Monolith: shared database, circular synchronous calls and
cross-service transactional dependency.

## Operational Impact

Nine logical deployables, each with a primary domain owner and a platform/SRE
co-owner (see the specification's "Why Nine, Not Four" mapping). A logical
deployable may run as several cooperating processes where its authority is one
thing but its runtime profile is not.

## Security/Authority Impact

Independent security exposure is one of the five boundary justifications. The
Oracle evaluation plane must be network- and identity-isolated from every
operational service (Item 22, section 41).

## Research/Evidence Impact

Isolating the Oracle evaluation plane keeps evaluation separate from operational
services. No other research impact is stated.

## Migration/Rollback

Reversibility class: `HIGHLY_DISRUPTIVE` (assigned by this record's author: the
service boundaries underlie every other architectural decision). A service or
bounded-context boundary change is a mandatory ADR trigger and needs a new
superseding ADR, following prepare -> compatibility/migrate -> cutover -> verify
-> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E0`
(the Master Specification's reasoned analysis of rejected alternatives). Validation
evidence is attached when the deployables exist and their boundaries are exercised
in integration.

## Revisit Triggers

When a boundary no longer corresponds to a real authority, runtime or failure
boundary, or when the decomposition no longer passes the five-point boundary test.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Application Architecture Style; Mandatory Logical Deployables; Why Nine, Not
  Four; The Backfill ADR Set.
- [ADR index](README.md)
