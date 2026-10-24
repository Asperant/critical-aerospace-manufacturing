"""Produce RUN-PLAT-001-DEV-001: the WP-PLAT-001 development run on the shared host.

Run from the repository root on a committed, clean work tree, with Docker:

    uv run --project ci --locked python evidence/WP-PLAT-001/collect_run.py

It measures startup-to-healthy of the `infra` profile twice with images already
local (NFR-DEP-002 is defined with images pre-available): a fresh start after
`stack.sh reset` (empty volumes, first Keycloak/PostgreSQL initialization) and a
restart with existing data. In between it runs the REAL smoke through mfgctl and
records the actual memory use against the declared limits. Every step is a
real invocation; exit codes and output are recorded as observed. Credentials,
host paths and the host name are replaced with placeholders. Note: `reset`
removes this machine's local platform data and credentials by design.
"""

from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RUN_ID = "RUN-PLAT-001-DEV-001"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
HEALTHY = re.compile(r"healthy in (\d+) s")


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    root = Path(git("rev-parse", "--show-toplevel"))
    os.chdir(root)
    if git("status", "--porcelain"):
        print("Refusing to run: commit or stash local changes first.", file=sys.stderr)
        return 2
    out = root / "evidence" / "WP-PLAT-001" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    stack = "infra/compose/stack.sh"
    uv = ["uv", "run", "--project", "ci", "--locked"]
    env = {**os.environ, "PYTHONPATH": "ci:ci/scripts"}
    state = Path(
        os.environ.get(
            "CAP_PLATFORM_STATE_DIR", Path.home() / ".local/state/cap-platform"
        )
    )
    replacements: list[tuple[str, str]] = []

    def refresh_secrets() -> None:
        credentials = state / "credentials.env"
        if credentials.is_file():
            for line in credentials.read_text("utf-8").splitlines():
                _, _, value = line.partition("=")
                if value and (value, "<redacted>") not in replacements:
                    replacements.insert(0, (value, "<redacted>"))

    def clean(text: str) -> str:
        text = ANSI.sub("", text)
        for old, new in [
            *replacements,
            (str(root), "<repo>"),
            (str(Path.home()), "<home>"),
            (socket.gethostname(), "<host>"),
        ]:
            text = text.replace(old, new)
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n"

    steps: list[tuple[str, list[str], str]] = [
        ("reset", [stack, "reset"], "reset.log.txt"),
        ("fresh-start", [stack, "up", "infra"], "fresh-start.log.txt"),
        ("smoke", [*uv, "mfgctl", "smoke", "platform-infra"], "smoke.log.txt"),
        (
            "memory",
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.Name}} {{.MemUsage}} {{.CPUPerc}}",
            ],
            "memory.txt",
        ),
        ("status", [*uv, "mfgctl", "status"], "status.log.txt"),
        ("down", [stack, "down"], "down.log.txt"),
        ("restart", [stack, "up", "infra"], "restart.log.txt"),
        ("final-down", [stack, "down"], "final-down.log.txt"),
    ]
    results = []
    startup: dict[str, int | None] = {}
    for name, argv, filename in steps:
        started = time.monotonic()
        completed = subprocess.run(
            argv, capture_output=True, text=True, env=env, check=False
        )
        refresh_secrets()
        body = completed.stdout + completed.stderr
        if name == "memory":
            body = "\n".join(
                line
                for line in completed.stdout.splitlines()
                if line.startswith("cap-platform-")
            )
        (out / filename).write_text(clean(body), encoding="utf-8")
        results.append(
            {
                "step": name,
                "exit_code": completed.returncode,
                "wall_s": round(time.monotonic() - started, 1),
                "output": filename,
            }
        )
        if name in {"fresh-start", "restart"}:
            match = HEALTHY.search(body)
            startup[name] = int(match[1]) if match else None
        print(f"{name:<12} exit={completed.returncode} -> {filename}")

    def tool(*argv: str) -> str:
        done = subprocess.run(list(argv), capture_output=True, text=True, check=False)
        return clean(done.stdout).strip()

    record = {
        "run_id": RUN_ID,
        "work_package": "WP-PLAT-001",
        "kind": "DEV run on the shared host; infra profile only (not the full Integration profile)",
        "boundary_mode": "REAL",
        "code_revision": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": {
            "machine": platform.machine(),
            "system": platform.system(),
            "cpus": os.cpu_count(),
            "docker": tool("docker", "version", "--format", "{{.Server.Version}}"),
            "compose": tool("docker", "compose", "version", "--short"),
        },
        "startup_to_healthy_s": {
            "fresh_start_images_local": startup.get("fresh-start"),
            "restart_with_data": startup.get("restart"),
            "nfr_dep_002_threshold_s": 600,
        },
        "steps": results,
        "non_zero_explained": {
            r["step"]: "unexpected: investigate before using this run"
            for r in results
            if r["exit_code"] != 0
        },
    }
    (out / "record.json").write_text(
        clean(json.dumps(record, indent=2, ensure_ascii=False)), encoding="utf-8"
    )
    print(
        f"Recorded {RUN_ID} for {record['code_revision'][:12]}: {record['startup_to_healthy_s']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
