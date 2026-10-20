import json
import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

from projectctl.cli import app
from projectctl.gates import evaluate
from projectctl.project import load_project


@pytest.fixture(scope="module")
def project():
    return load_project(Path(__file__).resolve().parents[3])


@pytest.mark.parametrize("gate", ["ready", "done"])
def test_planning_cannot_certify_gate(project, root, gate):
    result = evaluate(project, "WP-AI-007", gate, root)
    assert result["result"] == "UNKNOWN"
    assert result["transition_authorized"] is False
    assert result["criteria_refs"]
    assert result["governance_source"]["path"].startswith("docs/08_")
    assert result == evaluate(project, "WP-AI-007", gate, root)


@pytest.mark.parametrize("identity", ["WP-AI-999", "CAP-42", "CTRL-PM-013", "WP-AI-007 extra"])
def test_unknown_or_noncanonical_identity_fails(project, root, identity):
    assert evaluate(project, identity, "ready", root)["result"] == "FAIL"


def test_missing_governance_is_unknown(project, tmp_path):
    result = evaluate(project, "WP-AI-007", "done", tmp_path)
    assert result["result"] == "UNKNOWN"
    assert result["reason"] == "Governing DoR/DoD document unavailable"


def test_invalid_baseline_fails(tmp_path, sample):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/04_Work_Breakdown_Structure.md").write_text(sample)
    assert evaluate(load_project(tmp_path), "WP-SIM-001", "done", tmp_path)["result"] == "FAIL"


@pytest.mark.parametrize("gate", ["ready", "done"])
def test_cli_unknown_nonzero_without_network_or_writes(root, monkeypatch, gate):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network or write attempted")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    original = Path.open
    def guarded(self, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            forbidden()
        return original(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", guarded)
    result = CliRunner().invoke(app, [f"check-{gate}", "WP-AI-007", "--root", str(root)])
    assert result.exit_code == 1, result.output
    assert json.loads(result.output)["result"] == "UNKNOWN"


def test_cli_identity_fail_nonzero(root):
    result = CliRunner().invoke(app, ["check-done", "WP-AI-999", "--root", str(root)])
    assert result.exit_code == 1
    assert json.loads(result.output)["result"] == "FAIL"


@pytest.mark.parametrize("gate", ["ready", "done"])
@pytest.mark.parametrize("explicit_root", [False, True])
def test_gate_input_errors_exit_two(tmp_path, monkeypatch, gate, explicit_root):
    monkeypatch.chdir(tmp_path)
    args = [f"check-{gate}", "WP-AI-007"]
    if explicit_root:
        args.extend(["--root", str(tmp_path)])
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 2
    assert "INPUT_ERROR:" in result.output


@pytest.mark.parametrize("gate", ["ready", "done"])
def test_gate_evidence_has_no_mandatory_development_review(project, root, gate):
    result = evaluate(project, "WP-AI-007", gate, root)
    assert result["result"] == "UNKNOWN"
    assert result["transition_authorized"] is False
    assert result["criteria_refs"]
    explanation = json.dumps([result["reason"], result["missing_evidence"]]).lower()
    assert "execution evidence" in explanation
    assert "owner" in explanation
    assert "review" not in explanation
    assert "approval" not in explanation
    if gate == "done":
        assert "required CI and canonical validation" in result["missing_evidence"]
        assert "post-merge target-environment validation" in result["missing_evidence"]
