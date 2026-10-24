# Architecture Decision Records (ADR)

This directory is the ADR index of the implementation repository (WP-DOC-002,
FR-GOV-004). It is an **Implementation Constraint** derived from the
[System Architecture Specification](../02_System_Architecture_Specification.md)
(sections "Mandatory ADR Triggers", "ADR Identity, Lifecycle, and Levels" and
"The Backfill ADR Set"), not a Master Specification decision.

An ADR answers *why* a decision was made. The architecture specification
answers *what the current, accepted architecture is*. An ADR cannot silently
override the Master Specification: a genuine requirement or invariant change
needs change control against `01` first, then a Master Specification update,
then an ADR, then an update to `02`. An architecture-changing ADR without the
matching update to `02` is an incomplete change.

## Identity and lifecycle

Every ADR has a stable, global, immutable, never-reused ID: `ADR-0001`,
`ADR-0002`, and so on. IDs are minted in order. The next unused ID after the
backfill set is `ADR-0014`. A record file is named `NNNN-short-slug.md`.

Lifecycle: `PROPOSED -> ACCEPTED -> REJECTED -> SUPERSEDED -> DEPRECATED`.

- Accepted does not mean permanent, and accepted does not mean validated. The
  separate `ValidationState` field is `PENDING` or `VALIDATED`.
- An accepted ADR is never substantively rewritten. After acceptance only typo,
  formatting, broken-link, reference and supersession-metadata fixes are allowed.
- Reversing a decision needs a **new** ADR that formally supersedes the old one.
  The old ADR gets `Status: SUPERSEDED` and `SupersededBy: <new ID>`; its
  original text is never edited to pretend the reversal was the original decision.
- Backfilling cannot rewrite history. A backfilled ADR documents a decision that
  was already made, not one newly proposed.

## Decision levels

| Level | Scope |
|---|---|
| `ADR-L1` | Component |
| `ADR-L2` | Cross-Domain |
| `ADR-L3` | System-Critical |

Levels retain accountable scope and technical evidence and advisory domain
contacts. CHG-018 removes all development human approval and reviewer quotas;
product authority and HITL decisions are unchanged.

## Evidence levels

| Level | Meaning |
|---|---|
| `E0` | Reasoned Judgment |
| `E1` | Documentation/Literature |
| `E2` | Prototype/Spike |
| `E3` | Comparative Benchmark |
| `E4` | Integration Evidence |

A stronger or less reversible decision requires stronger evidence.

## Reversibility classes

Used for `ADR-L2` and `ADR-L3` decisions: `REVERSIBLE`, `COSTLY_TO_REVERSE`,
`HIGHLY_DISRUPTIVE`. A reversal follows the migration pattern: prepare ->
compatibility/migrate -> cutover -> verify -> remove old path.

## When a new ADR is required

An ADR is required whenever any of the following occurs:

- a service or bounded-context boundary change;
- a canonical data-ownership change;
- a manufacturing-state-authority change;
- an AI, Scheduler or Automation authority change;
- a cross-service integration-paradigm change (for example synchronous to
  asynchronous, or an event-backbone replacement);
- a canonical persistence-technology change;
- an event-backbone change;
- a durable-workflow-engine change;
- a security or trust-boundary change;
- a material deployment-topology change;
- a mandatory-scope implementation strategy materially changing the architecture;
- a difficult-to-reverse migration;
- a multi-domain structural change;
- the supersession of an accepted ADR (always requires a new ADR);
- new technology added to the mandatory critical path.

A **material trigger** also applies when no single hard trigger fires but two or
more architectural dimensions change materially at once: maintainability,
reliability, security, resource footprint, deployment complexity, portability,
licensing, supply-chain risk, research reproducibility, migration cost, developer
workflow.

## Exclusions

Decisions that normally do not require an ADR:

- a local refactor;
- function or class naming;
- a minor dependency patch upgrade;
- a CSS/UI detail;
- an isolated query optimization (unless architectural implications emerge);
- an internal algorithm refactor behind a stable contract;
- a logging text format change;
- a non-canonical developer-convenience tool.

Technology selection alone does not automatically require an ADR: adopting NATS
with JetStream as the durable event backbone requires one; adopting `httpx` as an
HTTP test client does not.

## Update flow

`ADR accepted -> architecture specification updated -> relevant contracts/config
updated -> Requirements Traceability Matrix and dependency documents updated
where required -> implementation links created -> validation evidence eventually
attached.`

## Writing a record

Copy [TEMPLATE.md](TEMPLATE.md). Keep the 14 metadata fields and all 16 body
sections, in order, even when a section is "None". `DECIDED_BY` trace edges never
count as verification (RTM-INV-17).

## Backfill map (fixed)

The 13 foundational decisions of the backfill set, in the order of the
architecture specification. The ID-to-position mapping is **fixed**: `ADR-00NN`
is the minted ID of the trace placeholder `backfill-NN` (see GAP-RTM-023). A
record row marked `Reserved` has its ID minted but its record not yet written.

| ADR ID | Trace placeholder | Decision | Specification source | Status | Record |
|---|---|---|---|---|---|
| ADR-0001 | backfill-01 | Modular Core + Specialized Bounded Services | Architecture Style | ACCEPTED | [0001-modular-core-specialized-bounded-services.md](0001-modular-core-specialized-bounded-services.md) |
| ADR-0002 | backfill-02 | PostgreSQL as the canonical operational store | Technology Baseline | ACCEPTED | [0002-postgresql-canonical-operational-store.md](0002-postgresql-canonical-operational-store.md) |
| ADR-0003 | backfill-03 | NATS with JetStream as the event backbone | Technology Baseline | ACCEPTED | [0003-nats-jetstream-event-backbone.md](0003-nats-jetstream-event-backbone.md) |
| ADR-0004 | backfill-04 | Temporal as the durable workflow engine | Automation Architecture | ACCEPTED | [0004-temporal-durable-workflow-engine.md](0004-temporal-durable-workflow-engine.md) |
| ADR-0005 | backfill-05 | SeaweedFS as object storage | Data Store, Event Backbone, Object Storage, and Local Development Bindings | ACCEPTED | [0005-seaweedfs-object-storage.md](0005-seaweedfs-object-storage.md) |
| ADR-0006 | backfill-06 | Qdrant as the retrieval/vector projection | RAG Architecture | Reserved | pending |
| ADR-0007 | backfill-07 | A custom Python discrete-event simulator, not a generic DES framework | Manufacturing Simulator Architecture | Reserved | pending |
| ADR-0008 | backfill-08 | OR-Tools CP-SAT as the planning engine | Scheduler Architecture | Reserved | pending |
| ADR-0009 | backfill-09 | Keycloak as the identity architecture | Security Architecture | Reserved | pending |
| ADR-0010 | backfill-10 | OpenTelemetry + OpenObserve as the observability stack | Observability Architecture | Reserved | pending |
| ADR-0011 | backfill-11 | Docker Compose as the shared-integration runtime orchestrator | Platform & Deployment Architecture | Reserved | pending |
| ADR-0012 | backfill-12 | Relational genealogy without a mandatory graph database | Data Architecture 10.6 | Reserved | pending |
| ADR-0013 | backfill-13 | A custom, explicit AI orchestrator rather than a heavy agent framework | AI Intelligence Service Architecture | Reserved | pending |
