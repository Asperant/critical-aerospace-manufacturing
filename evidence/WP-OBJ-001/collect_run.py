"""Produce RUN-OBJ-001-DEV-001: the WP-OBJ-001 run on the shared host.

Run from the repository root on a committed, clean work tree, with Docker:

    uv run --project ci --locked python evidence/WP-OBJ-001/collect_run.py

Every step is a real invocation against the infra profile (boundary mode REAL):
start the profile with its S3 identities, create the artifact buckets with the
admin identity, run the REAL store, registry and access tests (they create and
drop their own database and roles), probe anonymous access, run the consistency
command against an empty registry configuration (expects a configuration error,
proving it never guesses a DSN), and stop the profile. Exit codes and output are
recorded as observed; credentials, host paths and the host name are replaced
with placeholders.
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
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

RUN_ID = "RUN-OBJ-001-DEV-001"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
RESULT = re.compile(r"^(\S+::\S+) (PASSED|FAILED|ERROR|SKIPPED)", re.M)


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
    out = root / "evidence" / "WP-OBJ-001" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    stack = "infra/compose/stack.sh"
    uv = ["uv", "run", "--project", "ci", "--locked"]
    state = Path(
        os.environ.get(
            "CAP_PLATFORM_STATE_DIR", Path.home() / ".local/state/cap-platform"
        )
    )
    env = {
        **os.environ,
        "PYTHONPATH": "ci:ci/scripts",
        "CAP_ARTIFACT_TEST_DISPOSABLE": "1",
    }
    secrets: list[str] = []

    def refresh_secrets() -> None:
        credentials = state / "credentials.env"
        if credentials.is_file():
            for line in credentials.read_text("utf-8").splitlines():
                value = line.partition("=")[2]
                if value and value not in secrets:
                    secrets.append(value)

    def clean(text: str) -> str:
        text = ANSI.sub("", text)
        for value in secrets:
            text = text.replace(value, "<redacted>")
        for old, new in [
            (str(root), "<repo>"),
            (str(Path.home()), "<home>"),
            (socket.gethostname(), "<host>"),
        ]:
            text = text.replace(old, new)
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n"

    results: list[dict[str, object]] = []

    def step(
        name: str,
        argv: list[str],
        filename: str,
        expected: int = 0,
        extra: dict[str, str] | None = None,
    ) -> str:
        started = time.monotonic()
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            env={**env, **(extra or {})},
            check=False,
        )
        refresh_secrets()
        body = clean(done.stdout + done.stderr)
        (out / filename).write_text(body, encoding="utf-8")
        results.append(
            {
                "step": name,
                "exit_code": done.returncode,
                "expected_exit_code": expected,
                "wall_s": round(time.monotonic() - started, 1),
                "output": filename,
            }
        )
        print(f"{name:<14} exit={done.returncode} (expected {expected}) -> {filename}")
        return body

    step("up", [stack, "up", "infra"], "up.log.txt")
    stack_env = dict(
        line.split("=", 1)
        for line in subprocess.run(
            [stack, "env"], capture_output=True, text=True, check=True
        ).stdout.splitlines()
        if "=" in line
    )
    env.update(stack_env)
    refresh_secrets()
    step("ensure-buckets", [*uv, "python", "-m", "cap_artifacts", "ensure-buckets"], "ensure-buckets.log.txt",
         extra={"PYTHONPATH": "packages/artifacts/src"})  # fmt: skip
    tests = step(
        "real-tests",
        [*uv, "python", "-m", "pytest", "-c", "packages/artifacts/pyproject.toml", "packages/artifacts/tests",
         "-m", "integration", "-v", "-p", "pytest_quarantine"],
        "real-tests.log.txt",
    )  # fmt: skip
    anonymous = 0
    try:
        with urllib.request.urlopen(
            stack_env["CAP_S3_ENDPOINT"] + "/cap-artifacts-rc-b/"
        ) as response:
            anonymous = response.status
    except urllib.error.HTTPError as exc:
        anonymous = exc.code
    step("consistency-unconfigured", [*uv, "python", "-m", "cap_artifacts", "consistency"],
         "consistency-unconfigured.log.txt", expected=2,
         extra={"PYTHONPATH": "packages/artifacts/src", "CAP_ARTIFACT_REGISTRY_DSN": ""})  # fmt: skip
    step("down", [stack, "down"], "down.log.txt")

    per_test = {
        name.split("::", 1)[1]: status for name, status in RESULT.findall(tests)
    }
    files = sorted(
        {name.split("::", 1)[0].rsplit("/", 1)[-1] for name, _ in RESULT.findall(tests)}
    )
    unexpected = {
        str(r["step"]): f"exit {r['exit_code']}, expected {r['expected_exit_code']}"
        for r in results
        if r["exit_code"] != r["expected_exit_code"]
    }
    record = {
        "run_id": RUN_ID,
        "work_package": "WP-OBJ-001",
        "kind": "DEV run on the shared host; infra profile with S3 identities (not the Integration host)",
        "boundary_mode": "REAL",
        "test_ids": ["TEST-OBJ-001-003", "TEST-OBJ-001-005", "TEST-OBJ-001-007"],
        "code_revision": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": {
            "machine": platform.machine(),
            "system": platform.system(),
            "cpus": os.cpu_count(),
        },
        "outcome": {
            "real_tests_passed": sum(1 for s in per_test.values() if s == "PASSED"),
            "real_tests_not_passed": sorted(
                n for n, s in per_test.items() if s != "PASSED"
            ),
            "test_files": files,
            "anonymous_bucket_listing_status": anonymous,
        },
        "per_test": per_test,
        "steps": results,
        "unexpected": unexpected,
    }
    (out / "record.json").write_text(
        clean(json.dumps(record, indent=2, ensure_ascii=False)), encoding="utf-8"
    )
    print(f"Recorded {RUN_ID} for {record['code_revision'][:12]}: {record['outcome']}")
    ok = (
        not unexpected
        and not record["outcome"]["real_tests_not_passed"]
        and anonymous == 403
    )  # type: ignore[index]
    return 0 if ok and per_test else 1


if __name__ == "__main__":
    raise SystemExit(main())
