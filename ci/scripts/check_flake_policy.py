"""WP-CICD-001 flake governance gate (NFR-DX-006, 01 Item 41 §162–166).

1. Validates ``ci/flaky_tests.yaml``: every quarantine entry has an owner,
   issue, reason, start date, expiry and release impact; it is unique, not
   expired and not longer than ``max_quarantine_days``.
2. Rejects retry-until-green mechanisms in CI configuration (rerun plugins,
   retry actions, ``continue-on-error``), because a blind re-run is not
   evidence (§163, §165).
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "ci" / "flaky_tests.yaml"
SCHEMA_VERSION = "cap-flaky-registry-v1"
OWNERS = frozenset({"Asrın", "Selman", "Batu", "Yavuz"})
REQUIRED_FIELDS = (
    "test_id",
    "owner",
    "issue",
    "reason",
    "quarantined_on",
    "expires_on",
    "release_impact",
)
RETRY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("pytest rerun plugin", re.compile(r"pytest-rerunfailures|pytest-retry")),
    ("pytest rerun option", re.compile(r"--reruns\b")),
    ("retry action", re.compile(r"uses:\s*\S*(retry|wretry)\S*", re.IGNORECASE)),
    ("continue-on-error", re.compile(r"continue-on-error:\s*true", re.IGNORECASE)),
)


@dataclass(frozen=True)
class Quarantine:
    test_id: str
    owner: str
    issue: str
    reason: str
    quarantined_on: dt.date
    expires_on: dt.date
    release_impact: str


def _as_date(value: object) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def load_registry(
    path: Path = REGISTRY_PATH, today: dt.date | None = None
) -> tuple[list[Quarantine], list[str]]:
    """Return (valid entries, errors). Any error makes the gate fail."""
    today = today or dt.date.today()
    if not path.exists():
        return [], [f"{path}: registry file is missing"]
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return [], [f"{path}: registry must be a mapping"]
    data = cast(dict[str, Any], raw)
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    max_days = data.get("max_quarantine_days")
    if not isinstance(max_days, int) or not 1 <= max_days <= 30:
        errors.append("max_quarantine_days must be an integer between 1 and 30")
        max_days = 0
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        return [], [*errors, "entries must be a list"]
    entries: list[Quarantine] = []
    seen: set[str] = set()
    for index, item in enumerate(cast(list[object], raw_entries)):
        where = f"entries[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be a mapping")
            continue
        entry = cast(dict[str, object], item)
        missing = [name for name in REQUIRED_FIELDS if entry.get(name) in (None, "")]
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
            continue
        test_id = str(entry["test_id"])
        where = f"{where} ({test_id})"
        if "::" not in test_id:
            errors.append(f"{where}: test_id must be '<path>::<test name>'")
        if test_id in seen:
            errors.append(f"{where}: duplicate quarantine entry")
        seen.add(test_id)
        owner = str(entry["owner"])
        if owner not in OWNERS:
            errors.append(f"{where}: unknown owner {owner!r}")
        start = _as_date(entry["quarantined_on"])
        end = _as_date(entry["expires_on"])
        if start is None or end is None:
            errors.append(f"{where}: dates must be ISO dates (YYYY-MM-DD)")
            continue
        if end < start:
            errors.append(f"{where}: expires_on is before quarantined_on")
        if max_days and (end - start).days > max_days:
            errors.append(f"{where}: quarantine longer than {max_days} days")
        if end < today:
            errors.append(f"{where}: quarantine expired on {end.isoformat()}")
        entries.append(
            Quarantine(
                test_id=test_id,
                owner=owner,
                issue=str(entry["issue"]),
                reason=str(entry["reason"]),
                quarantined_on=start,
                expires_on=end,
                release_impact=str(entry["release_impact"]),
            )
        )
    return entries, errors


def default_config_files(root: Path = REPO_ROOT) -> list[Path]:
    patterns = (".github/workflows/*.yml", ".github/workflows/*.yaml")
    files = [path for pattern in patterns for path in sorted(root.glob(pattern))]
    for name in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
        files.extend(
            path
            for path in sorted(root.rglob(name))
            if not any(
                part.startswith(".") or part == "node_modules"
                for part in path.relative_to(root).parts[:-1]
            )
        )
    return files


def find_retry_mechanisms(files: Iterable[Path], root: Path = REPO_ROOT) -> list[str]:
    findings: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            code = line.split("#", 1)[0]
            for label, pattern in RETRY_PATTERNS:
                if pattern.search(code):
                    rel = path.relative_to(root).as_posix()
                    findings.append(
                        f"{rel}:{number}: forbidden {label}: {line.strip()}"
                    )
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-CICD-001 flake governance gate")
    parser.add_argument("--today", type=dt.date.fromisoformat, default=None)
    args = parser.parse_args(argv)
    entries, errors = load_registry(today=cast(dt.date | None, args.today))
    retry = find_retry_mechanisms(default_config_files())
    for line in errors:
        print(f"REGISTRY  {line}")
    for line in retry:
        print(f"RETRY     {line}")
    for entry in entries:
        print(
            f"QUARANTINED {entry.test_id} owner={entry.owner} issue={entry.issue} "
            f"expires={entry.expires_on.isoformat()}"
        )
    if errors or retry:
        print("FAIL: flake governance violated.")
        return 1
    print(f"PASS: {len(entries)} active quarantine(s); no retry-until-green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
