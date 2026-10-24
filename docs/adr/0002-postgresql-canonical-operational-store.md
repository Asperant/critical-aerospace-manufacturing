# ADR-0002: PostgreSQL as the canonical operational store

- **ADR-ID**: ADR-0002
- **Title**: PostgreSQL as the canonical operational store
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L3
- **AffectedCapabilities**: Canonical relational store (ARCH-DATA-PG, ARCH-CORE-DB); logical schema ownership; schema migration
- **AffectedRequirements**: None linked yet (no DECIDED_BY edge targets this ADR)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Items 35 and 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

The platform needs one canonical store for manufacturing truth. Item 35 set a
PostgreSQL-centric controlled polyglot persistence model; Item 61 fixed the
version (PostgreSQL 18).

## Decision Drivers

- One database used well before several used badly.
- Ownership enforced at the logical-schema level, never at the physical-server
  level.
- Specialized stores added only with measured workload evidence and an ADR.

## Constraints/Assumptions

- PostgreSQL remains the canonical relational operational-truth store
  (`TECH-INV-05`). Primary business state cannot move to a cache, document, vector
  or graph store.
- A single physical cluster is acceptable. Minimum logical schemas: `core`,
  `twin`, `automation`, `scheduler`, `ai`, `vision`, `audit`, `analytics`,
  extended with `knowledge` and, where applicable, `telemetry`.
- Each service gets credentials scoped to its own schema; cross-service
  private-schema SQL access is forbidden by default, and each service manages its
  own migrations.
- Exact PostgreSQL container image versions remain an open decision.

## Considered Options

- PostgreSQL-centric controlled polyglot persistence (PostgreSQL 18 + Valkey +
  object storage): **selected**.
- Several specialized databases from the start: not selected. Dedicated
  time-series, vector, graph and OLAP databases are added only with measured
  workload evidence and an ADR.
- Related choices recorded separately: Qdrant as the retrieval projection (ADR-0006
  reserved) and relational genealogy without a mandatory graph database (ADR-0012
  reserved).
- Not mandated: TimescaleDB (optional, non-baseline), a dedicated OLAP database,
  full event sourcing, read replicas and sharding at the target scale.

## Decision

PostgreSQL 18 is the canonical relational operational store. It owns Manufacturing
Truth, Genealogy, Approvals, Audit Metadata, Experiment Metadata, Model/Dataset
Governance Metadata, Artifact Metadata and Configuration/Version Bindings.

## Rationale

"Use one database well before using five databases badly." Logical-schema
ownership gives clear authority without requiring separate physical servers.

## Positive Consequences

- A single, primary source of truth for canonical state.
- Ownership enforced per logical schema with scoped credentials.
- Native time-series handling (partitioned tables, BRIN indexes, retention policy)
  is the first choice before any dedicated time-series database.

## Negative Consequences

Loss or outage of PostgreSQL halts all canonical mutation and read authority
system-wide: it is the highest-severity single point of failure.

## Risks

- The single point of failure above.
- Cross-schema access or a shared universal credential would erase the ownership
  boundaries (cross-schema mutation is prohibited, `RESP-INV-14`).

## Operational Impact

Runtime ownership: Yavuz. Schema and semantic owners: Asrın (`core`, `twin`,
`ai`/knowledge), Selman (`vision`), Batu (`simulator`, `scheduler`, `automation`),
Yavuz (platform and release metadata). The store is stateful on a durable on-host
volume. Backup and DR is F1 mandatory (Item 68, section II). Schema evolution
follows Expand -> Migrate -> Contract via Alembic. "PostgreSQL Runtime is not
LotStatus Authority": runtime ownership confers no business-state authority.

## Security/Authority Impact

High: it holds manufacturing truth, approvals and the audit trail. Access must be
schema-scoped, and application logs are never audit (`DB-INV` set).

## Research/Evidence Impact

It holds Experiment, Model/Dataset Governance and Artifact metadata, so
research-affecting provenance lives in the canonical store.

## Migration/Rollback

Reversibility class: `HIGHLY_DISRUPTIVE` (assigned by this record's author: every
service's canonical state depends on it). A canonical persistence-technology
change is a mandatory ADR trigger. Recovery from loss is restore from backup and
the mandatory DR drill.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1`
(documentation). Validation evidence is attached when real PostgreSQL integration,
migration replay and backup/restore evidence exists. The consolidated database
invariants are `DB-INV-01` to `DB-INV-16`.

## Revisit Triggers

Adoption of any specialized store (time-series, vector, graph, OLAP) needs measured
workload evidence and an ADR. Promoting TimescaleDB needs performance evidence.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Data Store, Event Backbone, Object Storage, and Local Development Bindings
  (Database Architecture); Technology Baseline; The Backfill ADR Set.
- [ADR index](README.md)
