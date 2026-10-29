"""Generic, offline reader for work-package post-merge evidence.

The evaluator deliberately consumes structured evidence records only.  It does
not infer completion from a PR, a green local test, or prose in an assessment.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

SHA = re.compile(r"^[0-9a-f]{40}$")
POST_MERGE_SCHEMA = "cap.post-merge-evidence/v1"
RUN_SCHEMA = "cap.run-record/v1"
BUNDLE_SCHEMA = "cap.evidence-bundle/v1"
UNAVAILABLE_MISSING = [
    "actual deliverables and requirement verification at required boundaries",
    "required CI and canonical validation",
    "post-merge target-environment validation",
    "trace dispositions and identity-bound accepted evidence",
    "applicable WP/capability/research/scope DoD confirmations",
]


def _json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"{path}: malformed JSON ({exc})"
    if not isinstance(value, dict):
        return None, f"{path}: JSON root must be an object"
    return value, None


def _sha(value: Any, field: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        errors.append(f"{field} is not a 40-character Git SHA")
        return False
    return True


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode in (0, 1):
        return result.returncode == 0
    return None


def _find_records(directory: Path, schema: str, work_package: str | None = None) -> tuple[list[tuple[Path, dict]], list[str]]:
    records: list[tuple[Path, dict]] = []
    errors: list[str] = []
    if not directory.is_dir():
        return records, [f"evidence directory unavailable: {directory}"]
    for path in sorted(directory.rglob("*.json")):
        value, error = _json(path)
        if error:
            # A malformed unrelated artifact is not a candidate.  A file that
            # declares the schema is a candidate and must fail closed.
            try:
                raw = path.read_text(encoding="utf-8")
                declared = '"schema"' in raw and schema in raw
            except OSError:
                declared = False
            if declared:
                errors.append(error)
            continue
        if value.get("schema") != schema:
            continue
        if work_package is None or value.get("work_package") == work_package:
            records.append((path, value))
    return records, errors


def _validate_bundle(root: Path, wp: str, run: dict, post: dict, errors: list[str]) -> dict[str, Any] | None:
    evidence_id = post.get("evidence_bundle")
    if not isinstance(evidence_id, str) or not evidence_id:
        errors.append("post-merge evidence_bundle is missing")
        return None
    cert = run.get("accountable_certification")
    if not isinstance(cert, dict) or cert.get("evidence_bundle") != evidence_id:
        errors.append("accountable certification and post-merge EvidenceBundle do not match")
        return None
    manifest_path = root / "evidence" / wp / evidence_id / "manifest.json"
    manifest, error = _json(manifest_path)
    if error:
        errors.append(error)
        return None
    assert manifest is not None
    if manifest.get("schema") != BUNDLE_SCHEMA:
        errors.append("EvidenceBundle schema is unsupported")
    if manifest.get("evidence_id") != evidence_id:
        errors.append("EvidenceBundle identity mismatch")
    if manifest.get("work_package") != wp or manifest.get("run_id") != run.get("run_id"):
        errors.append("EvidenceBundle work-package/run binding mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("EvidenceBundle artifact list is missing or empty")
    else:
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
                errors.append("EvidenceBundle contains a malformed artifact entry")
                continue
            artifact_sha = artifact.get("sha256")
            if not isinstance(artifact_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha):
                errors.append(f"EvidenceBundle artifact hash is malformed: {artifact['path']}")
                continue
            artifact_path = root / artifact["path"]
            try:
                observed = sha256(artifact_path.read_bytes()).hexdigest()
            except OSError as exc:
                errors.append(f"EvidenceBundle artifact unreadable: {artifact['path']} ({exc})")
                continue
            if observed != artifact_sha:
                errors.append(f"EvidenceBundle artifact hash mismatch: {artifact['path']}")
    return manifest


def _validate_trace(root: Path, wp: str, post: dict, errors: list[str]) -> None:
    trace = post.get("trace")
    if not isinstance(trace, dict) or trace.get("result") != "PASS":
        errors.append("post-merge trace validation is not PASS")
        return
    if trace.get("validated_main_sha") != post.get("main_sha"):
        errors.append("trace validation is not bound to post-merge main SHA")
    registry_path = root / str(trace.get("registry", ""))
    coverage_path = root / str(trace.get("evidence_coverage", ""))
    try:
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"trace registry unavailable or malformed ({exc})")
        registry = None
    requirements = trace.get("requirements")
    if not isinstance(requirements, list) or not requirements or not all(isinstance(item, str) for item in requirements):
        errors.append("trace requirement binding is missing or malformed")
        requirements = []
    if not isinstance(registry, dict) or registry.get("schema") != "cap.trace-registry/v1":
        errors.append("trace registry schema is unsupported")
    elif not isinstance(registry.get("requirements"), dict):
        errors.append("trace registry requirements are unavailable")
    else:
        for requirement in requirements:
            if requirement not in registry["requirements"]:
                errors.append(f"trace registry is missing {requirement}")
    try:
        with coverage_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        errors.append(f"generated evidence coverage unavailable or malformed ({exc})")
        rows = []
    evidence_id = post.get("evidence_bundle")
    run_id = post.get("run_id")
    for requirement in requirements:
        matches = [row for row in rows if row.get("requirement_id") == requirement]
        if len(matches) != 1:
            errors.append(f"trace evidence coverage must contain exactly one row for {requirement}")
            continue
        row = matches[0]
        if row.get("executed_as") != run_id or row.get("evidenced_by") != evidence_id:
            errors.append(f"trace evidence coverage binding mismatch for {requirement}")


def _validate_dod_source(root: Path, post: dict, errors: list[str]) -> None:
    dod = post.get("dod")
    if not isinstance(dod, dict):
        return
    source = dod.get("source")
    expected = dod.get("source_sha256")
    if not isinstance(source, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        errors.append("structured DoD source binding is missing or malformed")
        return
    try:
        observed = sha256((root / source).read_bytes()).hexdigest()
    except OSError as exc:
        errors.append(f"structured DoD source is unreadable: {source} ({exc})")
        return
    if observed != expected:
        errors.append("structured DoD source hash mismatch")


def evaluate_post_merge_evidence(project: Any, canonical: dict, root: Path, *, current_main_sha: str | None = None) -> dict[str, Any]:
    """Evaluate one generic structured post-merge record for a canonical WP."""
    del project  # reserved for future schema adapters; evaluation is repository-local.
    wp = canonical["work_package"]
    wp_id = wp["id"]
    evidence_dir = root / "evidence" / wp_id
    posts, scan_errors = _find_records(evidence_dir, POST_MERGE_SCHEMA, wp_id)
    if scan_errors:
        return {"result": "UNKNOWN", "missing_evidence": sorted(set(scan_errors + UNAVAILABLE_MISSING)),
                "reason": "Post-merge evidence is malformed or unavailable; accountable owner evidence unavailable",
                "execution_status": "EVIDENCE_ASSESSED"}
    if len(posts) != 1:
        reason = "Post-merge evidence is missing" if not posts else "Post-merge evidence is ambiguous"
        return {"result": "UNKNOWN", "missing_evidence": [reason],
                "reason": f"{reason}; accountable owner evidence unavailable",
                "execution_status": "EVIDENCE_ASSESSED"}
    post_path, post = posts[0]
    errors: list[str] = []
    if post.get("schema") != POST_MERGE_SCHEMA or post.get("work_package") != wp_id:
        errors.append("post-merge evidence schema/work-package binding is invalid")
    for field in ("main_sha", "technical_closure_sha"):
        _sha(post.get(field), f"post-merge {field}", errors)
    run_id = post.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        errors.append("post-merge run_id is missing")
    runs, run_errors = _find_records(evidence_dir, RUN_SCHEMA, wp_id)
    errors.extend(run_errors)
    matching_runs = [(path, value) for path, value in runs if value.get("run_id") == run_id]
    if len(matching_runs) != 1:
        errors.append("post-merge run binding is missing or ambiguous")
        run_path, run = (None, {})
    else:
        run_path, run = matching_runs[0]
    if run.get("work_package") != wp_id or run.get("boundary_mode") != "REAL" or run.get("result", "") == "":
        errors.append("run record is incomplete or not a real execution record")
    _sha(run.get("source_main_sha"), "run source_main_sha", errors)
    cert = run.get("accountable_certification")
    cert_record = cert if isinstance(cert, dict) else {}
    if run.get("accountable_acceptance") != "CERTIFIED" or not isinstance(cert, dict) or cert.get("status") != "CERTIFIED":
        errors.append("accountable owner certification is missing")
    else:
        owner = (wp.get("primary_owner") or {}).get("canonical_name")
        if cert.get("owner") != owner:
            errors.append("accountable owner certification is not bound to the canonical owner")
        selected = cert.get("assertions", {}).get("selected_dod_satisfied") if isinstance(cert.get("assertions"), dict) else None
        if not isinstance(selected, list) or set(selected) != set(wp.get("dod_refs") or []):
            errors.append("accountable certification does not cover the canonical WP DoD references")
        for key, value in (cert.get("assertions") or {}).items():
            if key != "selected_dod_satisfied" and isinstance(value, bool) and not value:
                errors.append(f"accountable certification assertion is false: {key}")
        for field in ("current_main_sha", "technical_closure_sha", "historical_runtime_evidence_sha"):
            _sha(cert_record.get(field), f"accountable certification {field}", errors)
        if cert_record.get("technical_closure_sha") != post.get("technical_closure_sha"):
            errors.append("technical closure SHA mismatch")
        if cert_record.get("evidence_bundle") != post.get("evidence_bundle"):
            errors.append("accountable certification EvidenceBundle mismatch")
    if post.get("run_id") != run.get("run_id"):
        errors.append("post-merge and run IDs do not match")
    if post.get("technical_closure_sha") != cert_record.get("technical_closure_sha"):
        errors.append("post-merge technical closure is not bound to the run certification")

    target = current_main_sha or _git(root, "rev-parse", "refs/remotes/origin/main") or _git(root, "rev-parse", "HEAD")
    if not _sha(target, "current main SHA", errors):
        target = None
    if target and isinstance(post.get("main_sha"), str) and SHA.fullmatch(post["main_sha"]):
        main_ancestor = _is_ancestor(root, post["main_sha"], target)
        if main_ancestor is False:
            errors.append("post-merge evidence is stale or not an ancestor of current main")
        elif main_ancestor is None:
            errors.append("post-merge main ancestry cannot be verified")
    if target:
        for field, value in (("run source_main_sha", run.get("source_main_sha")),
                             ("certification current_main_sha", cert_record.get("current_main_sha")),
                             ("technical closure SHA", post.get("technical_closure_sha"))):
            if isinstance(value, str) and SHA.fullmatch(value):
                ancestor = _is_ancestor(root, value, target)
                if ancestor is False:
                    errors.append(f"{field} is not an ancestor of current main")
                elif ancestor is None:
                    errors.append(f"{field} ancestry cannot be verified")

    ci = post.get("required_ci")
    if not isinstance(ci, list) or not ci:
        errors.append("required post-merge CI evidence is missing")
    else:
        for item in ci:
            if not isinstance(item, dict) or not item.get("name") or not item.get("run_id"):
                errors.append("post-merge CI entry is malformed")
                continue
            if item.get("conclusion") != "success" or item.get("main_sha") != post.get("main_sha"):
                errors.append(f"post-merge CI entry is not successful on the bound main: {item.get('name')}")

    dod = post.get("dod")
    assessments = dod.get("assessments") if isinstance(dod, dict) else None
    if not isinstance(assessments, dict):
        errors.append("structured DoD assessments are missing")
    else:
        for criterion in wp.get("dod_refs") or []:
            if assessments.get(criterion) != "PASS":
                errors.append(f"required DoD assessment is not PASS: {criterion}")
    _validate_dod_source(root, post, errors)
    _validate_trace(root, wp_id, post, errors)
    manifest = _validate_bundle(root, wp_id, run, post, errors)
    if errors:
        return {"result": "UNKNOWN", "execution_status": "EVIDENCE_ASSESSED",
                "evidence": {"path": str(post_path), "sha256": sha256(post_path.read_bytes()).hexdigest()},
                "missing_evidence": sorted(set(errors)),
                "reason": "Post-merge evidence is incomplete, stale or mismatched"}
    return {
        "result": "PASS",
        "execution_status": "EVIDENCE_ASSESSED",
        "evidence": {"path": str(post_path), "sha256": sha256(post_path.read_bytes()).hexdigest()},
        "run_id": run_id,
        "run_path": str(run_path),
        "bundle_id": post["evidence_bundle"],
        "main_sha": post["main_sha"],
        "ci_runs": [item["run_id"] for item in post["required_ci"]],
        "trace_requirements": post["trace"]["requirements"],
        "dod_refs": sorted(wp.get("dod_refs") or []),
        "bundle_status": manifest.get("status") if manifest else None,
        "missing_evidence": [],
        "reason": "Structured post-merge evidence, trace, CI and accountable DoD certification verified",
    }
