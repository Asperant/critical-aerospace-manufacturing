# WP-UI-001 — developer-side closeout

Owner: Asrın Dündar (Asperant). Branch: `wp/WP-UI-001-command-center-shell-bff`.
PR: https://github.com/Asperant/critical-aerospace-manufacturing/pull/39

This closeout covers everything the owner can execute for WP-UI-001 without a real
Core, Twin, identity provider or integrated scenario. Earlier slices are recorded
in `SLICE1_BFF_CONTRACT.md`; this one adds the browser acceptance, the BFF
observability required by DOD-WP-06, and the NFR-PERF-014 measurement.

## What was added last

- `services/operations-bff/e2e/harness.py`: one real `operations-bff` process over
  HTTPS that also serves the built shell from the same origin. Its only fakes are
  the external boundaries: a scripted identity provider port (checks PKCE and
  nonce) and fixture-backed Core and Twin read ports. `/__control/*` routes exist
  only in this harness.
- `services/command-center-web/e2e/command-center.spec.ts` (Playwright, Chromium
  and Firefox, no retries): unauthenticated overview; sign in through the BFF
  redirect chain (`/v1/session/login`, scripted authorize, `/v1/session/callback`)
  with a `Secure` `HttpOnly` `SameSite=Lax` cookie; authenticated session; world
  selection and rendering of items, freshness, sources and metadata; 503 with an
  explicit unavailable state and recovery; stale freshness; 401 returning to the
  signed-out UI; sign out with the session's CSRF value and a CSRF-less logout
  refused with 403; root redirect and not-found navigation; and a boundary test
  that every request stays on the BFF origin, no WebSocket opens, no storage or
  page content holds a credential, and no response contains a provider token.
  Run in `t1-integration`.
- BFF observability (DOD-WP-06): one JSON access record per request
  (`operations_bff.access`: method, route template, operation id, status, outcome,
  duration, correlation id; never query, cookie, header or body), a server-assigned
  `X-Correlation-Id` reused by error envelopes and overview metadata and passed to
  every read port, and an operational `GET /healthz` that reports process and
  configuration health without calling any backend.
- `e2e/bench.spec.ts` (`npm run bench:ui`, opt-in): the NFR-PERF-014 measurement.

## NFR-PERF-014 measurement — engineering measurement, not final acceptance

`docs/01` states the requirement ("primary route SHOULD become actionable at
p95 ≤ 3 s after warm application startup on the accepted LAN/client profile") and
no method, boundary or sample size; `BENCH-PERF-UI` is an EVALUATION-tier
benchmark. The method below is therefore this task's own documented choice.

- Boundary: navigation start of `GET /overview?world_id=…` in a fresh browser
  context (empty cache, signed-in session cookie, warm BFF process) until the
  populated "Needs attention" list first exists in the DOM.
- Samples: 100 per browser after 10 discarded warm-up runs; percentiles by
  nearest rank. Source revision `c109f9d143dd968b913efa80b328555c77bb098c`.
- Environment: development host (Intel Core i7-9700K, 8 cores, 30 GiB), loopback
  HTTPS to one process, scripted identity provider, fixture Core and Twin.

| Browser | n | min | p50 | p95 | p99 | max | vs 3000 ms |
|---|---|---|---|---|---|---|---|
| Chromium 156.0.8078.4 | 100 | 60 ms | 65.7 ms | **68.2 ms** | 69.7 ms | 69.7 ms | PASS |
| Firefox 157.0 | 100 | 75 ms | 87 ms | **98 ms** | 115 ms | 116 ms | PASS |

Raw results: `bench-ui-chromium.json`, `bench-ui-firefox.json`. These numbers prove
the shell and BFF path add little latency; they do not seal NFR-PERF-014. The
accepted LAN/client profile, real Core and Twin data volumes, a real identity
provider round trip and the integration environment are absent, so the canonical
measurement (DOD-WP-08/NFR-driven, correct environment and profile) is still
outstanding.

## Verification at the final source (c109f9d)

Frontend from a locked clean install: contract drift check, ESLint, Prettier,
TypeScript, 85 component and unit tests, production build, Playwright 28 of 28
(14 per browser). BFF: 218 tests, Ruff, Pyright 0 errors, `check_contracts.py`,
26 CI tooling tests, `static_ratchet`, workflow YAML. GitHub Actions results for
the final head are recorded in PR #39, not here.

## Trace (DOD-WP-02)

FR-UI-001 REALIZED_BY `services/command-center-web/src/**` (shell, session and
overview clients, generated contract types) and `services/operations-bff/**`
(contract `bff.operations-bff.v1`, session, login, OIDC adapter, overview path,
transport, composition). NFR-PERF-014 REALIZED_BY the same production build and
BFF path. VERIFIED_BY: TEST-UI-BROWSER at the harness boundary (Playwright specs
above), the BFF contract and runtime suites, the component suites, and
BENCH-PERF-UI as an engineering measurement. E2E-01, AV-SCEN-01 and DEMO-GS01-001
remain `NOT_YET_EXECUTED`. Coverage is advanced to IMPLEMENTED only; no requirement
is marked VERIFIED, and no evidence source, canonical requirement or DoD is
rewritten to fit the outcome.

## Acceptance classification

See `FINAL-ACCEPTANCE-GAPS.md` for each item and the blocking criterion. DOD-WP-05
and DOD-WP-12 final acceptance require attributable real integrated and
post-merge evidence that development fixtures cannot supply. Proposed post-merge
state: VALIDATING plus orthogonal BLOCKED, classified
`WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE`; never DONE from this
evidence.
