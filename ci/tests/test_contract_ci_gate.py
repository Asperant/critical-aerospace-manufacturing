"""TEST-EVT-001-006: contract CI adapter, snapshots and redacted JSON failures."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from cap_contracts.ci_gate import check_versions, main

REPO = Path(__file__).resolve().parents[2]
PACKAGE = "packages/contracts/"
SECRET = "PAYLOAD-SECRET-DO-NOT-PRINT"


def write(root: Path, path: str, value: object) -> dict[str, str]:
    import hashlib

    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value).encode()
    target.write_bytes(raw)
    return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}


def shape() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
        "additionalProperties": False,
    }


def contract(
    root: Path,
    schema: dict[str, Any],
    *,
    major: int = 1,
    producer: str = "manufacturing-core",
) -> dict[str, Any]:
    declaration: dict[str, Any] = json.loads(
        (REPO / PACKAGE / "registry/core.order-query.v1.json").read_text()
    )
    declaration.update(
        contract_id=f"core.order-query.v{major}",
        version=major,
        canonical_producer=producer,
    )
    declaration.pop("input_schema", None)
    declaration["output_schema"] = write(
        root, PACKAGE + f"schemas/output.v{major}.json", schema
    )
    payload = (
        {"id": 1}
        if schema.get("properties", {}).get("id", {}).get("type") == "integer"
        else {"id": "A"}
    )
    declaration["fixtures"] = [
        write(root, PACKAGE + f"fixtures/output.v{major}.json", payload)
    ]
    write(root, PACKAGE + f"registry/{declaration['contract_id']}.json", declaration)
    return declaration


def failures(report: dict[str, Any]) -> set[str]:
    return {item["code"] for item in report["failures"]}


def test_new_family_is_validated_without_claiming_previous_compatibility(
    tmp_path: Path,
) -> None:
    contract(tmp_path / "new", shape())
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["status"] == "PASS"
    assert report["added"] == 1
    assert report["compared"] == 0
    assert report["validated"] == 1


def test_unchanged_schema_is_validated_and_scoped_out_of_change_comparison(
    tmp_path: Path,
) -> None:
    document = {**shape(), "$id": "urn:cap:unsupported-by-comparison"}
    contract(tmp_path / "old", document)
    contract(tmp_path / "new", document)
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["status"] == "PASS"
    assert report["unchanged"] == 1
    assert report["compared"] == 0


def test_optional_field_same_major_passes(tmp_path: Path) -> None:
    contract(tmp_path / "old", shape())
    new = shape()
    new["properties"]["note"] = {"type": "string"}
    contract(tmp_path / "new", new)
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["status"] == "PASS"
    assert report["compared"] == 1


def test_breaking_same_major_is_rejected(tmp_path: Path) -> None:
    contract(tmp_path / "old", shape())
    new = shape()
    new["properties"]["id"]["type"] = "integer"
    contract(tmp_path / "new", new)
    assert failures(check_versions(tmp_path / "old", tmp_path / "new")) == {
        "BREAKING_CHANGE_REQUIRES_MAJOR"
    }


def test_breaking_next_major_is_allowed_without_removing_previous(
    tmp_path: Path,
) -> None:
    contract(tmp_path / "old", shape())
    contract(tmp_path / "new", shape())
    new = shape()
    new["properties"]["id"]["type"] = "integer"
    contract(tmp_path / "new", new, major=2)
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["status"] == "PASS"
    assert report["compared"] == 1


def test_authority_change_is_compared_not_just_schema(tmp_path: Path) -> None:
    contract(tmp_path / "old", shape())
    contract(tmp_path / "new", shape(), producer="vision")
    assert "BREAKING_CHANGE_REQUIRES_MAJOR" in failures(
        check_versions(tmp_path / "old", tmp_path / "new")
    )


def test_new_lower_major_and_removed_contract_are_rejected(tmp_path: Path) -> None:
    contract(tmp_path / "old", shape(), major=2)
    contract(tmp_path / "new", shape())
    assert failures(check_versions(tmp_path / "old", tmp_path / "new")) == {
        "CONTRACT_REMOVED",
        "VERSION_ROLLBACK",
    }


def test_unknown_changed_contract_fails_closed_even_with_new_major(
    tmp_path: Path,
) -> None:
    document = {**shape(), "format": "unknown"}
    contract(tmp_path / "old", document)
    contract(tmp_path / "new", document)
    contract(tmp_path / "new", document, major=2)
    assert "COMPATIBILITY_UNVERIFIABLE" in failures(
        check_versions(tmp_path / "old", tmp_path / "new")
    )


@pytest.mark.parametrize(
    "failure",
    [
        "declaration",
        "schema",
        "fixture",
        "drift",
        "replacement",
        "remote",
        "cycle",
        "unapproved",
        "duplicate_pin",
        "missing_pin",
        "pin_drift",
    ],
)
def test_invalid_inputs_fail_closed_without_payload_values(
    tmp_path: Path, failure: str
) -> None:
    contract(tmp_path / "old", shape())
    candidate = tmp_path / "new"
    declaration = contract(candidate, shape())
    if failure == "declaration":
        declaration["canonical_producer"] = SECRET
        declaration.pop("authority_level")
    elif failure == "schema":
        declaration["output_schema"] = write(
            candidate, PACKAGE + "schemas/output.v1.json", {"type": SECRET}
        )
    elif failure == "fixture":
        declaration["fixtures"] = [
            write(
                candidate,
                PACKAGE + "fixtures/output.v1.json",
                {"id": SECRET, "extra": SECRET},
            )
        ]
    elif failure == "drift":
        (candidate / declaration["output_schema"]["path"]).write_text(SECRET)
    elif failure == "replacement":
        declaration["deprecation"] = {
            "status": "DEPRECATED",
            "replacement": "core.order-query.v1",
        }
    elif failure in {"remote", "cycle", "unapproved"}:
        target = {
            "remote": "https://example.test/" + SECRET,
            "cycle": "#",
            "unapproved": "missing.json",
        }[failure]
        declaration["output_schema"] = write(
            candidate, PACKAGE + "schemas/output.v1.json", {"$ref": target}
        )
    else:
        pin = write(candidate, PACKAGE + "schemas/extra.json", shape())
        if failure == "missing_pin":
            (candidate / pin["path"]).unlink()
        elif failure == "pin_drift":
            (candidate / pin["path"]).write_text(SECRET)
        write(
            candidate,
            PACKAGE + "schema-refs.json",
            [pin, pin] if failure == "duplicate_pin" else [pin],
        )
    write(candidate, PACKAGE + "registry/core.order-query.v1.json", declaration)
    first = check_versions(tmp_path / "old", candidate)
    assert first["status"] == "FAIL"
    assert first["failures"]
    assert SECRET not in json.dumps(first)
    assert first == check_versions(tmp_path / "old", candidate)


def test_pinned_nested_references_are_resolved_and_compared(tmp_path: Path) -> None:
    for root, changed in ((tmp_path / "old", False), (tmp_path / "new", True)):
        leaf_shape = shape()
        if changed:
            leaf_shape["properties"]["note"] = {"type": "string"}
        leaf = write(
            root, PACKAGE + "schemas/leaf.json", {"$defs": {"Record": leaf_shape}}
        )
        middle = write(
            root, PACKAGE + "schemas/middle.json", {"$ref": "leaf.json#/$defs/Record"}
        )
        write(root, PACKAGE + "schema-refs.json", [leaf, middle])
        contract(root, {"$ref": "middle.json"})
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["status"] == "PASS"
    assert report["compared"] == 1


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, stderr=subprocess.DEVNULL, text=True
    ).strip()


@pytest.fixture
def history(tmp_path: Path) -> tuple[Path, str]:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "Gate test")
    git(tmp_path, "config", "user.email", "gate@example.invalid")
    contract(tmp_path, shape())
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "baseline")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def test_cli_checks_git_snapshots_and_emits_deterministic_json(
    history: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base = history
    new = shape()
    new["properties"]["id"]["type"] = "integer"
    contract(root, new)
    git(root, "add", ".")
    git(root, "commit", "-qm", "breaking")
    monkeypatch.chdir(root)
    assert main(["--base", base]) == 1
    output = capsys.readouterr().out
    assert "BREAKING_CHANGE_REQUIRES_MAJOR" in failures(json.loads(output))
    assert main(["--base", base]) == 1
    assert capsys.readouterr().out == output


def test_cli_default_base_uses_merge_base_for_new_branch(
    history: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base = history
    git(root, "update-ref", "refs/remotes/origin/main", base)
    monkeypatch.chdir(root)
    monkeypatch.setenv("CONTRACT_BASE", "0" * 40)
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["unchanged"] == 1


def test_cli_missing_base_fails_closed(
    history: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, _ = history
    monkeypatch.chdir(root)
    assert main(["--base", "no-such-revision-" + SECRET]) == 1
    output = capsys.readouterr().out
    assert json.loads(output)["failures"][0]["code"] == "GIT_INPUT_UNAVAILABLE"
    assert SECRET not in output


def test_cli_missing_tracked_file_is_not_supplied_by_worktree(
    history: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base = history
    git(root, "rm", PACKAGE + "schemas/output.v1.json")
    git(root, "commit", "-qm", "missing pinned schema")
    write(root, PACKAGE + "schemas/output.v1.json", shape())
    monkeypatch.chdir(root)
    assert main(["--base", base]) == 1
    assert "FILE_MISSING" in failures(json.loads(capsys.readouterr().out))


def test_cli_rejects_tracked_symlinks(
    history: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root, base = history
    path = root / PACKAGE / "schemas/output.v1.json"
    path.unlink()
    path.symlink_to("/etc/passwd")
    git(root, "add", ".")
    git(root, "commit", "-qm", "symlink")
    monkeypatch.chdir(root)
    assert main(["--base", base]) == 1
    assert "GIT_ENTRY_UNSUPPORTED" in failures(json.loads(capsys.readouterr().out))


def test_workflow_wiring_changes_only_contract_job() -> None:
    # PyYAML interprets the workflow's `on` as YAML 1.1; the jobs map is unaffected.
    current = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text())
    routes = [
        name
        for name, job in current["jobs"].items()
        for step in job["steps"]
        if "python -m cap_contracts.ci_gate" in step.get("run", "")
    ]
    assert routes == ["contract"]
    steps = current["jobs"]["contract"]["steps"]
    assert steps[0]["with"]["fetch-depth"] == 0
    gate = next(
        step
        for step in steps
        if step.get("name") == "Contract registry compatibility (WP-EVT-001)"
    )
    assert "python -m cap_contracts.ci_gate" in gate["run"]
    assert "github.event.pull_request.base.sha" in gate["env"]["CONTRACT_BASE"]


def test_invalid_baseline_fails_closed(tmp_path: Path) -> None:
    old = contract(tmp_path / "old", shape())
    contract(tmp_path / "new", shape())
    (tmp_path / "old" / old["output_schema"]["path"]).write_text(SECRET)
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["failures"] == [{"stage": "baseline", "code": "SCHEMA_DRIFT"}]


def test_absent_candidate_registry_cannot_pass(tmp_path: Path) -> None:
    contract(tmp_path / "old", shape())
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["failures"] == [{"stage": "candidate", "code": "REGISTRY_MISSING"}]


def test_new_family_with_nonfinite_json_fails_closed(tmp_path: Path) -> None:
    document = {**shape(), "default": float("nan")}
    contract(tmp_path / "new", document)
    report = check_versions(tmp_path / "old", tmp_path / "new")
    assert report["status"] == "FAIL"
