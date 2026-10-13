from dataclasses import dataclass, field
import re

from ..models import resolve_owner, Owner
from ..provenance import SourceRef
from ..requirement_models import Requirement, TraceOverlay
from .markdown import table_cells
from .yaml_blocks import records

MASTER = "docs/01_Master_Project_Specification.md"
RTM = "docs/03_Requirements_Traceability_Matrix.md"


@dataclass
class RequirementCatalog:
    requirements: list[Requirement] = field(default_factory=list)
    traces: list[TraceOverlay] = field(default_factory=list)
    index_assertions: list[list[str]] = field(default_factory=list)
    master_lines: list[str] = field(default_factory=list)


def item_region(text, number, next_number):
    matches = list(re.finditer(rf"^# {number} — .+$", text, re.M))
    ends = list(re.finditer(rf"^# {next_number} — .+$", text, re.M))
    if len(matches) != 1 or len(ends) != 1 or ends[0].start() <= matches[0].start():
        raise ValueError(f"Cannot uniquely locate Item {number}")
    return matches[0].start(), ends[0].start()


def parse_requirements(master, rtm):
    catalog = RequirementCatalog(master_lines=master.splitlines())
    start, end = item_region(master, 81, 82)
    base_line = master[:start].count("\n") + 1
    for offset, line in enumerate(master[start:end].splitlines()):
        row = table_cells(line)
        if not row or not row[0].startswith("FR-"):
            continue
        if len(row) != 6 or not re.fullmatch(r"FR-[A-Z]+-\d{3}", row[0]):
            raise ValueError(f"Malformed canonical FR row: {line}")
        number = base_line + offset
        ref = SourceRef(path=MASTER, heading=f"Item 81 / {row[0]}", line_start=number, line_end=number, raw_context=line)
        catalog.requirements.append(Requirement(id=row[0], kind="FR", title=None, statement=row[3], scope_class=row[1], quality_class=None,
                                                primary_owner=resolve_owner(row[2]), verification_codes=row[4].split("/"), evidence_codes=row[5].split("/"), provenance=ref))
    start, end = item_region(master, 82, 83)
    base_line = master[:start].count("\n") + 1
    region = master[start:end]
    for match in re.finditer(r"^## (NFR-[A-Z]+-\d{3}) — (.+)$", region, re.M):
        tail = region[match.end():]
        boundary = re.search(r"^#{1,2} ", tail, re.M)
        stop = match.end() + boundary.start() if boundary else len(region)
        raw = region[match.start():stop].rstrip()
        class_match = re.search(r"^\*\*Class:\*\* (.+)$", raw, re.M)
        owner_match = re.search(r"^\*\*Owner:\*\* (.+)$", raw, re.M)
        if class_match is None or owner_match is None:
            raise ValueError(f"Missing Class/Owner on {match[1]}")
        raw_owner = owner_match[1]
        primary_match = re.search(r"\bPrimaryOwner (Asrın|Selman|Batu|Yavuz)\b", raw_owner)
        owner = resolve_owner(primary_match[1] if primary_match else raw_owner)
        owner = Owner(source_spelling=raw_owner, canonical_name=owner.canonical_name)
        statement = re.sub(r"^\*\*(?:Class|Owner):\*\* .+\n?", "", raw.split("\n", 1)[1], flags=re.M).strip().removesuffix("---").rstrip()
        number = base_line + region[:match.start()].count("\n")
        catalog.requirements.append(Requirement(id=match[1], kind="NFR", title=match[2], statement=statement,
                                                scope_class=None, quality_class=class_match[1], primary_owner=owner,
                                                verification_codes=None, evidence_codes=None,
                                                provenance=SourceRef(path=MASTER, heading=f"Item 82 / {match[1]}", line_start=number,
                                                                     line_end=number + len(raw.splitlines()) - 1, raw_context=raw)))
    for key, value, ref in records(rtm, RTM, "## 17. Requirement Trace Records", "## 18. Machine-Readable"):
        catalog.traces.append(TraceOverlay(requirement_id=key, assertions=value, provenance=ref))
    region = rtm[rtm.index("## 6. View A"):rtm.index("## 7. View B")]
    catalog.index_assertions = [r for line in region.splitlines() if (r := table_cells(line)) and r[0].startswith(("FR-", "NFR-"))]
    catalog.requirements.sort(key=lambda r: r.id)
    catalog.traces.sort(key=lambda t: t.requirement_id)
    return catalog
