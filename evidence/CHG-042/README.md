# CHG-042 evidence applicability

This change corrects a WP-level dependency model. It does not claim that
`DN-CORE-CMDCON` is already `CONTRACT_READY` and does not create producer
evidence.

The first owner-executable slice of `WP-CORE-003` is the contract-first
producer slice for `DN-CORE-CMDCON`. Its required future evidence is:

- versioned hold, release, dispatch and maintenance-request command schemas;
- stable command/version identity;
- compatibility and example fixtures; and
- green producer/consumer contract tests.

The later execution capability remains responsible for idempotency, revision
preconditions and durable `CommandOutcome` persistence/query behavior.

No prior DEP-027 PASS evidence is invalidated: the canonical status remains
`NOT_READY` until the producer artifacts and accountable evidence exist.

The existing merged-binding provenance was refreshed to the current
`docs/04_Work_Breakdown_Structure.md` digest; no binding row or readiness
claim was added.
