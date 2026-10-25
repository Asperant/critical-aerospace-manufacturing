# WP-EVT-001 slice 1: contract registry layout, version rules and boundary validation

Status: IMPLEMENTED at unit/contract level on branch `wp/WP-EVT-001-event-contracts`. Accountable
owner: Asrın Dündar. Not integration, scenario or freeze evidence, and it certifies no readiness.

## START scope used

DEP-021 was accepted narrowly for this work package's START: `core.order-query.v1` (opaque
entity IDs and per-entity revisions, route and visit identity, request and response JSON Schemas,
the normal and reentrant fixtures, and the contract's registry declaration) as the first exemplar
for registry layout, version rules and boundary validators. It is not a global DN-CORE-CONTRACTS
CONTRACT_READY declaration and no Core file is changed. Registering the exemplar is a catalog
entry, not a readiness claim.

## Delivered

- `packages/contracts/` (`cap-contracts`, import `cap_contracts`)
  - `versioning`: contract ID `<family>.v<major>`; the successor rule (next major of the same
    family); the later-major rule used for deprecation replacements.
  - `registry`: declaration model (a subset of the 02 registry fields including exactly one
    canonical producer, contract type among the six classes, authority, sync semantics,
    deprecation), `Registry.load` (file name equals contract ID, only `.json` plus README),
    cross-declaration deprecation checks, and `Registry.verify` (files exist, SHA-256 match,
    schemas valid, every fixture validates).
  - `boundary`: `BoundaryValidator.validate` / `validate_request` for the producer and consumer
    roles; violations name JSON-pointer paths and keywords only, never payload values; every
    unverifiable case fails closed.
  - `registry/core.order-query.v1.json`: the exemplar declaration. README documents layout and rules.
- `ci/tests/test_contract_registry.py` (TEST-EVT-001-001): 98 unit/contract tests.
- `ci/pyproject.toml` pytest `pythonpath`, `pyrightconfig.json` include/extraPaths, and the
  `/packages/contracts/` CODEOWNERS route (owner Asrın, supporting reviewer Selman).

## Placement decision

The tests live in `ci/tests` and run in the existing `CI tooling tests` step. A dedicated CI
step would edit `.github/workflows/ci.yml`, a policy-pinned whole-blob source whose change
invalidates every released-wait proof and forces a policy refresh. The dedicated step is batched
with the compatibility-gate slice, which needs a CI change anyway.

## Checks run (development host, CI toolchain)

- `pytest ci/tests/test_contract_registry.py`: 98 passed.
- `ruff check` and `ruff format` on the changed files: clean. `pyright` with the root config
  (strict for `ci/`) and with `packages/contracts/pyrightconfig.json`: 0 errors.
- `check_test_strategy.py` and `projectctl validate`: see the commit; `git diff --check` clean.
- Not run: CI workflow, broad suites, integration.

## Not in this slice

The EVT envelope (WP-EVT-002), broker/NATS behaviour, Core command contracts, the outbox,
the compatibility/breaking-change detector in CI, canonical producer ACL generation,
INTEGRATION_READY or FROZEN behaviour, and the pre-freeze naming reconciliation.
