# WP-UI-002 — manufacturing facility state and operational views

Baseline: current `origin/main` `dd2dfa3e6059c68db80c9980ffc22bed01009380`.
Branch: `wp/WP-UI-002-state-views`.
Requirements: `FR-UI-002`, `NFR-PERF-005`.
Owner-local implementation status: complete for the scoped product slice.
Final DONE status: not claimed.

## Implemented

- Added the closed `bff.facility-state.v1` response contract and synthetic
  fixture under `services/operations-bff/contracts/v1/`.
- Added the BFF's read-only Twin facility-state port and query service. Every
  request carries an explicit `world_id`; optional simulation run, branch and
  historical `as_of` values are forwarded to the port with the session-derived
  actor and correlation ID.
- Kept lot `lifecycle_state`, `execution_state` and `hold_state` independent;
  route visit identity and position remain explicit. No browser or BFF route
  mutates canonical manufacturing state.
- Added `GET /v1/facility-state` with no partial/empty success on an unavailable
  or invalid Twin snapshot. Existing BFF access logging, correlation headers,
  authentication and cache-control apply to the route.
- Added the Command Center facility view with equipment and lot tables, honest
  freshness display, URL-backed world selection, and bounded three-second
  polling through the BFF only. The browser holds no broker, database or
  identity-provider client.
- Updated generated frontend contract types and boundary checks.

## Trace and verification

| Requirement / verification | Evidence |
|---|---|
| FR-UI-002 | `facility-state.v1`, `FacilityStateService`, `OverviewPage` facility view, world-scoped client and browser tests |
| NFR-PERF-005 | Bounded polling implementation and a focused cadence test; final accepted LAN/integration p95 measurement remains pending |
| TEST-UI-BROWSER | 93 frontend tests, including facility rendering, malformed/unavailable responses, world binding and polling cadence |
| Contract validation | BFF contract/transport tests validate the new schema, fixture, OpenAPI path and negative paths |

The frontend local check passed: contract generation/check, ESLint, Prettier,
TypeScript, Vitest and Vite production build. The BFF local suite passed 228
tests, and Ruff check/format passed. The only observed warning is the existing
Starlette/httpx TestClient deprecation warning.

## Readiness and acceptance boundary

- `projectctl startability WP-UI-002` on the current baseline is `STARTABLE`.
- `DEP-105` is `READY` for the previously published session/overview contract
  slice. The additive facility-state path is covered by this WP's contract
  tests; readiness evidence for the changed OpenAPI blob must be refreshed at
  the merged current-main revision before a later readiness/merge gate.
- `DEP-106` is `NOT_READY` at `MILESTONE_EXIT` and is not a START blocker. Real
  Twin integration, real Keycloak, cross-service acceptance, AV-SCEN-01,
  DEMO-GS01-001 and the accepted-profile `BENCH-PERF-UI` run remain external or
  later-stage evidence gates.
- Synthetic fixtures are used only for deterministic local contract and browser
  tests. They are not real-factory data and do not certify final acceptance.

No requirement, dependency, architecture authority or readiness node was
silently redefined.
