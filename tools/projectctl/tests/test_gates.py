import json
import shutil
import socket
from pathlib import Path

import pytest
from projectctl.cli import app
from projectctl.gates import evaluate, parse_assessment
from projectctl.post_merge_evidence import evaluate_post_merge_evidence
from projectctl.project import load_project
from typer.testing import CliRunner


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


def test_bound_ready_assessment_passes_and_skips_integration_edges(project, root):
    result = evaluate(project, "WP-CORE-003", "ready", root)
    assert result["result"] == "PASS"
    assert result["transition_authorized"] is True
    assert result["missing_evidence"] == []
    assert result["dependency_evidence"] == []


def test_assessment_parser_rejects_duplicate_rows(tmp_path):
    path = tmp_path / "READY.md"
    path.write_text(
        "Accountable owner: Example Owner\n\n"
        "| Criterion | Result | Evidence |\n|---|---|---|\n"
        "| DOR-TASK-01 | PASS | docs/04_Work_Breakdown_Structure.md |\n"
        "| DOR-TASK-01 | PASS | docs/04_Work_Breakdown_Structure.md |\n",
        encoding="utf-8",
    )
    assert "duplicate criterion: DOR-TASK-01" in parse_assessment(path)["errors"]


@pytest.mark.parametrize(
    "identity", ["WP-AI-999", "CAP-42", "CTRL-PM-013", "WP-AI-007 extra"]
)
def test_unknown_or_noncanonical_identity_fails(project, root, identity):
    assert evaluate(project, identity, "ready", root)["result"] == "FAIL"


def test_missing_governance_is_unknown(project, tmp_path):
    result = evaluate(project, "WP-AI-007", "done", tmp_path)
    assert result["result"] == "UNKNOWN"
    assert result["reason"] == "Governing DoR/DoD document unavailable"


def test_invalid_baseline_fails(tmp_path, sample):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/04_Work_Breakdown_Structure.md").write_text(sample)
    assert (
        evaluate(load_project(tmp_path), "WP-SIM-001", "done", tmp_path)["result"]
        == "FAIL"
    )


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
    result = CliRunner().invoke(
        app, [f"check-{gate}", "WP-AI-007", "--root", str(root)]
    )
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
    assert "evidence" in explanation
    assert "owner" in explanation
    assert "review" not in explanation
    assert "approval" not in explanation
    if gate == "done":
        assert "required CI and canonical validation" in result["missing_evidence"]
        assert "post-merge target-environment validation" in result["missing_evidence"]


MAIN_SHA = "359dbfd176925de4e9fbec0edeed21a1545deb53"


@pytest.fixture
def post_merge_fixture(tmp_path, root, monkeypatch):
    shutil.copytree(
        root / "evidence" / "WP-CORE-008", tmp_path / "evidence/WP-CORE-008"
    )
    shutil.copytree(root / "traceability", tmp_path / "traceability")
    monkeypatch.setattr(
        "projectctl.post_merge_evidence._is_ancestor", lambda *_args: True
    )
    return tmp_path


def _post_merge_result(project, fixture_root):
    canonical = project.catalog.work_packages[
        [wp.id for wp in project.catalog.work_packages].index("WP-CORE-008")
    ]
    context = {"work_package": canonical.model_dump(mode="json")}
    return evaluate_post_merge_evidence(
        project, context, fixture_root, current_main_sha=MAIN_SHA
    )


def _json_record(fixture_root, relative):
    path = fixture_root / relative
    value = json.loads(path.read_text(encoding="utf-8"))
    return path, value


def test_post_merge_adapter_accepts_structured_certified_evidence(
    project, post_merge_fixture
):
    result = _post_merge_result(project, post_merge_fixture)
    assert result["result"] == "PASS"
    assert result["bundle_id"] == "EVID-WP-CORE-008-TECH-20261029"


def test_post_merge_adapter_requires_owner_certification(project, post_merge_fixture):
    path, run = _json_record(
        post_merge_fixture, "evidence/WP-CORE-008/RUN-CORE-008-AV-20261029.json"
    )
    run.pop("accountable_certification")
    run["accountable_acceptance"] = "NOT_CERTIFIED"
    path.write_text(json.dumps(run), encoding="utf-8")
    result = _post_merge_result(project, post_merge_fixture)
    assert result["result"] == "UNKNOWN"
    assert any(
        "accountable owner certification" in item for item in result["missing_evidence"]
    )


def test_post_merge_adapter_rejects_wrong_sha_and_stale_main(
    project, post_merge_fixture, monkeypatch
):
    path, post = _json_record(
        post_merge_fixture, "evidence/WP-CORE-008/POST-MERGE-2026-10-29.json"
    )
    post["main_sha"] = "6299ab02491a9b7336b3637334ed461ce510ec21"
    post["trace"]["validated_main_sha"] = post["main_sha"]
    for ci in post["required_ci"]:
        ci["main_sha"] = post["main_sha"]
    path.write_text(json.dumps(post), encoding="utf-8")
    monkeypatch.setattr(
        "projectctl.post_merge_evidence._is_ancestor",
        lambda _root, ancestor, _descendant: ancestor != post["main_sha"],
    )
    result = _post_merge_result(project, post_merge_fixture)
    assert result["result"] == "UNKNOWN"
    assert any("stale" in item for item in result["missing_evidence"])


def test_post_merge_adapter_rejects_wrong_bundle(project, post_merge_fixture):
    path, post = _json_record(
        post_merge_fixture, "evidence/WP-CORE-008/POST-MERGE-2026-10-29.json"
    )
    post["evidence_bundle"] = "EVID-NOT-THE-BUNDLE"
    path.write_text(json.dumps(post), encoding="utf-8")
    result = _post_merge_result(project, post_merge_fixture)
    assert result["result"] == "UNKNOWN"
    assert any("EvidenceBundle" in item for item in result["missing_evidence"])


def test_post_merge_adapter_rejects_missing_bundle(project, post_merge_fixture):
    path, post = _json_record(
        post_merge_fixture, "evidence/WP-CORE-008/POST-MERGE-2026-10-29.json"
    )
    post.pop("evidence_bundle")
    path.write_text(json.dumps(post), encoding="utf-8")
    result = _post_merge_result(project, post_merge_fixture)
    assert result["result"] == "UNKNOWN"
    assert any("evidence_bundle" in item for item in result["missing_evidence"])


def test_post_merge_adapter_fails_closed_on_malformed_record(
    project, post_merge_fixture
):
    path = post_merge_fixture / "evidence/WP-CORE-008/POST-MERGE-BROKEN.json"
    path.write_text('{"schema":"cap.post-merge-evidence/v1"', encoding="utf-8")
    result = _post_merge_result(project, post_merge_fixture)
    assert result["result"] == "UNKNOWN"
    assert "malformed" in result["reason"]


def test_post_merge_adapter_rejects_incomplete_ci_evidence(project, post_merge_fixture):
    path, post = _json_record(
        post_merge_fixture, "evidence/WP-CORE-008/POST-MERGE-2026-10-29.json"
    )
    post.pop("required_ci")
    path.write_text(json.dumps(post), encoding="utf-8")
    result = _post_merge_result(project, post_merge_fixture)
    assert result["result"] == "UNKNOWN"
    assert any("CI evidence" in item for item in result["missing_evidence"])


def test_wp_core_008_real_current_records_are_consumed(project, root):
    canonical = project.catalog.work_packages[
        [wp.id for wp in project.catalog.work_packages].index("WP-CORE-008")
    ]
    result = evaluate_post_merge_evidence(
        project,
        {"work_package": canonical.model_dump(mode="json")},
        root,
        current_main_sha=MAIN_SHA,
    )
    assert result["result"] == "PASS"
