# WP-TWIN-001 — local projection slice

## Scope

Owner-executable local projection slice from commit
`127cfcef511dac839d96db531260184d507fd9e3`:

- service/package skeleton under `services/operational-twin`
- read-model, applied-event ledger and source-revision schema
- deterministic production/equipment/quality projection handlers
- duplicate, stale-order, gap, world and branch admission rules
- EVT-002 envelope validation and EVT-003 consumer adapter boundary
- read-only query/health surface and deterministic catch-up
- focused projection, readonly and negative-path tests

## Verification

Focused command:

```text
uv run --project ci --locked python -m pytest -c services/operational-twin/pyproject.toml services/operational-twin/tests -q
```

Result: `7 passed`.

## Explicitly pending

DEP-032 real NATS event-spine delivery and DEP-033 runtime PostgreSQL schema
migration were not claimed or executed. CHG-035 `BIND-EVT002-NATS-CONSUMER`
remains a future runtime binding obligation. Integrated scenario evidence is
therefore `NOT_YET_EXECUTED`; this artifact is local CI evidence only.
