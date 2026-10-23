from __future__ import annotations

import json
from pathlib import Path

from mfgctl import timing


def test_state_dir_precedence(tmp_path: Path) -> None:
    assert timing.state_dir({"MFGCTL_STATE_DIR": str(tmp_path / "x")}) == tmp_path / "x"
    assert timing.state_dir({"XDG_STATE_HOME": str(tmp_path)}) == tmp_path / "mfgctl"


def test_append_and_load_round_trip(isolated_state: Path) -> None:
    environ = {"MFGCTL_STATE_DIR": str(isolated_state)}
    timing.append(timing.make_record("doctor", 120, 0), environ)
    timing.append(timing.make_record("doctor", 80, 1), environ)
    records = timing.load(environ)
    assert [r["duration_ms"] for r in records] == [120, 80]
    assert records[0]["schema"] == timing.SCHEMA


def test_disabled_recording_writes_nothing(isolated_state: Path) -> None:
    environ = {"MFGCTL_STATE_DIR": str(isolated_state), "MFGCTL_TIMINGS": "off"}
    timing.append(timing.make_record("doctor", 1, 0), environ)
    assert not (isolated_state / timing.FILENAME).exists()


def test_unwritable_state_dir_warns_but_never_raises(tmp_path: Path, capsys) -> None:
    blocker = tmp_path / "file-not-dir"
    blocker.write_text("", encoding="utf-8")
    timing.append(
        timing.make_record("doctor", 1, 0), {"MFGCTL_STATE_DIR": str(blocker)}
    )
    assert "timing not recorded" in capsys.readouterr().err


def test_torn_or_foreign_lines_are_skipped(isolated_state: Path) -> None:
    path = isolated_state / timing.FILENAME
    path.parent.mkdir(parents=True)
    good = timing.make_record("doctor", 5, 0).to_json()
    path.write_text(good + "\n" + '{"schema": "other"}\n' + '{"torn', encoding="utf-8")
    assert len(timing.load({"MFGCTL_STATE_DIR": str(isolated_state)})) == 1


def test_summary_compares_median_with_target() -> None:
    records = [
        {"command": "doctor", "duration_ms": d} for d in (1_000, 40_000, 2_000)
    ] + [{"command": "check --fast", "duration_ms": 120_000}]
    rows = {row["command"]: row for row in timing.summarize(records)}
    assert rows["doctor"]["median_ms"] == 2_000
    assert rows["doctor"]["max_ms"] == 40_000
    assert rows["doctor"]["median_within_target"] is True
    assert rows["check --fast"]["median_within_target"] is False
    text = timing.render_summary(list(rows.values()), Path("/x"))
    assert "MISS" in text and "within target" in text
    json.dumps(list(rows.values()))  # serialisable for --json


def test_failed_runs_never_count_toward_targets() -> None:
    records = [
        {"command": "up", "duration_ms": 10, "exit_code": 2},
        {"command": "smoke", "duration_ms": 500_000, "exit_code": 1},
        {"command": "smoke", "duration_ms": 30_000, "exit_code": 0},
    ]
    rows = {row["command"]: row for row in timing.summarize(records)}
    assert rows["up"]["median_ms"] is None
    assert rows["up"]["failed_runs"] == 1
    assert rows["up"]["median_within_target"] is None
    assert rows["smoke"]["median_ms"] == 30_000
    assert rows["smoke"]["median_within_target"] is True
    text = timing.render_summary(list(rows.values()), Path("/x"))
    assert "no successful run yet" in text and "failed=1" in text
