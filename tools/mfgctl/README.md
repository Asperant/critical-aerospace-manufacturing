# mfgctl — developer and operator CLI (WP-PLAT-002)

`mfgctl` is the canonical high-level developer entry point (01 Item 74, DX-INV-02).
It is thin orchestration and diagnostics over Docker Compose, uv and the test
runners; it owns no business logic, and the underlying tools stay usable directly
(DX-INV-03/04).

## Run it

`mfgctl` is installed (editable) into the locked CI toolchain, so the same command
works on every machine and in CI:

```bash
uv run --project ci --locked mfgctl --help
uv run --project ci --locked mfgctl bootstrap     # prepare / refresh the toolchain
uv run --project ci --locked mfgctl doctor        # diagnose, changes nothing
uv run --project ci --locked mfgctl check --fast  # CI static tier locally
```

If the toolchain environment itself is missing or broken (for example created by
another Linux account), `uv run --project ci` cannot start. Run mfgctl from a
throw-away environment instead; it does not touch `ci/.venv`:

```bash
uv run --no-project --python 3.11 --with-editable tools/mfgctl mfgctl doctor
uv run --no-project --python 3.11 --with-editable tools/mfgctl mfgctl bootstrap
```

The repository root is found from the current directory; `MFGCTL_REPO_ROOT`
overrides it and must point at the root (no silent fallback, DX-INV-10).

## Commands

| Command | Slice | Status |
|---|---|---|
| `doctor [--json]` | A | available |
| `bootstrap [--dry-run]` | B | available |
| `check [--fast \| --pr]` | B | available |
| `timings [--json]` | B | available |
| `profile`, `smoke`, `scenario`, `diagnose bundle` | C | planned (Compose profiles arrive with WP-PLAT-001) |

Exit codes for every command: `0` success (warnings allowed), `1` a check or
step failed, `2` mfgctl could not run (outside the repository, unusable ci.yml).

### `mfgctl doctor`

Read-only diagnosis (DX-INV-06): it never changes the repository, containers or
your configuration. Each check reports `OK`, `WARN` or `FAIL`; every WARN/FAIL
prints a remediation. `--json` prints schema `mfgctl.doctor/v1`.

| Check | FAIL when | WARN when |
|---|---|---|
| git | Git missing, not a work tree, or "dubious ownership" | — |
| python | interpreter is not Python 3.11 | — |
| uv | uv missing | version differs from `UV_VERSION` in `.github/workflows/ci.yml` |
| venv | toolchain environment exists but its interpreter is unusable for this user | environment not created yet |
| docker | CLI missing or daemon unreachable (includes "not in docker group") | — |
| compose | Compose v2 plugin unavailable | — |
| disk | < 5 GiB free | < 20 GiB free |
| ports | — | a port used by `ci/scripts/integration_services.sh` is busy |
| lock | `ci/uv.lock` does not match `ci/pyproject.toml` | lock check timed out / skipped |

### `mfgctl bootstrap`

Prepares the locked toolchain with `uv sync --project ci --locked`. Idempotent
(DX-INV-05): a second run reports "no changes needed". It never starts the
platform runtime (§15) and never deletes anything: an unusable environment stops
bootstrap with the exact command to fix it (remove your own derived
environment, or set `UV_PROJECT_ENVIRONMENT` to a personal one when another
account owns it). `--dry-run` shows the plan without running `uv sync`.

### `mfgctl check`

Runs the CI commands locally (DX-INV-52). The commands are **read from
`.github/workflows/ci.yml`**, so local checks cannot drift from CI; if a job
disappears, check exits 2 instead of silently doing less.

| Tier | CI jobs run | Target |
|---|---|---|
| `--fast` (default) | `t1-static` (Ruff + Pyright ratchet) | NFR-DX-002: ≤ 90 s |
| `--pr` | `t1-static`, `t1-unit`, `t1-contract` | — |

`t1-integration` needs Docker services and is reported as **NOT RUN** with the
command to run it; it is never counted as passed. Every step runs even after a
failure, like independent CI jobs.

### `mfgctl timings`

Every command appends its duration and exit code to
`~/.local/state/mfgctl/timings.jsonl` (or `$MFGCTL_STATE_DIR`,
`$XDG_STATE_HOME/mfgctl`); `MFGCTL_TIMINGS=off` disables it. Records live outside
the repository, so doctor stays read-only for the repository. `mfgctl timings`
shows runs, median and maximum per command and compares the median with the DX
targets (doctor ≤ 30 s, check --fast ≤ 90 s). These are DEV measurements for
BENCH-DX-001, not release evidence.

## Tests

```bash
PYTHONPATH=ci:ci/scripts uv run --project ci --locked python -m pytest tools/mfgctl/tests -p pytest_quarantine
```

The tests replace the machine with fake runners (TEST-PLAT-FABCTL, boundary mode
FIXTURE_ALLOWED) and include the negative paths: missing tools, unreachable
daemon, wrong Python, unusable or foreign-owned environment, stale lock,
timeouts, low disk, busy ports, workflow drift and unwritable timing storage.
One test reads the real `.github/workflows/ci.yml` to guard against drift.
