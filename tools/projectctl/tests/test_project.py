import json
import socket

import pytest
from typer.testing import CliRunner

from projectctl.cli import app
from projectctl.project import load_project
from projectctl.queries import context, planning_candidates


@pytest.fixture
def project(root):
    return load_project(root)


def test_unified_snapshot_and_provenance(project):
    snapshot = project.snapshot()
    assert len(snapshot["work_packages"]) == 179
    assert len(snapshot["requirements"]) == 306
    assert len(snapshot["dependency_nodes"]) == 100
    assert len(snapshot["dependency_edges"]) == 217
    assert len(snapshot["schedule"]["cycles"]) == 13
    assert all(len(value) == 64 for value in snapshot["source_manifest"].values())
    assert snapshot["parser_version"] == "offline-project-v1"
    assert project.summary()["validation"] == "PASS"


def test_context_preserves_all_windows_and_findings(project):
    payload = context(project, "WP-VIS-001")
    assert payload["cycle_ids"] == ["S3", "S4"]
    assert payload["milestone_id"] == "M2"
    assert payload["work_package"]["primary_owner"]["canonical_name"] == "Selman Özdemir"
    assert payload["requirements"] and payload["dependency_edges"]
    assert any(d["code"] == "READINESS_INCOMPATIBLE" for d in payload["diagnostics"])
    assert payload["work_package"]["dor_refs"] and payload["work_package"]["dod_refs"]
    assert payload["work_package"]["provenance"]["path"].startswith("docs/")


def test_planning_candidates_exclude_optional_and_unscheduled(project):
    payload = planning_candidates(project, "Asrın Dündar")
    assert payload["result_type"] == "PLANNING_CANDIDATES"
    assert payload["readiness"] == "NOT_CERTIFIED"
    ids = {item["id"] for item in payload["candidates"]}
    assert not {"WP-R2-001", "WP-R2-002", "WP-S-001", "WP-X-001"} & ids
    assert planning_candidates(project, "Batu", "S2")["owner"] == "Batuhan Kaya"
    with pytest.raises(ValueError, match="owner"):
        planning_candidates(project, "Team")
    with pytest.raises(ValueError, match="cycle"):
        planning_candidates(project, "Batu", "S99")
    with pytest.raises(ValueError, match="WP ID"):
        context(project, "WP-NORMAL")


def test_unified_dangling_reference_fails(project):
    c = project.catalog
    c.work_packages[0] = c.work_packages[0].model_copy(update={"readiness_refs": ["DN-NONEXISTENT"]})
    assert any(d.code == "WBS_DEPENDENCY_REFERENCE" for d in project.diagnostics())
    assert project.summary()["validation"] == "FAIL"


@pytest.mark.parametrize("args", [["context", "WP-CORE-001"], ["next", "--owner", "Batu", "--cycle", "S2"]])
def test_queries_are_offline_read_only(args, root, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected mutation/network operation")
    import io
    original = io.open
    def guarded(path, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            forbidden()
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(io, "open", guarded)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    result = CliRunner().invoke(app, args + ["--root", str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["execution_status"].startswith("UNAVAILABLE")
