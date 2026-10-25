"""TEST-EVT-001-010: approved local catalog loading and whole-snapshot gate."""

import copy
import hashlib
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from cap_contracts import ContractError, StreamDefinitions
from cap_contracts.ci_gate import check_versions, main
from cap_contracts.streams import STREAM_CATALOG_PATH
from test_contract_subject_bindings import catalog, context, stream

SECRET = "PRIVATE-INPUT-DO-NOT-EMIT"


def write(root: Path, value: object) -> Path:
    path = root / STREAM_CATALOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def snapshot(root: Path) -> None:
    """Real hash-verified artifacts for the synthetic async declaration fixtures."""
    registry, _ = context()
    producers: list[dict[str, Any]] = []
    for contract_id in registry.contract_ids():
        declaration = registry.get(contract_id)
        schema_path = root / declaration.output_schema.path
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema = b'{"type":"object","properties":{"id":{"type":"string"}}}'
        schema_path.write_bytes(schema)
        record = asdict(declaration)
        record["output_schema"]["sha256"] = hashlib.sha256(schema).hexdigest()
        fixture = schema_path.with_name("example.json")
        fixture.write_bytes(b"{}")
        record["fixtures"] = [
            {
                "path": str(fixture.relative_to(root)),
                "sha256": hashlib.sha256(b"{}").hexdigest(),
            }
        ]
        path = root / "packages/contracts/registry" / f"{contract_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record))
        producers.append(
            {
                "producer": declaration.canonical_producer,
                "semantic_owner": declaration.semantic_owner,
                "source_roots": [
                    str(Path(declaration.output_schema.path).parent) + "/"
                ],
                "contracts": [
                    {
                        "family": declaration.parsed_id.family,
                        "contract_type": declaration.contract_type,
                        "authority_level": declaration.authority_level,
                    }
                ],
            }
        )
    (root / "packages/contracts/producer-authorities.json").write_text(
        json.dumps(
            {"schema_version": "cap-producer-authorities-v1", "producers": producers}
        )
    )
    write(root, catalog(stream(), stream("other")))


def test_loads_complete_multi_entry_catalog_deterministically(tmp_path: Path) -> None:
    value = catalog(stream("other"), stream())
    path = write(tmp_path, value)
    model = StreamDefinitions.load(tmp_path, *context())
    assert len(model.definitions) == 2
    assert [item.bindings[0].binding_id for item in model.definitions] == [
        "test.observation.v1",
        "test.other.v1",
    ]
    path.write_text(json.dumps(catalog(stream(), stream("other")), sort_keys=True))
    assert StreamDefinitions.load(tmp_path, *context()).to_json() == model.to_json()


@pytest.mark.parametrize(
    "failure,code",
    [
        ("duplicate_id", "SUBJECT_BINDING_DUPLICATE"),
        ("conflicting_subject", "SUBJECT_OWNERSHIP_CONFLICT"),
        ("unknown_producer", "SUBJECT_PRODUCER_MISMATCH"),
        ("family", "SUBJECT_FAMILY_MISMATCH"),
        ("version", "SUBJECT_VERSION_MISMATCH"),
        ("malformed", "STREAM_DEFINITION_INVALID"),
        ("missing", "STREAM_DEFINITION_INVALID"),
    ],
)
def test_one_invalid_entry_rejects_whole_catalog_and_gate(
    tmp_path: Path, failure: str, code: str
) -> None:
    old, new = tmp_path / "old", tmp_path / "new"
    snapshot(old)
    snapshot(new)
    first, second = stream(), stream("other")
    if failure == "duplicate_id":
        second = copy.deepcopy(first)
        second["stream_id"] = "test.another-stream.v1"
        second["bindings"][0]["subject"] = "test.another-subject.v1"
    elif failure == "conflicting_subject":
        second["bindings"][0]["subject"] = first["bindings"][0]["subject"]
    elif failure == "unknown_producer":
        second["bindings"][0]["canonical_producer"] = "unknown-producer"
    elif failure == "family":
        second["bindings"][0]["schema_family"] = "test.observation"
    elif failure == "version":
        second["bindings"][0]["version"] = 2
    elif failure == "malformed":
        second["bindings"][0] = None
    else:
        del second["dlq_policy"]
    write(new, catalog(first, second))
    with pytest.raises(ContractError, match=code):
        StreamDefinitions.load(new, *context())
    report = check_versions(old, new)
    assert report["status"] == "FAIL"
    assert report["validated"] == 0
    assert report["failures"] == [{"stage": "candidate", "code": code}]
    assert check_versions(old, new) == report


@pytest.mark.parametrize(
    "raw",
    [
        "{",
        "null",
        "[]",
        '{"schema_version":"cap-stream-definitions-v1","streams":[]}',
        '{"schema_version":"cap-stream-definitions-v1","streams":[],"streams":[]}',
        '{"schema_version":"cap-stream-definitions-v1","streams":NaN}',
    ],
)
def test_malformed_json_or_catalog_fails_closed(tmp_path: Path, raw: str) -> None:
    write(tmp_path, {}).write_text(raw)
    with pytest.raises(ContractError):
        StreamDefinitions.load(tmp_path, *context())


def test_duplicate_json_fields_inside_binding_are_rejected(tmp_path: Path) -> None:
    raw = json.dumps(catalog(stream()))
    raw = raw.replace(
        '"subject": "test.observation.v1"',
        '"subject": "test.observation.v1", "subject": "test.other.v1"',
    )
    write(tmp_path, {}).write_text(raw)
    with pytest.raises(ContractError, match="STREAM_CATALOG_INVALID"):
        StreamDefinitions.load(tmp_path, *context())


@pytest.mark.parametrize("component", ["file", "parent", "dangling", "directory"])
def test_only_regular_local_catalog_source_is_approved(
    tmp_path: Path, component: str
) -> None:
    external = tmp_path / "external"
    path = write(external, catalog(stream()))
    root = tmp_path / "repository"
    target = root / STREAM_CATALOG_PATH
    target.parent.mkdir(parents=True)
    if component == "parent":
        target.parent.rmdir()
        target.parent.symlink_to(path.parent, target_is_directory=True)
    elif component == "directory":
        target.mkdir()
    else:
        target.symlink_to(path if component == "file" else external / "missing.json")
    with pytest.raises(ContractError, match="STREAM_CATALOG_SOURCE_INVALID"):
        StreamDefinitions.load(root, *context())


def test_alternate_filename_and_include_are_not_approved(tmp_path: Path) -> None:
    path = write(tmp_path, catalog(stream()))
    path.rename(path.with_name("unapproved-catalog.json"))
    with pytest.raises(ContractError, match="STREAM_CATALOG_MISSING"):
        StreamDefinitions.load(tmp_path, *context())
    value = catalog(stream())
    value["includes"] = ["https://example.invalid/remote.json", "../external.json"]
    write(tmp_path, value)
    with pytest.raises(ContractError, match="STREAM_DEFINITION_INVALID"):
        StreamDefinitions.load(tmp_path, *context())


def test_gate_validates_unchanged_catalog_and_preserves_hash_checks(
    tmp_path: Path,
) -> None:
    old, new = tmp_path / "old", tmp_path / "new"
    snapshot(old)
    snapshot(new)
    assert check_versions(old, new)["status"] == "PASS"
    assert check_versions(old, new)["unchanged"] == 2
    before = check_versions(old, new)
    write(new, catalog(stream("other"), stream()))
    assert check_versions(old, new) == before
    declaration = context()[0].get("test.observation.v1")
    (new / declaration.output_schema.path).write_text(SECRET)
    report = check_versions(old, new)
    assert report["failures"] == [{"stage": "candidate", "code": "SCHEMA_DRIFT"}]
    assert SECRET not in json.dumps(report)


def test_gate_rejects_invalid_baseline_and_catalog_removal(tmp_path: Path) -> None:
    old, new = tmp_path / "old", tmp_path / "new"
    snapshot(old)
    snapshot(new)
    path = write(old, {"invalid": SECRET})
    report = check_versions(old, new)
    assert report["failures"] == [
        {"stage": "baseline", "code": "STREAM_DEFINITION_INVALID"}
    ]
    assert SECRET not in json.dumps(report)
    write(old, catalog(stream(), stream("other")))
    (new / STREAM_CATALOG_PATH).unlink()
    assert check_versions(old, new)["failures"] == [
        {"stage": "candidate", "code": "STREAM_CATALOG_REMOVED"}
    ]
    path.unlink()
    assert check_versions(old, new)["status"] == "PASS"


def test_unknown_registered_producer_rejects_catalog_in_gate(tmp_path: Path) -> None:
    snapshot(tmp_path)
    declaration = tmp_path / "packages/contracts/registry/test.observation.v1.json"
    record = json.loads(declaration.read_text())
    record["canonical_producer"] = "unknown-producer"
    declaration.write_text(json.dumps(record))
    value = stream()
    value["bindings"][0]["canonical_producer"] = "unknown-producer"
    write(tmp_path, catalog(value, stream("other")))
    assert check_versions(tmp_path / "absent", tmp_path)["failures"] == [
        {"stage": "candidate", "code": "PRODUCER_UNKNOWN"}
    ]


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL
    ).strip()


@pytest.mark.parametrize("source", ["invalid", "symlink", "directory"])
def test_cli_uses_committed_catalog_and_redacts_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    source: str,
) -> None:
    snapshot(tmp_path)
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.name", "Catalog test")
    git(tmp_path, "config", "user.email", "catalog@example.invalid")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "valid catalog")
    baseline = git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.chdir(tmp_path)
    assert main(["--base", baseline]) == 0
    assert json.loads(capsys.readouterr().out)["unchanged"] == 2
    path = tmp_path / STREAM_CATALOG_PATH
    if source == "invalid":
        write(tmp_path, {"malformed": SECRET})
    else:
        path.unlink()
        if source == "symlink":
            path.symlink_to("/unapproved/" + SECRET)
        else:
            path.mkdir()
            (path / "unexpected.json").write_text(SECRET)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-qm", "invalid catalog")
    if source == "invalid":
        write(tmp_path, catalog(stream(), stream("other")))
    assert main(["--base", baseline]) == 1
    output = capsys.readouterr().out
    assert SECRET not in output
    report = json.loads(output)
    assert report["status"] == "FAIL"
    expected = {
        "invalid": "STREAM_DEFINITION_INVALID",
        "symlink": "GIT_ENTRY_UNSUPPORTED",
        "directory": "STREAM_CATALOG_SOURCE_INVALID",
    }[source]
    assert report["failures"][0]["code"] == expected
    assert main(["--base", baseline]) == 1
    assert capsys.readouterr().out == output
