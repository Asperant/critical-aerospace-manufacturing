# WP-TEST-002 slice 1 — DEP-021 consumer contract suite

Added a current-main consumer-side contract suite for the exact DEP-021 slice.
Both normal and re-entrant `core.order-query.v1` fixtures are validated through
the registered contract boundary as producer and consumer; an unknown field is
rejected fail-closed. This reuses the canonical registry and Core-owned
fixtures rather than creating another schema source.

## Verification

- `ci/tests/test_wp_test_002_contract_suite.py`: 3 passed
- Existing registry/authority/compatibility/envelope focused suite: 318 passed
- Fixture-only contract evidence; no broker, database or integration acceptance
  is claimed.
