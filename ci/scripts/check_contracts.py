"""WP-CICD-001 contract tier: JSON Schema contracts tracked in the repository.

For every tracked ``*.schema.json``:

* the schema itself must be valid for its declared ``$schema`` dialect;
* if a sibling instance ``<name>.json`` exists it must validate against it.

Today this covers ``requirements/catalog.schema.json`` (WP-GOV-001). Service
API/event contracts (OpenAPI, AsyncAPI, event envelopes) join this tier when
their owners publish them; the number of checked contracts is printed so an
empty tier is visible instead of silently passing (01 Item 41 §181–182).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from jsonschema import exceptions, validators

REPO_ROOT = Path(__file__).resolve().parents[2]


def tracked_schemas(root: Path = REPO_ROOT) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.schema.json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"git ls-files failed: {result.stderr}")
    return [root / name for name in result.stdout.split("\0") if name]


def check_schema_file(schema_path: Path) -> tuple[list[str], bool]:
    """Return (errors, instance_checked) for one schema and its sibling."""
    errors: list[str] = []
    try:
        schema = cast(dict[str, Any], json.loads(schema_path.read_text("utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{schema_path.name}: unreadable schema: {exc}"], False
    # jsonschema's public API is only partially typed; keep the boundary explicit.
    validator_cls: Any = cast(Any, validators).validator_for(schema)
    try:
        validator_cls.check_schema(schema)
    except exceptions.SchemaError as exc:
        return [f"{schema_path.name}: invalid schema: {exc.message}"], False
    instance_path = schema_path.with_name(
        schema_path.name.removesuffix(".schema.json") + ".json"
    )
    if not instance_path.exists():
        return errors, False
    try:
        instance = json.loads(instance_path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{instance_path.name}: unreadable instance: {exc}"], True
    validator: Any = validator_cls(schema)
    found: list[Any] = list(validator.iter_errors(instance))
    found.sort(key=lambda e: [str(part) for part in e.path])
    for error in found[:20]:
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{instance_path.name}: {location}: {error.message}")
    return errors, True


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    schemas = tracked_schemas()
    failures: list[str] = []
    instances = 0
    for schema_path in schemas:
        errors, checked = check_schema_file(schema_path)
        instances += int(checked)
        rel = schema_path.relative_to(REPO_ROOT).as_posix()
        print(
            f"{'FAIL' if errors else 'OK  '}  {rel}{' (+instance)' if checked else ''}"
        )
        failures.extend(errors)
    for line in failures:
        print(f"  {line}")
    print(f"Contracts: {len(schemas)} schema(s), {instances} instance(s) validated.")
    if failures:
        print("FAIL: contract validation errors.")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
