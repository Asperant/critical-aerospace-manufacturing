# WP-CORE-003 local verification

This record contains only verification actually executed on the WP branch.

## Passed

- `uv run --project ci --locked python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests -m 'not integration' -q` — 261 passed, 33 deselected.
- `uv run --project ci --locked python -m pytest -c ci/pyproject.toml ci/tests/test_core_command_contract.py -q` — 3 passed.
- `uv run --project ci --locked pyright --project services/manufacturing-core/pyrightconfig.json` — 0 errors, 0 warnings.
- `uv run --project ci --locked ruff check services/manufacturing-core/src services/manufacturing-core/tests ci/tests/test_core_command_contract.py` — pass.
- `uv run --project ci --locked python ci/scripts/check_contracts.py` — 19 schemas and 8 instances validated, pass.
- `PYTHONPATH=packages/contracts/src uv run --project ci --locked python -m cap_contracts.ci_gate` — pass after the contract authority binding was committed.

## Not executed

- Real PostgreSQL migration/persistence tests: `CI_PG_DSN` and explicit `CORE_TEST_DISPOSABLE=1` were unavailable in the workspace. The test fixture failed closed as designed.
- Automation consumer acceptance, `DEP-027` integration evidence and `DEP-028` Core transition integration evidence: external integration-stage evidence is not locally claimable.

This artifact does not claim `CONTRACT_READY`, `INTEGRATION_READY`, `VERIFIED` or `DONE`.
