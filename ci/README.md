# CI — tiered pipeline (WP-CICD-001)

Owner: Yavuz (Platform Engineering, Delivery & Reliability). Sources: 01 Item 41
(CI), Item 61 (uv, Ruff, Pyright), NFR-DX-006, FR-PLAT-004 (CI half).

## Tiers

| Tier | Where | Job / command | Blocks merge? |
|---|---|---|---|
| T0 developer feedback | your workspace | the same commands as below | no — local success is not merge authority (Item 41 §2) |
| T1 `t1-static` | GitHub Actions | `static_ratchet.py check` (Ruff lint + format, Pyright), frontend lint, format, type-check and build | via `ci-gate` |
| T1 `t1-unit` | GitHub Actions | flake policy, CI tooling tests, projectctl + host tests, frontend component tests | via `ci-gate` |
| T1 `t1-contract` | GitHub Actions | `check_contracts.py` (JSON Schema contracts), Operations BFF v1 contract tests + Pyright | via `ci-gate` |
| T1 `t1-integration` | GitHub Actions | REAL PostgreSQL 16 + NATS JetStream smoke | via `ci-gate` |
| T1 `ci-gate` | GitHub Actions | fails unless all four jobs ran and succeeded | **yes** (required check) |
| T1 `projectctl` | GitHub Actions (`projectctl.yml`) | validate, catalog lint, hygiene | **yes** (required check) |

`projectctl.yml` is intentionally unchanged: the Plane transition helper
(`tools/host/plane-transition`) binds to its job and step names.

## Running the same checks locally (T0)

```bash
uv sync --project ci --locked                       # exact pinned toolchain (ci/uv.lock)
export PYTHONPATH=ci:ci/scripts
uv run --project ci python ci/scripts/static_ratchet.py check
uv run --project ci python ci/scripts/check_flake_policy.py
uv run --project ci python -m pytest ci/tests -p pytest_quarantine
uv run --project ci python -m pytest tools/projectctl/tests -q -p pytest_quarantine
uv run --project ci python ci/scripts/check_contracts.py
ci/scripts/integration_services.sh up && eval "$(ci/scripts/integration_services.sh env | sed 's/^/export /')"
uv run --project ci python -m pytest ci/integration -m integration -p pytest_quarantine
ci/scripts/integration_services.sh down
```

On the shared host, coordinate before starting the integration containers
(TEAM_WORKFLOW / guide §11). They bind only to 127.0.0.1 on ports 55432/54222.

## Static ratchet

Rules live in `ruff.toml` and `pyrightconfig.json` — never in a home directory
or IDE (Item 41 §17). Existing findings are recorded per file and per rule in
`ci/static_baseline.json` (Item 41 §21):

* a count may only stay equal or go down; any increase fails;
* a file not in the baseline (all new code, including `ci/`) must be clean;
* `ci/` is type-checked in Pyright **strict** mode;
* a formatted file must stay formatted;
* tool versions are part of the baseline; upgrading Ruff/Pyright is a separate PR.

When you fix findings, tighten the baseline in the same PR:

```bash
uv run --project ci python ci/scripts/static_ratchet.py update
```

`update` refuses to record regressions. Never edit the JSON by hand.

## Flaky tests (NFR-DX-006)

A flaky test is a defect. Retry-until-green is forbidden: rerun plugins, retry
actions and `continue-on-error: true` fail `check_flake_policy.py`. To
quarantine temporarily, add an entry to `ci/flaky_tests.yaml` with owner,
issue, reason, start, expiry (≤ 14 days) and release impact. The test still
runs (XFAIL); expired or incomplete entries fail the gate. `unittest`-based
host tests are not covered by the pytest plugin (known limitation).

## Required checks and branch protection

`ci/required_checks.json` defines the required checks (`ci-gate`, `projectctl`)
with 0 required approvals (CHG-018). Status: **NOT_APPLIED** — GitHub returns
HTTP 403 for branch protection on this private repository under the current
plan (CTRL-PM-012). After the repository owner enables a supporting plan:

```bash
ci/scripts/apply_branch_protection.sh            # dry run: prints the request
ci/scripts/apply_branch_protection.sh --apply    # owner/admin session only
```

Record the response under `evidence/WP-CICD-001/`.

## Not in this WP

CD to INTEGRATION and DeploymentRecords (WP-CICD-002, TEST-PLAT-CD,
INSP-DEP-HOST), SBOM/scanning/SHA-pinned actions (WP-CICD-004), untrusted fork
isolation (WP-CICD-006), T2/T3 scheduled suites and the test-tier policy
document (WP-TEST-001).
