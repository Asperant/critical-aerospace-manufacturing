"""Produce RUN-OBS-001-DEV-001: the WP-OBS-001 development run on the shared host.

Run from the repository root on a committed, clean work tree, with Docker:

    uv run --project ci --locked python evidence/WP-OBS-001/collect_run.py

Every step is a real invocation against the REAL Collector and OpenObserve; its
exit code and output are recorded as observed (a failing step is recorded, never
hidden). Credentials, host paths and the host name are replaced with
placeholders before anything is written. The stack is stopped at the end, its
data is kept (``stack.sh reset`` removes it).
"""

from __future__ import annotations

import base64
import json
import os
import re
import socket
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

RUN_ID = "RUN-OBS-001-DEV-001"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
EXPLANATIONS: dict[str, str] = {}
SAMPLE = """\
import logging, sys
from cap_observability.telemetry import configure
from opentelemetry import trace

telemetry = configure("evidence-sample", "0.1.0", environ={
    "USER": "evidence", "CAP_ENVIRONMENT": "local-evidence",
    "OTEL_EXPORTER_OTLP_ENDPOINT": sys.argv[1]})
log = logging.getLogger("evidence")
with trace.get_tracer("evidence").start_as_current_span("evidence.sample"):
    log.info("sample started", extra={"event_name": "evidence.sample_started",
                                       "correlation_id": "evidence-1"})
    log.warning("token=abc123 must be redacted", extra={"correlation_id": "evidence-1"})
    try:
        raise TimeoutError("dependency did not answer")
    except TimeoutError:
        log.exception("dependency failed", extra={"error_code": "DEPENDENCY_TIMEOUT",
                                                  "correlation_id": "evidence-1"})
telemetry.shutdown()
"""


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
    out = root / "evidence" / "WP-OBS-001" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    stack = "infra/observability/stack.sh"
    env = {**os.environ, "PYTHONPATH": "ci:ci/scripts"}
    up = subprocess.run([stack, "up"], capture_output=True, text=True, check=False)
    printed = subprocess.run(
        [stack, "env"], capture_output=True, text=True, check=False
    ).stdout
    stack_env = dict(line.split("=", 1) for line in printed.splitlines() if "=" in line)
    env.update(stack_env)
    secrets_ = [stack_env.get("O2_ROOT_PASSWORD", "")]
    if secrets_[0]:
        token = f"{stack_env.get('O2_ROOT_EMAIL', '')}:{secrets_[0]}"
        secrets_.append(base64.b64encode(token.encode()).decode())
    replacements = [(s, "<redacted>") for s in secrets_ if s] + [
        (str(root), "<repo>"),
        (str(Path.home()), "<home>"),
        (socket.gethostname(), "<host>"),
    ]

    def clean(text: str) -> str:
        text = ANSI.sub("", text)
        for old, new in replacements:
            text = text.replace(old, new)
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n"

    uv = ["uv", "run", "--project", "ci", "--locked"]
    pytest = [*uv, "python", "-m", "pytest", "-p", "pytest_quarantine"]
    sample = out / "sample-logs.jsonl"
    otlp = stack_env.get("OTLP_HTTP_URL", "http://127.0.0.1:54318")
    steps: list[tuple[str, list[str], str]] = [
        (
            "unit-tests",
            [*pytest, "packages/observability/tests", "infra/observability/tests"]
            + ["-m", "not integration", "-q"],
            "unit-tests.log.txt",
        ),
        (
            "coverage",
            [*uv, "python", "-m", "cap_observability", "check-coverage"]
            + ["infra/observability/coverage.json"],
            "coverage.log.txt",
        ),
        ("dashboards", [stack, "dashboards"], "dashboards.log.txt"),
        (
            "integration-tests",
            [*pytest, "infra/observability/tests", "-m", "integration", "-v"],
            "integration-tests.log.txt",
        ),
        ("sample", [*uv, "python", "-c", SAMPLE, otlp], "sample-logs.jsonl"),
        (
            "check-logs",
            [*uv, "python", "-m", "cap_observability", "check-logs", str(sample)],
            "check-logs.log.txt",
        ),
        ("status", [stack, "status"], "status.log.txt"),
        ("down", [stack, "down"], "down.log.txt"),
    ]
    (out / "up.log.txt").write_text(clean(up.stdout + up.stderr), encoding="utf-8")
    results = [{"step": "up", "exit_code": up.returncode, "output": "up.log.txt"}]
    print(f"{'up':<18} exit={up.returncode} -> up.log.txt")
    for name, argv, filename in steps:
        completed = subprocess.run(
            argv, capture_output=True, text=True, env=env, check=False
        )
        body = (
            completed.stdout
            if filename.endswith(".jsonl")
            else completed.stdout + completed.stderr
        )
        (out / filename).write_text(clean(body), encoding="utf-8")
        results.append(
            {"step": name, "exit_code": completed.returncode, "output": filename}
        )
        print(f"{name:<18} exit={completed.returncode} -> {filename}")

    record = {
        "run_id": RUN_ID,
        "work_package": "WP-OBS-001",
        "kind": "DEV run on the shared host against the REAL Collector and OpenObserve",
        "boundary_mode": "REAL",
        "code_revision": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "steps": results,
        "non_zero_explained": {
            r["step"]: EXPLANATIONS.get(
                str(r["step"]), "unexpected: investigate before using this run"
            )
            for r in results
            if r["exit_code"] != 0
        },
    }
    (out / "record.json").write_text(
        clean(json.dumps(record, indent=2, ensure_ascii=False)), encoding="utf-8"
    )
    print(
        f"Recorded {RUN_ID} for {record['code_revision'][:12]} in {out.relative_to(root)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
