"""python -m cap_trace {validate|seed|generate|drift|requirement|orphans} — run
from the repository root (mfgctl trace … wraps the same commands).

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
from .references import coverage
from .seed import RTM, SeedError, dump, seed
from .views import write


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


def cmd_validate(root: Path, as_json: bool, base: str | None) -> int:
    registry, findings = lint_files(root, base)
    if as_json:
        print(
            json.dumps(
                {
                    "registry": REGISTRY,
                    "checks": list(IMPLEMENTED_CHECKS),
                    "findings": [f.__dict__ for f in findings],
                    "coverage": dict(sorted(coverage(registry).items())),
                    "result": "FAIL" if findings else "PASS",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for finding in findings:
            print(finding.line())
        for mode, count in sorted(coverage(registry).items()):
            print(f"  {count:5d} edges: {mode}")
        verdict = f"{len(findings)} finding(s)" if findings else "PASS"
        print(
            f"trace lint ({', '.join(IMPLEMENTED_CHECKS)}): {verdict}; {summary(registry)}"
        )
    return 1 if findings else 0


def cmd_seed(root: Path) -> int:
    registry = seed(root)
    (root / REGISTRY).write_text(dump(registry), encoding="utf-8")
    print(f"seeded {REGISTRY} from {RTM} §17: {summary(registry)}")
    return cmd_generate(root)


def cmd_generate(root: Path) -> int:
    for path in write(root, load_yaml(root / REGISTRY)):
        print(f"generated {path}")
    return 0


def cmd_requirement(root: Path, requirement: str) -> int:
    registry = load_yaml(root / REGISTRY)
    nodes = cast(dict[str, Any], registry.get("requirements", {}))
    if requirement not in nodes:
        print(f"{requirement}: not in {REGISTRY}", file=sys.stderr)
        return 2
    print(json.dumps({requirement: nodes[requirement]}, ensure_ascii=False, indent=2))
    for edge in cast(list[dict[str, str]], registry.get("edges", [])):
        if edge["from"] == requirement:
            print(f"  {edge['relation']:<13} {edge['to']}  [{edge['applicability']}]")
    return 0


def cmd_orphans(root: Path) -> int:
    report = json.loads(
        (root / "traceability/generated/orphan_report.json").read_text("utf-8")
    )
    for relation, items in report["orphan_requirements"].items():
        print(
            f"without {relation}: {len(items)}"
            + (f" ({', '.join(items)})" if items else "")
        )
    print(f"without a recorded realization: {report['without_recorded_realization']}")
    print(f"without a run: {report['without_run']}")
    print(
        "coverage states: "
        + ", ".join(f"{k} {v}" for k, v in report["coverage_states"].items())
    )
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
        "validate", help="lint the registry (" + ", ".join(IMPLEMENTED_CHECKS) + ")"
    )
    validate.add_argument("--json", action="store_true", help="machine-readable result")
    validate.add_argument(
        "--base", help="Git revision for the TL-08 coverage-regression comparison"
    )
    sub.add_parser("seed", help="regenerate the registry from 03 §17, then the views")
    sub.add_parser("generate", help="regenerate traceability/generated/ (TL-07)")
    requirement = sub.add_parser("requirement", help="one requirement's node and edges")
    requirement.add_argument("id")
    sub.add_parser("orphans", help="summary of the orphan report")
    drift = sub.add_parser("drift", help="compare the registry with 03 §17")
    drift.add_argument("--strict", action="store_true", help="exit 1 on any drift")
    args = parser.parse_args(argv)
    try:
        root = find_root(Path.cwd())
        if args.command == "validate":
            return cmd_validate(root, bool(args.json), args.base)
        if args.command == "seed":
            return cmd_seed(root)
        if args.command == "generate":
            return cmd_generate(root)
        if args.command == "requirement":
            return cmd_requirement(root, str(args.id))
        if args.command == "orphans":
            return cmd_orphans(root)
        return cmd_drift(root, bool(args.strict))
    except (RegistryError, SeedError, OSError, KeyError) as exc:
        print(f"{args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
