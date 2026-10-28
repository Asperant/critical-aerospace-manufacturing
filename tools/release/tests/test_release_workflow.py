"""TEST-CICD-002-004: the release workflow and the host hook keep the release path trusted.

The workflow is a security boundary (it publishes images and signs provenance), so
its properties are asserted from the file: publishing only from main, the narrowest
permissions, no secret beyond the job token, SBOM and provenance on, no mutable tag
as identity, and a stack.sh hook that pulls by digest and never builds.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from cap_release.deploy import render_override
from cap_release.registry import load_registry
from test_deploy import make_manifest

REPO = Path(__file__).resolve().parents[3]
TEXT = (REPO / ".github/workflows/release.yml").read_text("utf-8")
WORKFLOW: dict[Any, Any] = yaml.safe_load(TEXT)
BUILD: dict[str, Any] = WORKFLOW["jobs"]["build"]


def steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return job["steps"]


def step(job: dict[str, Any], uses_prefix: str) -> dict[str, Any]:
    found = [s for s in steps(job) if str(s.get("uses", "")).startswith(uses_prefix)]
    assert len(found) == 1, f"{uses_prefix}: {len(found)} steps"
    return found[0]


def test_pull_requests_only_dry_run_and_only_for_release_paths() -> None:
    triggers = WORKFLOW[True]  # YAML reads the key `on` as the boolean True
    assert triggers["push"] == {"branches": ["main"]}
    assert "release/**" in triggers["pull_request"]["paths"]
    assert (
        BUILD["env"]["PUBLISH"]
        == "${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}"
    )
    assert (
        step(BUILD, "docker/build-push-action")["with"]["push"]
        == "${{ env.PUBLISH == 'true' }}"
    )


def test_everything_that_pushes_or_signs_is_guarded_by_the_publish_flag() -> None:
    for name in ("docker/login-action", "actions/attest-build-provenance"):
        assert step(BUILD, name)["if"] == "env.PUBLISH == 'true'"
    manifest = WORKFLOW["jobs"]["manifest"]
    assert (
        manifest["if"]
        == "github.event_name != 'pull_request' && github.ref == 'refs/heads/main'"
    )


def test_permissions_are_read_only_by_default_and_widened_only_for_the_build_job() -> (
    None
):
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert BUILD["permissions"] == {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
        "attestations": "write",
    }
    for name in ("plan", "manifest"):
        assert (
            "permissions" not in WORKFLOW["jobs"][name]
        ), f"{name} must keep the read-only default"


def test_no_secret_but_the_job_token_is_used() -> None:
    import re

    secrets = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", TEXT))
    assert secrets == {"GITHUB_TOKEN"}, secrets


def test_every_checkout_drops_the_credentials() -> None:
    for job in WORKFLOW["jobs"].values():
        for item in steps(job):
            if str(item.get("uses", "")).startswith("actions/checkout"):
                assert item["with"]["persist-credentials"] is False


def test_sbom_provenance_and_attestation_are_produced_for_every_published_image() -> (
    None
):
    build = step(BUILD, "docker/build-push-action")["with"]
    assert build["sbom"] is True and build["provenance"] == "mode=max"
    attest = step(BUILD, "actions/attest-build-provenance")["with"]
    assert (
        attest["subject-digest"] == "${{ steps.build.outputs.digest }}"
        and attest["push-to-registry"] is True
    )


def test_the_image_tag_is_a_name_never_latest_and_the_manifest_uses_the_digest() -> (
    None
):
    tags = step(BUILD, "docker/build-push-action")["with"]["tags"]
    assert tags.endswith(":sha-${{ github.sha }}")
    # No image reference may use the mutable `latest` tag (the runner name ubuntu-latest is not one).
    assert ":latest" not in TEXT
    assert "--digests-dir" in TEXT and "cap_release validate" in TEXT


def test_the_image_owner_comes_from_the_registry_not_from_the_workflow() -> None:
    assert (
        BUILD["env"]["IMAGE"]
        == "${{ matrix.image.owner }}/${{ matrix.image.repository }}"
    )
    registry = json.loads((REPO / "release/images.json").read_text("utf-8"))
    assert registry["owner"] == "ghcr.io/asperant" and "ghcr.io/asperant" not in TEXT


def test_the_workflow_checks_the_registry_before_it_builds() -> None:
    plan = "\n".join(str(s.get("run", "")) for s in steps(WORKFLOW["jobs"]["plan"]))
    assert "cap_release registry-check" in plan
    assert WORKFLOW["jobs"]["build"]["needs"] == "plan"


def test_stack_sh_pulls_by_override_and_never_builds_on_the_host_when_it_is_set() -> (
    None
):
    script = (REPO / "infra/compose/stack.sh").read_text("utf-8")
    assert 'COMPOSE+=(-f "${CAP_COMPOSE_OVERRIDE}")' in script
    assert 'if [[ -z "${CAP_COMPOSE_OVERRIDE:-}" ]]; then' in script


@pytest.mark.skipif(
    shutil.which("docker") is None, reason="docker is not installed here; CI has it"
)
def test_compose_renders_the_override_without_a_build_key(tmp_path: Path) -> None:
    registry = load_registry(REPO)
    override = tmp_path / "override.yaml"
    override.write_text(render_override(registry, make_manifest(REPO)))
    done = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(REPO / "infra/compose/compose.yaml"),
            "-f",
            str(override),
            "--profile",
            "full",
            "config",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-300:]
    services = json.loads(done.stdout)["services"]
    for name in registry.images[0].compose_services:
        assert "build" not in services[name], f"{name} would still build on the host"
        assert (
            "@sha256:" in services[name]["image"]
            and ":sha-" not in services[name]["image"]
        )
