# Operational Twin

This service is a read-only projection of canonical manufacturing events. It
does not own manufacturing transitions and has no mutation command surface.

## Local slice

The projection core keeps an explicit `(world_id, branch_id)` scope, an
aggregate revision map, an applied-event ledger, and a source-event revision.
Duplicate delivery is idempotent. Old events are rejected, revision gaps mark
the projection `STALE` and require reconciliation, and world/branch mismatch is
rejected before any local effect.

Projected entities expose an explicit epistemic class (`ACTUAL`, `OBSERVED`,
`INFERRED`, `PREDICTED`, `PLANNED` or `COUNTERFACTUAL`) and query freshness.
Recoverable dependency lag is marked `DEGRADED`; revision gaps remain
fail-closed `STALE`. Unknown epistemic values are rejected before projection
state changes.

`migrations/0001_twin.sql` defines the `twin` read model, applied-event ledger,
and projection revision tables. `PostgresProjectionStore` restores and advances
that model using the caller-owned transaction, so projection state and the
EVT-003 delivery ledger commit before ACK. Deployment applies this migration and
supplies a schema-scoped runtime connection.

## Runtime boundary

`nats_consumer.py` reuses the EVT-002 envelope validator and binds the EVT-003
consumer to `PostgresProjectionStore` in the same caller-owned transaction.
Stream, subject, durable and ACK settings remain explicit inputs; this package
does not provision or alter NATS durables. Real Core publication and deployed
JetStream delivery remain DEP-032/CHG-035 integration work.

## Recovery

On a revision gap the projector becomes `STALE`; operators must reconcile or
rebuild from canonical sources before current-state semantics are restored.
Startup catch-up is deterministic through `Projector.catch_up`. A process
restart must retain the applied-event ledger and source revision in the runtime
database; the migration is intentionally not destructive.
