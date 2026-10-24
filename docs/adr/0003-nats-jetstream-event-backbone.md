# ADR-0003: NATS with JetStream as the event backbone

- **ADR-ID**: ADR-0003
- **Title**: NATS with JetStream as the event backbone
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L3
- **AffectedCapabilities**: Durable event backbone (ARCH-EVT-BROKER); transactional outbox relay; durable consumers; replay
- **AffectedRequirements**: None linked yet (DECIDED_BY edges still use the placeholder `backfill-03`; GAP-RTM-023)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Item 61, Technology Selection) and already incorporated
> into the architecture specification. It does not propose or change anything.
> The date is the date this record was written, not the date of the decision.

## Context

The architecture needs a durable event backbone with at-least-once delivery,
idempotent consumers, a transactional outbox and controlled replay, for a
single-node integration environment. Items 35-38 specify only the required broker
capabilities; Item 61 names the product that satisfies them (reconciliation R-008).

## Decision Drivers

Broker capabilities required by the architecture: durable persistence, consumer
groups or subscriptions, multiple independent consumers, key- or partition-based
ordering, acknowledgement and checkpointing, retention, replay, access control,
backpressure support, persistent volumes, bounded message sizes, and lag and
health observability. A low operational footprint on the single shared host, and
a good fit with the Python-first application architecture.

## Constraints/Assumptions

- Delivery is at-least-once; duplicate delivery is a normal condition. No
  broker-specific "exactly-once" feature is an application-wide guarantee.
- Consumer idempotency is mandatory for critical consumers, keyed on `event_id`.
- The broker is transport. It carries facts and does not decide them
  (TECH-INV-09, ARCH-INV-046).
- Exact NATS container image versions remain an open decision of the architecture.

## Considered Options

- NATS with JetStream: **selected**.
- Kafka: rejected (unnecessary operational complexity).
- RabbitMQ: rejected as the primary backbone.
- Redpanda: rejected (no sufficient capability advantage).
- Database-only integration: considered as an alternative, not selected.

## Decision

NATS with JetStream is the durable event and work messaging backbone: domain
events, work events, telemetry streams, replay and durable consumers.

## Rationale

Item 61 selects NATS with JetStream because it satisfies the required broker
capability list with a comparatively low operational footprint, offers pub/sub
plus durable streams, and fits the Python-first application architecture.

## Positive Consequences

- Comparatively low operational footprint.
- Pub/sub plus durable streams in one product.
- A good fit with the Python-first application architecture.

## Negative Consequences

- The application must still implement its own idempotency.
- A weaker fit than a Kafka-class architecture for a hypothetical future
  massive-analytics scale.

## Risks

- Delivery delay or backlog. This does not itself corrupt business truth when the
  outbox and idempotency are implemented correctly.
- Duplicate publication remains possible (for example a relay crash after the
  broker accepted a message) and is handled by consumer idempotency.

## Operational Impact

Runtime ownership: Yavuz. Event semantic ownership stays with each canonical
producer (Asrın for Core, Twin and AI events; Selman for Vision events; Batu for
Simulator, Scheduler and Automation events). The broker is stateless over durable
streams; JetStream persists streams to disk. If the broker is lost, it is
reprovisioned and consumers replay from the durable stream or outbox. Broker
retention is not a substitute for backup.

## Security/Authority Impact

Medium: the broker carries domain event payloads, and access control applies at
producer and consumer level. The browser does not directly issue protected
commands to NATS (ARCH-INV-058). "NATS Runtime is not Event Meaning": runtime
ownership of the broker confers no business or event-semantic authority.

## Research/Evidence Impact

Replay is a first-class operation and must never re-trigger a live side effect
(EV-INV-07). Broker history is not canonical business truth.

## Migration/Rollback

Reversibility class: `COSTLY_TO_REVERSE` (assigned by this record's author:
producers, the outbox relay and consumers are built against the broker). A
reversal needs a new superseding ADR and follows prepare -> compatibility/migrate
-> cutover -> verify -> remove old path. Operational rollback of a broker incident
is reprovisioning plus replay.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1`
(documentation). NATS JetStream is a HARD requirement for real event-driven M1/M2
integration; fixtures are allowed before that point. Validation evidence is
attached when real JetStream integration, outbox relay and replay evidence exists.

## Revisit Triggers

If workload or retention needs exceed the validated resource envelope of the
single shared host (Shared Host Resource Architecture), or if the Item 61
promotion and exit policy for the broker is triggered.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Data Store, Event Backbone, Object Storage, and Local
  Development Bindings; Command/Event Semantics and Event Architecture;
  Normative Reconciliation Register (R-008); The Backfill ADR Set.
- [ADR index](README.md)
