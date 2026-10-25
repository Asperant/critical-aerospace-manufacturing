"""python -m cap_trace {validate|seed|drift} — run from the repository root.

Exit codes: 0 clean; 1 findings (validate) or drift with --strict; 2 the inputs
cannot be read (missing file, invalid YAML, a §17 record that cannot be seeded).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast

from .drift import compare
from .lint import IMPLEMENTED_CHECKS, REGISTRY, RegistryError, lint_files, load_yaml
from .seed import RTM, SeedError, dump, seed


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / RTM).is_file():
            return candidate
    raise RegistryError(f"no repository root with {RTM} above {start}")


def summary(registry: dict[str, Any]) -> str:
    edges = cast(list[dict[str, str]], registry.get("edges", []))
    by_relation = Counter(e.get("relation", "?") for e in edges)
    parts = ", ".join(f"{k} {v}" for k, v in sorted(by_relation.items()))
    nodes = cast(dict[str, Any], registry.get("requirements", {}))
    return f"{len(nodes)} requirements, {len(edges)} edges ({parts})"


def cmd_validate(root: Path, as_json: bool) -> int:
    registry, findings = lint_files(root)
    if as_json:
        print(
            json.dumps(
                {
                    "registry": REGISTRY,
                    "checks": list(IMPLEMENTED_CHECKS),
                    "findings": [f.__dict__ for f in findings],
                    "result": "FAIL" if findings else "PASS",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for finding in findings:
            print(finding.line())
        verdict = f"{len(findings)} finding(s)" if findings else "PASS"
        print(
            f"trace lint ({', '.join(IMPLEMENTED_CHECKS)}): {verdict}; {summary(registry)}"
        )
    return 1 if findings else 0


def cmd_seed(root: Path) -> int:
    registry = seed(root)
    (root / REGISTRY).write_text(dump(registry), encoding="utf-8")
    print(f"seeded {REGISTRY} from {RTM} §17: {summary(registry)}")
    return 0


def cmd_drift(root: Path, strict: bool) -> int:
    drift = compare(load_yaml(root / REGISTRY), seed(root))
    for line in drift.lines():
        print(line)
    if drift.empty:
        print(f"no drift between {REGISTRY} and {RTM} §17")
        return 0
    print(
        f"drift: {len(drift.lines())} difference(s); refresh with "
        "`python -m cap_trace seed` (reported, not failed, until slice 4)"
    )
    return 1 if strict else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cap_trace")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser(
        "validate", help="lint the registry (TL-01, TL-04, TL-05)"
    )
    validate.add_argument("--json", action="store_true", help="machine-readable result")
    sub.add_parser("seed", help="regenerate the registry from 03 §17")
    drift = sub.add_parser("drift", help="compare the registry with 03 §17")
    drift.add_argument("--strict", action="store_true", help="exit 1 on any drift")
    args = parser.parse_args(argv)
    try:
        root = find_root(Path.cwd())
        if args.command == "validate":
            return cmd_validate(root, bool(args.json))
        if args.command == "seed":
            return cmd_seed(root)
        return cmd_drift(root, bool(args.strict))
    except (RegistryError, SeedError) as exc:
        print(f"{args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
