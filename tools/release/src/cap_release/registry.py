"""The image registry `release/images.json`: which deployable images the pipeline builds."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

REGISTRY_PATH = "release/images.json"
SCHEMA = "cap.release-images/v1"
NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
OWNER = re.compile(r"^ghcr\.io/[a-z0-9._-]+$")
SKIPPED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}


class RegistryError(Exception):
    """The registry cannot be read or is malformed; it is never read as 'no images'."""


@dataclass(frozen=True)
class Image:
    name: str
    repository: str
    context: str
    dockerfile: str
    compose_file: str
    compose_services: tuple[str, ...]


@dataclass(frozen=True)
class ImageRegistry:
    owner: str
    images: tuple[Image, ...]

    def repository(self, image: Image) -> str:
        return f"{self.owner}/{image.repository}"

    def reference(self, image: Image, digest: str) -> str:
        return f"{self.repository(image)}@{digest}"


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegistryError(f"{REGISTRY_PATH}: {field} must be a non-empty string")
    return value


def load_registry(root: Path) -> ImageRegistry:
    try:
        loaded: Any = json.loads((root / REGISTRY_PATH).read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"{REGISTRY_PATH} unreadable: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RegistryError(f"{REGISTRY_PATH}: the top level must be an object")
    data = cast("dict[str, Any]", loaded)
    if data.get("schema") != SCHEMA:
        raise RegistryError(f"{REGISTRY_PATH}: schema must be {SCHEMA}")
    owner = _text(data.get("owner"), "owner")
    if not OWNER.fullmatch(owner):
        raise RegistryError(
            f"{REGISTRY_PATH}: owner {owner!r} must be ghcr.io/<lower-case owner>"
        )
    raw = data.get("images")
    if not isinstance(raw, list) or not raw:
        raise RegistryError(f"{REGISTRY_PATH}: images must be a non-empty list")
    images: list[Image] = []
    for index, item in enumerate(cast("list[Any]", raw)):
        if not isinstance(item, dict):
            raise RegistryError(f"{REGISTRY_PATH}: images[{index}] is not an object")
        entry = cast("dict[str, Any]", item)
        services = entry.get("compose_services")
        if not isinstance(services, list) or not services:
            raise RegistryError(
                f"{REGISTRY_PATH}: images[{index}].compose_services must be a list"
            )
        images.append(
            Image(
                name=_text(entry.get("name"), f"images[{index}].name"),
                repository=_text(
                    entry.get("repository"), f"images[{index}].repository"
                ),
                context=_text(entry.get("context"), f"images[{index}].context"),
                dockerfile=_text(
                    entry.get("dockerfile"), f"images[{index}].dockerfile"
                ),
                compose_file=_text(
                    entry.get("compose_file"), f"images[{index}].compose_file"
                ),
                compose_services=tuple(
                    _text(s, "compose_services[]") for s in cast("list[Any]", services)
                ),
            )
        )
    return ImageRegistry(owner=owner, images=tuple(images))


def repository_dockerfiles(root: Path) -> list[str]:
    """Every Dockerfile in the repository, as repository-relative paths."""
    found: list[str] = []
    for path in sorted(root.rglob("Dockerfile")):
        relative = path.relative_to(root)
        if not SKIPPED_DIRS.intersection(relative.parts):
            found.append(relative.as_posix())
    return found


def compose_services(root: Path, compose_file: str) -> dict[str, Any]:
    document = cast(
        "dict[str, Any]", yaml.safe_load((root / compose_file).read_text("utf-8"))
    )
    return cast("dict[str, Any]", document["services"])


def check_registry(root: Path) -> list[str]:
    """Problems that would make the pipeline build the wrong thing, or miss an image."""
    try:
        registry = load_registry(root)
    except RegistryError as exc:
        return [str(exc)]
    problems: list[str] = []
    names: set[str] = set()
    repositories: set[str] = set()
    for image in registry.images:
        if image.name in names:
            problems.append(f"duplicate image name {image.name}")
        if image.repository in repositories:
            problems.append(
                f"{image.name}: repository {image.repository} is used twice"
            )
        names.add(image.name)
        repositories.add(image.repository)
        if not NAME.fullmatch(image.name):
            problems.append(
                f"{image.name}: name must be lower-case letters, digits and dashes"
            )
        if image.repository != image.repository.lower():
            problems.append(f"{image.name}: GHCR repository names must be lower case")
        if not (root / image.dockerfile).is_file():
            problems.append(f"{image.name}: {image.dockerfile} does not exist")
        if not (root / image.context).is_dir():
            problems.append(
                f"{image.name}: build context {image.context} does not exist"
            )
        if not image.dockerfile.startswith(image.context.rstrip("/") + "/"):
            problems.append(
                f"{image.name}: the Dockerfile is outside its build context"
            )
        try:
            services = compose_services(root, image.compose_file)
        except (OSError, KeyError, ValueError, yaml.YAMLError) as exc:
            problems.append(f"{image.name}: {image.compose_file} unreadable: {exc}")
            continue
        for service in image.compose_services:
            if service not in services:
                problems.append(
                    f"{image.name}: Compose service {service} is not in {image.compose_file}"
                )
    listed = {image.dockerfile for image in registry.images}
    for path in repository_dockerfiles(root):
        if path not in listed:
            problems.append(
                f"{path} is a Dockerfile that {REGISTRY_PATH} does not list"
            )
    return problems
