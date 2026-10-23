"""Command line checks of the telemetry standard (WP-OBS-001).

    python -m cap_observability check-logs FILE...       JSON Lines logs vs cap.log/v1
    python -m cap_observability check-coverage REGISTRY  mandatory deployable adoption

Exit 0 when everything conforms, 1 on violations, 2 on usage errors or
unreadable input. Both run in CI.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from cap_observability import coverage
from cap_observability.standard import check_log_lines

USAGE = (
    "usage: python -m cap_observability check-logs FILE...\n"
    "       python -m cap_observability check-coverage REGISTRY"
)


def _check_logs(files: list[str]) -> int:
    failed = False
    for name in files:
        try:
            lines = Path(name).read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            print(f"{name}: cannot read: {exc.strerror or exc}", file=sys.stderr)
            return 2
        findings = check_log_lines(lines)
        for finding in findings:
            print(f"{name}: {finding}")
        failed = failed or bool(findings)
        if not findings:
            print(f"{name}: {sum(1 for line in lines if line.strip())} records conform")
    return 1 if failed else 0


def _check_coverage(registry: str, today: date | None = None) -> int:
    try:
        data = coverage.load(Path(registry))
    except (OSError, ValueError) as exc:
        print(f"{registry}: cannot read: {exc}", file=sys.stderr)
        return 2
    result = coverage.check(data, Path.cwd(), today or date.today())
    for violation in result.violations:
        print(f"VIOLATION {violation}")
    print(result.summary())
    return 1 if result.violations else 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "check-logs":
        return _check_logs(argv[1:])
    if len(argv) == 2 and argv[0] == "check-coverage":
        return _check_coverage(argv[1])
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
