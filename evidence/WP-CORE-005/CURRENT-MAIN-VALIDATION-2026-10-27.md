# WP-CORE-005 — exact merged-revision owner-local validation

Date: 2026-10-27
Owner: Asrın Dündar
Canonical WP: `WP-CORE-005`
Readiness control: `CHG-073 / CTRL-HOST-047`
Product merge SHA: `5e9544bcc1cbcd2dc57f85a529ecf53e0e79a5bf`
Product PR: `#171`

## Verification

- T1 CI run `40551363304` is bound to the exact product merge SHA.
- The real PostgreSQL 18 integration lane completed successfully for Core
  initial migration and persistence, including the transactional Core path
  exercised by the merged WP-CORE-005 implementation.
- Contract, static and unit jobs passed on the same exact product merge SHA.
- The focused Core integration suite covers accepted mutation plus durable
  outbox insertion, duplicate replay, conflicting idempotency, and rollback on
  event-constraint failure.
- The product PR checks and the control PR checks passed; the later control
  change only corrected the projectctl precision expectation from 173 to 167.

## Readiness boundary

This is sufficient evidence for the owner-local `DEP-022` predicate at
`COMPONENT_READY`. It does not claim NATS/relay delivery, consumer projection,
effect verification, `DEP-023`, `DEP-024`, `DEP-025`, or work-package DONE.

The shared CI run continued into unrelated browser acceptance after the Core
PostgreSQL steps passed; no overall CI success or browser result is claimed by
this artifact.
