"""Contract tier checks (WP-CICD-001)."""

from __future__ import annotations

import json
from pathlib import Path

from check_contracts import check_schema_file

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["id"],
    "properties": {"id": {"type": "string"}},
}


def write(tmp_path: Path, schema: object, instance: object | None) -> Path:
    schema_path = tmp_path / "thing.schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    if instance is not None:
        (tmp_path / "thing.json").write_text(json.dumps(instance), encoding="utf-8")
    return schema_path


def test_valid_pair_passes(tmp_path: Path) -> None:
    assert check_schema_file(write(tmp_path, SCHEMA, {"id": "x"})) == ([], True)


def test_schema_without_instance_is_checked_alone(tmp_path: Path) -> None:
    assert check_schema_file(write(tmp_path, SCHEMA, None)) == ([], False)


def test_invalid_instance_fails(tmp_path: Path) -> None:
    errors, checked = check_schema_file(write(tmp_path, SCHEMA, {"id": 3}))
    assert checked and errors == ["thing.json: id: 3 is not of type 'string'"]


def test_invalid_schema_fails(tmp_path: Path) -> None:
    errors, _ = check_schema_file(
        write(tmp_path, {**SCHEMA, "type": "nonsense"}, {"id": "x"})
    )
    assert errors and "invalid schema" in errors[0]
