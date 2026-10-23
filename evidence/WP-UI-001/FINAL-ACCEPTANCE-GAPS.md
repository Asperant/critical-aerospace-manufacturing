# WP-UI-001 — final acceptance gap assessment

Accountable owner: Asrın Dündar (Asperant). Assessed branch:
`wp/WP-UI-001-command-center-shell-bff`; assessed source `c109f9d143dd968b913efa80b328555c77bb098c`
plus this evidence. Result: NOT COMPLETE for DONE; developer implementation
complete. No DONE or readiness certification is made here.

## Blocking criterion and the exact missing evidence

`docs/08_Definition_of_Ready_and_Done.md` DOD-WP-05 requires cross-boundary
behaviour verified against real infrastructure, with no mocked broker, database
or identity in the acceptance path, plus post-merge validation on the target
environment and evidenced consumer usability. DOD-WP-12 forbids using a
development fixture as milestone or final evidence, and the F0 supplement requires
participation in a real integrated acceptance path (AV-SCEN / E2E). WP-UI-001
carries TEST-UI-BROWSER, E2E-01, AV-SCEN-01, DEMO-GS01-001 and BENCH-PERF-UI.

Everything executed so far uses a scripted identity provider and fixture Core
and Twin ports. The missing artifact is an attributable, source- and
environment-bound real run of the Command Center path: real Keycloak sign-in,
the overview served from the real Core and Twin Query APIs, within an integrated
scenario, plus BENCH-PERF-UI on the accepted LAN/client profile. Contract
fixtures and the Playwright harness cannot stand in for it.

## Item by item

| Item | Classification | Why |
|---|---|---|
| Playwright Chromium and Firefox against a real BFF process | Done before merge | Canonical TEST-UI-BROWSER browsers; reported at harness boundary only |
| DOD-WP-06 health, structured logs, correlation | Done before merge | Added and tested |
| Engineering NFR-PERF-014 measurement | Done before merge | Recorded, not sealed (see closeout) |
| BENCH-PERF-UI / NFR-PERF-014 on the accepted profile | Downstream acceptance | Needs the real environment and data |
| Real Core and Twin overview adapters | Downstream integration | Query APIs are not canonically bound yet; DEP-106 also needs the Twin skeleton (another owner) |
| Live Keycloak realm, client and role mapping | Downstream integration | Platform owner (Yavuz) runtime; adapter has run only against a local HTTP stand-in |
| E2E-01 | Downstream acceptance | Later checkpoint, producer WP-TEST-006 (Batuhan) |
| AV-SCEN-01 | Downstream acceptance | Integration scenario, producer WP-TEST-003 (Asrın) |
| DEMO-GS01-001 | Downstream acceptance | Formal clean-world demo, many producer WPs |
| Real-time stream transport | Outside WP-UI-001 completion | Transport ADR is open; contract carries message schemas only; no WP-UI-001 deliverable needs it |
| Shared session store | Outside WP-UI-001 completion | Platform/persistence decision; in-memory single process is documented |
| MUI, TanStack Query and Table, ECharts | Outside WP-UI-001 completion | Selected libraries for later UI work packages; no deliverable here needs them |
| CSP, ingress, CORS | Outside WP-UI-001 completion | Edge and platform scope; the same-origin assumption is documented |
| Partial or degradable overview contract | Outside WP-UI-001 completion | Needs a contract extension and owner decision; current fail-closed 503 is truthful |
| Frontend toolchain choices (Node, npm, Vitest, ESLint, Prettier) | Owner confirmation, advisory | Not fixed by canonical documents; recorded in evidence |

## DoD checklist

| Criterion | Assessment |
|---|---|
| DOD-WP-01 | Shell, BFF contract with fixtures, session and OIDC integration, routes and navigation exist with real references; source requirements implemented as far as backends allow |
| DOD-WP-02 | REALIZED_BY and VERIFIED_BY declared in the PR and closeout; coverage advanced to IMPLEMENTED only |
| DOD-WP-03 | Required gates must be green on the final head without retries or quarantine; result recorded in PR #39 |
| DOD-WP-05 | BLOCKED: real-infrastructure integrated and post-merge evidence absent |
| DOD-WP-06 | PASS locally: health surface, structured correlation logs, duration in every record |
| DOD-WP-12 | Honoured for evidence classification; BLOCKED for final evidence because only fixtures exist |

Zero development human approvals are required; reviewer presence is not the
blocker. Implementing the other services or changing the required acceptance
boundary is outside this work package.

Owner-executable implementation work after merge: NONE.
