"""WP-EVT-005 architecture boundary rules.

These checks are deliberately small and deterministic. They protect the
repository-level boundaries that can be checked without starting services;
runtime service identity and real integration authorization remain separate
integration work.

WP-TEST-007 adds the identity of each rule and the requirements it protects
(ci/architecture/rules.json), so a violation is reported with its requirement
context, and a defined exception process (ci/architecture/exceptions.json): a
temporary, change-controlled, owned and expiring allowance for the rules that
permit one. An exception never waives a requirement or changes acceptance.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = "ci/architecture/rules.json"
EXCEPTIONS_PATH = "ci/architecture/exceptions.json"
CHANGE_REGISTER = "09_change/change_requests.csv"
EXCEPTION_PROCESS_RULE = "BR-05"
MAX_EXCEPTION_DAYS = 90
DB_IMPORT = re.compile(r"^\s*(?:from|import)\s+(?:psycopg|asyncpg|sqlalchemy)\b")
CORE_IMPORT = re.compile(r"^\s*(?:from|import)\s+manufacturing_core(?:\.|\s|$)")
LITERAL_CREDENTIAL = re.compile(
    r"\b(?:password|client_secret|api[_-]?key|access[_-]?token|refresh[_-]?token)\s*=\s*['\"]"
)


class Violation(str):
    """A violation line that also knows its rule and file.

    It is a str, so it prints, compares and substring-matches like one.
    """

    rule: str
    path: str

    def __new__(cls, rule: str, path: str, text: str) -> Violation:
        value = super().__new__(cls, f"[{rule}] {text}")
        value.rule = rule
        value.path = path
        return value


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
                errors.append(
                    Violation(
                        "BR-01", str(path), f"{path}: missing canonical contract_id"
                    )
                )
            elif contract_id in seen_ids:
                errors.append(
                    Violation(
                        "BR-01",
                        str(path),
                        f"{path}: duplicate contract_id {contract_id}",
                    )
                )
            else:
                seen_ids.add(contract_id)
            if not isinstance(producer, str) or not producer.strip():
                errors.append(
                    Violation("BR-01", str(path), f"{path}: missing canonical producer")
                )
            elif producer not in producers:
                errors.append(
                    Violation(
                        "BR-01",
                        str(path),
                        f"{path}: producer {producer!r} is not registered",
                    )
                )
            declarations.append(value)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [
            Violation(
                "BR-01",
                str(authority_path),
                f"contract producer registry unreadable: {exc}",
            )
        ]
    if len(declarations) != len(seen_ids):
        errors.append(
            Violation(
                "BR-01",
                str(registry_dir),
                "contract producer registry does not have unique declarations",
            )
        )
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
            errors.append(
                Violation("BR-04", relative, f"{relative}: unreadable source: {exc}")
            )
            continue
        for line_number, line in enumerate(lines, start=1):
            if not is_core and DB_IMPORT.match(line):
                errors.append(
                    Violation(
                        "BR-02",
                        relative,
                        f"{relative}:{line_number}: private database import outside manufacturing-core",
                    )
                )
            if not is_core and CORE_IMPORT.match(line):
                errors.append(
                    Violation(
                        "BR-03",
                        relative,
                        f"{relative}:{line_number}: direct private manufacturing-core import",
                    )
                )
            if LITERAL_CREDENTIAL.search(line):
                errors.append(
                    Violation(
                        "BR-04",
                        relative,
                        f"{relative}:{line_number}: literal credential assignment in service source",
                    )
                )
    return errors


def load_rules(root: Path) -> dict[str, dict[str, Any]]:
    """The rule catalog by id; an unreadable catalog is an error, never an empty one."""
    value = json.loads((root / RULES_PATH).read_text(encoding="utf-8"))
    return {rule["id"]: rule for rule in value["rules"]}


def approved_changes(root: Path) -> set[str]:
    """CHG ids whose decision is an approval (DRAFT and rejected records do not count)."""
    with (root / CHANGE_REGISTER).open(encoding="utf-8", newline="") as stream:
        return {
            row["id"]
            for row in csv.DictReader(stream)
            if row["decision"].startswith("APPROVED")
        }


def process_violation(path: str, text: str) -> Violation:
    return Violation(EXCEPTION_PROCESS_RULE, path, f"{path}: {text}")


def check_exceptions(
    root: Path, violations: list[str], today: dt.date
) -> tuple[list[str], list[str]]:
    """Apply the exception registry: (violations that remain, report lines for applied ones).

    An exception is valid only for a rule that allows one, for an existing file, with an
    owner, a reason, an approved CHG and an expiry in the future within MAX_EXCEPTION_DAYS.
    An invalid, expired or unused (stale) exception is a BR-05 violation, and a violation
    it does not validly cover stays reported.
    """
    path = EXCEPTIONS_PATH
    try:
        registry = json.loads((root / path).read_text(encoding="utf-8"))
        entries = registry["exceptions"]
        rules = load_rules(root)
        changes = approved_changes(root)
        if registry["schema"] != "cap.architecture-exceptions/v1" or not isinstance(
            entries, list
        ):
            raise ValueError("unknown schema or exceptions is not a list")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        # Fail closed: an unreadable registry is a violation, never "no exceptions".
        return [*violations, process_violation(path, f"unreadable: {exc}")], []

    problems: list[str] = []
    applied: list[str] = []
    valid: dict[tuple[str, str], dict[str, Any]] = {}
    seen: set[str] = set()
    horizon = today + dt.timedelta(days=MAX_EXCEPTION_DAYS)
    for index, raw in enumerate(cast("list[Any]", entries)):
        label = f"{path}[{index}]"
        if not isinstance(raw, dict):
            problems.append(str(process_violation(label, "entry is not an object")))
            continue
        entry = cast("dict[str, Any]", raw)
        name = str(entry.get("id", index))
        label = f"{path} exception {name}"
        rule = rules.get(str(entry.get("rule")))
        target = str(entry.get("path", ""))
        owner = str(entry.get("owner", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        change = str(entry.get("chg", ""))
        try:
            expires = dt.date.fromisoformat(str(entry.get("expires")))
        except ValueError:
            expires = None
        faults: list[str] = []
        if name in seen:
            faults.append("duplicate id")
        seen.add(name)
        if rule is None:
            faults.append(f"unknown rule {entry.get('rule')!r}")
        elif not rule.get("exception_allowed"):
            faults.append(f"{rule['id']} does not allow exceptions")
        if (
            not target
            or target.startswith("/")
            or ".." in Path(target).parts
            or not (root / target).is_file()
        ):
            faults.append(f"path {target!r} is not an existing repository file")
        if not owner:
            faults.append("owner is missing")
        if len(reason) < 20:
            faults.append("reason is missing or too short to explain the exception")
        if change not in changes:
            faults.append(
                f"{change or 'chg'} is not an approved change in the CHG register"
            )
        if expires is None:
            faults.append("expires is not an ISO date")
        elif expires <= today:
            faults.append(f"expired on {expires}")
        elif expires > horizon:
            faults.append(
                f"expires {expires}, beyond the {MAX_EXCEPTION_DAYS}-day limit ({horizon})"
            )
        if faults:
            problems.append(str(process_violation(label, "; ".join(faults))))
            continue
        assert rule is not None and expires is not None
        valid[(rule["id"], target)] = entry
        entry["_expires"] = expires

    remaining: list[str] = []
    used: set[tuple[str, str]] = set()
    for item in violations:
        key = (getattr(item, "rule", ""), getattr(item, "path", ""))
        if key in valid:
            used.add(key)
            entry = valid[key]
            applied.append(
                f"EXCEPTED {item} (exception {entry['id']}, {entry['chg']}, "
                f"owner {entry['owner']}, until {entry['_expires']})"
            )
        else:
            remaining.append(item)
    for key, entry in valid.items():
        if key not in used:
            problems.append(
                str(
                    process_violation(
                        f"{path} exception {entry['id']}",
                        f"stale: no {key[0]} violation in {key[1]}; remove the exception",
                    )
                )
            )
    return [*remaining, *problems], applied


def check(root: Path = REPO_ROOT, today: dt.date | None = None) -> list[str]:
    violations = [*check_registry(root), *check_service_sources(root)]
    remaining, _ = check_exceptions(root, violations, today or dt.date.today())
    return remaining


def describe(root: Path, item: str) -> list[str]:
    """Requirement context of one violation: rule, protected requirements, owner."""
    rule_id = getattr(item, "rule", "")
    try:
        rules = load_rules(root)
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return ["  context: rule catalog unreadable (ci/architecture/rules.json)"]
    rule = rules.get(rule_id)
    if rule is None:
        return [
            f"  context: {rule_id or 'no rule id'} is not in ci/architecture/rules.json"
        ]
    requirements = rule["requirements"]
    lines = [f"  rule: {rule_id} - {rule['summary']}"]
    if requirements:
        lines.append(
            f"  protects: {', '.join(requirements)} "
            f"(architecture {', '.join(rule['architecture'])}); rule owner {rule['owner']}"
        )
    if rule_id == EXCEPTION_PROCESS_RULE:
        lines.append(
            f"  process: fix {EXCEPTIONS_PATH} (see ci/architecture/README.md); "
            "an exception never waives a requirement"
        )
    elif rule["exception_allowed"]:
        lines.append(
            f"  fix the code, or record a temporary exception in {EXCEPTIONS_PATH} "
            "backed by an approved CHG"
        )
    else:
        lines.append("  fix the code: this rule does not allow exceptions")
    return lines


def main() -> int:
    violations = [*check_registry(REPO_ROOT), *check_service_sources(REPO_ROOT)]
    remaining, applied = check_exceptions(REPO_ROOT, violations, dt.date.today())
    for line in applied:
        print(line)
    if remaining:
        for error in remaining:
            print(f"VIOLATION {error}")
            for line in describe(REPO_ROOT, error):
                print(line)
        print(f"FAIL: {len(remaining)} architecture boundary violation(s)")
        return 1
    print(
        "PASS: architecture boundary rules (producer ownership, private imports, "
        "literal credentials, exceptions)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
