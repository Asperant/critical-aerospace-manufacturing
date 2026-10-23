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
