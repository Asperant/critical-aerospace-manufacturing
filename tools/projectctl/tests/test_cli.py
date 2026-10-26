import json
import socket
from pathlib import Path
import pytest
from typer.testing import CliRunner

from projectctl.cli import app

runner = CliRunner()


@pytest.mark.parametrize("command", ["parse", "validate", "status", "catalog-lint", "catalog-export"])
def test_default_commands_no_network_or_file_mutation(command, root, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network or file mutation attempted")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.chdir(root)
    # Deny writable opens, including files outside the repository.
    import builtins
    import io
    import os
    original_open, original_io_open, original_os_open = builtins.open, io.open, os.open
    def guard_open(original):
        def guarded(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                forbidden()
            return original(file, mode, *args, **kwargs)
        return guarded
    def guarded_os_open(path, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            forbidden()
        return original_os_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", guard_open(original_open))
    monkeypatch.setattr(io, "open", guard_open(original_io_open))
    monkeypatch.setattr(os, "open", guarded_os_open)
    for name in ["mkdir", "rename", "replace", "remove", "unlink", "rmdir"]:
        monkeypatch.setattr(os, name, forbidden)
    result = runner.invoke(app, [command])
    assert result.exit_code == 0, result.output
    if command == "catalog-export":
        assert len(json.loads(result.output)["requirements"]) == 306
    elif command == "catalog-lint":
        assert "PASS (306 records)" in result.output
        assert "NOT_CERTIFIED" in result.output
    elif command == "parse":
        assert len(json.loads(result.output)["work_packages"]) == 180
    else:
        assert "UNAVAILABLE (documentation only)" in result.output
        assert "PASS" in result.output
        assert "BACKLOG" not in result.output


def test_json_is_deterministic(root):
    args = ["parse", "--root", str(root)]
    first = runner.invoke(app, args)
    second = runner.invoke(app, args)
    assert first.exit_code == second.exit_code == 0
    assert first.output == second.output


@pytest.mark.parametrize("command", ["validate", "status"])
def test_summary_json(command, root):
    result = runner.invoke(app, [command, "--root", str(root), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["wp_count"] == 180
    assert payload["capability_count"] == 29
    assert payload["validation"] == "PASS"
    assert payload["execution_status"].startswith("UNAVAILABLE")


def test_validation_errors_nonzero(tmp_path, sample):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/04_Work_Breakdown_Structure.md").write_text(sample, encoding="utf-8")
    result = runner.invoke(app, ["validate", "--root", str(tmp_path), "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output)["validation"] == "FAIL"


def test_missing_input(tmp_path):
    result = runner.invoke(app, ["parse", "--root", str(tmp_path)])
    assert result.exit_code == 2
    assert "INPUT_ERROR" in result.output


def test_no_sync_command():
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 2


@pytest.mark.parametrize("metadata,code", [
    ("MISSING", "TRACE_META_CONFLICT"), ({}, "TRACE_META_CONFLICT"),
    (None, "TRACE_META_SHAPE"), ([], "TRACE_META_SHAPE"),
    ("scalar", "TRACE_META_SHAPE"), (7, "TRACE_META_SHAPE"),
    (True, "TRACE_META_SHAPE"), ({"class": []}, "TRACE_META_SHAPE"),
    ({"owner": []}, "TRACE_META_SHAPE"), ({"owner": None}, "TRACE_META_SHAPE"),
    ({"anchor": 123}, "TRACE_META_SHAPE"), ({"anchor": None}, "TRACE_META_SHAPE"),
])
def test_malformed_rtm_metadata_has_deterministic_json(root, monkeypatch, metadata, code):
    path = root / "docs/03_Requirements_Traceability_Matrix.md"
    text = path.read_text()
    line = next(line for line in text.splitlines() if line.startswith("  meta:"))
    replacement = "  ignored_meta: {}" if metadata == "MISSING" else "  meta: " + json.dumps(metadata)
    malformed = text.replace(line, replacement, 1)
    original = Path.read_text

    def read_text(self, *args, **kwargs):
        return malformed if self == path else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    args = ["validate", "--root", str(root), "--json"]
    first = runner.invoke(app, args)
    second = runner.invoke(app, args)
    assert first.exit_code == second.exit_code == 1
    assert first.output == second.output
    payload = json.loads(first.output)
    assert payload["validation"] == "FAIL"
    errors = [d for d in payload["diagnostics"] if d["code"] == code]
    assert len(errors) == 1
    assert errors[0]["severity"] == "ERROR"
    assert errors[0]["record_id"] == "FR-GOV-001"
    assert errors[0]["source"]["path"] == "docs/03_Requirements_Traceability_Matrix.md"


@pytest.mark.parametrize("cells", [1, 2])
def test_short_rtm_index_row_has_json_error(root, monkeypatch, cells):
    path = root / "docs/03_Requirements_Traceability_Matrix.md"
    text = path.read_text()
    start, end = text.index("## 6. View A"), text.index("## 7. View B")
    view = text[start:end]
    line = next(line for line in view.splitlines() if line.startswith("| FR-"))
    values = line.split("|")[1:-1]
    short = "|" + "|".join(values[:cells]) + "|"
    malformed = text[:start] + view.replace(line, short, 1) + text[end:]
    original = Path.read_text

    def read_text(self, *args, **kwargs):
        return malformed if self == path else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    result = runner.invoke(app, ["validate", "--root", str(root), "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["validation"] == "FAIL"
    errors = [d for d in payload["diagnostics"] if d["code"] == "RTM_INDEX_SHAPE"]
    assert len(errors) == 1
    assert errors[0]["severity"] == "ERROR"
    assert errors[0]["record_id"] == values[0].strip()
