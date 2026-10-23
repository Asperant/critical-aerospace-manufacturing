"""Command surface of mfgctl (01 Item 74 §13–39).

Slice A ships ``doctor``; bootstrap, check, profile, smoke, scenario and
diagnose join in later slices of WP-PLAT-002.

Exit codes: 0 success (warnings allowed), 1 a check failed, 2 mfgctl could not
run (for example outside the repository).
"""

from __future__ import annotations

import os
from pathlib import Path

import typer

from mfgctl import __version__
from mfgctl import doctor as doctor_module
from mfgctl.repo import RepoNotFoundError, find_repo_root

app = typer.Typer(
    help="mfgctl — canonical developer and operator entry point (01 Item 74).",
    add_completion=False,
    no_args_is_help=True,
)


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


@app.command()
def doctor(
    json_output: bool = typer.Option(
        False, "--json", help="Print machine-readable JSON (schema mfgctl.doctor/v1)."
    ),
) -> None:
    """Diagnose the developer environment without changing anything."""
    report = doctor_module.run_doctor(doctor_module.default_environment(_repo_root()))
    if json_output:
        typer.echo(doctor_module.render_json(report))
    else:
        typer.echo(doctor_module.render_text(report))
    raise typer.Exit(report.exit_code)
