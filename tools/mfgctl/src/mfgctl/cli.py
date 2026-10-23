"""Command surface of mfgctl (01 Item 74 §13–39).

Slice A: ``doctor``. Slice B: ``bootstrap``, ``check`` and ``timings``.
Profile, smoke, scenario and diagnose join in slice C of WP-PLAT-002.

Exit codes: 0 success (warnings allowed), 1 a check or step failed, 2 mfgctl
could not run (for example outside the repository or ci.yml unusable).
Every command records its duration (see ``mfgctl timings``).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path

import typer

from mfgctl import __version__, probe, timing
from mfgctl import bootstrap as bootstrap_module
from mfgctl import check as check_module
from mfgctl import doctor as doctor_module
from mfgctl.repo import RepoNotFoundError, find_repo_root

app = typer.Typer(
    help="mfgctl — canonical developer and operator entry point (01 Item 74).",
    add_completion=False,
    no_args_is_help=True,
)


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
