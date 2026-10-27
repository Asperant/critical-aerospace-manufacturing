"""Static checks of the platform Compose definition (WP-PLAT-001; no Docker needed).

They hold the runtime definition to the rules of 02 between integration runs:
the canonical profile set, the `infra` layer in every profile, exact image
pins, localhost-only ports, a health check and a memory limit for every
service, a bounded memory budget, and credentials only from the environment.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

HERE = Path(__file__).resolve().parents[1]
COMPOSE: dict[str, Any] = yaml.safe_load((HERE / "compose.yaml").read_text("utf-8"))
SERVICES: dict[str, Any] = COMPOSE["services"]

# 02 "Local Development Environment": minimum logical profiles.
CANONICAL_PROFILES = {
    "infra",
    "core",
    "vision",
    "ai",
    "planning",
    "platform",
    "full",
    "e2e",
}
# 02: PostgreSQL, event backbone, S3-compatible object storage, cache, identity provider.
INFRA = {"postgres", "nats", "seaweedfs", "valkey", "keycloak"}
INFRA_MEMORY_BUDGET_MIB = 3 * 1024


def mebibytes(value: str) -> int:
    match = re.fullmatch(r"(\d+)([mg])", str(value).lower())
    assert match, f"memory limit {value!r} must be like 512m or 1g"
    number, unit = int(match[1]), match[2]
    return number * 1024 if unit == "g" else number


def test_infra_layer_is_complete() -> None:
    assert set(SERVICES) >= INFRA


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_profiles_are_canonical(name: str) -> None:
    profiles = set(SERVICES[name].get("profiles", []))
    assert profiles, f"{name}: every service belongs to explicit profiles"
    assert profiles <= CANONICAL_PROFILES, f"{name}: {profiles - CANONICAL_PROFILES}"
    if name in INFRA:
        assert profiles == CANONICAL_PROFILES, f"{name}: infra is in every profile"


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_images_are_pinned_to_exact_releases(name: str) -> None:
    image = SERVICES[name]["image"]
    repository, _, tag = image.rpartition(":")
    assert repository, image
    assert re.fullmatch(
        r"v?\d+\.\d+(\.\d+)?(-[a-z0-9.]+)?", tag
    ), f"{image}: pin an exact release"
    assert "latest" not in tag


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_ports_bind_localhost_only(name: str) -> None:
    for port in SERVICES[name].get("ports", []):
        assert str(port).startswith("127.0.0.1:"), f"{name}: {port}"


def one_shot(service: dict[str, Any]) -> bool:
    """A setup job (WP-PLAT-003): runs to completion, never restarted."""
    return service.get("restart") == "no"


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_every_service_has_health_check_and_memory_limit(name: str) -> None:
    service = SERVICES[name]
    mebibytes(service["deploy"]["resources"]["limits"]["memory"])
    if not one_shot(service):
        assert service.get("healthcheck", {}).get("test"), f"{name}: health check"
        return
    # A one-shot job has no running state to probe: it publishes no port and
    # starts only once everything it needs is healthy or has completed.
    assert not service.get("ports"), f"{name}: a setup job publishes no port"
    needs = service.get("depends_on")
    assert isinstance(needs, dict) and needs, f"{name}: a setup job declares its needs"
    for dependency, condition in needs.items():
        assert condition.get("condition") in {
            "service_healthy",
            "service_completed_successfully",
        }, f"{name} -> {dependency}: wait for health or completion"


def test_infra_memory_budget() -> None:
    total = sum(
        mebibytes(SERVICES[n]["deploy"]["resources"]["limits"]["memory"]) for n in INFRA
    )
    assert total <= INFRA_MEMORY_BUDGET_MIB, f"infra limits sum to {total} MiB"


def test_stack_script_knows_the_canonical_profiles() -> None:
    script = (HERE / "stack.sh").read_text("utf-8")
    match = re.search(r"PROFILES_ALL=\(([^)]*)\)", script)
    assert match and set(match[1].split()) == CANONICAL_PROFILES
    assert "--wait" in script and "add-mask" in script and "smoke)" in script


# --------------------------------------------- mfgctl registry (DEP-003) ---

REPO = HERE.parents[1]
REGISTRY_PATH = REPO / "infra/mfgctl/capabilities.json"


def test_registry_conforms_to_the_mfgctl_contract() -> None:
    import json

    import jsonschema

    schema = json.loads(
        (REPO / "tools/mfgctl/schemas/capabilities.schema.json").read_text("utf-8")
    )
    jsonschema.validate(json.loads(REGISTRY_PATH.read_text("utf-8")), schema)


def test_registry_matches_the_composition() -> None:
    from mfgctl import registry

    loaded = registry.load(REPO, {})
    assert loaded.compose_files == ("infra/compose/compose.yaml",)
    assert {p.name for p in loaded.profiles} == CANONICAL_PROFILES
    for capability in loaded.capabilities:
        assert capability.profile in CANONICAL_PROFILES
        assert (REPO / capability.smoke[0]).is_file(), capability.smoke
    for scenario in loaded.scenarios:
        assert scenario.profile in CANONICAL_PROFILES


def test_credentials_never_in_the_definition() -> None:
    text = (HERE / "compose.yaml").read_text("utf-8")
    assert not re.search(r"(PASSWORD|SECRET|TOKEN)\s*:", text)
    for name in (
        "postgres",
        "keycloak",
        "temporal-schema",
        "temporal",
        "qdrant",
        "mlflow-init",
        "mlflow",
    ):
        (entry,) = SERVICES[name]["env_file"]
        assert entry["path"].startswith("${CAP_PLATFORM_STATE_DIR:-${HOME}/"), entry


EPHEMERAL_PORT_FLOOR = 32768  # Linux default ip_local_port_range starts here


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_host_ports_are_outside_the_ephemeral_range(name: str) -> None:
    for port in SERVICES[name].get("ports", []):
        match = re.search(r"\$\{[A-Z0-9_]+:-(\d+)\}:\d+$", str(port))
        assert match, f"{name}: host port must be ${{VAR:-default}}: {port}"
        assert int(match[1]) < EPHEMERAL_PORT_FLOOR, f"{name}: {port}"


def test_stack_script_defaults_match_the_definition() -> None:
    script = (HERE / "stack.sh").read_text("utf-8")
    defaults = dict(
        re.findall(r'(CAP_[A-Z_]+_PORT)="\$\{CAP_[A-Z_]+_PORT:-(\d+)\}"', script)
    )
    compose = (HERE / "compose.yaml").read_text("utf-8")
    declared = dict(re.findall(r"\$\{(CAP_[A-Z_]+_PORT):-(\d+)\}", compose))
    assert defaults == declared and declared


def test_mlflow_server_never_holds_the_s3_admin_identity() -> None:
    """WP-PLAT-003: only the one-shot init job creates the bucket; the server is bucket-scoped."""
    script = (HERE / "stack.sh").read_text("utf-8")
    (server_env,) = re.findall(
        r"printf 'MLFLOW_BACKEND_STORE_URI=[^\n]*\n[^\n]*mlflow\.env\"", script
    )
    assert "S3_ADMIN" not in server_env and "S3_MLFLOW_KEY" in server_env
    assert SERVICES["mlflow"]["env_file"][0]["path"].endswith("/mlflow.env")
    assert SERVICES["mlflow-init"]["env_file"][0]["path"].endswith("/mlflow-init.env")


# ------------------------------- WP-PLAT-003: dependency-ordered startup ---

# 02 Sequence I (host reboot / platform recovery): identity -> data stores (with the
# workflow-engine and artifact stores) -> event backbone -> application services.
STARTUP_LAYERS = {
    "keycloak": 0,
    "postgres": 1,
    "seaweedfs": 1,
    "valkey": 1,
    "qdrant": 1,
    "temporal-schema": 1,
    "temporal": 1,
    "temporal-namespace": 1,
    "mlflow-init": 1,
    "mlflow": 1,
    "nats": 2,
}


def layer_violations(services: dict[str, Any], layers: dict[str, int]) -> list[str]:
    """Waits that are not readiness, or that point to a later Sequence I layer."""
    found = []
    for name, service in services.items():
        for dependency, condition in (service.get("depends_on") or {}).items():
            if condition.get("condition") not in {
                "service_healthy",
                "service_completed_successfully",
            }:
                found.append(
                    f"{name} -> {dependency}: bare start order is not readiness"
                )
            elif layers[dependency] > layers[name]:
                found.append(
                    f"{name} (layer {layers[name]}) waits for {dependency} "
                    f"(layer {layers[dependency]}): against 02 Sequence I"
                )
    return found


def startup_cycle(services: dict[str, Any]) -> list[str] | None:
    """The first wait cycle found, as a path, or None."""
    state: dict[str, int] = {}

    def visit(name: str, path: list[str]) -> list[str] | None:
        if state.get(name) == 2:
            return None
        if state.get(name) == 1:
            return path + [name]
        state[name] = 1
        for dependency in services[name].get("depends_on") or {}:
            if cycle := visit(dependency, path + [name]):
                return cycle
        state[name] = 2
        return None

    for name in services:
        if cycle := visit(name, []):
            return cycle
    return None


def test_every_service_has_a_startup_layer() -> None:
    assert set(STARTUP_LAYERS) == set(SERVICES)


def test_dependencies_follow_sequence_i() -> None:
    """A service waits only for the health or completion of its own or an earlier layer."""
    assert layer_violations(SERVICES, STARTUP_LAYERS) == []


def test_startup_graph_has_no_cycle() -> None:
    """No health check can wait, directly or transitively, on a service that waits on it."""
    assert startup_cycle(SERVICES) is None


def test_ordering_checks_reject_broken_graphs() -> None:
    healthy = {"condition": "service_healthy"}
    later = {"keycloak": {"depends_on": {"nats": healthy}}, "nats": {}}
    assert layer_violations(later, {"keycloak": 0, "nats": 2})
    bare = {
        "temporal": {"depends_on": {"postgres": {"condition": "service_started"}}},
        "postgres": {},
    }
    assert layer_violations(bare, {"temporal": 1, "postgres": 1})
    loop = {"a": {"depends_on": {"b": healthy}}, "b": {"depends_on": {"a": healthy}}}
    assert startup_cycle(loop) == ["a", "b", "a"]
