"""Command surface of mfgctl (01 Item 74 §13–39).

Slice A: ``doctor``. Slice B: ``bootstrap``, ``check`` and ``timings``.
Slice C: ``profile list``, ``up``, ``down``, ``status``, ``smoke``, ``scenario``
and ``diagnose bundle`` over the capability registry (mfgctl.capabilities/v1).
WP-GOV-002: ``trace validate|generate|seed|drift|impact|requirement|orphans``.

Exit codes: 0 success (warnings allowed), 1 a check or step failed, 2 mfgctl
could not run (outside the repository, ci.yml unusable, registry missing or
invalid, unknown profile/capability/scenario).
Every command records its duration (see ``mfgctl timings``).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

import typer

from mfgctl import __version__, probe, registry, runtime, timing
from mfgctl import bootstrap as bootstrap_module
from mfgctl import check as check_module
from mfgctl import diagnose as diagnose_module
from mfgctl import doctor as doctor_module
from mfgctl import trace as trace_module
from mfgctl.repo import RepoNotFoundError, find_repo_root

app = typer.Typer(
    help="mfgctl — canonical developer and operator entry point (01 Item 74).",
    add_completion=False,
    no_args_is_help=True,
)
profile_app = typer.Typer(help="Capability profiles (Compose).", no_args_is_help=True)
scenario_app = typer.Typer(help="Declared scenarios.", no_args_is_help=True)
diagnose_app = typer.Typer(help="Diagnostics for support.", no_args_is_help=True)
app.add_typer(profile_app, name="profile")
app.add_typer(scenario_app, name="scenario")
trace_app = typer.Typer(
    help="Trace registry and linter (WP-GOV-002, 03 §18).", no_args_is_help=True
)
app.add_typer(diagnose_app, name="diagnose")
app.add_typer(trace_app, name="trace")


class Tier(StrEnum):
    fast = "fast"
    pr = "pr"


def _show_version(value: bool) -> None:
    if value:
        typer.echo(f"mfgctl {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_show_version,
        is_eager=True,
        help="Show the mfgctl version and exit.",
    ),
) -> None:
    """Thin orchestration and diagnostics over Docker, uv and the test runners."""


def _repo_root() -> Path:
    try:
        return find_repo_root(Path.cwd(), os.environ)
    except RepoNotFoundError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc


@contextmanager
def _timed(command: str, clock: Callable[[], float] = time.monotonic) -> Iterator[None]:
    """Record duration and exit code of the wrapped command, whatever happens."""
    started = clock()
    code = 0
    try:
        yield
    except typer.Exit as exc:
        code = exc.exit_code
        raise
    except BaseException:
        code = 1
        raise
    finally:
        elapsed = round((clock() - started) * 1000)
        timing.append(timing.make_record(command, elapsed, code), os.environ)


@app.command()
def doctor(
    json_output: bool = typer.Option(
        False, "--json", help="Print machine-readable JSON (schema mfgctl.doctor/v1)."
    ),
) -> None:
    """Diagnose the developer environment without changing anything."""
    with _timed("doctor"):
        root = _repo_root()
        report = doctor_module.run_doctor(doctor_module.default_environment(root))
        if json_output:
            typer.echo(doctor_module.render_json(report))
        else:
            typer.echo(doctor_module.render_text(report))
        raise typer.Exit(report.exit_code)


@app.command()
def bootstrap(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show the plan; run only read-only checks."
    ),
) -> None:
    """Prepare the locked toolchain environment (idempotent; never deletes)."""
    with _timed("bootstrap --dry-run" if dry_run else "bootstrap"):
        root = _repo_root()
        env = doctor_module.default_environment(root)
        outcome = bootstrap_module.run_bootstrap(env, dry_run=dry_run)
        typer.echo(bootstrap_module.render_text(outcome, dry_run))
        raise typer.Exit(outcome.exit_code)


@app.command()
def check(
    tier: Tier = typer.Option(
        Tier.fast,
        "--tier",
        help="fast: static ratchet; pr: static, unit and contract jobs of CI.",
    ),
    fast: bool = typer.Option(False, "--fast", help="Shortcut for --tier fast."),
    pr: bool = typer.Option(False, "--pr", help="Shortcut for --tier pr."),
) -> None:
    """Run the same commands CI runs, read from .github/workflows/ci.yml."""
    if fast and pr:
        typer.echo("ERROR: choose either --fast or --pr", err=True)
        raise typer.Exit(2)
    selected = "pr" if pr else "fast" if fast else tier.value
    with _timed(f"check --{selected}"):
        root = _repo_root()
        try:
            commands = check_module.load_commands(root, selected)
        except check_module.WorkflowError as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(2) from exc
        report = check_module.run_check(
            root,
            commands,
            selected,
            probe.run_streaming,
            lambda line: typer.secho(line, bold=True),
        )
        typer.echo(check_module.render_summary(report))
        raise typer.Exit(report.exit_code)


@app.command()
def timings(
    json_output: bool = typer.Option(False, "--json", help="Print JSON rows."),
) -> None:
    """Summarise recorded command durations against the DX targets."""
    records = timing.load(os.environ)
    rows = timing.summarize(records)
    if json_output:
        typer.echo(json.dumps(rows, indent=2))
    else:
        location = timing.state_dir(os.environ) / timing.FILENAME
        typer.echo(timing.render_summary(rows, location))


def _registry(root: Path) -> registry.Registry:
    try:
        return registry.load(root, os.environ)
    except (registry.RegistryMissingError, registry.RegistryInvalidError) as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc


def _action(build: Callable[[registry.Registry], runtime.Action]) -> runtime.Action:
    root = _repo_root()
    try:
        return build(_registry(root))
    except registry.UnknownNameError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc


def _run(action: runtime.Action) -> None:
    typer.secho(f"$ {' '.join(action.argv)}", bold=True)
    result = runtime.execute(action, _repo_root(), probe.run_streaming)
    typer.echo(result.summary())
    raise typer.Exit(0 if result.passed else 1)


@profile_app.command("list")
def profile_list() -> None:
    """List the declared capability profiles."""
    with _timed("profile list"):
        typer.echo(runtime.render_profiles(_registry(_repo_root())))


@app.command()
def up(name: str = typer.Argument(..., help="Profile name.")) -> None:
    """Start a capability profile (docker compose --profile NAME up --wait)."""
    with _timed("up"):
        _run(_action(lambda reg: runtime.profile_up(reg, name)))


@app.command()
def down(name: str = typer.Argument(..., help="Profile name.")) -> None:
    """Stop a capability profile."""
    with _timed("down"):
        _run(_action(lambda reg: runtime.profile_down(reg, name)))


@app.command()
def status() -> None:
    """Show container state for the declared Compose files."""
    with _timed("status"):
        _run(_action(runtime.status))


@app.command()
def smoke(capability: str = typer.Argument(..., help="Capability name.")) -> None:
    """Run the smoke path a capability declares (DX-INV-27)."""
    with _timed("smoke"):
        _run(_action(lambda reg: runtime.smoke(reg, capability)))


@scenario_app.command("list")
def scenario_list() -> None:
    """List the declared scenarios."""
    with _timed("scenario list"):
        typer.echo(runtime.render_scenarios(_registry(_repo_root())))


@scenario_app.command("run")
def scenario_run(identity: str = typer.Argument(..., help="Scenario ID.")) -> None:
    """Run a declared scenario."""
    with _timed("scenario run"):
        _run(_action(lambda reg: runtime.scenario(reg, identity)))


@diagnose_app.command("bundle")
def diagnose_bundle(
    output: Path | None = typer.Option(
        None, "--output", help="Directory for the archive (default: state dir)."
    ),
) -> None:
    """Write a redacted diagnostics archive; review it before sharing."""
    with _timed("diagnose bundle"):
        env = doctor_module.default_environment(_repo_root())
        files = diagnose_module.collect(env, os.environ)
        target = output or diagnose_module.default_target(os.environ)
        try:
            path = diagnose_module.write_bundle(files, target, datetime.now(UTC))
        except OSError as exc:
            typer.echo(f"ERROR: cannot write bundle: {exc}", err=True)
            raise typer.Exit(1) from exc
        typer.echo(f"Diagnostics bundle: {path}")
        typer.echo("Contents: " + ", ".join(sorted(files)))
        typer.echo("Secrets are redacted, but review the archive before sharing it.")


def _trace(command: str, args: list[str]) -> None:
    with _timed(f"trace {command}"):
        try:
            code = trace_module.run(_repo_root(), [command, *args])
        except trace_module.TraceUnavailableError as exc:
            typer.echo(f"ERROR: {exc}", err=True)
            raise typer.Exit(2) from exc
        raise typer.Exit(code)


@trace_app.command("validate")
def trace_validate(
    base: str | None = typer.Option(
        None, "--base", help="Git revision for the TL-08 regression comparison."
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable result."),
) -> None:
    """Lint the trace registry (TL-01…TL-12)."""
    _trace(
        "validate",
        [*(["--base", base] if base else []), *(["--json"] if json_output else [])],
    )


@trace_app.command("generate")
def trace_generate() -> None:
    """Regenerate traceability/generated/ from the registry (TL-07)."""
    _trace("generate", [])


@trace_app.command("seed")
def trace_seed() -> None:
    """Regenerate the registry from 03 §17, then the views."""
    _trace("seed", [])


@trace_app.command("drift")
def trace_drift(
    strict: bool = typer.Option(False, "--strict", help="Exit 1 on any drift."),
) -> None:
    """Compare the registry with 03 §17."""
    _trace("drift", ["--strict"] if strict else [])


@trace_app.command("requirement")
def trace_requirement(identity: str = typer.Argument(..., help="FR-/NFR- ID.")) -> None:
    """Show one requirement's node and edges."""
    _trace("requirement", [identity])


@trace_app.command("orphans")
def trace_orphans() -> None:
    """Summarize the orphan report."""
    _trace("orphans", [])


@trace_app.command("impact")
def trace_impact(
    body_file: Path = typer.Option(..., "--body-file", help="PR description file."),
    base: str = typer.Option(
        "origin/main", "--base", help="Revision the PR merges into."
    ),
) -> None:
    """Check a PR description's requirement impact (TL-13)."""
    _trace("impact", ["--body-file", str(body_file.resolve()), "--base", base])
