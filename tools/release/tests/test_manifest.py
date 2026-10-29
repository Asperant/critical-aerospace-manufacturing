"""TEST-CICD-002-002: ReleaseManifest, built from facts and validated (02, Release Manifest)."""

from __future__ import annotations

import copy
import datetime as dt
from pathlib import Path
from typing import Any

import pytest
from cap_release.manifest import (
    ManifestError,
    build_manifest,
    canonical_bytes,
    fingerprint,
    validate_manifest,
)
from cap_release.registry import load_registry

DIGEST = "sha256:" + "a" * 64
COMMIT = "b" * 40
WHEN = dt.datetime(2026, 10, 28, 12, 0, tzinfo=dt.UTC)
ALL_DIGESTS = {
    "mlflow": DIGEST,
    "demo-runtime": DIGEST,
    "command-center-web": DIGEST,
}


def manifest(repo: Path, **kwargs: Any) -> dict[str, Any]:
    registry = load_registry(repo)
    return build_manifest(
        repo,
        registry,
        {image.name: DIGEST for image in registry.images},
        commit=COMMIT,
        run_id=77,
        run_attempt=1,
        run_url="https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/77",
        created_at=WHEN,
        **kwargs,
    )


def test_a_built_manifest_validates_and_carries_every_02_field(repo: Path) -> None:
    built = manifest(repo)
    assert validate_manifest(built) == []
    assert built["release_id"] == f"REL-{COMMIT[:12]}-77"
    image = built["service_images"][0]
    assert image["reference"] == f"ghcr.io/asperant/cap-mlflow@{DIGEST}"
    # 02's thirteen required identities are all present, none null.
    assert all(built[k] is not None for k in built)


def test_identities_without_a_producer_say_so_instead_of_guessing(repo: Path) -> None:
    built = manifest(repo)
    for field in (
        "model_versions",
        "workflow_definition_versions",
        "prompt_tool_routing_versions",
        "knowledge_index_version",
        "configuration_schema_version",
    ):
        assert built[field]["state"] == "NOT_YET_PRODUCED", field
        assert built[field]["reason"]
    assert built["contract_catalog_version"]["contracts"] > 0


def test_the_database_target_is_bound_to_the_declared_migration_sets(
    repo: Path,
) -> None:
    target = manifest(repo)["database_schema_target"]
    assert target["state"] == "BOUND"
    assert target["identity"].startswith("manufacturing-core:0")


def test_a_release_without_a_migration_set_states_it_has_no_target(tiny: Path) -> None:
    built = build_manifest(
        tiny,
        load_registry(tiny),
        {"mlflow": DIGEST},
        commit=COMMIT,
        run_id=1,
        run_attempt=1,
        run_url="https://github.com/x/y/actions/runs/1",
        created_at=WHEN,
    )
    target = built["database_schema_target"]
    assert (
        target["state"] == "NOT_YET_PRODUCED"
        and "no database migration set" in target["reason"]
    )
    assert validate_manifest(built) == []


def test_evidence_locations_are_recorded_when_supplied(repo: Path) -> None:
    built = manifest(
        repo,
        sbom_location={"mlflow": "oci://sbom"},
        attestation_location={"mlflow": "https://a"},
    )
    image = built["service_images"][0]
    assert image["sbom"] == {"state": "PUBLISHED", "location": "oci://sbom"}
    assert image["provenance_attestation"]["location"] == "https://a"
    assert manifest(repo)["service_images"][0]["sbom"]["state"] == "NOT_PRODUCED"


def test_the_fingerprint_is_stable_and_any_change_gives_a_new_one(repo: Path) -> None:
    built = manifest(repo)
    assert fingerprint(built) == fingerprint(copy.deepcopy(built))
    assert canonical_bytes(built) == canonical_bytes(copy.deepcopy(built))
    changed = copy.deepcopy(built)
    changed["service_images"][0]["digest"] = "sha256:" + "d" * 64
    assert fingerprint(changed) != fingerprint(built)


@pytest.mark.parametrize(
    "digests",
    [
        {},
        {**ALL_DIGESTS, "ghost": DIGEST},
        {**ALL_DIGESTS, "mlflow": "sha256:short"},
        {**ALL_DIGESTS, "mlflow": "latest"},
    ],
)
def test_the_builder_rejects_digests_that_do_not_match_the_registry(
    repo: Path, digests: dict[str, str]
) -> None:
    with pytest.raises(ManifestError):
        build_manifest(
            repo,
            load_registry(repo),
            digests,
            commit=COMMIT,
            run_id=1,
            run_attempt=1,
            run_url="https://github.com/x/y/actions/runs/1",
            created_at=WHEN,
        )


def broken(repo: Path, mutate: Any) -> list[str]:
    value = manifest(repo)
    mutate(value)
    return validate_manifest(value)


@pytest.mark.parametrize(
    ("mutate", "expect"),
    [
        (
            lambda m: m["service_images"][0].update(
                reference="ghcr.io/asperant/cap-mlflow:latest"
            ),
            "reference",
        ),
        (
            lambda m: m["service_images"][0].update(
                reference="ghcr.io/asperant/cap-mlflow:1.0@" + DIGEST
            ),
            "tag is not an identity",
        ),
        (lambda m: m["service_images"][0].update(digest="sha256:nothex"), "digest"),
        (
            lambda m: m["service_images"][0].update(
                reference=f"ghcr.io/asperant/other@{DIGEST}"
            ),
            "not repository@digest",
        ),
        (lambda m: m.update(service_images=[]), "service_images"),
        (
            lambda m: m.update(release_id="REL-000000000000-1"),
            "does not carry the source commit",
        ),
        (lambda m: m.update(release_id="release-1"), "release_id"),
        (lambda m: m["source"].update(commit="abc"), "commit"),
        (lambda m: m.update(model_versions=None), "model_versions"),
        (
            lambda m: m.update(model_versions={"state": "NOT_YET_PRODUCED"}),
            "model_versions",
        ),
        (lambda m: m.update(extra="field"), "extra"),
        (lambda m: m.pop("created_at"), "created_at"),
        (lambda m: m.update(schema="cap.release-manifest/v2"), "schema"),
        (lambda m: m.update(product_version="one"), "product_version"),
    ],
)
def test_an_invalid_manifest_is_rejected(repo: Path, mutate: Any, expect: str) -> None:
    problems = broken(repo, mutate)
    assert any(expect in p for p in problems), problems


@pytest.mark.parametrize(
    "key", ["password", "client_secret", "api_key", "access_token", "private_key"]
)
def test_secret_plaintext_is_rejected_anywhere_in_a_manifest(
    repo: Path, key: str
) -> None:
    problems = broken(repo, lambda m: m["build_provenance"].update({key: "hunter2"}))
    assert any("secret plaintext" in p for p in problems), problems


def test_prose_fields_may_mention_secrets_without_being_secrets(repo: Path) -> None:
    value = manifest(repo)
    value["model_versions"] = {
        "state": "NOT_YET_PRODUCED",
        "reason": "the token registry does not exist",
    }
    assert validate_manifest(value) == []
