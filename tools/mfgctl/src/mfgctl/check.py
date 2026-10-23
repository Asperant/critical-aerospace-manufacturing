"""``mfgctl check`` — run the CI checks locally (01 Item 74 §34, §128–130, DX-INV-52).

The commands are read from ``.github/workflows/ci.yml`` instead of being copied
here, so local checks cannot drift from CI: every ``uv run ...`` step of the
selected jobs is executed with the job's environment, exactly as CI runs it.
A multi-line step runs line by line; each of its lines must be a ``uv run``.

Tiers:
- ``fast`` (default): job ``static`` — Ruff and Pyright ratchet (NFR-DX-002 ≤ 90 s);
- ``pr``: jobs ``static``, ``unit`` and ``contract`` — the T1 jobs that need no
  services. ``t1-integration`` needs Docker services and is reported as NOT RUN
  with the command to run it, never counted as passed.

If ci.yml stops defining a job or its ``uv run`` steps, check fails with exit 2
rather than silently running less than CI does.
"""

from __future__ import annotations

import shlex
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mfgctl.probe import NOT_FOUND, TIMED_OUT, StreamRunner

WORKFLOW = ".github/workflows/ci.yml"
TIERS: dict[str, tuple[str, ...]] = {
    "fast": ("static",),
    "pr": ("static", "unit", "contract"),
}
NOT_RUN: dict[str, tuple[tuple[str, str], ...]] = {
    "fast": (),
    "pr": (
        (
            "t1-integration",
            "needs Docker services: ci/scripts/integration_services.sh up, then "
            "the integration step of .github/workflows/ci.yml",
        ),
    ),
}
STEP_TIMEOUT = 900.0


class WorkflowError(Exception):
    """ci.yml cannot provide the commands for the requested tier."""


@dataclass(frozen=True)
class Command:
    job: str
    name: str
    argv: tuple[str, ...]
    env: Mapping[str, str]


@dataclass(frozen=True)
class StepResult:
    command: Command
    returncode: int
    duration_ms: int

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass
class CheckReport:
    tier: str
    results: list[StepResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)

    @property
    def exit_code(self) -> int:
        return 0 if self.passed else 1


def _as_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowError(f"{WORKFLOW}: {where} is not a mapping")
    return value


def load_commands(root: Path, tier: str) -> list[Command]:
    if tier not in TIERS:
        raise WorkflowError(f"unknown tier {tier!r}; choose one of {', '.join(TIERS)}")
    try:
        document = yaml.safe_load((root / WORKFLOW).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise WorkflowError(f"cannot read {WORKFLOW}: {exc}") from exc
    jobs = _as_mapping(_as_mapping(document, "document").get("jobs"), "jobs")
    commands: list[Command] = []
    for key in TIERS[tier]:
        if key not in jobs:
            raise WorkflowError(f"{WORKFLOW} no longer defines job {key!r}")
        job = _as_mapping(jobs[key], f"job {key}")
        label = str(job.get("name", key))
        env = {
            str(k): str(v) for k, v in _as_mapping(job.get("env", {}), "env").items()
        }
        found = 0
        for step in job.get("steps") or []:
            run = step.get("run") if isinstance(step, dict) else None
            if not isinstance(run, str) or not run.strip().startswith("uv run "):
                continue  # checkout, tool installation and sync are CI plumbing
            name = str(step.get("name", run.strip()))
            lines = [line.strip() for line in run.splitlines() if line.strip()]
            if any(not line.startswith("uv run ") for line in lines):
                raise WorkflowError(
                    f"{label} · {name}: every line of a multi-line step must be a "
                    "uv run command"
                )
            for index, line in enumerate(lines, start=1):
                suffix = f" ({index}/{len(lines)})" if len(lines) > 1 else ""
                commands.append(
                    Command(label, name + suffix, tuple(shlex.split(line)), env)
                )
            found += 1
        if not found:
            raise WorkflowError(f"{WORKFLOW} job {key!r} has no uv run steps")
    return commands


def run_check(
    root: Path,
    commands: list[Command],
    tier: str,
    runner: StreamRunner,
    announce: Callable[[str], None],
    clock: Callable[[], float] = time.monotonic,
) -> CheckReport:
    report = CheckReport(tier)
    for index, command in enumerate(commands, start=1):
        announce(f"[{index}/{len(commands)}] {command.job} · {command.name}")
        started = clock()
        code = runner(command.argv, command.env, root, STEP_TIMEOUT)
        report.results.append(
            StepResult(command, code, round((clock() - started) * 1000))
        )
    return report


def _reason(code: int) -> str:
    if code == NOT_FOUND:
        return "command not found"
    if code == TIMED_OUT:
        return f"timed out after {STEP_TIMEOUT:.0f} s"
    return f"exit {code}"


def render_summary(report: CheckReport) -> str:
    lines = [f"mfgctl check --{report.tier} summary"]
    for result in report.results:
        state = "PASS" if result.passed else "FAIL"
        extra = "" if result.passed else f" ({_reason(result.returncode)})"
        lines.append(
            f"  {state:<7} {result.command.job:<15} {result.command.name}"
            f" [{result.duration_ms / 1000:.1f} s]{extra}"
        )
    for job, why in NOT_RUN[report.tier]:
        lines.append(f"  NOT RUN {job:<15} {why}")
    total = sum(result.duration_ms for result in report.results) / 1000
    verdict = "PASS" if report.passed else "FAIL"
    lines.append(f"Result: {verdict} in {total:.1f} s")
    return "\n".join(lines)
