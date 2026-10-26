# Operational Twin

This service is a read-only projection of canonical manufacturing events. It
does not own manufacturing transitions and has no mutation command surface.

## Local slice

The projection core keeps an explicit `(world_id, branch_id)` scope, an
aggregate revision map, an applied-event ledger, and a source-event revision.
Duplicate delivery is idempotent. Old events are rejected, revision gaps mark
the projection `STALE` and require reconciliation, and world/branch mismatch is
rejected before any local effect.

`migrations/0001_twin.sql` defines the `twin` read model, applied-event ledger,
and projection revision tables. The SQL is a model/migration artifact only until
the runtime PostgreSQL binding is supplied by DEP-033.

## Runtime boundary

`nats_consumer.py` reuses the EVT-002 envelope validator and exposes an adapter
for the EVT-003 transaction-owning consumer. Stream, subject, durable and ACK
settings are explicit inputs; this package does not provision or alter NATS
durables. Real Core publication and JetStream delivery remain DEP-032/CHG-035
integration work.

## Recovery

On a revision gap the projector becomes `STALE`; operators must reconcile or
rebuild from canonical sources before current-state semantics are restored.
Startup catch-up is deterministic through `Projector.catch_up`. A process
restart must retain the applied-event ledger and source revision in the runtime
database; the migration is intentionally not destructive.
