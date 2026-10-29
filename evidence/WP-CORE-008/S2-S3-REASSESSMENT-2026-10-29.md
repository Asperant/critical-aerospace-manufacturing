# Affected S2/S3 WP Reassessment — 2026-10-29

This is a narrow integration-impact assessment from the WP-CORE-008 runtime;
it does not mass-mark work packages or replace their owner DoD records.

| Work package | Classification | Basis and limit |
| --- | --- | --- |
| WP-CORE-002 | ACCEPTANCE_ONLY | Hold/dispatch legal and illegal transition behavior is exercised on real PostgreSQL through Core; its full owner DoD and trace closure remain unassessed. |
| WP-CORE-003 | ACCEPTANCE_ONLY | Durable command outcome, revision, idempotency identity, and dispatch command path are observed; broader command-execution acceptance is not closed by this demo. |
| WP-CORE-005 | ACCEPTANCE_ONLY | Transactional outbox mutation and publication are observed; its owner-local full DoD/evidence record is not replaced by this runtime record. |
| WP-EVT-003 | ACCEPTANCE_ONLY | The real JetStream consumer boundary and downstream adoption are exercised; the WP’s complete duplicate/crash/replay acceptance remains broader. |
| WP-TWIN-001 | ACCEPTANCE_ONLY | Real PostgreSQL projection, source-event ledger, revision, and catch-up are observed; the WP’s owner trace and complete DoD remain open. |
| WP-UI-002 | ACCEPTANCE_ONLY | Authenticated Keycloak browser access and real BFF/Twin-backed visible state are observed; this does not close the UI WP’s full DoD. |

No affected WP is promoted to `DONE_ELIGIBLE` by this evidence alone. The
corresponding `projectctl check-done` results remain `UNKNOWN` until each WP’s
own accountable DoD and trace evidence is assessed.
