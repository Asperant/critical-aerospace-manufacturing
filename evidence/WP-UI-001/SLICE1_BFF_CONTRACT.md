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
