# CTRL-HOST-036 — DEP-021 current-main edge binding

## Disposition

`DEP-021` is `READY` at `CONTRACT_READY` for the bounded initial consumer slice
of `WP-EVT-001` and `WP-EVT-002`. The predicate is the published
`core.order-query.v1` contract: opaque nonblank entity IDs and per-entity
revisions, ordered re-entrant route visits, normal and reentrant fixtures, and
green producer contract tests.

This is an edge-specific binding. It does not reuse or generalize the existing
`DEP-018` consumer-edge claim, and it does not certify global
`DN-CORE-CONTRACTS`, domain events, the outbox, broker/transport readiness,
commands, or full `DN-EVT-CONTRACTS` readiness. `DEP-031` remains separate.

## Current-main verification

- Verified main: `30c92c13f71e1a021f17df1e55d2ac1eac79f03d`
- Producer: `WP-CORE-001`, PR #24, merge
  `ad30bc67077bd0fb6009efdc85f8ec20649d99ce`
- The producer merge is an ancestor of verified main.
- Producer files and exact Git blobs are listed in
  `evidence/readiness/DN-CORE-CONTRACTS-DEP-021.json`.
- Focused current-main run:
  `uv run --project ci --locked python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/test_query_contract.py -q`
  — `34 passed`.
- The broader current-main contract/envelope regression run also passed:
  `351 passed` across the registry, compatibility, authority and envelope test
  families.

## Limits

No outbox, NATS/broker, event-payload, command, HTTP, production transport or
integrated acceptance claim is made. The fixtures are synthetic development
fixtures, not factory observations. This evidence changes only the canonical
dependency projection needed for the exact DEP-021 start gate.
