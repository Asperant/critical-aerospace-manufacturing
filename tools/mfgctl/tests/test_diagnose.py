from __future__ import annotations

import stat
import tarfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import make_env
from mfgctl import diagnose
from mfgctl import doctor as doctor_module
from mfgctl.cli import app
from mfgctl.probe import Result
from mfgctl.repo import ENV_ROOT
from typer.testing import CliRunner

TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"
PAT = "github_pat_" + "11ABCDEFG0123456789_abcdefghijklmnop"


@pytest.mark.parametrize(
    ("raw", "kept"),
    [
        (f"token {TOKEN} here", "token [REDACTED] here"),
        (f"x {PAT}", "x [REDACTED]"),
        ("AWS AKIAABCDEFGHIJKLMNOP", "AWS [REDACTED]"),
        ("PASSWORD=hunter2 next", "PASSWORD=[REDACTED] next"),
        ('api_key: "abc def"', "api_key: [REDACTED]"),
        (
            "postgresql://ci:s3cret@127.0.0.1/db",
            "postgresql://ci:[REDACTED]@127.0.0.1/db",
        ),
        ("plain text stays", "plain text stays"),
    ],
)
def test_redaction(raw: str, kept: str) -> None:
    assert diagnose.redact(raw) == kept


def test_private_key_block_is_removed() -> None:
    block = (
        "-----BEGIN OPENSSH PRIVATE KEY-----\nabc\n-----END OPENSSH PRIVATE KEY-----"
    )
    assert diagnose.redact(f"a\n{block}\nb") == "a\n[REDACTED]\nb"


def test_bundle_contents_are_redacted_and_private(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SOME_SECRET_ENV", "must-never-appear")
    status = ("git", "-C", str(repo), "status", "--short")
    env = make_env(repo, {status: Result(0, f"?? leaked-{TOKEN}.txt")})
    files = diagnose.collect(env, {"MFGCTL_STATE_DIR": str(tmp_path / "state")})
    assert set(files) == {"doctor.json", "git.txt", "timings.json", "versions.json"}
    everything = "\n".join(files.values())
    assert TOKEN not in everything and "[REDACTED]" in everything
    assert "must-never-appear" not in everything

    now = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
    path = diagnose.write_bundle(files, tmp_path / "out", now)
    assert path.name == "mfgctl-diagnose-20261023T120000Z.tar.gz"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with tarfile.open(path) as archive:
        names = sorted(member.name.split("/", 1)[1] for member in archive.getmembers())
    assert names == ["doctor.json", "git.txt", "timings.json", "versions.json"]


def test_cli_writes_bundle_to_requested_directory(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_ROOT, str(repo))
    monkeypatch.setattr(
        doctor_module, "default_environment", lambda root: make_env(root)
    )
    out = tmp_path / "bundles"
    result = CliRunner().invoke(app, ["diagnose", "bundle", "--output", str(out)])
    assert result.exit_code == 0
    assert "review the archive" in result.output
    assert len(list(out.glob("mfgctl-diagnose-*.tar.gz"))) == 1
    assert not list(repo.rglob("mfgctl-diagnose-*"))  # never inside the repository
