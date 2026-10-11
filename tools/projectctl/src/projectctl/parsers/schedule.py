from pathlib import Path
import re

from ..models import resolve_owner
from ..provenance import SourceRef
from ..schedule_models import Cycle, Milestone, ScheduleProjection
from .markdown import headings, table_cells

PLAN_PATH = "docs/07_Milestone_and_Release_Plan.md"
MASTER_PATH = "docs/01_Master_Project_Specification.md"
ROADMAPS = {
    "Asrın": "docs/06A_Asrin_Engineering_Roadmap.md",
    "Selman": "docs/06B_Selman_Engineering_Roadmap.md",
    "Batu": "docs/06C_Batu_Engineering_Roadmap.md",
    "Yavuz": "docs/06D_Yavuz_Engineering_Roadmap.md",
}


def block(text, path, heading):
    lines = text.splitlines()
    raw = "\n".join(lines[heading.line - 1:heading.end])
    return raw, SourceRef(path=path, heading=heading.title, line_start=heading.line,
                          line_end=heading.end, raw_context=raw)


def rows(text):
    return [row for line in text.splitlines() if (row := table_cells(line))]


def unique_section(text, title):
    matches = [h for h in headings(text) if h.level == 2 and h.title == title]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one section: {title}")
    return block(text, "", matches[0])[0]


def parse_schedule(plan: str, roadmaps: dict[str, str], master: str) -> ScheduleProjection:
    cycles, milestones, provenance = [], [], []
    for h in headings(plan):
        if h.level != 3:
            continue
        if h.title.startswith("6.S"):
            match = re.fullmatch(r"6\.(S\d+) Sprint \d+ — (.+) \(.*ends W(\d+)\)", h.title)
            if not match:
                raise ValueError(f"Unsupported cycle heading: {h.title}")
            raw, ref = block(plan, PLAN_PATH, h)
            fields = {r[0]: r[1] for r in rows(raw) if len(r) == 2}
            cycles.append(Cycle(id=match[1], title=match[2], effective_week_end=int(match[3]),
                                goal=fields.get("Sprint goal"), work_package_ids=[r[0] for r in rows(raw) if r[0].startswith("WP-")],
                                provenance=ref))
        elif h.title.startswith("5.M"):
            match = re.fullmatch(r"5\.(M\d+) M\d+ — (.+)", h.title)
            if not match:
                raise ValueError(f"Unsupported milestone heading: {h.title}")
            raw, ref = block(plan, PLAN_PATH, h)
            fields = {r[0]: r[1] for r in rows(raw) if len(r) == 2}
            target = re.fullmatch(r"End (S\d+) / effective W(\d+)", fields.get("Target", ""))
            if target is None:
                raise ValueError(f"Unsupported milestone target: {fields.get('Target')}")
            milestones.append(Milestone(id=match[1], title=match[2], target_cycle=target[1],
                                        effective_week_end=int(target[2]), raw_planning_status=fields.get("Status"),
                                        work_package_ids=[r[0] for r in rows(raw) if r[0].startswith("WP-")], provenance=ref))
    owners = {}
    memberships = {}
    for alias, text in roadmaps.items():
        path = ROADMAPS[alias]
        owner = resolve_owner(alias).canonical_name
        owners[owner] = [m[1] for m in re.finditer(r"^### 9\.(WP-[A-Z0-9]+-\d{3}) —", text, re.M)]
        for row in rows(unique_section(text, "10. Sprint-Level Execution Projection")):
            if re.fullmatch(r"S\d+", row[0]):
                memberships.setdefault(row[0], []).extend(re.findall(r"\bWP-[A-Z0-9]+-\d{3}\b", row[2]))
        for h in headings(text):
            if h.level == 2 and h.title in {"9. Work Package Mapping", "10. Sprint-Level Execution Projection"}:
                provenance.append(block(text, path, h)[1])
    cadence = [r[1] for r in rows(unique_section(plan, "3. Planning Baseline: Horizon, Cadence, Capacity")) if r[0] == "Cadence"]
    if len(cadence) != 1 or not re.fullmatch(r"13 × \d+-week sprints", cadence[0]):
        raise ValueError("Unsupported or duplicate cadence declaration in 07")
    weeks = int(re.search(r"(\d+)-week", cadence[0])[1])
    # Verify the upstream declaration, never use 07 to override 01.
    item = re.search(r"^# 65 — Sprint / Milestone Plan\n(.*?)^# 66 —", master, re.M | re.S)
    if item is None or f"13 × {weeks}-week sprint" not in item[1]:
        raise ValueError("01 Item 65 and 07 cadence declarations disagree")
    return ScheduleProjection(cycles=sorted(cycles, key=lambda c: int(c.id[1:])),
                              milestones=sorted(milestones, key=lambda m: m.id), effective_weeks_per_cycle=weeks,
                              roadmap_owner_ids=owners, roadmap_cycle_ids=memberships, provenance=provenance)


def load_schedule(root: Path):
    return parse_schedule((root / PLAN_PATH).read_text(), {owner: (root / path).read_text() for owner, path in ROADMAPS.items()},
                          (root / MASTER_PATH).read_text())
