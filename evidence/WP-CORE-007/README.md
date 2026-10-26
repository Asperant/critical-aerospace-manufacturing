# WP-CORE-007 owner-scope evidence

This evidence records only work executed on the WP branch. It does not claim
shared-host or integration readiness.

Owner assessment at `41a6822`:

- Owner-executable implementation work: NONE.
- Local actionable work: NONE.
- The branch is not merge-ready because the required CI fast gate is blocked
  by the unrelated host/control-plane recovery-policy check
  `MERGED_BINDING_PROVENANCE_INVALID`; this WP does not modify control-plane
  policy.

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
- real PostgreSQL migration/rerun/checksum/authorization suite: passed in CI
  run `40250659891`, including the migration-status artifact; no local shared
  database or credentials were used.

## Pending

- real `twin`, `automation` and `ai` service-role bindings are not invented;
  their integration evidence requires explicit platform-provided identities.
- DEP-007 shared-host/integration readiness is not claimed.
- The same CI run's unit gate remains blocked by
  `test_generated_policy_pins_the_recovery_sources` with
  `MERGED_BINDING_PROVENANCE_INVALID`; remediation belongs to the control-plane
  owner and is intentionally not attempted here.
