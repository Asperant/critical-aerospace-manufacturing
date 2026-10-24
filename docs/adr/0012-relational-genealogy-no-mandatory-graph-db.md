# ADR-0012: Relational genealogy without a mandatory graph database

- **ADR-ID**: ADR-0012
- **Title**: Relational genealogy without a mandatory graph database
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: None named in the specification
- **DecisionLevel**: ADR-L2
- **AffectedCapabilities**: Genealogy and knowledge-graph representation (ARCH-CORE-GENEALOGY); lot and component lineage
- **AffectedRequirements**: FR-CORE-012 (DECIDED_BY edge in the RTM; a decision link, never verification)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Item 61 and the Data Architecture) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

Genealogy and relationship facts underpin RCA. A Knowledge Graph is a semantic model, and the question is whether it needs graph-database technology.

## Decision Drivers

Keep canonical genealogy in the single operational truth store, avoid an additional database without capability justification, and preserve split, merge, rework, hold, release and scrap relationships permanently.

## Constraints/Assumptions

- Canonical genealogy and relationship facts (material parent/child, `ProcessExecution`, machine and recipe-version exposure, inspection and incident relationships) stay in the PostgreSQL relational model.
- Traversal uses recursive SQL/CTEs, with precomputed projections for performance.
- A Knowledge Graph is a semantic model, not a mandate for graph-database technology.

## Considered Options

- PostgreSQL relational genealogy with recursive CTEs: **selected**.
- A dedicated graph database (Neo4j-class): rejected as mandatory.

## Decision

Canonical genealogy and knowledge-graph relationships are represented relationally in PostgreSQL, and no graph database is mandatory.

## Rationale

A Knowledge Graph semantic model does not imply a graph database, and keeping genealogy in PostgreSQL honors the single canonical store principle (ADR-0002).

## Positive Consequences

No additional database to operate; genealogy lives beside the transactional truth it describes.

## Negative Consequences

The specification does not enumerate negative consequences. Performance relies on recursive queries and precomputed projections rather than native graph traversal.

## Risks

Deep or wide traversals may need precomputed projections; adopting a graph database later needs measured workload evidence and an ADR.

## Operational Impact

Owned within the Core domain (Asrın). `LotGenealogyRelation` and `MaterialGenealogy` preserve split, merge, rework, hold, release and scrap relationships permanently and are the primary RCA evidence source.

## Security/Authority Impact

None specific; it follows the PostgreSQL access model (schema-scoped access).

## Research/Evidence Impact

Genealogy is the primary RCA evidence source, so its history must not be overwritten.

## Migration/Rollback

Reversibility class: `COSTLY_TO_REVERSE` (assigned by this record's author, because lineage history and queries are built on the relational model). A canonical persistence-technology change is a mandatory ADR trigger. A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Implementation work exists under WP-CORE-004; this record does not certify it, and validation evidence is attached from accepted work-package evidence.

## Revisit Triggers

Measured genealogy workload that recursive queries and projections cannot meet, which would need evidence and a new ADR.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline (PostgreSQL relational genealogy); Database Architecture; Data Architecture 10.6; The Backfill ADR Set.
- [ADR index](README.md)
