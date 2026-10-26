# WP-CORE-007 owner-scope evidence

This evidence records only work executed on the WP branch. It does not claim
shared-host or integration readiness.

## Implemented owner scope

- Alembic is the canonical migration runner, with migration ledger status
  inspectable through the explicit Core migration DSN;
- role bindings are declarative and credential-free;
- role application requires exactly `core`, `twin`, `automation` and `ai`,
  verifies restricted existing roles and schema ownership, and emits only
  same-schema grants;
- CI integration writes a versioned migration-status artifact after the
  disposable PostgreSQL migration fixture succeeds.

## Focused verification

- role-matrix and Core domain unit tests: executed locally;
- Ruff and Pyright: executed locally through the pinned CI environment;
- real PostgreSQL migration/rerun/checksum/authorization suite: required on the
  CI integration path; no local shared database or credentials were used.

## Pending

- real `twin`, `automation` and `ai` service-role bindings are not invented;
  their integration evidence requires explicit platform-provided identities.
- DEP-007 shared-host/integration readiness is not claimed.
