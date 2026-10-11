import sys
from pathlib import Path

import typer

from .enums import Severity
from .loader import find_root, load
from .rendering import emit_json, emit_summary, summary
from .validators.wbs import validate as validate_catalog
from .validators.schedule import validate_schedule
from .validators.dependencies import validate_dependencies, hard_cycle
from .validators.requirements import validate_requirements

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
    diagnostics = validate_catalog(catalog)
    if catalog.schedule is not None:
        diagnostics.extend(validate_schedule(catalog, catalog.schedule))
    if catalog.dependencies is not None:
        diagnostics.extend(validate_dependencies(catalog.dependencies))
    if catalog.requirements is not None:
        diagnostics.extend(validate_requirements(catalog, catalog.requirements))
    payload = summary(catalog, diagnostics)
    if catalog.schedule is not None:
        payload.update(cycle_count=len(catalog.schedule.cycles), milestone_count=len(catalog.schedule.milestones),
                       scheduled_wp_count=len({wp for c in catalog.schedule.cycles for wp in c.work_package_ids}),
                       unscheduled_wp_ids=sorted({wp.id for wp in catalog.work_packages} - {wp for c in catalog.schedule.cycles for wp in c.work_package_ids}))
    if catalog.dependencies is not None:
        payload.update(dependency_node_count=len(catalog.dependencies.nodes), dependency_edge_count=len(catalog.dependencies.edges),
                       hard_edge_count=sum(e.blocking for e in catalog.dependencies.edges),
                       soft_edge_count=sum(not e.blocking for e in catalog.dependencies.edges),
                       hard_cycle_count=int(hard_cycle(catalog.dependencies.edges) is not None))
    if catalog.requirements is not None:
        payload.update(requirement_count=len(catalog.requirements.requirements),
                       fr_count=sum(r.kind == "FR" for r in catalog.requirements.requirements),
                       nfr_count=sum(r.kind == "NFR" for r in catalog.requirements.requirements))
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
