# WP-EVT-005 slice 1 — repository architecture boundary rules

Implemented `ci/scripts/check_architecture_boundaries.py` and connected it to
the `t1-static` CI job. The deterministic gate currently checks:

- every contract declaration has a unique ID and a registered canonical
  producer;
- non-Core service source cannot import private PostgreSQL/SQLAlchemy drivers
  or `manufacturing_core` private repository modules directly;
- service source cannot contain literal credential assignments.

The test suite covers the current repository and negative synthetic examples.
Runtime service identity authorization and real cross-service integration remain
outside this static slice and are not claimed by it.

## Verification

- `ci/scripts/check_architecture_boundaries.py`: PASS
- `ci/tests/test_architecture_boundaries.py`: 4 passed
- `ci/scripts/check_test_strategy.py`: PASS, 0 violations
- Ruff check/format: PASS
