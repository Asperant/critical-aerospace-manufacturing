"""TL-13 PR Requirement-Impact (01 Item 83 #98–#99, 03 §19 Same-PR Rule).

A behavior-changing pull request declares the requirements it impacts in the
existing template field ``Requirements (stable IDs, or ...):`` — the same field
the Plane helper's PR governance check reads, so nothing about the template's
shape changes. The value either names catalog requirement IDs, all of them
active, or says ``NONE — <reason>`` (or explains a control-only scope); the
reason is for the reviewer to accept (advisory, CHG-018).

A change that only touches documentation, evidence, change records, project
control files, the host control plane (`tools/host/`) or CODEOWNERS is not
behavior-changing and needs no declaration. Calibrated on the last 25 merged
PRs (25 October 2026): host-control and automatic START-preparation PRs pass on
these paths; a work-package PR with an empty Requirements field fails.

For declared requirements the check names their owners, so the author can ask
the right people to look (review stays advisory; CHG-018).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from .model import Finding
from .sources import Index

FIELD = re.compile(r"^\s*(?:\*\*)?requirements\b[^:]*:(?:\*\*)?\s*(.*)$", re.I)
NEXT_FIELD = re.compile(r"^\s*(?:\*\*)?[A-Za-z][^:]{0,80}:(?:\*\*)?(?:\s|$)")
REQUIREMENT = re.compile(r"(?<![A-Za-z0-9-])((?:FR|NFR)-[A-Z]+-\d{3})(?![A-Za-z0-9-])")
# An explicit no-impact or control-only explanation; it must say why (≥ 15 characters).
NO_IMPACT = re.compile(
    r"\b(?:none|n/a|not applicable|control[- ]only|control scope|"
    r"no (?:product |normative )?requirements?)\b",
    re.I,
)
MIN_REASON = 15
# Not product behavior: documentation, evidence, change records, project control
# and the host control plane (tools/host/, CTRL-HOST work: Plane/host automation,
# no product requirement), plus review routing (.github/CODEOWNERS).
NON_BEHAVIOR = ("docs/", "evidence/", "09_change/", "project_control/", "tools/host/")
NON_BEHAVIOR_FILES = frozenset({".github/CODEOWNERS"})
TEAM = "project_control/TEAM_WORKFLOW.md"
TEAM_ROW = re.compile(r"^\| ([^|]+?) \| ([A-Za-z0-9-]+) \|", re.M)


def behavior_changing(files: Iterable[str]) -> list[str]:
    """Changed files that can change behavior (not docs/evidence/control only)."""
    return [
        f
        for f in files
        if not f.startswith(NON_BEHAVIOR)
        and f not in NON_BEHAVIOR_FILES
        and not f.endswith(".md")
    ]


def declared(body: str) -> str | None:
    """The value of the Requirements field, continuation lines included."""
    lines = body.splitlines()
    for number, line in enumerate(lines):
        match = FIELD.match(line)
        if not match:
            continue
        value = [match.group(1).strip()]
        for following in lines[number + 1 :]:
            if (
                not following.strip()
                or following.startswith("#")
                or NEXT_FIELD.match(following)
            ):
                break
            value.append(following.strip())
        return " ".join(v for v in value if v)
    return None


def owners(root: Path) -> dict[str, str]:
    """Canonical first name → GitHub handle, from the team workflow table."""
    path = root / TEAM
    if not path.is_file():
        return {}
    return {
        name.split()[0]: handle
        for name, handle in TEAM_ROW.findall(path.read_text("utf-8"))
        if name.strip() not in {"Developer", "---"}
    }


def check(
    body: str, files: Iterable[str], index: Index, requirement_owner: dict[str, str]
) -> tuple[list[Finding], list[str]]:
    """(findings, advisory notes) for one pull request."""
    changed = behavior_changing(files)
    if not changed:
        return [], ["no behavior-changing file; no requirement impact needed"]
    value = declared(body)
    if value is None or not value:
        return [
            Finding(
                "TL-13",
                "PR body",
                "behavior-changing PR without a Requirements field "
                "(stable IDs, or NONE — reason)",
            )
        ], []
    ids = sorted(set(REQUIREMENT.findall(value)))
    if not ids:
        if NO_IMPACT.search(value) and len(value) >= MIN_REASON:
            return [], [f"no requirement impact declared: {value}"]
        return [
            Finding(
                "TL-13",
                "PR body",
                "Requirements names no requirement ID and no `NONE — reason`",
            )
        ], []
    findings = [
        Finding(
            "TL-13", requirement, "declared requirement is not an active catalog ID"
        )
        for requirement in ids
        if requirement not in index.requirements
    ]
    by_owner: dict[str, list[str]] = {}
    for requirement in ids:
        owner = requirement_owner.get(requirement)
        if owner:
            by_owner.setdefault(owner, []).append(requirement)
    notes = [f"impacted requirements: {', '.join(ids)}"]
    notes += [
        f"owner {owner}: {', '.join(reqs)}" for owner, reqs in sorted(by_owner.items())
    ]
    return findings, notes
