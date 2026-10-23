from __future__ import annotations

import json
import socket
from pathlib import Path

from conftest import FakeRunner, make_env, make_repo
from mfgctl import probe
from mfgctl.doctor import (
    KNOWN_PORTS,
    SCHEMA,
    Report,
    Status,
    pinned_uv_version,
    render_json,
    render_text,
    run_doctor,
)
from mfgctl.probe import Result

DOCKER = ("docker", "version", "--format", "{{.Server.Version}}")
COMPOSE = ("docker", "compose", "version", "--short")
UV = ("uv", "--version")


def by_name(report: Report) -> dict[str, Status]:
    return {check.name: check.status for check in report.checks}


def check(report: Report, name: str):
    return next(c for c in report.checks if c.name == name)


def test_healthy_machine_passes_every_check(repo: Path) -> None:
    report = run_doctor(make_env(repo))
    assert set(by_name(report).values()) == {Status.OK}
    assert report.exit_code == 0
    assert [c.name for c in report.checks] == [
        "git",
        "python",
        "uv",
        "venv",
        "docker",
        "compose",
        "disk",
        "ports",
        "lock",
    ]


def test_missing_docker_fails_with_install_hint(repo: Path) -> None:
    report = run_doctor(make_env(repo, {DOCKER: Result(127), COMPOSE: Result(127)}))
    docker = check(report, "docker")
    assert docker.status is Status.FAIL
    assert docker.remediation and "Install Docker" in docker.remediation
    assert report.exit_code == 1


def test_unreachable_daemon_is_reported_separately_from_missing_cli(repo: Path) -> None:
    denied = Result(1, stderr="permission denied while trying to connect to the socket")
    docker = check(run_doctor(make_env(repo, {DOCKER: denied})), "docker")
    assert docker.status is Status.FAIL
    assert "permission denied" in docker.detail
    assert docker.remediation and "docker group" in docker.remediation


def test_wrong_python_fails(repo: Path) -> None:
    python = check(run_doctor(make_env(repo, python=(3, 12, 1))), "python")
    assert python.status is Status.FAIL
    assert "3.11" in python.detail


def test_uv_version_drift_is_a_warning_not_a_failure(repo: Path) -> None:
    report = run_doctor(make_env(repo, {UV: Result(0, "uv 0.11.32 (x 2026-01-01)")}))
    uv = check(report, "uv")
    assert uv.status is Status.WARN
    assert uv.remediation == 'pipx install "uv==0.12.13" --force'
    assert report.exit_code == 0


def test_missing_uv_fails_and_skips_lock_check(repo: Path) -> None:
    env = make_env(repo, {UV: Result(127, stderr="uv: command not found")})
    report = run_doctor(env)
    assert by_name(report)["uv"] is Status.FAIL
    assert by_name(report)["lock"] is Status.WARN
    assert isinstance(env.run, FakeRunner)
    assert not any(call[:2] == ("uv", "lock") for call in env.run.calls)


def test_stale_lock_fails_and_timeout_warns(repo: Path) -> None:
    lock = ("uv", "lock", "--locked", "--project", str(repo / "ci"))
    stale = Result(2, stderr="The lockfile needs to be updated")
    assert by_name(run_doctor(make_env(repo, {lock: stale})))["lock"] is Status.FAIL
    timeout = Result(probe.TIMED_OUT, stderr="uv: timed out after 120 s")
    assert by_name(run_doctor(make_env(repo, {lock: timeout})))["lock"] is Status.WARN


def test_dubious_ownership_gets_safe_directory_remedy(repo: Path) -> None:
    rev_parse = ("git", "-C", str(repo), "rev-parse", "--is-inside-work-tree")
    refused = Result(128, stderr="fatal: detected dubious ownership in repository")
    git = check(run_doctor(make_env(repo, {rev_parse: refused})), "git")
    assert git.status is Status.FAIL
    assert git.remediation == f"git config --global --add safe.directory {repo}"


def test_disk_thresholds(repo: Path) -> None:
    assert by_name(run_doctor(make_env(repo, free_gib=2)))["disk"] is Status.FAIL
    assert by_name(run_doctor(make_env(repo, free_gib=10)))["disk"] is Status.WARN
    assert by_name(run_doctor(make_env(repo, free_gib=50)))["disk"] is Status.OK


def test_busy_known_port_warns_and_names_it(repo: Path) -> None:
    ports = check(run_doctor(make_env(repo, busy_ports=frozenset({55432}))), "ports")
    assert ports.status is Status.WARN
    assert "55432" in ports.detail and "PostgreSQL" in ports.detail


def test_real_port_probe_detects_listener() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        assert probe.port_in_use(port)
    assert not probe.port_in_use(port)


def test_uv_pin_is_read_from_ci_workflow(repo: Path, tmp_path: Path) -> None:
    assert pinned_uv_version(repo) == "0.12.13"
    unpinned = make_repo(tmp_path / "unpinned", uv_pin=None)
    assert pinned_uv_version(unpinned) is None
    assert by_name(run_doctor(make_env(unpinned)))["uv"] is Status.WARN


def test_doctor_does_not_modify_the_repository(repo: Path) -> None:
    def snapshot() -> dict[str, bytes]:
        return {str(p): p.read_bytes() for p in sorted(repo.rglob("*")) if p.is_file()}

    before = snapshot()
    run_doctor(make_env(repo, busy_ports=frozenset(KNOWN_PORTS)))
    assert snapshot() == before


def test_json_output_follows_schema(repo: Path) -> None:
    report = run_doctor(
        make_env(repo, {DOCKER: Result(127)}), clock=iter([1.0, 1.25]).__next__
    )
    payload = json.loads(render_json(report))
    assert payload["schema"] == SCHEMA
    assert payload["status"] == "FAIL"
    assert payload["duration_ms"] == 250
    assert {c["name"] for c in payload["checks"]} >= {"git", "docker", "lock"}
    assert all(
        set(c) == {"name", "status", "detail", "remediation"} for c in payload["checks"]
    )


def test_text_output_shows_remediation_only_for_problems(repo: Path) -> None:
    text = render_text(run_doctor(make_env(repo, {DOCKER: Result(127)})))
    assert "FAIL  docker" in text
    assert "→ Install Docker Engine" in text
    assert text.count("→") == 1  # only docker failed; healthy checks stay quiet
    assert text.splitlines()[-1].startswith("Result: FAIL")


def test_runner_turns_missing_binary_and_timeout_into_results() -> None:
    missing = probe.run_command(["mfgctl-test-no-such-binary"], 5)
    assert missing.returncode == probe.NOT_FOUND
    slow = probe.run_command(["sleep", "5"], 0.2)
    assert slow.returncode == probe.TIMED_OUT
