# WP-CORE-005 — Core domain-event contract slice

Accountable owner: Asrın Dündar
Branch: `wp/WP-CORE-005-domain-event-contracts`
Source commit: `c8a0d3b` (`[WP-CORE-005] Register Core domain event payload contracts`)

## Owner-executable artifacts

- Registered `core.lot-held.v1` / `LotHeld.v1` with Core as canonical producer.
- Registered `core.lot-dispatch-authorized.v1` / `LotDispatchAuthorized.v1` with Core as canonical producer.
- Added closed, versioned payload schemas under `services/manufacturing-core/contracts/v1/`.
- Added deterministic TWIN-relevant fixtures containing actual versioned payloads.
- Extended the existing EVT-001 registry and producer-authority declarations; no parallel registry or envelope was introduced.
- Bound the payload declarations to the existing EVT-002 `event-envelope.v1` metadata boundary.

`OperationStarted.v1` is not included: the canonical producer is the simulator/core
integration path, not the Core producer scope implemented here.

## Trace and verification

| Scope | Artifact | Verification |
|---|---|---|
| Core accepted transition payloads | `lot-held.v1.schema.json`, `lot-dispatch-authorized.v1.schema.json` | `TEST-EVT-SCHEMA` registry/hash checks |
| TWIN consumer input | `lot-held.twin.json`, `lot-dispatch-authorized.twin.json` | producer and consumer boundary validation |
| Canonical producer authority | `producer-authorities.json` and registry declarations | registry authority and consumer checks |
| DEP-031 input evidence | versioned declarations, fixtures and hashes | focused contract test suite |

Focused verification:

```text
uv run --project ci --locked pytest -c ci/pyproject.toml \
  ci/tests/test_contract_registry.py \
  ci/tests/test_contract_ci_gate.py \
  ci/tests/test_contract_stream_catalog.py \
  ci/tests/test_core_domain_event_contracts.py -q
160 passed
```

## Explicitly pending

This evidence does not claim DEP-022 readiness or integrated acceptance. Real
PostgreSQL atomic outbox, runtime NATS publication, subject/stream binding,
runtime ACL enforcement, and TWIN runtime consumer integration remain pending.
The contract artifacts are available on this branch; DEP-031 should be reassessed
against the merged commit and current-head CI before being marked PASS.
