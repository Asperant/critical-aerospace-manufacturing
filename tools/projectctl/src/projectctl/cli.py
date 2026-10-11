import sys
from pathlib import Path

import typer

from .enums import Severity
from .loader import find_root
from .project import load_project
from .queries import context as wp_context, planning_candidates
from .rendering import emit_json, emit_summary

sys.dont_write_bytecode = True
app = typer.Typer(help="Deterministic offline project documentation bridge.", add_completion=False)


def read_project(root: Path | None):
    try:
        return load_project(root if root is not None else find_root(Path.cwd()))
    except (OSError, UnicodeError, ValueError) as exc:
        typer.echo(f"INPUT_ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc


@app.command()
def parse(root: Path | None = typer.Option(None, help="Repository root.")):
    """Emit the complete deterministic offline model to stdout."""
    project = read_project(root)
    emit_json(project.snapshot())
    if any(d.severity == Severity.ERROR for d in project.diagnostics()):
        raise typer.Exit(1)


def report(root, json_output):
    payload = read_project(root).summary()
    emit_json(payload) if json_output else emit_summary(payload)
    if payload["validation"] != "PASS":
        raise typer.Exit(1)


@app.command()
def validate(root: Path | None = typer.Option(None), json_output: bool = typer.Option(False, "--json")):
    """Validate the full offline baseline; semantic findings remain visible."""
    report(root, json_output)


@app.command()
def status(root: Path | None = typer.Option(None), json_output: bool = typer.Option(False, "--json")):
    """Show documentation inventory; execution status is unavailable."""
    report(root, json_output)


@app.command()
def context(wp_id: str, root: Path | None = typer.Option(None)):
    """Show canonical WP context, provenance and unresolved findings."""
    try:
        emit_json(wp_context(read_project(root), wp_id))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc


@app.command(name="next")
def next_candidates(owner: str = typer.Option(...), cycle: str | None = typer.Option(None), root: Path | None = typer.Option(None)):
    """List scheduled mandatory planning candidates; never certify READY."""
    project = read_project(root)
    if any(d.severity == Severity.ERROR for d in project.diagnostics()):
        typer.echo("Canonical validation failed; candidate selection unavailable.", err=True)
        raise typer.Exit(1)
    try:
        emit_json(planning_candidates(project, owner, cycle))
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
