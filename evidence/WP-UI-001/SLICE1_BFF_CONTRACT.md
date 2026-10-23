# WP-UI-001 slice 1: BFF contract surface

Status: IMPLEMENTED, focused contract tests executed locally. Not merged,
not CONTRACT_READY, no integration or milestone evidence. WP-UI-001 remains
unfinished; shell, auth/session, navigation and the startup measurement are
not started.

Scope delivered (canonical task: "define BFF surface from view needs"):

- `services/operations-bff/contracts/v1/`: OpenAPI 3.1 contract, four JSON
  Schemas, one synthetic normal fixture and a README with the registry fields.
- `services/operations-bff/tests/test_contract_v1.py`: contract tests.

Checks run on the development host (Python 3.11 CI toolchain):

- `pytest -c services/operations-bff/pyproject.toml services/operations-bff/tests`
- `ruff check`, `ruff format --check` and `pyright` for `services/operations-bff`
- `ci/scripts/check_contracts.py`: PASS (8 schemas, 2 instances)
- `ci/scripts/static_ratchet.py check`: FAIL with 16 pyright regressions, all in
  `tools/mfgctl`; the count is identical with this change stashed, and none is in
  `services/operations-bff`

Not run: CI workflow, browser tests, benchmarks (`BENCH-PERF-UI`), integration
scenarios. The new tests were not in CI at commit 2ad0f89.

Open points for the owner: `meta.revision` as a composed-view token, stream
transport ADR, authentication scheme, and whether further views are added
before DN-UI-BFFCON is declared CONTRACT_READY.

CI wiring (follow-up commit): the `t1-contract` job in `.github/workflows/ci.yml`
now also runs the Operations BFF pytest suite and its Pyright config, so
`ci-gate` covers them. Local verification of the same commands: 15 tests passed,
Pyright 0 errors, `check_contracts.py` PASS, `ci/tests` pass. `static_ratchet.py
check` still reports the same 16 pre-existing `tools/mfgctl` Pyright regressions
and none elsewhere; they were not modified. The GitHub Actions run itself is not
yet observed.

## Slice 2: session contract and session-derived ActorContext

Contract-only addition to the same v1 draft (`bff.session.v1`): `browserSession`
cookie and `csrfToken` header schemes, OIDC login/callback/session/logout
operations, `UnauthorizedError` / `ForbiddenError` responses, `SessionActor` and
`ActorRef` shapes, `x-bff-actor-context`, a recursive key restriction on command
`parameters`, `acted_as` on the command receipt, and `session.normal.json`.
No OIDC provider integration, token exchange, runtime, shell or routes exist.

Local verification: 21 contract tests pass (6 new groups for security schemes,
anonymous 401, payload injection, session fixture, receipt actor), Ruff lint and
format, Pyright 0 errors, `check_contracts.py` PASS (9 schemas). The CI run for
this commit is not yet observed. `static_ratchet` status is unchanged and was
not rerun for this slice.

## Slice 3: framework-neutral session runtime foundation

Canonical stack (02 technology baseline): Python with FastAPI as a transport-only
framework and Pydantic; domain/application layers carry no FastAPI dependency.
This slice therefore adds only stdlib Python under
`services/operations-bff/src/operations_bff/` and no FastAPI adapter yet, since
that needs a change to the locked CI toolchain.

Added: opaque server-side session manager with an in-memory store port (records
keyed by a SHA-256 digest of the cookie value), bounded lifetimes (absolute cap
12 h, idle and rotation intervals within it; defaults 8 h / 30 min / 15 min are
provisional), rotation that never extends absolute expiry, fresh id on login and
logout invalidation, CSRF check on state-changing methods (constant time), typed
`Unauthorized` 401 / `Forbidden` 403 / `BadRequest` 400 whose envelopes validate
against the contract schemas, session-derived `ActorContext`, and refusal of
actor, role or identity keys in payloads and headers. `AuthenticatedIdentity`
has no token fields, so no access, refresh or bearer token can reach a response.

Not done: OIDC provider contact, code exchange, HTTP adapter, persistence,
broker or database access, authorization decisions, shell, routes.

Local verification: 51 tests pass (30 new), Ruff lint and format, Pyright 0
errors. CI for this commit is not yet observed.

## Slice 4: FastAPI transport adapter for the session primitives

Dependencies (repository workflow: `ci/pyproject.toml` plus `uv lock --project ci`,
consumed by `uv sync --project ci --locked`): `fastapi==0.142.4`,
`httpx==0.28.1` (TestClient; already in the lock) and `starlette==1.7.0` (pinned
so the resolver does not take 1.9.0, released 2026-10-18). Lock additions:
fastapi, starlette, opentelemetry-api.

Wired: `GET /v1/session` (`getSession`) and `POST /v1/session/logout` (`logout`)
in `src/operations_bff/api.py`, the only module importing FastAPI. Both call the
existing `authenticate_request`; the adapter maps `BffError` to the contract
envelopes with a server-generated correlation id. Generated docs and
`/openapi.json` are disabled; the contract file stays the API description.
Cookie `cap_session`: HttpOnly and Secure are always on and not configurable;
`CookieSettings.same_site` (strict or lax) is required configuration with no
default; Max-Age is the remaining session life; logout clears the cookie. Cookie
write is implemented as `write_session_cookie` for the later login slice and is
only exercised by a unit test, since no route sets it yet.

Not wired: startLogin, completeLogin, queries, commands, rotation on read, OIDC,
tokens, shell, routes, broker or database.

Local verification with the CI commands (`uv run --project ci --locked`): 67
tests pass (16 new transport tests), Ruff lint and format, Pyright 0 errors,
`check_contracts.py` PASS, `ci/tests` 26 passed, `static_ratchet check` PASS (the
earlier 16 mfgctl findings came from an unsynced local environment). One
Starlette deprecation warning about `httpx` in TestClient (it prefers `httpx2`)
is unaddressed. CI for this commit is not yet observed.

## Slice 5: OIDC login-flow skeleton behind an IdP port

Canonical basis (02, Authentication and Browser/BFF Security): OIDC/OAuth2 flow
run by the BFF, no custom protocol, server-validated identity, session rotation on
login, claims are input and never a decision. The documents name no PKCE, state
or nonce rules; those follow the OAuth 2.0 / OIDC authorization-code standard
and were requested for this slice.

Added in `src/operations_bff/`: `idp.py` (port `IdentityProvider` with
`authorization_url` and `complete`, returning only an `AuthenticatedIdentity`;
errors `IdentityProviderError` and `IdentityProviderUnavailable`), `login.py`
(`LoginService`, single-use login transactions with S256 PKCE verifier, state and
nonce, in-memory store, pending cap and TTL up to 15 min), `LoginConfig` and the
`cap_login` binding cookie name in `config.py`, `LoginRejected` (401) and
`Unavailable` (503) in `errors.py`, and `startLogin` / `completeLogin` routes in
`api.py`, mounted only when a `LoginService` is supplied.

startLogin: 302 to the provider URL plus the `cap_login` cookie. completeLogin:
spends the transaction first, then checks expiry and browser binding, calls the
port, accepts only a complete `AuthenticatedIdentity`, creates the session (any
previous session is ended), writes `cap_session` through `write_session_cookie`,
clears `cap_login` and redirects to a configured same-origin path. Failures are
the contract envelopes: 401 rejected, 503 provider unavailable, 400 invalid
parameters. No concrete provider, URL, secret or token handling exists.

Contract change made here: `startLogin` now declares the `Set-Cookie` header.
`BadRequest` is now generic (`INVALID_REQUEST`); authority refusal moved to
`AuthorityRejected`.

Local verification with the CI commands: 97 tests pass (30 new), Ruff lint and
format, Pyright 0 errors, `check_contracts.py` PASS, `ci/tests` 26 passed,
`static_ratchet check` PASS. Not done: a real provider adapter, token validation,
persistent stores, rotation on read, shell, routes. CI for this commit is not yet
observed.

## Slice 6: OIDC provider adapter (Keycloak) behind the IdentityProvider port

Canonical basis: Keycloak is the selected self-hosted identity provider using
OIDC/OAuth2 for user authentication (01 Items 158 to 162, 02 Authentication);
its identity and role claims are input, never the authorization decision. The
documents fix no realm, issuer, client type, client identifier, redirect URI or
Keycloak version, and give the Keycloak runtime to the platform owner. Those are
therefore runtime settings here and nothing provider specific is hard-coded.

Added: `src/operations_bff/oidc.py` with `OidcSettings` (explicit settings,
`from_environ` reading `OPERATIONS_BFF_OIDC_*`, secret optional and never in
`repr`) and `OidcIdentityProvider`. Discovery is read from
`<issuer>/.well-known/openid-configuration` and keys from its `jwks_uri`, both
cached with a TTL and a rate-limited refetch on an unknown `kid`. Authorization
URL carries state, S256 challenge and nonce from the existing login flow. The
code is exchanged server side; the ID token is validated for signature
(asymmetric allow-list, `none` and HMAC refused), issuer, audience (`azp` when
several), expiry, issued-at, not-before, subject and nonce, then discarded.
Access and refresh tokens are never read. Discovery documents with a different
issuer, a non-https endpoint or no S256 support are refused. Provider rejection
maps to `IdentityProviderError` (401), network failures, 5xx and discovery or
key outages to `IdentityProviderUnavailable` (503). Roles come from a
configurable claim path (default `realm_access.roles`) and the environment id
from settings, so the Keycloak mapper must put roles into the ID token.
`LoginService.start` now calls the provider before storing the transaction and
maps an outage to 503.

Dependencies (locked): `pyjwt[crypto]==2.15.1`, `cryptography==50.0.2`.

Not done: wiring the adapter and settings into an application entry point,
plain-http development issuer, Keycloak realm and client provisioning, any live
provider call, token refresh, persistence, shell, routes.

Local verification with the CI commands: 146 tests pass (49 new), Ruff lint and
format, Pyright 0 errors, `check_contracts.py` PASS, `ci/tests` 26 passed,
`static_ratchet check` PASS. Tests use `httpx.MockTransport` and generated RSA
keys only. CI for this commit is not yet observed.

## Slice 7: composition root and entrypoint

Added `src/operations_bff/composition.py` (`RuntimeSettings.from_environ`,
`ConfigurationError`, `build_app`) and `src/operations_bff/main.py`
(`create_app()`, an ASGI factory that reads the process environment). It is the
only module that imports the OIDC adapter; the entrypoint is the only one that
reads `os.environ`. `api.create_app` gained an optional `lifespan` so the HTTP
client created by the root is closed on shutdown.

Configuration (all read from the environment, nothing committed): the
`OPERATIONS_BFF_OIDC_*` settings of slice 6 plus
`OPERATIONS_BFF_COOKIE_SAMESITE` (strict or lax),
`OPERATIONS_BFF_SESSION_ABSOLUTE_TTL_SECONDS`,
`OPERATIONS_BFF_SESSION_IDLE_TTL_SECONDS` and
`OPERATIONS_BFF_SESSION_ROTATE_AFTER_SECONDS`. These and the OIDC issuer, client,
redirect URI and environment id are required and have no defaults, so the
owner-level SameSite and lifetime decisions cannot be hidden. Optional with
bounded defaults: `OPERATIONS_BFF_LOGIN_TTL_SECONDS`,
`OPERATIONS_BFF_LOGIN_MAX_PENDING`, `OPERATIONS_BFF_POST_LOGIN_PATH` (`/`). All
problems are reported together by setting name and never include the client
secret. Building the app makes no network call.

Known limits: sessions and login transactions are in memory, so only one
process can serve them; rotation on read is still not wired; no ASGI server
dependency was added, so the factory is run by whichever server the deployment
uses.

Local verification with the CI commands: 181 tests pass (35 new), Ruff lint and
format, Pyright 0 errors, `check_contracts.py` PASS, `ci/tests` 26 passed,
`static_ratchet check` PASS. No broker or database module is imported, checked
statically and in a clean interpreter. CI for this commit is not yet observed.

## Slice 8: getManufacturingOverview query path

Canonical basis (02, operations-bff catalog and aggregation rules): the BFF
consumes backend Query APIs, requires `manufacturing-core` and treats the Twin,
Scheduler, AI and Vision services as degradable; it composes without creating a
new status, passes world, branch and `as_of` through, forwards the actor and
keeps the least-fresh marker. The documents do not bind a concrete backend Query
API for attention items, so the read ports stay abstract.

Added in `src/operations_bff/`: `overview.py` (port `AttentionReader`,
`OverviewQuery` carrying world, `as_of` and the session `ActorContext`,
`SourceSnapshot`, `OverviewService`) and the `GET /v1/overview` route in
`api.py`, mounted only when a service is supplied. Composition: sources sorted by
name, items ordered by contract kind then id, `meta.freshness` is the least fresh
source, `meta.as_of` the oldest source `as_of`, `meta.revision` a SHA-256 digest
of world and source revisions, `generated_at` from the clock, cursor pagination
bound to the view revision (a moved view gives 400 `STALE_STATE`). Authentication
runs as a dependency before query validation, so anonymous callers always get
401. No role filtering and no derived status exist. `BffError` gained optional
`details`.

Gap kept visible: the contract cannot show an unavailable source, and a missing
source must not read as nothing needing attention. Any unavailable or invalid
backend therefore returns 503 `DEPENDENCY_UNAVAILABLE` naming the sources, which
is stricter than the canonical degradable dependencies. Partial results need a
contract extension (a per-source availability field) and an owner decision. Real
Core and Twin adapters are integration work and the process entrypoint leaves the
route off until they exist.

Local verification with the CI commands: 208 tests pass (27 new), Ruff lint and
format, Pyright 0 errors, `check_contracts.py` PASS, `ci/tests` 26 passed,
`static_ratchet check` PASS. Tests use in-memory readers built from
`overview-query.normal.json`. CI for this commit is not yet observed.

## Slice 9A: frontend toolchain and minimum shell foundation

Canonical basis (01 Items 163 to 175 and Frontend CI 118 to 120, 146; 02 Command
Center architecture): TypeScript with strict configuration, React, Vite, React
Router, MUI Core, TanStack Query and Table, ECharts, generated OpenAPI clients,
and Playwright for browser tests; frontend CI carries format/lint, type-check
and production build, with an exact committed lockfile. The documents fix no Node
version, package manager, test runner, linter or package versions, and the
repository had no frontend before this slice. Those are therefore implementation
choices made here and open to owner review: Node 24.21.0 (Active LTS, pinned in
`.node-version`, `engines` `^24.15.0`), npm with a committed `package-lock.json`,
Vitest with Testing Library and jsdom, ESLint with typescript-eslint and the
React hooks rules, Prettier. Every dependency is pinned exactly and was
published at least two weeks before 2026-10-23. TypeScript is 6.0.3, not 7.0.2,
because typescript-eslint 8.71 supports `<6.1.0`. `.npmrc` sets
`ignore-scripts`, `engine-strict` and `save-exact`.

Host setup, no sudo and no global packages: the official Node 24.21.0 tarball
was verified against `SHASUMS256.txt` and unpacked to
`~/.local/opt/node-v24.21.0`; the shell profile and system packages are
untouched, so commands are run with that directory first on `PATH`.

Added `services/command-center-web/`: Vite and React bootstrap (`main.tsx`),
`App.tsx` with React Router, a root layout with banner and main landmarks, one
placeholder Overview page at `/overview` (the index redirects there), a not-found
page, strict `tsconfig.json`, and 8 tests: mounting, routes, and boundary checks
that no broker, database or identity-provider package is declared, every
dependency is pinned exactly, application code contains no network, storage or
credential access, and `index.html` loads nothing external. Nothing consumes
`/v1/session` or `/v1/overview` yet.

CI (existing tiers, no new job): `t1-static` now installs with `npm ci` and runs
lint, format check, type-check and production build; `t1-unit` runs the component
tests. `actions/setup-node@v4` follows the tag convention of `actions/checkout`.
`ci/README.md` is updated.

Local verification with a clean `npm ci`: ESLint, Prettier check, `tsc` and
production build pass, 8 tests pass; Python side unchanged (208 BFF tests, 26 CI
tooling tests pass). Not done: MUI, TanStack Query, generated API types,
Playwright, CSP and security headers, the Node setup action's behaviour on
GitHub, and any visual design. CI for this commit is not yet observed.

## Slice 9B: browser session consumption

Added to `services/command-center-web`: `scripts/generate-contract-types.mjs`
(json-schema-to-typescript 16.0.0, resolving the contract `$id` host from disk)
which generates `src/contract/generated.ts` from `session.schema.json` and the
`ErrorEnvelope` of `common.schema.json`, so contract types are not hand-copied
(01 Item 175). `npm run contract:check` fails on drift and runs in `t1-static`.
`src/session/sessionClient.ts` is the only code that touches the network: one
`GET /v1/session` with `credentials: "include"`, `Accept` as the only header and
no body, giving authenticated (200, checked at runtime as a `bff.session.v1`
with `derived_from` SESSION), unauthenticated (401) or an error (any other
status, network failure, non-JSON or malformed reply). `SessionProvider` holds
the state in memory (loading, authenticated, unauthenticated, error), aborts on
unmount and ignores late answers. The Overview page shows the server-derived
display name, actor id, roles (marked informational), environment and expiry,
a neutral "Sign-in required." state with no sign-in control, or an error. The
CSRF token is kept in memory and never rendered.

Not done: login and logout UI, overview data, streaming, navigation, MUI,
TanStack Query (a plain provider is enough for one request), visual design.

Local verification from a clean `npm ci`: contract check, ESLint, Prettier,
`tsc`, 41 tests and the production build pass; BFF side unchanged (208 tests,
Ruff, `check_contracts.py`, 26 CI tooling tests, `static_ratchet` pass). Tests
read the real `session.normal.json` contract fixture and assert: request shape,
401, error statuses, forged actor refused, no storage or cookie writes, no token
shown, and that `fetch` appears only in the session client with only `/v1/session`.

## Slice 10: browser integration (sign in, sign out, overview, navigation)

No BFF contract or runtime change was needed: `GET /v1/session` already returns
the session's CSRF value, which the browser keeps in memory and sends only as
`X-CSRF-Token` on logout. Everything below is in `services/command-center-web`.

- Sign in: a plain anchor to `/v1/session/login` (operation `startLogin`), shown to
  an unauthenticated user. It is a full browser navigation, so the BFF runs the
  provider redirects and the app never sees a code or token. A test ties the
  path and operation id to the OpenAPI file.
- Sign out: `signOut` posts `/v1/session/logout` with the cookie and the
  session's CSRF value. Success, or a 401 for an already-ended session, returns
  the UI to unauthenticated; any other outcome keeps the user signed in and says
  so. The server ends the session.
- Overview: `fetchOverview` calls `GET /v1/overview` with an explicit `world_id`
  taken from the URL (a small form selects it; none is invented) and the cursor
  when paging. Replies are checked at runtime against the contract shape. The page
  renders revision, as_of, generated_at, freshness, world, the per-source table
  and each attention item with kind, epistemic class, subject, source revision
  and freshness, and warns when freshness is not FRESH. States: idle, loading,
  ready, 401 (back to unauthenticated), 400 stale (reload), 400 invalid, 503
  (explicit unavailable state naming the sources, never an empty list), and error
  for network failures or malformed replies. "Load more" appends the next page.
- Navigation: root redirects to `/overview`; a primary nav with Overview; a
  header session area (name and Sign out, Sign in, or an error); a not-found page
  linking back.
- Types: `ManufacturingOverviewResponse` is now generated with the other
  contract types; `contract:check` runs in CI and in a unit test.

Local verification from a clean `npm ci`: contract check, ESLint, Prettier,
`tsc`, 85 tests and the production build pass. BFF side unchanged and passing:
208 tests, Ruff lint and format, Pyright 0 errors, `check_contracts.py`, 26 CI
tooling tests, `static_ratchet`, workflow YAML. GitHub Actions was deliberately
not consulted for this commit.

Remaining WP-UI-001 acceptance gaps, exactly:
1. Browser tests against a running BFF in Chromium-family and Firefox
   (`TEST-UI-BROWSER`, Playwright): not started; the current tests stub `fetch`.
2. Warm-start measurement to an actionable route, p95 at most 3 s on the accepted
   LAN and client profile (`NFR-PERF-014`, `BENCH-PERF-UI`): not started.
3. Integrated scenario evidence (`E2E-01`, `AV-SCEN-01`, `DEMO-GS01-001`): not
   executed; recorded as `NOT_YET_EXECUTED`.
4. Real backend adapters for the overview: only abstract ports and in-memory test
   readers exist, and the process entrypoint leaves `/v1/overview` unmounted.
   "UI shows real Twin state via BFF" (DEP-106) also depends on the Twin skeleton.
5. Live Keycloak: realm, client and role mapper provisioning (platform owner) and
   one real login. The adapter has only run against a local HTTP stand-in.
6. Owner decisions still open: session cookie SameSite (Strict or Lax) and the
   session lifetimes; partial-result representation for an unavailable source
   (needs a contract extension); the stream transport ADR; Node, npm, Vitest,
   ESLint and Prettier as the frontend toolchain.
7. Not built: realtime stream consumption, MUI, TanStack Query, ECharts, CSP and
   security headers, CORS and ingress for the same-origin assumption, a shared
   session store.
8. Process: the draft PR is not merged and merged is not done; DoD, post-merge
   validation and the owner's closeout assessment remain.
