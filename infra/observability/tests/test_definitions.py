"""Static checks of the observability runtime definitions (no Docker needed).

They keep the Compose file and Collector pipeline honest between integration
runs: pinned images, localhost-only ports, memory limits, credentials only from
the environment, and pipelines that reference what they define.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

HERE = Path(__file__).resolve().parents[1]
COMPOSE: dict[str, Any] = yaml.safe_load((HERE / "compose.yaml").read_text("utf-8"))
COLLECTOR: dict[str, Any] = yaml.safe_load(
    (HERE / "otel-collector.yaml").read_text("utf-8")
)
SERVICES: dict[str, Any] = COMPOSE["services"]


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_images_are_pinned_to_exact_releases(name: str) -> None:
    image = SERVICES[name]["image"]
    repository, _, tag = image.rpartition(":")
    assert repository and "/" in repository, image
    assert re.fullmatch(r"v?\d+\.\d+\.\d+", tag), f"{image}: pin an exact release"


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_ports_bind_localhost_only(name: str) -> None:
    for port in SERVICES[name].get("ports", []):
        assert str(port).startswith("127.0.0.1:"), f"{name}: {port}"


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_memory_limits_protect_the_single_host(name: str) -> None:
    limit = SERVICES[name]["deploy"]["resources"]["limits"]["memory"]
    assert re.fullmatch(r"\d+[mg]", limit), limit


def test_credentials_only_from_required_environment() -> None:
    o2 = SERVICES["openobserve"]["environment"]
    collector = SERVICES["otel-collector"]["environment"]
    for value in (
        o2["ZO_ROOT_USER_EMAIL"],
        o2["ZO_ROOT_USER_PASSWORD"],
        collector["O2_BASIC_AUTH"],
    ):
        assert re.fullmatch(r"\$\{[A-Z0-9_]+:\?.+\}", value), value
    headers = COLLECTOR["exporters"]["otlphttp/openobserve"]["headers"]
    assert headers["Authorization"] == "Basic ${env:O2_BASIC_AUTH}"


def test_telemetry_phone_home_is_disabled() -> None:
    assert SERVICES["openobserve"]["environment"]["ZO_TELEMETRY"] == "false"


@pytest.mark.parametrize("signal", ["logs", "metrics", "traces"])
def test_every_signal_has_a_complete_pipeline(signal: str) -> None:
    pipeline = COLLECTOR["service"]["pipelines"][signal]
    for kind in ("receivers", "processors", "exporters"):
        for name in pipeline[kind]:
            assert name in COLLECTOR[kind], f"{signal}: undefined {kind[:-1]} {name}"
    assert pipeline["processors"][0] == "memory_limiter", "memory_limiter goes first"
    assert pipeline["exporters"] == ["otlphttp/openobserve"]


def test_collector_ports_match_compose() -> None:
    published = {str(p).rsplit(":", 1)[1] for p in SERVICES["otel-collector"]["ports"]}
    protocols = COLLECTOR["receivers"]["otlp"]["protocols"]
    listening = {
        protocols["grpc"]["endpoint"].rsplit(":", 1)[1],
        protocols["http"]["endpoint"].rsplit(":", 1)[1],
        COLLECTOR["extensions"]["health_check"]["endpoint"].rsplit(":", 1)[1],
    }
    assert published == listening
    assert "health_check" in COLLECTOR["service"]["extensions"]


def test_exporter_targets_the_compose_service() -> None:
    endpoint = COLLECTOR["exporters"]["otlphttp/openobserve"]["endpoint"]
    assert endpoint == "http://openobserve:5080/api/default"
    assert "openobserve" in SERVICES


def test_stack_script_is_valid_bash_and_prints_secrets_only_in_env() -> None:
    script = HERE / "stack.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    text = script.read_text("utf-8")
    body = text.split('case "${1:-}" in', 1)[1]
    branches = re.split(r"\n  (\w+)\)\n", body)
    printing = {
        branches[i]
        for i in range(1, len(branches) - 1, 2)
        if "O2_ROOT_PASSWORD}" in branches[i + 1] and "echo" in branches[i + 1]
    }
    assert printing == {"env"}
