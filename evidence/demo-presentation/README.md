# Demo presentation evidence

The live command writes these real artifacts here:

- `scenario-context.json` — the Core command and observed event chain before
  browser verification;
- `browser-result.json` and `browser-final.png` — written by the real Playwright
  login/UI run only after its assertions pass;
- `latest.json` and `verification.txt` — the compact current-run verification;
- `rehearsal-runs.json` — the two clean live rehearsal summaries and their
  durable identifiers;
- `runbook` and technical explanation: [`docs/demo/DEMO_RUNBOOK.md`](../../docs/demo/DEMO_RUNBOOK.md)
  and [`docs/demo/TECHNICAL_CHEAT_SHEET.md`](../../docs/demo/TECHNICAL_CHEAT_SHEET.md).

The current generated artifacts are from two clean live rehearsals. Both runs
used the real Keycloak login and the containerized Playwright fallback because
host Node/npm is not installed. The current `latest.json` and screenshot are
the second run; `rehearsal-runs.json` retains both run summaries.
The WP requirement mapping is `FR-UI-009`, `NFR-PERF-013`, and `NFR-UX-006`.

Existing real runtime fallback evidence from the proven current main slice is
also retained at:

- `evidence/WP-CORE-008/RUNTIME-E2E-2026-10-29.md`
- `evidence/WP-CORE-008/AV-SCEN-01-2026-10-29.json`
- `evidence/WP-CORE-008/AV-SCEN-01-CONSISTENCY-2026-10-29.json`

Those artifacts remain scoped to WP-CORE-008's implemented Core/outbox/
JetStream/Twin/BFF/UI slice and must not be described as full GS-01, production
security acceptance, or real-factory evidence.
