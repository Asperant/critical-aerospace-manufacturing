"""``mfgctl doctor`` — diagnose the developer environment (01 Item 74 §16–19).

Rules from the specification:
- diagnostic by default: no check mutates repository, runtime or user state
  (DX-INV-06); every probe below is a read-only command or system call;
- actionable: every WARN/FAIL carries a concrete remediation (§17);
- machine-readable output with ``--json`` (§18).

Status semantics: FAIL means the documented workflow will not work and makes
the command exit 1; WARN means it works but differs from what CI pins.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path

from mfgctl import probe, venv
from mfgctl.probe import Result, Runner

SCHEMA = "mfgctl.doctor/v1"
REQUIRED_PYTHON = (3, 11)
GIB = 1024**3
DISK_FAIL_GIB = 5
DISK_WARN_GIB = 20
# Host ports the repository's own tooling binds; keep in sync with
# ci/scripts/integration_services.sh (Compose profiles add theirs in WP-PLAT-001).
KNOWN_PORTS = {
    55432: "integration PostgreSQL (ci/scripts/integration_services.sh)",
    54222: "integration NATS client (ci/scripts/integration_services.sh)",
    58222: "integration NATS monitoring (ci/scripts/integration_services.sh)",
}
UV_PIN_SOURCE = ".github/workflows/ci.yml"
LOCK_PROJECT = "ci"
QUICK_TIMEOUT = 15.0
LOCK_TIMEOUT = 120.0


class Status(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str
    remediation: str | None = None


@dataclass
class Environment:
    """Everything doctor reads from the machine; replaceable in tests."""

    root: Path
    run: Runner = probe.run_command
    python_version: tuple[int, int, int] = (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    disk_free_bytes: Callable[[Path], int] = probe.disk_free_bytes
    port_in_use: Callable[[int], bool] = probe.port_in_use
    environ: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    current_user: str = field(default_factory=getpass.getuser)


@dataclass
class Report:
    root: Path
    checks: list[Check] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def status(self) -> Status:
        statuses = {check.status for check in self.checks}
        if Status.FAIL in statuses:
            return Status.FAIL
        return Status.WARN if Status.WARN in statuses else Status.OK

    @property
    def exit_code(self) -> int:
        return 1 if self.status is Status.FAIL else 0


def default_environment(root: Path) -> Environment:
    return Environment(root=root)


def pinned_uv_version(root: Path) -> str | None:
    """The uv version CI installs; the workflow is the single source of truth."""
    try:
        text = (root / UV_PIN_SOURCE).read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r'^\s*UV_VERSION:\s*"?([0-9][0-9.]*)"?\s*$', text, re.MULTILINE)
    return match.group(1) if match else None


def check_git(env: Environment) -> Check:
    version = env.run(["git", "--version"], QUICK_TIMEOUT)
    if not version.ok:
        return Check(
            "git",
            Status.FAIL,
            version.first_error_line(),
            "Install Git (sudo apt install git) and open a new shell.",
        )
    tree = env.run(
        ["git", "-C", str(env.root), "rev-parse", "--is-inside-work-tree"],
        QUICK_TIMEOUT,
    )
    if tree.ok and tree.stdout == "true":
        return Check("git", Status.OK, f"{version.stdout}; work tree readable")
    if "dubious ownership" in tree.stderr:
        return Check(
            "git",
            Status.FAIL,
            "Git refuses this checkout: it is owned by another user",
            f"git config --global --add safe.directory {env.root}",
        )
    return Check(
        "git",
        Status.FAIL,
        tree.first_error_line(),
        "Run mfgctl inside a Git checkout of the repository.",
    )


def check_python(env: Environment) -> Check:
    found = ".".join(str(part) for part in env.python_version)
    if env.python_version[:2] == REQUIRED_PYTHON:
        return Check("python", Status.OK, f"Python {found}")
    wanted = ".".join(str(part) for part in REQUIRED_PYTHON)
    return Check(
        "python",
        Status.FAIL,
        f"Python {found} is running mfgctl; the repository targets {wanted}",
        "Run through the locked toolchain: uv run --project ci --locked mfgctl doctor",
    )


def _uv_version(result: Result) -> str | None:
    match = re.match(r"uv ([0-9][0-9.]*)", result.stdout)
    return match.group(1) if match else None


def check_uv(env: Environment) -> Check:
    pinned = pinned_uv_version(env.root)
    result = env.run(["uv", "--version"], QUICK_TIMEOUT)
    install = f'pipx install "uv=={pinned}" --force' if pinned else "pipx install uv"
    if not result.ok:
        return Check("uv", Status.FAIL, result.first_error_line(), install)
    found = _uv_version(result)
    if pinned is None:
        return Check(
            "uv",
            Status.WARN,
            f"uv {found}; no UV_VERSION pin found in {UV_PIN_SOURCE}",
            f"Restore the UV_VERSION pin in {UV_PIN_SOURCE}.",
        )
    if found != pinned:
        return Check("uv", Status.WARN, f"uv {found}; CI pins {pinned}", install)
    return Check("uv", Status.OK, f"uv {found} (matches CI pin)")


def check_venv(env: Environment) -> Check:
    path = venv.environment_path(env.root, env.environ)
    if not path.exists():
        return Check(
            "venv",
            Status.WARN,
            f"{path} does not exist yet",
            "Create the locked toolchain environment: mfgctl bootstrap",
        )
    problem = venv.problem(path)
    if problem is not None:
        return Check(
            "venv",
            Status.FAIL,
            problem,
            venv.remediation(path, env.current_user),
        )
    return Check("venv", Status.OK, f"{path} usable")


def check_docker(env: Environment) -> Check:
    result = env.run(
        ["docker", "version", "--format", "{{.Server.Version}}"], QUICK_TIMEOUT
    )
    if result.returncode == probe.NOT_FOUND:
        return Check(
            "docker",
            Status.FAIL,
            "Docker CLI not found",
            "Install Docker Engine: https://docs.docker.com/engine/install/",
        )
    if not result.ok:
        return Check(
            "docker",
            Status.FAIL,
            f"Docker daemon unreachable: {result.first_error_line()}",
            "Start Docker (sudo systemctl start docker) and make sure your user "
            "is in the docker group (sudo usermod -aG docker $USER, then log in again).",
        )
    return Check("docker", Status.OK, f"Docker Engine {result.stdout}")


def check_compose(env: Environment) -> Check:
    result = env.run(["docker", "compose", "version", "--short"], QUICK_TIMEOUT)
    if not result.ok:
        return Check(
            "compose",
            Status.FAIL,
            f"Docker Compose v2 unavailable: {result.first_error_line()}",
            "Install the Compose plugin (sudo apt install docker-compose-plugin).",
        )
    return Check("compose", Status.OK, f"Docker Compose {result.stdout}")


def check_disk(env: Environment) -> Check:
    free_gib = env.disk_free_bytes(env.root) / GIB
    detail = f"{free_gib:.1f} GiB free at {env.root}"
    if free_gib < DISK_FAIL_GIB:
        return Check(
            "disk",
            Status.FAIL,
            detail,
            "Free space: docker system df, then remove unused images "
            "(docker image prune) and old build outputs.",
        )
    if free_gib < DISK_WARN_GIB:
        return Check(
            "disk",
            Status.WARN,
            detail,
            f"Images and volumes need more room; keep at least {DISK_WARN_GIB} GiB free.",
        )
    return Check("disk", Status.OK, detail)


def check_ports(env: Environment) -> Check:
    busy = [port for port in sorted(KNOWN_PORTS) if env.port_in_use(port)]
    if not busy:
        return Check("ports", Status.OK, f"{len(KNOWN_PORTS)} known ports free")
    listing = ", ".join(f"{port} ({KNOWN_PORTS[port]})" for port in busy)
    return Check(
        "ports",
        Status.WARN,
        f"in use: {listing}",
        "If the integration services are already running this is expected "
        "(ci/scripts/integration_services.sh down stops them); otherwise stop the "
        "process (ss -ltnp) or override CI_PG_PORT / CI_NATS_PORT / CI_NATS_MON_PORT.",
    )


def check_lock(env: Environment, uv_available: bool) -> Check:
    if not uv_available:
        return Check(
            "lock",
            Status.WARN,
            "skipped: uv is not available",
            "Fix the uv check first.",
        )
    project = env.root / LOCK_PROJECT
    result = env.run(
        ["uv", "lock", "--locked", "--project", str(project)], LOCK_TIMEOUT
    )
    if result.ok:
        return Check("lock", Status.OK, "ci/uv.lock matches ci/pyproject.toml")
    if result.returncode == probe.TIMED_OUT:
        return Check(
            "lock",
            Status.WARN,
            result.first_error_line(),
            "Check network access to the package index and run mfgctl doctor again.",
        )
    return Check(
        "lock",
        Status.FAIL,
        f"ci/uv.lock is not consistent with ci/pyproject.toml: {result.first_error_line()}",
        "uv lock --project ci, review the diff and commit ci/uv.lock.",
    )


def run_doctor(env: Environment, clock: Callable[[], float] = time.monotonic) -> Report:
    started = clock()
    report = Report(root=env.root)
    report.checks.append(check_git(env))
    report.checks.append(check_python(env))
    uv = check_uv(env)
    report.checks.append(uv)
    report.checks.append(check_venv(env))
    report.checks.append(check_docker(env))
    report.checks.append(check_compose(env))
    report.checks.append(check_disk(env))
    report.checks.append(check_ports(env))
    report.checks.append(check_lock(env, uv_available=uv.status is not Status.FAIL))
    report.duration_ms = round((clock() - started) * 1000)
    return report


def render_json(report: Report) -> str:
    payload = {
        "schema": SCHEMA,
        "status": report.status.value,
        "duration_ms": report.duration_ms,
        "repo_root": str(report.root),
        "checks": [
            {**asdict(check), "status": check.status.value} for check in report.checks
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def render_text(report: Report) -> str:
    lines = [f"mfgctl doctor — {report.root}"]
    for check in report.checks:
        lines.append(f"  {check.status.value:<5} {check.name:<8} {check.detail}")
        if check.remediation and check.status is not Status.OK:
            lines.append(f"  {'':<5} {'':<8} → {check.remediation}")
    counts = {status: 0 for status in Status}
    for check in report.checks:
        counts[check.status] += 1
    lines.append(
        f"Result: {report.status.value} ({counts[Status.FAIL]} fail, "
        f"{counts[Status.WARN]} warn) in {report.duration_ms / 1000:.1f} s"
    )
    return "\n".join(lines)
