# ADR-0011: Docker Compose as the shared-integration runtime orchestrator

- **ADR-ID**: ADR-0011
- **Title**: Docker Compose as the shared-integration runtime orchestrator
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L2
- **AffectedCapabilities**: Deployment and orchestration topology (ARCH-PLAT-COMPOSE)
- **AffectedRequirements**: FR-PLAT-001 (DECIDED_BY edge in the RTM; a decision link, never verification)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Items 39, 44 and 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

Items 39 and 44 name Docker Compose only as the canonical example in the runtime chain (Linux host, container runtime, Docker Compose, platform services and infrastructure) without locking a version. Item 61 settles the orchestration mechanism.

## Decision Drivers

A single shared Linux host, a reproducible versioned deployment definition, and no unjustified orchestration complexity.

## Constraints/Assumptions

- Kubernetes is not the baseline; it is only evaluated later if a measured deployment or scaling need justifies it (`TECH-INV-19`). Cloud portability cannot make Kubernetes mandatory.
- Compose manifests are versioned in Git; redeploy is from the ReleaseManifest and pinned images.
- The exact Compose file organization and naming remain an architecture open decision (`OD-LOCAL-01`).

## Considered Options

- Docker Engine + Docker Compose v2: **selected**.
- Kubernetes: rejected for the current baseline.
- Nomad: rejected.
- A Proxmox or VM layer: rejected.

## Decision

Docker Engine with Docker Compose v2 is the canonical deployment and orchestration mechanism, including for the shared-integration runtime.

## Rationale

Compose fits the single-host constraint and keeps the deployment definition in Git, while Kubernetes adoption stays conditional on measured evidence.

## Positive Consequences

Low operational complexity on a single host and a versioned, reproducible deployment definition.

## Negative Consequences

The specification does not enumerate negative consequences. The record author notes that multi-node scale-out is not provided by this baseline; this is an observation, not a specification statement.

## Risks

Deployment and redeploy are blocked if the orchestration layer is unavailable, although running containers may persist temporarily.

## Operational Impact

Runtime owner: Yavuz. Redeploy from the ReleaseManifest and pinned images.

## Security/Authority Impact

Medium: it controls container privilege boundaries. It carries no business or domain logic.

## Research/Evidence Impact

None stated in the specification for this decision.

## Migration/Rollback

Reversibility class: `COSTLY_TO_REVERSE` (assigned by this record's author, because every deployable is composed through it). A material deployment-topology change is a mandatory ADR trigger, and any Kubernetes requirement needs an evidence-driven ADR (`TECH-INV-19`). A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Implementation exists under WP-PLAT-001; this record does not certify it, and validation evidence is attached from that work package's accepted evidence.

## Revisit Triggers

A measured, evidence-backed deployment or scaling need that single-host Compose cannot satisfy, or a research contribution that genuinely depends on distributed scale-out.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Platform & Deployment Architecture (Docker Engine + Docker Compose v2); `TECH-INV-19`; The Backfill ADR Set.
- [ADR index](README.md)
