"""ReleaseManifest: build it from verified facts, validate it, fingerprint it.

02 (Release Manifest): a manifest is immutable, identifies a runnable composition by
digest, never trusts a tag as the only identity and never carries secret plaintext.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections.abc import Mapping
from importlib import resources
from pathlib import Path
from typing import Any, cast

import jsonschema

from cap_release.registry import ImageRegistry

SCHEMA = "cap.release-manifest/v1"
MIGRATIONS = "services/manufacturing-core/src/manufacturing_core/migrations"
CONTRACT_REGISTRY = "packages/contracts/registry"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SECRET_KEY = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|private[_-]?key)", re.I
)
# 'reason' and 'location' are prose or paths; a secret is a value under a secret-looking key.
PROSE_KEYS = {"reason", "location", "detail"}


class ManifestError(Exception):
    """The manifest cannot be built from the given facts."""


def load_schema(name: str) -> dict[str, Any]:
    text = resources.files("cap_release").joinpath("schemas", name).read_text("utf-8")
    return cast("dict[str, Any]", json.loads(text))


def schema_problems(schema_name: str, instance: Mapping[str, Any]) -> list[str]:
    """Where `instance` breaks the named JSON Schema, as readable lines."""
    validator: Any = jsonschema.Draft202012Validator(
        load_schema(schema_name), format_checker=jsonschema.FormatChecker()
    )
    errors = list(validator.iter_errors(instance))
    return [
        f"{'.'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}"
        for e in errors
    ]


def canonical_bytes(manifest: Mapping[str, Any]) -> bytes:
    """The bytes the manifest is fingerprinted by: sorted keys, no whitespace."""
    return json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def fingerprint(manifest: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(manifest)).hexdigest()


SCHEMA_OWNER_IMAGE = "manufacturing-core"


def database_schema_target(root: Path, registry: ImageRegistry) -> dict[str, str]:
    """The Core store's newest migration, bound only when its owner is part of the release.

    A release states the migration state of the deployables it contains. Until
    manufacturing-core is a release image, that state is explicitly not yet produced,
    not guessed from a directory the release does not deploy.
    """
    if SCHEMA_OWNER_IMAGE not in {image.name for image in registry.images}:
        return {
            "state": "NOT_YET_PRODUCED",
            "reason": "manufacturing-core is not a release image yet; its versioned migrations join the release with it",
        }
    heads = sorted(
        p.stem for p in (root / MIGRATIONS).glob("[0-9][0-9][0-9][0-9]_*.sql")
    )
    if not heads:
        return {"state": "NOT_YET_PRODUCED", "reason": "no versioned migration exists"}
    return {"state": "BOUND", "identity": f"{SCHEMA_OWNER_IMAGE}:{heads[-1]}"}


def contract_catalog_version(root: Path) -> dict[str, Any]:
    """A content identity of the contract registry: any change gives a new digest."""
    files = sorted((root / CONTRACT_REGISTRY).glob("*.json"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return {"digest": f"sha256:{digest.hexdigest()}", "contracts": len(files)}


def not_yet(reason: str) -> dict[str, str]:
    return {"state": "NOT_YET_PRODUCED", "reason": reason}


def build_manifest(
    root: Path,
    registry: ImageRegistry,
    digests: Mapping[str, str],
    *,
    commit: str,
    run_id: int,
    run_attempt: int,
    run_url: str,
    created_at: dt.datetime,
    ref: str = "refs/heads/main",
    tag: str | None = None,
    sbom_location: Mapping[str, str] | None = None,
    attestation_location: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """A ReleaseManifest for exactly the registry's images, each pinned by digest."""
    missing = sorted(i.name for i in registry.images if i.name not in digests)
    unknown = sorted(set(digests) - {i.name for i in registry.images})
    if missing or unknown:
        raise ManifestError(
            f"digests do not match the registry: missing {missing}, unknown {unknown}"
        )
    images: list[dict[str, Any]] = []
    for image in registry.images:
        digest = digests[image.name]
        if not DIGEST.fullmatch(digest):
            raise ManifestError(f"{image.name}: {digest!r} is not a sha256 digest")
        sbom = (sbom_location or {}).get(image.name)
        attest = (attestation_location or {}).get(image.name)
        images.append(
            {
                "name": image.name,
                "repository": registry.repository(image),
                "digest": digest,
                "reference": registry.reference(image, digest),
                "sbom": (
                    {"state": "PUBLISHED", "location": sbom}
                    if sbom
                    else {
                        "state": "NOT_PRODUCED",
                        "reason": "no SBOM location was supplied",
                    }
                ),
                "provenance_attestation": (
                    {"state": "PUBLISHED", "location": attest}
                    if attest
                    else {
                        "state": "NOT_PRODUCED",
                        "reason": "no attestation location was supplied",
                    }
                ),
            }
        )
    version = (root / "release" / "VERSION").read_text("utf-8").strip()
    return {
        "schema": SCHEMA,
        "release_id": f"REL-{commit[:12]}-{run_id}",
        "product_version": version,
        "source": {"commit": commit, "ref": ref, "tag": tag},
        "service_images": images,
        "database_schema_target": database_schema_target(root, registry),
        "contract_catalog_version": contract_catalog_version(root),
        "model_versions": not_yet("no ModelPackage exists yet"),
        "workflow_definition_versions": not_yet(
            "no Automation workflow definition exists yet"
        ),
        "prompt_tool_routing_versions": not_yet(
            "no prompt, tool or model-routing version exists yet"
        ),
        "knowledge_index_version": not_yet("no KnowledgeIndexVersion exists yet"),
        "configuration_schema_version": not_yet("no configuration schema exists yet"),
        "build_provenance": {
            "workflow": "release",
            "run_id": run_id,
            "run_attempt": run_attempt,
            "run_url": run_url,
        },
        "created_at": created_at.astimezone(dt.UTC).isoformat(timespec="seconds"),
    }


def _plaintext_secrets(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in cast("dict[str, Any]", value).items():
            where = f"{path}.{key}"
            if (
                SECRET_KEY.search(key)
                and key not in PROSE_KEYS
                and isinstance(item, str)
                and item
            ):
                found.append(where)
            found.extend(_plaintext_secrets(item, where))
    elif isinstance(value, list):
        for index, item in enumerate(cast("list[Any]", value)):
            found.extend(_plaintext_secrets(item, f"{path}[{index}]"))
    return found


def validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Schema and semantic problems; an empty list means the manifest may be deployed."""
    problems = schema_problems("release-manifest.schema.json", manifest)
    images = manifest.get("service_images")
    if isinstance(images, list):
        for image in cast("list[Any]", images):
            if not isinstance(image, dict):
                continue
            item = cast("dict[str, Any]", image)
            reference, digest, repository = (
                item.get("reference"),
                item.get("digest"),
                item.get("repository"),
            )
            if (
                isinstance(reference, str)
                and isinstance(digest, str)
                and isinstance(repository, str)
                and reference != f"{repository}@{digest}"
            ):
                problems.append(
                    f"{item.get('name')}: reference is not repository@digest"
                )
            if (
                isinstance(reference, str)
                and ":" in reference.split("/")[-1].split("@")[0]
            ):
                problems.append(
                    f"{item.get('name')}: a tag is not an identity; the reference must be digest-pinned"
                )
    source = manifest.get("source")
    release_id = manifest.get("release_id")
    if isinstance(source, dict) and isinstance(release_id, str):
        commit = cast("dict[str, Any]", source).get("commit")
        if isinstance(commit, str) and not release_id.startswith(f"REL-{commit[:12]}-"):
            problems.append("release_id does not carry the source commit")
    problems.extend(
        f"{where}: secret plaintext is not allowed in a manifest"
        for where in _plaintext_secrets(manifest)
    )
    return problems
