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
