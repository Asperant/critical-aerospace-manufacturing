"""Per-command timing records for the DX targets (NFR-DX-001…004, BENCH-DX-001).

Every mfgctl command appends one JSON line to a file in the user's state
directory — never inside the repository, so doctor stays read-only for the
repository. Location: ``$MFGCTL_STATE_DIR`` or ``$XDG_STATE_HOME/mfgctl`` or
``~/.local/state/mfgctl``. ``MFGCTL_TIMINGS=off`` disables recording.

These records are development measurements (BENCH-DX-001 runs in DEV); they are
not release evidence until bound to a HardwareProfile in a later WP.
"""

from __future__ import annotations

import json
import platform
import socket
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mfgctl import __version__

SCHEMA = "mfgctl.timing/v1"
FILENAME = "timings.jsonl"
# Targets from 01 Item 82 (S2 class: measured and recorded, PASS or MISS).
TARGETS_MS = {
    "doctor": 30_000,  # NFR-DX-001
    "check --fast": 90_000,  # NFR-DX-002
    "smoke": 120_000,  # NFR-DX-003
    "up": 300_000,  # NFR-DX-004
    "diagnose bundle": 120_000,  # NFR-DX-008
}


def state_dir(environ: Mapping[str, str]) -> Path:
    if environ.get("MFGCTL_STATE_DIR"):
        return Path(environ["MFGCTL_STATE_DIR"]).expanduser()
    base = environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base).expanduser() / "mfgctl"


def enabled(environ: Mapping[str, str]) -> bool:
    return environ.get("MFGCTL_TIMINGS", "").lower() not in {"off", "0", "false"}


@dataclass(frozen=True)
class Record:
    command: str
    duration_ms: int
    exit_code: int
    recorded_at: str
    host: str
    python: str
    version: str = __version__

    def to_json(self) -> str:
        return json.dumps({"schema": SCHEMA, **self.__dict__}, ensure_ascii=False)


def make_record(command: str, duration_ms: int, exit_code: int) -> Record:
    return Record(
        command=command,
        duration_ms=duration_ms,
        exit_code=exit_code,
        recorded_at=datetime.now(UTC).isoformat(timespec="seconds"),
        host=socket.gethostname(),
        python=f"{platform.python_implementation()} {platform.python_version()}",
    )


def append(record: Record, environ: Mapping[str, str]) -> None:
    """Best effort: a failing write warns on stderr and never fails the command."""
    if not enabled(environ):
        return
    target = state_dir(environ) / FILENAME
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json() + "\n")
    except OSError as exc:
        print(f"mfgctl: timing not recorded ({exc})", file=sys.stderr)


def load(environ: Mapping[str, str]) -> list[dict[str, object]]:
    target = state_dir(environ) / FILENAME
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    records: list[dict[str, object]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue  # a torn last line must not hide the rest
        if isinstance(value, dict) and value.get("schema") == SCHEMA:
            records.append(value)
    return records


def _median(values: Sequence[int]) -> int:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def summarize(records: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    by_command: dict[str, list[int]] = {}
    for record in records:
        duration = record.get("duration_ms")
        command = record.get("command")
        if isinstance(command, str) and isinstance(duration, int):
            by_command.setdefault(command, []).append(duration)
    rows: list[dict[str, object]] = []
    for command, durations in sorted(by_command.items()):
        target = TARGETS_MS.get(command)
        median = _median(durations)
        rows.append(
            {
                "command": command,
                "runs": len(durations),
                "median_ms": median,
                "max_ms": max(durations),
                "last_ms": durations[-1],
                "target_ms": target,
                "median_within_target": None if target is None else median <= target,
            }
        )
    return rows


def render_summary(rows: Sequence[Mapping[str, object]], location: Path) -> str:
    if not rows:
        return f"No timing records yet in {location}."
    lines = [f"mfgctl timings — {location}"]
    for row in rows:
        target = row["target_ms"]
        verdict = ""
        if isinstance(target, int):
            verdict = "  within target" if row["median_within_target"] else "  MISS"
            verdict += f" ({target / 1000:.0f} s)"
        lines.append(
            f"  {row['command']:<20} runs={row['runs']:<3} "
            f"median={_seconds(row['median_ms'])} max={_seconds(row['max_ms'])}{verdict}"
        )
    return "\n".join(lines)


def _seconds(value: object) -> str:
    return f"{value / 1000:.1f}s" if isinstance(value, int) else "?"
