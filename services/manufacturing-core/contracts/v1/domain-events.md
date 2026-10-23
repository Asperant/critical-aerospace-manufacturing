# Core domain facts v1 — WP-CORE-005 Slice 1

Initial typed contracts for the four Core outputs named in
`docs/02_System_Architecture_Specification.md`, Service Catalog §manufacturing-core
(line 3883). This is a bounded first payload slice, not the complete event catalog
or a declaration of CONTRACT_READY / integration readiness.

| Event type | Aggregate type / payload identity | Meaning / trigger | Intended consumers |
|---|---|---|---|
| `production.LotReleased` | `Lot` / `lot_id` | Accepted Core lot release has taken effect | Twin, Simulator |
| `production.MaterialHoldApplied` | `MaterialHold` / `material_hold_id` | Accepted Core material hold has taken effect | Twin, Automation effect verification |
| `quality.QualityExcursionConfirmed` | `QualityExcursion` / `quality_excursion_id` | Core quality governance has confirmed an excursion | Twin, RCA |
| `scheduling.ScheduleActivated` | `ScheduleVersion` / `schedule_id` | Governed activation has changed Core's active schedule fact | Twin, Automation effect verification |

Each has one canonical semantic producer: `manufacturing-core`. Scheduling
proposes and Automation executes governed activation; a typed object neither
approves nor performs either action. These contracts contain no transition
engine, state enum, transport, or publisher. Other accepted transition families,
including equipment, remain workstream scope for later bounded slices.

`DomainEventV1` validates the discriminated union. Its JSON Schema is
`domain-event.schema.json`; each `domain-event.<Name>.json` is a deterministic
**SYNTHETIC TEST** fixture. These are simulated research examples, not factory
observations, accepted commands, or evidence of manufacturing effects.

The initial wire binding is `<canonical namespace>.<canonical event name>` plus
required string `schema_version: "1"`; the pair identifies the event contract
version. The namespace choices follow 02 Event Architecture (production material
control, quality governance, scheduling). This implements the initial wire
binding left to implementation planning in 01 Item 12; it changes no existing
wire contract, requirement or authority. The per-event payloads currently carry
only the named domain identity, never an aggregate snapshot. Hold target details,
excursion evidence and schedule contents require their governed domain contracts;
the minimal fact alone cannot authorize downstream execution.

The envelope preserves the minimum in 01 Item 36 §17: event/type/version,
producer/source, world/run/branch, occurrence time, aggregate type/identity/version,
correlation/causation/trace IDs and payload. All fields are required. Identities
and revisions reuse Core's opaque nonblank strict strings; no UUID scheme,
numeric revision allocator or ordering comparison is introduced. Payload identity
must equal `aggregate_id`; this equality is checked by `DomainEventV1`, beyond
structural JSON Schema. Callers must use that semantic validator as well.

`occurred_at` is timezone aware domain occurrence time. It is not publication,
ingestion or processing time. Schema consumers should enable RFC 3339 `date-time`
format checking; the schema also explicitly rejects missing timezone suffixes.
Broker authentication, world routing, uniqueness, revision freshness and actual
transition authorization are outside structural validation. String producer/world
metadata is no proof of authentication or authority.

Ordering scope is the aggregate identity; revision is preserved, not interpreted.
Correlation/causation values are preserved without minting or rewriting them.
Replay describes an immutable historical fact and grants no execution authority.
Sensitivity is internal manufacturing metadata (no Oracle or binary content).
Retention and operational consumer bindings remain governed by the event-spine
work; no stream, subscription, retention duration or global ordering is created.

Compatibility: this is the first supported version; no previous supported event
schema exists. The schema and fixtures are checked against the typed models.
Missing/renamed required fields, altered types/identities, unknown event kinds,
wrong namespaces and unknown schema versions fail closed. Like the existing Core
v1 query contracts, shapes are closed: unknown fields are rejected. Forward
acceptance of future additions is not promised. Changing semantics or required
fields requires a new version and consumer compatibility assessment (01 Item 12
Schema Evolution); no registry, migration or speculative v2 support is added.

Full acceptance still needs atomic mutation/outbox, durable publication, real
PostgreSQL crash consistency, observability and integrated scenario evidence.
DEP-022 remains HARD at INTEGRATION, not START.
