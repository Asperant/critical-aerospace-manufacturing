"""WP-EVT-005 architecture boundary rules.

These checks are deliberately small and deterministic. They protect the
repository-level boundaries that can be checked without starting services;
runtime service identity and real integration authorization remain separate
integration work.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_IMPORT = re.compile(r"^\s*(?:from|import)\s+(?:psycopg|asyncpg|sqlalchemy)\b")
CORE_IMPORT = re.compile(r"^\s*(?:from|import)\s+manufacturing_core(?:\.|\s|$)")
LITERAL_CREDENTIAL = re.compile(
    r"\b(?:password|client_secret|api[_-]?key|access[_-]?token|refresh[_-]?token)\s*=\s*['\"]"
)


def check_registry(root: Path) -> list[str]:
    registry_dir = root / "packages/contracts/registry"
    authority_path = root / "packages/contracts/producer-authorities.json"
    errors: list[str] = []
    declarations: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    try:
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
        producers = {item["producer"] for item in authority["producers"]}
        for path in sorted(registry_dir.glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            contract_id = value.get("contract_id")
            producer = value.get("canonical_producer")
            if not isinstance(contract_id, str) or not contract_id.strip():
                errors.append(f"{path}: missing canonical contract_id")
            elif contract_id in seen_ids:
                errors.append(f"{path}: duplicate contract_id {contract_id}")
            else:
                seen_ids.add(contract_id)
            if not isinstance(producer, str) or not producer.strip():
                errors.append(f"{path}: missing canonical producer")
            elif producer not in producers:
                errors.append(f"{path}: producer {producer!r} is not registered")
            declarations.append(value)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [f"contract producer registry unreadable: {exc}"]
    if len(declarations) != len(seen_ids):
        errors.append("contract producer registry does not have unique declarations")
    return errors


def check_service_sources(root: Path) -> list[str]:
    errors: list[str] = []
    source_root = root / "services"
    for path in sorted(source_root.glob("*/src/**/*.py")):
        relative = path.relative_to(root).as_posix()
        is_core = relative.startswith("services/manufacturing-core/")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            errors.append(f"{relative}: unreadable source: {exc}")
            continue
        for line_number, line in enumerate(lines, start=1):
            if not is_core and DB_IMPORT.match(line):
                errors.append(
                    f"{relative}:{line_number}: private database import outside manufacturing-core"
                )
            if not is_core and CORE_IMPORT.match(line):
                errors.append(
                    f"{relative}:{line_number}: direct private manufacturing-core import"
                )
            if LITERAL_CREDENTIAL.search(line):
                errors.append(
                    f"{relative}:{line_number}: literal credential assignment in service source"
                )
    return errors


def check(root: Path = REPO_ROOT) -> list[str]:
    return [*check_registry(root), *check_service_sources(root)]


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print(f"VIOLATION {error}")
        print(f"FAIL: {len(errors)} architecture boundary violation(s)")
        return 1
    print(
        "PASS: architecture boundary rules (producer ownership, private imports, literal credentials)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
