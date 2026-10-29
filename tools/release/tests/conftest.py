"""Shared fixtures: the real repository root and a minimal throw-away repository."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def repo() -> Path:
    return REPO


@pytest.fixture
def tiny(tmp_path: Path) -> Path:
    """A minimal repository: one image, its Dockerfile, a Compose file, a VERSION."""
    (tmp_path / "release").mkdir()
    shutil.copy(REPO / "release/images.json", tmp_path / "release/images.json")
    data = json.loads((tmp_path / "release/images.json").read_text())
    data["images"] = [data["images"][0]]
    data.pop(
        "database_migrations", None
    )  # the minimal repository declares no migration set
    (tmp_path / "release/images.json").write_text(json.dumps(data))
    (tmp_path / "release/VERSION").write_text("1.2.3\n")
    (tmp_path / "infra/compose/mlflow").mkdir(parents=True)
    (tmp_path / "infra/compose/mlflow/Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "infra/compose/compose.yaml").write_text(
        "services:\n  mlflow:\n    image: x\n  mlflow-init:\n    image: x\n"
    )
    return tmp_path


def write_registry(root: Path, **changes: object) -> None:
    data = json.loads((root / "release/images.json").read_text())
    data.update(changes)
    (root / "release/images.json").write_text(json.dumps(data))
