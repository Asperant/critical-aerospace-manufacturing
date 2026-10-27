from __future__ import annotations

import json
from pathlib import Path

from check_architecture_boundaries import check, check_registry, check_service_sources

ROOT = Path(__file__).resolve().parents[2]


def test_current_repository_passes_architecture_boundary_rules() -> None:
    assert check(ROOT) == []


def test_non_core_service_cannot_import_private_database_or_core_repository(
    tmp_path: Path,
) -> None:
    source = tmp_path / "services" / "operations-bff" / "src" / "bad.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import psycopg\nfrom manufacturing_core.repository import Repository\n",
        encoding="utf-8",
    )
    errors = check_service_sources(tmp_path)
    assert any("private database import" in item for item in errors)
    assert any("direct private manufacturing-core import" in item for item in errors)


def test_service_source_cannot_embed_literal_credentials(tmp_path: Path) -> None:
    source = tmp_path / "services" / "example" / "src" / "config.py"
    source.parent.mkdir(parents=True)
    source.write_text('client_secret = "not-allowed"\n', encoding="utf-8")
    assert any("literal credential" in item for item in check_service_sources(tmp_path))


def test_registry_requires_unique_registered_canonical_producers(
    tmp_path: Path,
) -> None:
    registry = tmp_path / "packages" / "contracts" / "registry"
    registry.mkdir(parents=True)
    (tmp_path / "packages" / "contracts" / "producer-authorities.json").write_text(
        json.dumps({"producers": [{"producer": "core"}]}), encoding="utf-8"
    )
    declaration = {"contract_id": "core.example.v1", "canonical_producer": "unknown"}
    (registry / "one.json").write_text(json.dumps(declaration), encoding="utf-8")
    (registry / "two.json").write_text(json.dumps(declaration), encoding="utf-8")
    errors = check_registry(tmp_path)
    assert any("not registered" in item for item in errors)
    assert any("duplicate contract_id" in item for item in errors)
