"""Produce RUN-PLAT-003-DEV-001: the WP-PLAT-003 development run on the shared host.

Run from the repository root on a committed, clean work tree, with Docker:

    uv run --project ci --locked python evidence/WP-PLAT-003/collect_run.py

It brings the complete `full` profile (infra, Temporal, Qdrant, MLflow) up from
empty volumes beside the observability stack, runs the REAL platform tests and the
05 readiness checklist, repeats `up` to show the setup jobs are idempotent, then
simulates a host reboot (every long-running container started at once, without
Compose ordering, as Docker does after a reboot) and checks health, the checklist
and the REAL tests again, and finally restarts with existing data. Every step is a
real invocation; exit codes and output are recorded as observed. Credentials, host
paths and the host name are replaced with placeholders. Note: `reset` removes this
machine's local platform data and credentials by design.
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

RUN_ID = "RUN-PLAT-003-DEV-001"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
HEALTHY = re.compile(r"healthy in (\d+) s")
PROJECT = "label=com.docker.compose.project=cap-platform"
REBOOT_TIMEOUT_S = 900


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def docker(*args: str) -> str:
    done = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False
    )
    return done.stdout


def simulate_reboot() -> tuple[int, str]:
    """Stop the platform, start every long-running container at once, wait for health."""
    compose = [
        "docker",
        "compose",
        "-f",
        "infra/compose/compose.yaml",
        "--profile",
        "full",
    ]
    subprocess.run([*compose, "stop"], capture_output=True, check=False)
    rows = docker("ps", "-a", "--filter", PROJECT, "--format", "{{.ID}} {{.Names}}")
    # Docker restarts only containers with a restart policy; setup jobs have none.
    names = {
        cid: name
        for cid, name in (line.split() for line in rows.splitlines())
        if docker(
            "inspect", "--format", "{{.HostConfig.RestartPolicy.Name}}", cid
        ).strip()
        not in {"", "no"}
    }
    started = time.monotonic()
    subprocess.run(["docker", "start", *names], capture_output=True, check=False)
    lines: list[str] = []
    healthy = False
    while time.monotonic() - started < REBOOT_TIMEOUT_S:
        states = {
            cid: docker("inspect", "--format", "{{.State.Health.Status}}", cid).strip()
            for cid in names
        }
        if all(state == "healthy" for state in states.values()):
            healthy = True
            break
        time.sleep(5)
    elapsed = round(time.monotonic() - started)
    lines.append(f"started {len(names)} long-running containers at once")
    lines.append(f"all healthy: {healthy} after {elapsed} s")
    for cid, name in sorted(names.items(), key=lambda item: item[1]):
        info = docker(
            "inspect",
            "--format",
            "{{.State.Health.Status}} restarts={{.RestartCount}}",
            cid,
        ).strip()
        lines.append(f"{name} {info}")
    return (0 if healthy else 1), "\n".join(lines) + f"\nREBOOT_HEALTHY_S={elapsed}\n"


def main() -> int:
    root = Path(git("rev-parse", "--show-toplevel"))
    os.chdir(root)
    if git("status", "--porcelain"):
        print("Refusing to run: commit or stash local changes first.", file=sys.stderr)
        return 2
    out = root / "evidence" / "WP-PLAT-003" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    stack = "infra/compose/stack.sh"
    observability = "infra/observability/stack.sh"
    env = {**os.environ, "PYTHONPATH": "ci:ci/scripts"}
    home = Path.home()
    states = [
        Path(
            os.environ.get("CAP_PLATFORM_STATE_DIR", home / ".local/state/cap-platform")
        ),
        Path(
            os.environ.get(
                "CAP_OBS_STATE_DIR",
                Path(os.environ.get("XDG_STATE_HOME", home / ".local/state"))
                / "cap-observability",
            )
        ),
    ]
    replacements: list[tuple[str, str]] = []

    def refresh_secrets() -> None:
        for state in states:
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
            (str(home), "<home>"),
            (socket.gethostname(), "<host>"),
        ]:
            text = text.replace(old, new)
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n"

    memory = [
        "docker",
        "stats",
        "--no-stream",
        "--format",
        "{{.Name}} {{.MemUsage}} {{.CPUPerc}}",
    ]
    steps: list[tuple[str, list[str] | None, str]] = [
        ("reset", [stack, "reset"], "reset.log.txt"),
        ("observability-up", [observability, "up"], "observability-up.log.txt"),
        ("fresh-start", [stack, "up", "full"], "fresh-start.log.txt"),
        ("smoke", [stack, "smoke"], "smoke.log.txt"),
        ("readiness", [stack, "readiness"], "readiness.log.txt"),
        ("memory", memory, "memory.txt"),
        ("second-up", [stack, "up", "full"], "second-up.log.txt"),
        ("reboot", None, "reboot.log.txt"),
        ("reboot-readiness", [stack, "readiness"], "reboot-readiness.log.txt"),
        ("reboot-smoke", [stack, "smoke"], "reboot-smoke.log.txt"),
        ("down", [stack, "down"], "down.log.txt"),
        ("restart", [stack, "up", "full"], "restart.log.txt"),
        ("final-down", [stack, "down"], "final-down.log.txt"),
        ("observability-down", [observability, "down"], "observability-down.log.txt"),
    ]
    results = []
    startup: dict[str, int | None] = {}
    for name, argv, filename in steps:
        started = time.monotonic()
        if argv is None:
            code, body = simulate_reboot()
        else:
            completed = subprocess.run(
                argv, capture_output=True, text=True, env=env, check=False
            )
            code, body = completed.returncode, completed.stdout + completed.stderr
            if name == "memory":
                body = "\n".join(
                    line
                    for line in completed.stdout.splitlines()
                    if line.startswith(("cap-platform-", "cap-observability-"))
                )
        refresh_secrets()
        (out / filename).write_text(clean(body), encoding="utf-8")
        results.append(
            {
                "step": name,
                "exit_code": code,
                "wall_s": round(time.monotonic() - started, 1),
                "output": filename,
            }
        )
        if name in {"fresh-start", "second-up", "restart"}:
            match = HEALTHY.search(body)
            startup[name] = int(match[1]) if match else None
        if name == "reboot":
            match = re.search(r"REBOOT_HEALTHY_S=(\d+)", body)
            startup[name] = int(match[1]) if match and code == 0 else None
        print(f"{name:<18} exit={code} -> {filename}")

    def tool(*argv: str) -> str:
        done = subprocess.run(list(argv), capture_output=True, text=True, check=False)
        return clean(done.stdout).strip()

    record = {
        "run_id": RUN_ID,
        "work_package": "WP-PLAT-003",
        "kind": "DEV run on the shared host: full profile with the observability stack",
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
            "fresh_start_empty_volumes_images_local": startup.get("fresh-start"),
            "second_up_idempotent": startup.get("second-up"),
            "simulated_reboot_parallel_start": startup.get("reboot"),
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
