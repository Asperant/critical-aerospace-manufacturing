"""TEST-CICD-002-001: the image registry release/images.json (rules BR in README)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cap_release.registry import RegistryError, check_registry, load_registry
from conftest import write_registry


def test_the_real_repository_registry_is_consistent(repo: Path) -> None:
    assert check_registry(repo) == []
    registry = load_registry(repo)
    assert registry.owner == "ghcr.io/asperant"
    assert [i.name for i in registry.images] == ["mlflow"]
    assert registry.reference(registry.images[0], "sha256:" + "0" * 64).startswith(
        "ghcr.io/asperant/cap-mlflow@sha256:"
    )


def test_a_minimal_repository_passes(tiny: Path) -> None:
    assert check_registry(tiny) == []


def test_an_unlisted_dockerfile_is_a_problem(tiny: Path) -> None:
    (tiny / "services/new").mkdir(parents=True)
    (tiny / "services/new/Dockerfile").write_text("FROM scratch\n")
    problems = check_registry(tiny)
    assert any(
        "services/new/Dockerfile" in p and "does not list" in p for p in problems
    )


def test_dockerfiles_under_vendored_directories_are_not_counted(tiny: Path) -> None:
    (tiny / "services/web/node_modules/pkg").mkdir(parents=True)
    (tiny / "services/web/node_modules/pkg/Dockerfile").write_text("FROM scratch\n")
    assert check_registry(tiny) == []


@pytest.mark.parametrize(
    ("change", "expect"),
    [
        ({"dockerfile": "infra/compose/mlflow/Missing"}, "does not exist"),
        ({"context": "infra/compose/nowhere"}, "build context"),
        ({"repository": "Cap-MLflow"}, "lower case"),
        ({"compose_services": ["mlflow", "ghost"]}, "Compose service ghost"),
        ({"compose_file": "infra/compose/missing.yaml"}, "unreadable"),
        ({"name": "ML Flow"}, "lower-case letters"),
    ],
)
def test_a_broken_entry_is_reported(
    tiny: Path, change: dict[str, object], expect: str
) -> None:
    data = json.loads((tiny / "release/images.json").read_text())
    data["images"][0].update(change)
    write_registry(tiny, images=data["images"])
    assert any(expect in p for p in check_registry(tiny)), check_registry(tiny)


def test_duplicate_names_and_repositories_are_reported(tiny: Path) -> None:
    data = json.loads((tiny / "release/images.json").read_text())
    write_registry(tiny, images=[data["images"][0], data["images"][0]])
    problems = check_registry(tiny)
    assert any("duplicate image name" in p for p in problems)
    assert any("used twice" in p for p in problems)


@pytest.mark.parametrize(
    "text",
    [
        "{",
        "[]",
        '{"schema": "other"}',
        '{"schema": "cap.release-images/v1", "owner": "docker.io/x", "images": []}',
    ],
)
def test_an_unreadable_or_malformed_registry_fails_closed(
    tiny: Path, text: str
) -> None:
    (tiny / "release/images.json").write_text(text)
    problems = check_registry(tiny)
    assert problems and "release/images.json" in problems[0]
    with pytest.raises(RegistryError):
        load_registry(tiny)


def test_a_missing_registry_fails_closed(tiny: Path) -> None:
    (tiny / "release/images.json").unlink()
    assert check_registry(tiny)
