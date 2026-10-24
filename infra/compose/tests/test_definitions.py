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


@pytest.mark.parametrize("name", sorted(SERVICES))
def test_every_service_has_health_check_and_memory_limit(name: str) -> None:
    service = SERVICES[name]
    assert service.get("healthcheck", {}).get("test"), f"{name}: health check"
    mebibytes(service["deploy"]["resources"]["limits"]["memory"])


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
    for name in ("postgres", "keycloak"):
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
