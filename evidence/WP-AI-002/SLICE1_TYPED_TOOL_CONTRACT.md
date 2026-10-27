# WP-AI-002 — typed tool contract slice

## Scope

Requirement coverage: `FR-AI-002` (typed versioned interfaces) and `FR-AI-003`
(READ/SIMULATE/PROPOSE allowlist).
The pull request records this requirement impact explicitly for TL-13 review.

This slice publishes `ai.tool-interface.v1` with four explicit, versioned tool
surfaces:

- `core.order.read` — `READ`
- `twin.scheduling_snapshot.read` — `READ`
- `sim.recovery.counterfactual` — `SIMULATE`
- `ai.recovery.propose` — `PROPOSE`

The contract carries explicit `world_id`, stable tool/version identity and
typed inputs. The proposal surface contains evidence and base-revision binding
but no executable command fields.

## Authority boundary

The allowlist is deliberately limited to READ, SIMULATE and PROPOSE. Shell,
arbitrary SQL, credentials, broker administration and direct Core mutation are
not represented as tools. This contract does not grant AI execution authority
and does not claim orchestrator or RCA completion.

## Verification

- `ci/tests/test_ai_tool_contract.py`: 7 passed
- `ci/tests/test_contract_registry.py`: passed
- `ci/tests/test_contract_producer_authority.py`: passed
- `cap_contracts.ci_gate`: PASS, 5 validated, 0 failures
- `ci/test-strategy.json`: registered as `TEST-AI-002-001` in the unit tooling suite

The remaining WP-AI-002 typed clients, runtime allowlist enforcement and
orchestrator integration are separate work and are not claimed by this slice.
