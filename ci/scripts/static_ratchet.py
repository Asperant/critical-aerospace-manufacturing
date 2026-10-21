"""WP-CICD-001 static-analysis ratchet (01 Item 41 §17–21).

Runs Ruff lint, Ruff format and Pyright with the repository configuration and
compares the findings with ``ci/static_baseline.json``:

* every (file, rule) count may only stay equal or go down;
* a file that is not in the baseline (all new code) must have zero findings;
* a file that is formatted today may never become unformatted;
* the tool versions in the baseline must match the installed tools, because
  counts are only comparable for identical tool versions.

``check`` fails on any regression and also when the baseline has become loose
(findings were fixed but the baseline was not tightened), so improvements are
locked in. ``update`` tightens the baseline and refuses to record regressions.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "ci" / "static_baseline.json"
SCHEMA_VERSION = "cap-static-ratchet-v1"

Counts = dict[str, dict[str, int]]


@dataclass
class Snapshot:
    """Findings of one run, keyed by repository-relative POSIX path."""

    ruff: Counts = field(default_factory=lambda: {})
    pyright: Counts = field(default_factory=lambda: {})
    unformatted: list[str] = field(default_factory=lambda: [])
    tools: dict[str, str] = field(default_factory=lambda: {})


def _tool(name: str) -> str:
    """Prefer the executable installed next to this interpreter (the ci venv)."""
    local = Path(sys.executable).parent / name
    return str(local) if local.exists() else name


def _run(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    command = [_tool(args[0]), *args[1:]]
    return subprocess.run(
        command, cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )


def _relative(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        candidate = candidate.resolve().relative_to(REPO_ROOT)
    return candidate.as_posix()


def _add(counts: Counts, path: str, rule: str) -> None:
    per_file = counts.setdefault(path, {})
    per_file[rule] = per_file.get(rule, 0) + 1


def collect_ruff() -> tuple[Counts, list[str], str]:
    lint = _run(["ruff", "check", "--output-format", "json", "--exit-zero", "."])
    if lint.returncode != 0:
        raise SystemExit(f"ruff check could not run:\n{lint.stderr}")
    counts: Counts = {}
    for item in cast(list[dict[str, Any]], json.loads(lint.stdout or "[]")):
        _add(counts, _relative(str(item["filename"])), str(item["code"]))
    fmt = _run(["ruff", "format", "--check", "."])
    if fmt.returncode not in (0, 1):
        raise SystemExit(f"ruff format could not run:\n{fmt.stderr}")
    unformatted = sorted(
        _relative(line.removeprefix("Would reformat: ").strip())
        for line in fmt.stdout.splitlines()
        if line.startswith("Would reformat: ")
    )
    version = _run(["ruff", "--version"]).stdout.strip()
    return counts, unformatted, version


def collect_pyright() -> tuple[Counts, str]:
    result = _run(["pyright", "--outputjson", "--pythonpath", sys.executable])
    if result.returncode not in (0, 1):
        raise SystemExit(f"pyright could not run:\n{result.stderr}{result.stdout}")
    report = cast(dict[str, Any], json.loads(result.stdout))
    counts: Counts = {}
    for diag in cast(list[dict[str, Any]], report.get("generalDiagnostics", [])):
        if diag.get("severity") not in ("error", "warning"):
            continue
        rule = str(diag.get("rule") or "unnamed")
        _add(counts, _relative(str(diag["file"])), rule)
    version = str(report.get("version", "unknown"))
    return counts, f"pyright {version}"


def collect() -> Snapshot:
    ruff_counts, unformatted, ruff_version = collect_ruff()
    pyright_counts, pyright_version = collect_pyright()
    return Snapshot(
        ruff=ruff_counts,
        pyright=pyright_counts,
        unformatted=unformatted,
        tools={"ruff": ruff_version, "pyright": pyright_version},
    )


def _as_counts(raw: object) -> Counts:
    data = cast(Mapping[str, Mapping[str, int]], raw or {})
    return {path: dict(rules) for path, rules in data.items()}


def load_baseline(path: Path = BASELINE_PATH) -> Snapshot:
    if not path.exists():
        raise SystemExit(f"Missing baseline {path}; run `static_ratchet.py update`.")
    raw = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"Unexpected baseline schema in {path}.")
    return Snapshot(
        ruff=_as_counts(raw.get("ruff")),
        pyright=_as_counts(raw.get("pyright")),
        unformatted=sorted(cast(list[str], raw.get("unformatted", []))),
        tools=dict(cast(Mapping[str, str], raw.get("tools", {}))),
    )


def _total(counts: Counts) -> int:
    return sum(sum(rules.values()) for rules in counts.values())


def compare(baseline: Snapshot, current: Snapshot) -> tuple[list[str], list[str]]:
    """Return (regressions, loosened) messages."""
    regressions: list[str] = []
    loosened: list[str] = []
    for tool in ("ruff", "pyright"):
        if baseline.tools.get(tool) != current.tools.get(tool):
            regressions.append(
                f"{tool}: version {current.tools.get(tool)!r} differs from baseline "
                f"{baseline.tools.get(tool)!r}; counts are not comparable."
            )
    for name, base, now in (
        ("ruff", baseline.ruff, current.ruff),
        ("pyright", baseline.pyright, current.pyright),
    ):
        for path in sorted(set(base) | set(now)):
            for rule in sorted(set(base.get(path, {})) | set(now.get(path, {}))):
                allowed = base.get(path, {}).get(rule, 0)
                found = now.get(path, {}).get(rule, 0)
                if found > allowed:
                    regressions.append(
                        f"{name}: {path} {rule}: {found} finding(s), allowed {allowed}"
                    )
                elif found < allowed:
                    loosened.append(
                        f"{name}: {path} {rule}: {found} < baseline {allowed}"
                    )
    allowed_unformatted = set(baseline.unformatted)
    for path in current.unformatted:
        if path not in allowed_unformatted:
            regressions.append(
                f"format: {path} is not formatted (`ruff format {path}`)"
            )
    for path in sorted(allowed_unformatted - set(current.unformatted)):
        loosened.append(f"format: {path} is now formatted")
    return regressions, loosened


def tightened(baseline: Snapshot, current: Snapshot) -> Snapshot:
    """Baseline lowered to the current findings; never raised."""
    regressions, _ = compare(baseline, current)
    if regressions:
        raise SystemExit(
            "Refusing to update: regressions cannot be recorded in the baseline.\n"
            + "\n".join(regressions)
        )
    return Snapshot(
        ruff=current.ruff,
        pyright=current.pyright,
        unformatted=current.unformatted,
        tools=current.tools,
    )


def write_baseline(snapshot: Snapshot, path: Path = BASELINE_PATH) -> None:
    data = {
        "schema_version": SCHEMA_VERSION,
        "description": (
            "WP-CICD-001 static ratchet baseline. Counts may only go down; files "
            "not listed must stay at zero findings. Regenerate only with "
            "`uv run --project ci python ci/scripts/static_ratchet.py update`."
        ),
        "tools": snapshot.tools,
        "totals": {
            "ruff": _total(snapshot.ruff),
            "pyright": _total(snapshot.pyright),
            "unformatted_files": len(snapshot.unformatted),
        },
        "ruff": {p: dict(sorted(r.items())) for p, r in sorted(snapshot.ruff.items())},
        "pyright": {
            p: dict(sorted(r.items())) for p, r in sorted(snapshot.pyright.items())
        },
        "unformatted": snapshot.unformatted,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-CICD-001 static-analysis ratchet")
    parser.add_argument("mode", choices=["check", "update", "init"])
    args = parser.parse_args(argv)
    current = collect()
    print(
        f"Current: ruff={_total(current.ruff)} pyright={_total(current.pyright)} "
        f"unformatted={len(current.unformatted)} ({current.tools})"
    )
    if args.mode == "init":
        if BASELINE_PATH.exists():
            print("Baseline already exists; use `update` to tighten it.")
            return 1
        write_baseline(current)
        print(f"Baseline initialised at {BASELINE_PATH.relative_to(REPO_ROOT)}.")
        return 0
    baseline = load_baseline()
    if args.mode == "update":
        write_baseline(tightened(baseline, current))
        print("Baseline tightened.")
        return 0
    regressions, loosened = compare(baseline, current)
    for line in regressions:
        print(f"REGRESSION  {line}")
    for line in loosened:
        print(f"IMPROVED    {line}")
    if regressions:
        print(f"FAIL: {len(regressions)} regression(s).")
        return 1
    if loosened:
        print(
            "FAIL: findings were fixed but the baseline was not tightened. Run "
            "`uv run --project ci python ci/scripts/static_ratchet.py update` and "
            "commit ci/static_baseline.json in the same PR."
        )
        return 1
    print("PASS: no new static findings; baseline is tight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
