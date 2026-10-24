# ADR-0005: SeaweedFS as object storage

- **ADR-ID**: ADR-0005
- **Title**: SeaweedFS as object storage
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L2
- **AffectedCapabilities**: S3-compatible object storage (ARCH-DATA-OBJ); artifact storage and lifecycle
- **AffectedRequirements**: None linked yet (no DECIDED_BY edge uses the placeholder `backfill-05`; GAP-RTM-023)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Items 37 and 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

The platform needs S3-compatible object storage for datasets, images, models,
reports, experiment bundles, simulator snapshots and documentary files. Item 37
fixes only the "S3-compatible" requirement; Item 61 names the product.

## Decision Drivers

- S3-compatible, self-hosted storage.
- Relational artifact metadata, immutable artifact identity and a provenance-aware
  lifecycle.
- Portability: the S3 API, not any product-specific behaviour, is the contract
  boundary.

## Constraints/Assumptions

- No proprietary SeaweedFS semantics may leak into the domain (`TECH-INV-13`).
- An object is not an artifact: `Artifact -> ArtifactReference -> Physical Object`.
  A bucket or object key is never a business identity or a cross-service contract;
  contracts reference `artifact_id` or `ArtifactReference`.
- A finalized artifact is never overwritten in place; new bytes need a new
  artifact version. Normal consumers use only `AVAILABLE` artifacts.
- The browser never holds permanent storage credentials; signed access is
  short-lived and scoped.
- Open item: the exact checksum hash algorithm is not pinned by any approved Item;
  a SHA-256-class algorithm is the natural default and is to be confirmed by an ADR
  at implementation time. This record does not decide it.

## Considered Options

- SeaweedFS: **selected**.
- MinIO: rejected as a new core baseline.

## Decision

SeaweedFS is the self-hosted S3-compatible object store for datasets, images,
models, reports, experiment bundles, simulator snapshots and artifacts, and
documentary files, with the S3 API as the contract boundary.

## Rationale

Item 61 confirms SeaweedFS satisfies the S3-compatible requirement, and keeping the
S3 API as the contract boundary keeps the product replaceable.

## Positive Consequences

- Portability through the S3 API; the exit cost is explicitly low.
- Artifact provenance and immutability are enforced in the platform, not the
  product.

## Negative Consequences

Loss of artifact access (images, models, datasets) blocks the Vision, AI and
experiment pipelines that depend on it.

## Risks

- The loss of artifact access above.
- Silent drift between metadata and objects, guarded by a background orphan sweeper
  and bidirectional integrity checks.

## Operational Impact

Semantic owner: each artifact's domain producer. Runtime owner: Yavuz. The store is
stateful and durable, and artifact provenance is F1 mandatory.

## Security/Authority Impact

Medium: it may hold sensitive artifacts (inspection images, models). Access goes
through the S3 contract boundary only.

## Research/Evidence Impact

It holds experiment bundles, datasets and models. Finalized versioned artifacts are
immutable and carry a checksum verified at finalize time.

## Migration/Rollback

Reversibility class: `REVERSIBLE` (assigned by this record's author, from the
specification's statement that the exit cost is explicitly low). The S3 API
contract boundary is what keeps a replacement migration bounded.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1`
(documentation). Validation evidence is attached when real artifact upload,
finalize and integrity-check evidence exists.

## Revisit Triggers

If SeaweedFS-specific behaviour is needed outside the S3 contract boundary, or if
the Item 61 promotion and exit policy for object storage is triggered.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Object Storage; `TECH-INV-13`; The Backfill ADR Set.
- [ADR index](README.md)
