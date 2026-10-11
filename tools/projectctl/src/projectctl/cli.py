import sys
from pathlib import Path

import typer

from .enums import Severity
from .loader import find_root, load
from .rendering import emit_json, emit_summary, summary
from .validators.wbs import validate as validate_catalog

sys.dont_write_bytecode = True
app = typer.Typer(help="Offline canonical WBS tooling (CTRL-PM-001).", add_completion=False)


def read_catalog(root: Path | None):
    try:
        return load(root if root is not None else find_root(Path.cwd()))
    except (OSError, UnicodeError, ValueError) as exc:
        typer.echo(f"INPUT_ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc


@app.command()
def parse(root: Path | None = typer.Option(None, help="Repository root.")):
    """Read WBS and emit deterministic JSON; never write generated state."""
    catalog = read_catalog(root)
    emit_json({
        "source": catalog.source_path,
        "capability_areas": [a.model_dump(mode="json") for a in catalog.capability_areas],
        "work_packages": [wp.model_dump(mode="json") for wp in catalog.work_packages],
        "diagnostics": [d.model_dump(mode="json") for d in catalog.diagnostics],
    })
    if any(d.severity == Severity.ERROR for d in catalog.diagnostics):
        raise typer.Exit(1)


def report(root: Path | None, json_output: bool):
    catalog = read_catalog(root)
    payload = summary(catalog, validate_catalog(catalog))
    if json_output:
        emit_json(payload)
    else:
        emit_summary(payload)
    if payload["validation"] != "PASS":
        raise typer.Exit(1)


@app.command()
def validate(root: Path | None = typer.Option(None), json_output: bool = typer.Option(False, "--json")):
    """Validate WBS identities, owners, local references and baseline counts."""
    report(root, json_output)


@app.command()
def status(root: Path | None = typer.Option(None), json_output: bool = typer.Option(False, "--json")):
    """Show parser inventory; execution status is unavailable."""
    report(root, json_output)
