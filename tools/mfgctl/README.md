# mfgctl — developer and operator CLI (WP-PLAT-002)

`mfgctl` is the canonical high-level developer entry point (01 Item 74, DX-INV-02).
It is thin orchestration and diagnostics over Docker Compose, uv and the test
runners; it owns no business logic, and the underlying tools stay usable directly
(DX-INV-03/04).

## Run it

`mfgctl` is installed (editable) into the locked CI toolchain, so the same command
works on every machine and in CI:

```bash
uv sync --project ci --locked              # once, or after ci/uv.lock changes
uv run --project ci --locked mfgctl --help
uv run --project ci --locked mfgctl doctor
uv run --project ci --locked mfgctl doctor --json
```

The repository root is found from the current directory; `MFGCTL_REPO_ROOT`
overrides it and must point at the root (no silent fallback, DX-INV-10).

## Commands

| Command | Slice | Status |
|---|---|---|
| `doctor [--json]` | A | available |
| `bootstrap`, `check --fast/--pr`, timing records | B | planned |
| `profile`, `smoke`, `scenario`, `diagnose bundle` | C | planned (Compose profiles arrive with WP-PLAT-001) |

### `mfgctl doctor`

Read-only diagnosis (DX-INV-06): it never changes the repository, containers or
your configuration. Each check reports `OK`, `WARN` or `FAIL`; every WARN/FAIL
prints a remediation.

| Check | FAIL when | WARN when |
|---|---|---|
| git | Git missing, not a work tree, or "dubious ownership" | — |
| python | interpreter is not Python 3.11 | — |
| uv | uv missing | version differs from `UV_VERSION` in `.github/workflows/ci.yml` |
| docker | CLI missing or daemon unreachable | — |
| compose | Compose v2 plugin unavailable | — |
| disk | < 5 GiB free | < 20 GiB free |
| ports | — | a port used by `ci/scripts/integration_services.sh` is busy |
| lock | `ci/uv.lock` does not match `ci/pyproject.toml` | lock check timed out / skipped |

Exit codes: `0` no failure (warnings allowed), `1` at least one check failed,
`2` mfgctl could not run (for example outside the repository).
`--json` prints schema `mfgctl.doctor/v1` with `status`, `duration_ms` and every check.

## Tests

```bash
PYTHONPATH=ci:ci/scripts uv run --project ci --locked python -m pytest tools/mfgctl/tests -p pytest_quarantine
```

The tests replace the machine with a fake command runner (TEST-PLAT-FABCTL,
boundary mode FIXTURE_ALLOWED) and include the negative paths: missing tools,
unreachable daemon, wrong Python, stale lock, timeouts, low disk and busy ports.
