# WP-TWIN-002 slice 1 — epistemic and freshness semantics

The Twin projection now exposes explicit epistemic metadata on every projected
entity and freshness on query/health responses. Supported classes are
`ACTUAL`, `OBSERVED`, `INFERRED`, `PREDICTED`, `PLANNED` and `COUNTERFACTUAL`.
Recoverable consumer lag is `DEGRADED`; an event revision gap is fail-closed
`STALE` and carries a reconciliation reason. Unsupported epistemic values are
rejected before the projection is changed.

This is a local projection slice. It does not claim real NATS delivery,
PostgreSQL persistence, simulated-world integration, or integrated acceptance
under DEP-035.

## Verification

- `services/operational-twin/tests`: 9 passed
- Pyright: 0 errors
- Negative paths: unsupported epistemic class, revision gap, and degraded/stale
  visibility
