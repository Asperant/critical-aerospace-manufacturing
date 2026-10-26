"""Read-only, fail-closed DoR/DoD preflight with local evidence support."""
import re
from hashlib import sha256
from pathlib import Path
from typing import Literal

from .enums import Severity
from .queries import context

_DOR = re.compile(r"^DOR-(TASK|WP)-\d{2}$")
_DEP = re.compile(r"^(DEP-\d{3})$")
_REF = re.compile(r"(?:`([^`]+)`|((?:docs|evidence|project_control|requirements|tools)/[^\s,;)]+))")


def _table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and not all(set(cell) <= {"-", ":", " "} for cell in cells):
            rows.append(cells)
    return rows


def _has_reference(value: str) -> bool:
    return bool(_REF.search(value))


def parse_assessment(path: Path) -> dict:
    """Parse the supported immutable Markdown assessment format."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"errors": [f"assessment unreadable: {exc}"]}
    criteria: dict[str, dict] = {}
    dependencies: dict[str, dict] = {}
    errors: list[str] = []
    for row in _table_rows(text):
        key = row[0].strip(" `")
        if _DOR.fullmatch(key):
            if key in criteria:
                errors.append(f"duplicate criterion: {key}")
                continue
            result = row[1].upper().strip()
            if not (result.startswith("PASS") or result.startswith("N/A")):
                errors.append(f"unsupported criterion result: {key}")
                continue
            criteria[key] = {"result": result, "detail": " | ".join(row[2:]).strip()}
        elif _DEP.fullmatch(key):
            if key in dependencies:
                errors.append(f"duplicate dependency: {key}")
                continue
            dependencies[key] = {"readiness": row[1].upper().strip(), "detail": " | ".join(row[2:]).strip()}
    owner_match = re.search(r"(?im)^\s*Accountable owner\s*:\s*(.+?)\s*$", text)
    return {"path": str(path), "sha256": sha256(text.encode()).hexdigest(), "text": text,
            "criteria": criteria, "dependencies": dependencies,
            "owner": owner_match.group(1).split("(", 1)[0].strip() if owner_match else None,
            "errors": errors}


def _criteria_result(record: dict, criterion: str, *, allow_na: bool) -> str | None:
    item = record["criteria"].get(criterion)
    if item is None:
        return None
    if item["result"].startswith("PASS"):
        # The assessment itself is the bound evidence artifact.  Criterion
        # rows must explain the disposition; they do not each need a second
        # path token when the explanation points to the canonical scope.
        return "PASS" if item["detail"] else "INVALID"
    if allow_na and item["result"].startswith("N/A") and item["detail"]:
        return "N/A"
    return "INVALID"


def _ready_evidence(canonical: dict, root: Path) -> dict:
    wp = canonical["work_package"]
    path = root / "evidence" / wp["id"] / "READY.md"
    record = parse_assessment(path)
    if record.get("errors") or "criteria" not in record:
        return {"result": "UNKNOWN", "evidence": {"path": str(path)},
                "missing_evidence": ["readable, unambiguous READY assessment"],
                "reason": "; ".join(record.get("errors", ["READY assessment unavailable"])) + "; accountable owner evidence unavailable"}

    missing: list[str] = []
    owner = (wp.get("primary_owner") or {}).get("canonical_name")
    if record.get("owner") != owner:
        missing.append("accountable owner readiness assessment bound to the canonical owner")
    scope = wp.get("scope_class")
    task_ids = [f"DOR-TASK-{number:02d}" for number in range(1, 13) if scope == "R1" or number != 12]
    for criterion in task_ids:
        result = _criteria_result(record, criterion, allow_na=criterion in {"DOR-TASK-04", "DOR-TASK-12"})
        if result is None:
            missing.append(f"{criterion} confirmation")
        elif result == "INVALID":
            missing.append(f"unambiguous supported {criterion} confirmation")
    for criterion in wp.get("dor_refs") or []:
        result = _criteria_result(record, criterion, allow_na=criterion in {"DOR-WP-04", "DOR-WP-08"})
        if result is None:
            missing.append(f"{criterion} confirmation")
        elif result == "INVALID":
            missing.append(f"unambiguous supported {criterion} confirmation")

    start_edges = [edge for edge in canonical.get("dependency_edges", [])
                   if edge.get("semantics", {}).get("strength") == "HARD"
                   and edge.get("semantics", {}).get("blocking_stage") == "START"]
    for edge in start_edges:
        dep = record["dependencies"].get(edge["id"])
        if not dep or dep["readiness"] in {"NOT_APPLICABLE", "N/A", "UNKNOWN", ""} or not dep["detail"] or not _has_reference(dep["detail"]):
            missing.append(f"START dependency {edge['id']} readiness and precise consumed contract evidence")
    if missing:
        return {"result": "UNKNOWN", "evidence": {"path": record["path"], "sha256": record["sha256"]},
                "missing_evidence": sorted(set(missing)), "reason": "READY assessment is missing or ambiguous required evidence"}
    return {"result": "PASS", "evidence": {"path": record["path"], "sha256": record["sha256"]},
            "missing_evidence": [], "reason": "Canonical DoR assessment and applicable START evidence verified",
            "assessed_criteria": sorted(record["criteria"]),
            "dependency_evidence": sorted(edge["id"] for edge in start_edges)}


def evaluate(project, wp_id: str, gate: Literal["ready", "done"], root: Path) -> dict:
    if gate not in {"ready", "done"}:
        raise ValueError("Unknown governance gate")
    payload = {
        "schema_version": "projectctl-gate-v1", "wp_id": wp_id, "gate": gate,
        "result": "UNKNOWN", "transition_authorized": False,
        "execution_status": "EVIDENCE_ASSESSED" if gate == "ready" else "UNAVAILABLE (documentation only)",
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
    payload.update(governance_source={"path": source, "sha256": sha256(governance).hexdigest()},
                   criteria_refs=wp["dor_refs" if gate == "ready" else "dod_refs"],
                   criteria_scope="WP references plus all applicable docs/08 level and scope supplements")
    if gate == "ready":
        evidence = _ready_evidence(canonical, root)
        payload.update(evidence, transition_authorized=evidence["result"] == "PASS")
        return payload
    payload.update(reason="Required post-merge verification and accountable owner DoD evidence are unavailable",
                   missing_evidence=["actual deliverables and requirement verification at required boundaries", "required CI and canonical validation", "post-merge target-environment validation", "trace dispositions and identity-bound accepted evidence", "applicable WP/capability/research/scope DoD confirmations"],
                   limitation="Done certification remains fail-closed until post-merge evidence is assessed")
    return payload
