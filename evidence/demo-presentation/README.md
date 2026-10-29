# Demo presentation evidence

The live command writes these real artifacts here:

- `scenario-context.json` — the Core command and observed event chain before
  browser verification;
- `browser-initial-result.json`, `browser-result.json`, `browser-initial.png`,
  `browser-anomaly.png`, and `browser-final.png` — written by the real
  Playwright login/UI stages only after their assertions pass;
- `latest.json` and `verification.txt` — the compact current-run verification;
- `rehearsal-runs.json` — the two clean live rehearsal summaries and their
  durable identifiers;
- `runbook` and technical explanation: [`docs/demo/DEMO_RUNBOOK.md`](../../docs/demo/DEMO_RUNBOOK.md)
  and [`docs/demo/TECHNICAL_CHEAT_SHEET.md`](../../docs/demo/TECHNICAL_CHEAT_SHEET.md).

The checked-in generated artifacts are from two clean WP-DOC-004 integrated
showcase rehearsals. Both used the real Keycloak login and the pinned
containerized Playwright runner; `rehearsal-runs.json` retains the durable
identities from both runs. Regenerate them with
`./tools/demo-runtime/demo.sh showcase` when a fresh presentation run is
needed; the command fails closed if the runtime or authenticated browser path
is unavailable.

The simulator operational-event contract has no event-ID field. The integrated
showcase therefore records its deterministic scenario/seed, replay digests,
and a derived trigger reference bound to the Core command's persisted
`causation_id`; it does not invent a simulator event ID. Vision remains an
explicitly bounded optional path and is not used by the primary showcase.
The WP requirement mapping is `FR-UI-009`, `NFR-PERF-013`, and `NFR-UX-006`.

Existing real runtime fallback evidence from the proven current main slice is
also retained at:

- `evidence/WP-CORE-008/RUNTIME-E2E-2026-10-29.md`
- `evidence/WP-CORE-008/AV-SCEN-01-2026-10-29.json`
- `evidence/WP-CORE-008/AV-SCEN-01-CONSISTENCY-2026-10-29.json`

Those artifacts remain scoped to WP-CORE-008's implemented Core/outbox/
JetStream/Twin/BFF/UI slice and must not be described as full GS-01, production
security acceptance, or real-factory evidence.
