# ADR-0006: Qdrant as the retrieval/vector projection

- **ADR-ID**: ADR-0006
- **Title**: Qdrant as the retrieval/vector projection
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L2
- **AffectedCapabilities**: Retrieval projection for RAG (ARCH-DATA-VECTOR); dense, sparse and hybrid retrieval profiles
- **AffectedRequirements**: None linked yet (no DECIDED_BY edge uses the placeholder `backfill-06`)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Items 26 and 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

Item 26 kept the exact vector-store technology open, and an earlier candidate mention named pgvector on PostgreSQL as a possible default. Item 61 (Technology Selection) later selected the retrieval engine (reconciliation R-007).

## Decision Drivers

Dense, sparse (BM25-like) and multivector retrieval with native fusion, supporting the RAG retrieval profiles RAG-B1 (sparse, mandatory baseline), RAG-B2 (dense, mandatory) and RAG-B3 (dense plus sparse hybrid, mandatory final candidate).

## Constraints/Assumptions

- Qdrant is a retrieval projection, not the documentary source of truth (`TECH-INV-06`). PostgreSQL owns canonical document metadata, provenance and rights.
- Loss of Qdrant must be recoverable from the canonical corpus (`TECH-INV-07`).
- ColBERT late-interaction support is optional and evidence-gated; it cannot become mandatory without evaluation evidence (`TECH-INV-08`).
- The exact Qdrant version is deferred to an ADR and is not decided here.

## Considered Options

- Qdrant: **selected**.
- pgvector on PostgreSQL: not the primary RAG engine (earlier candidate, superseded by Item 61).
- Elasticsearch/OpenSearch, Pinecone, Weaviate and Milvus: rejected as mandatory.

## Decision

Qdrant is the canonical vector and retrieval projection engine for RAG, holding dense, sparse and multivector representations.

## Rationale

Item 61 is the later and more specific technology-selection authority, and Qdrant covers the hybrid retrieval profiles with native fusion. The retrieval index stays rebuildable and never becomes a knowledge source of truth.

## Positive Consequences

- Hybrid dense plus sparse retrieval with native fusion in one engine.
- The index is rebuildable, so its loss does not endanger documentary truth.

## Negative Consequences

The specification does not enumerate negative consequences. The record author notes that it adds one stateful service to operate; this is an observation, not a specification statement.

## Risks

Loss of Qdrant affects RAG retrieval only; the documentary source of truth (PostgreSQL) is unaffected.

## Operational Impact

Semantic owner of the logical retrieval model: Asrın. Runtime owner: Yavuz. The index is stateful and rebuildable from the canonical corpus plus the embedding and retrieval profile.

## Security/Authority Impact

Medium: it is the retrieval surface for RAG queries and has no independent write authority over domain truth.

## Research/Evidence Impact

The index is a derived projection; retrieval results must trace to canonical documents. No other research impact is stated.

## Migration/Rollback

Reversibility class: `REVERSIBLE` (assigned by this record's author, from the specification's exit note that the index is rebuilt from the canonical corpus). A change of retrieval engine is a mandatory ADR trigger (new technology on the critical path). A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Validation evidence is attached when real retrieval profiles are evaluated against the canonical corpus.

## Revisit Triggers

If another retrieval engine shows a measurable benefit under the evaluation profiles, or if the Item 61 promotion and exit policy for the vector store is triggered.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Normative Reconciliation Register (R-007); RAG Architecture; `TECH-INV-06` to `TECH-INV-08`; The Backfill ADR Set.
- [ADR index](README.md)
