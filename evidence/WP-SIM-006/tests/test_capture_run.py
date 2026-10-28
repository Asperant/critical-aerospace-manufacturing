"""Focused tests of the evidence collector (capture_run.py): raw byte retention,
full stderr, failing and missing commands, and input binding of the scripts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "capture_run", Path(__file__).resolve().parents[1] / "capture_run.py"
)
assert _SPEC is not None and _SPEC.loader is not None
cr = importlib.util.module_from_spec(_SPEC)
sys.modules["capture_run"] = cr
_SPEC.loader.exec_module(cr)

PY = sys.executable
RAW = b"\xff\xfe \r\nout  \n\n"
NOISE = "".join(f"diagnostic {i} \n" for i in range(6))
WRITE = f"import sys; sys.stdout.buffer.write({RAW!r}); sys.stderr.write({NOISE!r})"


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *cmd], cwd=repo, check=True)
    (repo / "base.txt").write_text("base\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
    return repo


def results_of(out: Path) -> list[dict]:
    return json.loads((out / "results.json").read_text())


def test_stdout_and_stderr_are_kept_byte_for_byte_with_hashes(tmp_path: Path) -> None:
    repo, out = make_repo(tmp_path), tmp_path / "run"
    assert cr.capture(repo, out, [("w", [PY, "-c", WRITE])]) == 0
    (entry,) = results_of(out)
    assert (out / "w.stdout").read_bytes() == RAW
    assert (out / "w.stderr").read_bytes() == NOISE.encode()  # all 6 lines
    assert entry["stdout_sha256"] == hashlib.sha256(RAW).hexdigest()
    assert entry["stderr_sha256"] == hashlib.sha256(NOISE.encode()).hexdigest()
    assert (entry["stdout_bytes"], entry["stderr_bytes"]) == (len(RAW), len(NOISE))
    # The display line is derived and separate; it never touches the stored bytes.
    assert entry["display_result_line"] == "out"


def test_failing_and_missing_commands_are_recorded_and_the_run_continues(
    tmp_path: Path,
) -> None:
    repo, out = make_repo(tmp_path), tmp_path / "run"
    fail = "import sys; print('x'); sys.stderr.write('why\\n'); sys.exit(3)"
    commands = [
        ("fail", [PY, "-c", fail]),
        ("missing", ["/nonexistent/command"]),
        ("ok", [PY, "-c", "print('fine')"]),
    ]
    assert cr.capture(repo, out, commands) == 1
    fail_r, missing_r, ok_r = results_of(out)
    assert (fail_r["exit_code"], missing_r["exit_code"], ok_r["exit_code"]) == (
        3,
        None,
        0,
    )
    assert (out / "fail.stderr").read_bytes() == b"why\n"
    assert "FileNotFoundError" in missing_r["error"]
    assert ok_r["display_result_line"] == "fine"


def test_scripts_are_bound_into_the_input_manifest_and_only_outputs_excluded(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    ev = repo / "evidence/WP-SIM-006"
    (ev / "runs/run-x").mkdir(parents=True)
    for name in ("capture_run.py", "other_script.py", "README.md", "other.md"):
        (ev / name).write_text(name + "\n")
    (ev / "runs/run-x/results.json").write_text("{}\n")
    (repo / "base.txt").write_text("changed\n")
    files = cr.input_manifest(repo, cr.MANIFEST_EXCLUDES)
    assert set(files) == {
        "base.txt",
        "evidence/WP-SIM-006/capture_run.py",
        "evidence/WP-SIM-006/other_script.py",
        "evidence/WP-SIM-006/other.md",
    }
    (ev / "other_script.py").write_text("edited\n")
    after = cr.input_manifest(repo, cr.MANIFEST_EXCLUDES)
    key = "evidence/WP-SIM-006/other_script.py"
    assert after[key] != files[key]
    assert (
        after["evidence/WP-SIM-006/capture_run.py"]
        == files["evidence/WP-SIM-006/capture_run.py"]
    )


def test_host_facts_are_taken_at_start_and_at_finish(tmp_path: Path) -> None:
    repo, out = make_repo(tmp_path), tmp_path / "run"
    cr.capture(repo, out, [("slow", [PY, "-c", "import time; time.sleep(1.1)"])])
    identity = json.loads((out / "identity.json").read_text())
    (entry,) = results_of(out)
    assert identity["host_at_start"]["recorded_utc"] <= entry["started_utc"]
    assert identity["host_at_finish"]["recorded_utc"] >= entry["finished_utc"]
    # The command took over a second, so a finish measurement copied from the start
    # would be strictly earlier.
    assert (
        identity["host_at_start"]["recorded_utc"]
        < identity["host_at_finish"]["recorded_utc"]
    )
    assert "loadavg_at_start" not in identity["hardware"]
    assert identity["source"]["manifest_excludes"] == list(cr.MANIFEST_EXCLUDES)


def test_an_existing_run_directory_is_never_overwritten(tmp_path: Path) -> None:
    repo, out = make_repo(tmp_path), tmp_path / "run"
    out.mkdir()
    try:
        cr.capture(repo, out, [])
    except FileExistsError:
        return
    raise AssertionError("an existing run directory was reused")


def test_a_clean_tree_stays_clean_with_the_run_directory_inside_it(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path)
    out = repo / "runs" / "run-1"
    cr.capture(repo, out, [("ok", [PY, "-c", "pass"])])
    identity = json.loads((out / "identity.json").read_text())
    assert identity["source"]["tree_clean"] is True
    assert identity["source"]["changed_or_untracked_files_sha256"] == {}
    (repo / "stray.txt").write_text("x\n")
    cr.capture(repo, repo / "runs" / "run-2", [])
    again = json.loads((repo / "runs/run-2/identity.json").read_text())
    assert again["source"]["tree_clean"] is False
