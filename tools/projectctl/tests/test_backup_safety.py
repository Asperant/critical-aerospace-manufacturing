"""Safety boundaries for the standalone operations script; no live Docker calls."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def backup_module():
    path = Path(__file__).resolve().parents[2] / "operations/plane_backup.py"
    spec = importlib.util.spec_from_file_location("plane_backup", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_restore_target_has_no_network_or_live_volume(backup_module):
    args = backup_module.restore_command("plane-restore-verify-test")
    assert args[args.index("--network") + 1] == "none"
    assert "--tmpfs" in args
    assert not set(args) & {"-v", "--volume", "--mount", "--volumes-from", "-p", "--publish"}
    assert backup_module.DB not in args


def test_checksums_detect_corruption_and_unexpected_files(backup_module, tmp_path, monkeypatch):
    monkeypatch.setattr(backup_module, "BACKUP_ROOT", tmp_path)
    path = tmp_path / "backup"
    path.mkdir()
    file = path / "postgres.dump"
    file.write_bytes(b"snapshot")
    (path / "manifest.json").write_text(json.dumps({"sha256": {"postgres.dump": backup_module.digest(file)}}))
    assert backup_module.verify_files(path)["sha256"]
    file.write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        backup_module.verify_files(path)
    file.write_bytes(b"snapshot")
    (path / "unexpected").write_bytes(b"extra")
    with pytest.raises(ValueError, match="checksum"):
        backup_module.verify_files(path)


def test_backup_path_rejects_outside_root_and_symlink(backup_module, tmp_path, monkeypatch):
    root = tmp_path / "backups"
    root.mkdir()
    monkeypatch.setattr(backup_module, "BACKUP_ROOT", root)
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValueError):
        backup_module.safe_backup(outside)
    link = root / "linked"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        backup_module.safe_backup(link)


def test_sql_and_secret_expansion_are_not_interpolated_on_host(backup_module):
    args = backup_module.db_command("psql", ("-Atc", backup_module.COUNTS))
    assert args[-1] == backup_module.COUNTS
    assert '"$@"' in args[5]
    assert '$POSTGRES_PASSWORD' in args[5]
