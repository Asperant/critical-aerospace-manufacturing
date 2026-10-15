import json
import socket
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
        assert len(json.loads(result.output)["work_packages"]) == 179
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
    assert payload["wp_count"] == 179
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
