"""``python -m cap_observability check-logs FILE...`` — check JSON Lines logs.

Exit 0 when every record conforms to ``cap.log/v1``, 1 when any does not,
2 on usage errors or unreadable files. Used by the field-coverage check in CI.
"""

from __future__ import annotations

import sys
from pathlib import Path

from cap_observability.standard import check_log_lines


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "check-logs":
        print("usage: python -m cap_observability check-logs FILE...", file=sys.stderr)
        return 2
    failed = False
    for name in argv[1:]:
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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
