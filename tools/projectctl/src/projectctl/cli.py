import sys
from pathlib import Path

import typer
import yaml

from .enums import Severity
from .loader import find_root
from .project import load_project
from .queries import context as wp_context
from .queries import planning_candidates
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


@app.command(name="plane-audit")
def plane_audit(root: Path | None = typer.Option(None)):
    """Explicit GET-only live API v1 discovery; sanitized JSON to stdout."""
    from .plane import PlaneError, PlaneReader, load_config
    try:
        repo = root if root is not None else find_root(Path.cwd())
        with PlaneReader(load_config(repo / "project_control/local/plane.env")) as reader:
            audit = reader.audit()
            from .control_plane import classify_inventory
            audit["item_classification"] = classify_inventory(read_project(repo), audit)
            emit_json(audit)
    except (PlaneError, OSError) as exc:
        typer.echo(str(exc) if isinstance(exc, PlaneError) else "Plane configuration unavailable", err=True)
        raise typer.Exit(2) from None


@app.command(name="plane-plan")
def plane_plan(audit: Path = typer.Option(..., help="Explicit sanitized API v1 audit JSON; no network."),
               root: Path | None = typer.Option(None)):
    """Emit a pure bootstrap dry-run; findings block live application."""
    import json

    from .plane import PlaneError
    from .plane_plan import bootstrap_plan
    try:
        payload = bootstrap_plan(read_project(root), json.loads(audit.read_text()))
        emit_json(payload)
    except (PlaneError, OSError, ValueError, KeyError, TypeError) as exc:
        typer.echo(str(exc) if isinstance(exc, PlaneError) else "Invalid Plane audit input (details redacted)", err=True)
        raise typer.Exit(2) from None


def check_gate(wp_id, root, gate):
    from .gates import evaluate
    try:
        repo = root if root is not None else find_root(Path.cwd())
    except (OSError, ValueError) as exc:
        typer.echo(f"INPUT_ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc
    payload = evaluate(read_project(repo), wp_id, gate, repo)
    emit_json(payload)
    if payload["result"] != "PASS":
        raise typer.Exit(1)


@app.command(name="check-ready")
def check_ready(wp_id: str, root: Path | None = typer.Option(None)):
    """Fail-closed read-only DoR check; UNKNOWN without execution evidence."""
    check_gate(wp_id, root, "ready")


@app.command(name="startability")
def startability(wp_id: str, root: Path | None = typer.Option(None)):
    """Evaluate CHG-054's canonical product-start rule; no Plane or evidence reads."""
    from .execution_queue import evaluate_startability

    project = read_project(root)
    payload = evaluate_startability(project, wp_id)
    emit_json(payload)
    if payload["result"] != "STARTABLE":
        raise typer.Exit(1)


@app.command(name="check-done")
def check_done(wp_id: str, root: Path | None = typer.Option(None)):
    """Fail-closed read-only DoD check; merge/tests never imply DONE."""
    check_gate(wp_id, root, "done")


@app.command(name="catalog-export")
def catalog_export(artifact: str = typer.Option("catalog", help="catalog, schema, counts or rtm-counts; stdout only."),
                   root: Path | None = typer.Option(None)):
    """Generate WP-GOV-001 artifacts without writing files or changing lifecycle."""
    from .requirement_catalog import (
        CATALOG,
        catalog_schema,
        coverage_counts,
        from_sources,
        read_catalog,
        rtm_counts,
    )
    try:
        repo = root if root is not None else find_root(Path.cwd())
        if artifact == "schema":
            payload = catalog_schema()
        elif artifact in {"catalog", "counts", "rtm-counts"}:
            prior = read_catalog(repo / CATALOG) if (repo / CATALOG).exists() else None
            catalog = from_sources(repo, prior.retired_ids if prior else ())
            if artifact == "rtm-counts":
                typer.echo(rtm_counts(catalog))
                return
            payload = catalog.model_dump() if artifact == "catalog" else coverage_counts(catalog)
        else:
            raise ValueError("Artifact must be catalog, schema, counts or rtm-counts")
        emit_json(payload)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        detail = "Invalid embedded YAML (details redacted)" if isinstance(exc, yaml.YAMLError) else str(exc)
        typer.echo(f"CATALOG_INPUT_ERROR: {detail}", err=True)
        raise typer.Exit(2) from None


@app.command(name="catalog-lint")
def catalog_lint(root: Path | None = typer.Option(None),
                 base: str | None = typer.Option(None, help="Git commit for historical ID checks; required in CI."),
                 json_output: bool = typer.Option(False, "--json")):
    """Check schema, canonical fidelity, counts, and optional historical non-reuse."""
    from .requirement_catalog import lint_catalog
    try:
        payload = lint_catalog(root if root is not None else find_root(Path.cwd()), base)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        detail = "Invalid embedded YAML (details redacted)" if isinstance(exc, yaml.YAMLError) else str(exc)
        typer.echo(f"CATALOG_INPUT_ERROR: {detail}", err=True)
        raise typer.Exit(2) from None
    if json_output:
        emit_json(payload)
    else:
        typer.echo(f"Requirement catalog: {payload['result']} ({payload['counts']['total']} records)")
        typer.echo(f"History: {payload['history']}")
        for issue in payload["issues"]:
            typer.echo(issue)
        for gap in payload["source_gaps"]:
            typer.echo(f"SOURCE_GAP: {gap}")
        typer.echo("Readiness/evidence: NOT_CERTIFIED")
    if payload["result"] != "PASS":
        raise typer.Exit(1)


@app.command(name="execution-preferences")
def execution_preferences(root: Path | None = typer.Option(None)):
    """Validate canonical AUTO_NEXT planning preference; never mutate Plane."""
    from .execution_queue import validate_preferences
    repo = root if root is not None else find_root(Path.cwd())
    project = read_project(repo)
    policy = yaml.safe_load((repo / 'project_control/execution_preferences.yaml').read_text())
    errors = validate_preferences(project, policy)
    emit_json({'result': 'FAIL' if errors else 'PASS', 'errors': errors,
               'coverage': {owner: len(ids) for owner, ids in policy['sequences'].items()}})
    if errors:
        raise typer.Exit(1)


@app.command(name="queue-preview")
def queue_preview(owner: str = typer.Option(...), live: Path = typer.Option(...),
                  evidence: Path = typer.Option(...), root: Path | None = typer.Option(None)):
    """Pure offline AUTO_NEXT preview of explicit snapshots; no authorization."""
    import json

    from .execution_queue import compute_next_eligible
    repo = root if root is not None else find_root(Path.cwd())
    result = compute_next_eligible(read_project(repo), json.loads(live.read_text()),
                                  json.loads(evidence.read_text()), owner,
                                  yaml.safe_load((repo / 'project_control/execution_preferences.yaml').read_text()))
    emit_json(result)
    if result['status'] in {'INVALID_BASELINE','UNAVAILABLE'}:
        raise typer.Exit(1)
