"""Read-only, fail-closed DoR/DoD preflight. No execution evidence adapter yet."""
from hashlib import sha256
from pathlib import Path
from typing import Literal

from .enums import Severity
from .queries import context


def evaluate(project, wp_id: str, gate: Literal["ready", "done"], root: Path) -> dict:
    if gate not in {"ready", "done"}:
        raise ValueError("Unknown governance gate")
    payload = {
        "schema_version": "projectctl-gate-v1", "wp_id": wp_id, "gate": gate,
        "result": "UNKNOWN", "transition_authorized": False,
        "execution_status": "UNAVAILABLE (documentation only)",
        "source_manifest": project.source_manifest,
        "criteria_refs": [],
    }
    try:
        canonical = context(project, wp_id)
    except ValueError as exc:
        return {**payload, "result": "FAIL", "reason": str(exc)}
    if any(d.severity == Severity.ERROR for d in project.diagnostics()):
        return {**payload, "result": "FAIL", "reason": "Canonical validation failed"}
    source = "docs/08_Definition_of_Ready_and_Done.md"
    try:
        governance = (root / source).read_bytes()
    except OSError:
        return {**payload, "reason": "Governing DoR/DoD document unavailable"}
    wp = canonical["work_package"]
    payload.update(
        governance_source={"path": source, "sha256": sha256(governance).hexdigest()},
        criteria_refs=wp["dor_refs" if gate == "ready" else "dod_refs"],
        criteria_scope="WP references plus all applicable docs/08 level and scope supplements",
        reason="Required execution evidence and accountable owner assessments are unavailable",
        missing_evidence=(
            ["actual dependency readiness and precise consumed contracts", "accountable owner readiness assessments", "applicable task/scope readiness confirmations"]
            if gate == "ready" else
            ["actual deliverables and requirement verification at required boundaries", "required CI and canonical validation", "post-merge target-environment validation", "trace dispositions and identity-bound accepted evidence", "applicable WP/capability/research/scope DoD confirmations"]
        ),
        limitation="No trusted execution evidence input is implemented; planning prose never yields PASS",
    )
    return payload
