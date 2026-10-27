# CTRL-HOST-038 — DEP-031 current-main edge binding

DEP-031 is READY at CONTRACT_READY for the bounded Core domain-event contract
set: versioned payload schemas, canonical producer/event declarations,
Twin-relevant fixtures and green producer/consumer boundary tests.

- Current main: `5462191dc80496fede955d070d13047715b16052` (PR #160 merge)
- Producer PR #73 merge: `d8388a7e6c7f5c93ffc3c4343bbe6246a5d0269f`
- Producer PR #76 merge: `9db6a1080b8604a36a4629d85c8f844b57879cd6`
- Both merges are ancestors of current main and were authored by Asperant.
- `ci/tests/test_core_domain_event_contracts.py`: **7 passed**.
- PR #154 required checks: **PASS** (`ci-scope`, `projectctl`, `t1-contract`,
  `t1-static`, `t1-unit`, `ci-gate`); `t1-integration` correctly skipped for
  this contract-only change.
- Bound contracts: `core.lot-held.v1` and `core.lot-dispatch-authorized.v1`,
  including payload schemas and Twin fixtures.

This edge-specific result does not certify the full event spine, outbox, broker
delivery, envelope transport, integration readiness or WP-TWIN-001 completion.
