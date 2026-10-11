from dataclasses import dataclass, field
import re

from ..diagnostics import Diagnostic
from ..enums import Severity
from ..models import CapabilityArea, WorkPackage, resolve_owner
from ..provenance import SourceRef
from .markdown import headings, table_cells

WBS_PATH = "docs/04_Work_Breakdown_Structure.md"
WP_ID = r"WP-[A-Z0-9]+-[0-9]{3}"
AREA = re.compile(r"6\.\d+ (.+) \(`(WP-[A-Z0-9]+)-\*`, (\d+) work packages\)")
LABEL = re.compile(r"^\*\*(.+?)\.\*\*(?: (.*))?$")


@dataclass
class Catalog:
    source_path: str
    work_packages: list[WorkPackage] = field(default_factory=list)
    capability_areas: list[CapabilityArea] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    # Cross-check assertions, not another catalog.
    area_rows: list[tuple[list[str], SourceRef]] = field(default_factory=list)
    dor_ids: set[str] = field(default_factory=set)
    dod_ids: set[str] = field(default_factory=set)
    schedule: object | None = None
    dependencies: object | None = None


def references(value: str | None, pattern: str) -> list[str] | None:
    if value is None:
        return None
    return sorted(set(re.findall(r"(?<![A-Z0-9-])" + pattern + r"(?![A-Z0-9-])", value)))


def criteria(value: str | None, prefix: str) -> list[str] | None:
    if value is None:
        return None
    match = re.search(rf"{prefix}-WP-(\d{{2}})([^.;]*)", value)
    if not match:
        return []
    numbers = [int(match[1])]
    tail = match[2]
    for token in re.finditer(r"(…|–|,\s*)(\d{2})", tail):
        last = int(token[2])
        if token[1] in {"…", "–"}:
            numbers.extend(range(numbers[-1] + 1, last + 1))
        else:
            numbers.append(last)
    return [f"{prefix}-WP-{n:02d}" for n in sorted(set(numbers))]


def parse_wbs(text: str, source_path: str = WBS_PATH) -> Catalog:
    catalog = Catalog(source_path)
    lines = text.splitlines()
    scanned = headings(text)

    def source(h) -> SourceRef:
        return SourceRef(path=source_path, heading=h.title, line_start=h.line,
                         line_end=h.end, raw_context="\n".join(lines[h.line - 1:h.end]))

    def error(code: str, message: str, ref: SourceRef, record: str | None = None):
        catalog.diagnostics.append(Diagnostic(code=code, severity=Severity.ERROR,
                                             message=message, source=ref, record_id=record))

    sections = [h for h in scanned if h.level == 2 and h.title == "6. Capability Areas and Work Packages"]
    if len(sections) != 1:
        catalog.diagnostics.append(Diagnostic(code="WBS_SECTION", severity=Severity.ERROR,
                                             message="Expected exactly one WBS section 6."))
        return catalog
    section = sections[0]
    current: CapabilityArea | None = None
    for h in scanned:
        if not section.line < h.line <= section.end:
            continue
        if h.level == 3:
            current = None
            match = AREA.fullmatch(h.title)
            if not match:
                error("AREA_HEADING", "Unsupported capability heading grammar.", source(h))
                continue
            current = CapabilityArea(id=match[2], title=match[1], declared_wp_count=int(match[3]),
                                     provenance=source(h))
            catalog.capability_areas.append(current)
            # The area index ends at its first WP card.
            end = next((x.line - 1 for x in scanned if x.line > h.line and x.level == 4), h.end)
            for number in range(h.line, min(end, h.end)):
                row = table_cells(lines[number])
                if row and row[0].startswith("WP-"):
                    ref = SourceRef(path=source_path, heading=h.title, line_start=number + 1,
                                    line_end=number + 1, raw_context=lines[number])
                    catalog.area_rows.append((row, ref))
        elif h.level == 4:
            match = re.fullmatch(r"(\S+) — (.+)", h.title)
            if not match or not re.fullmatch(WP_ID, match[1]):
                error("WP_ID_SYNTAX", "Expected a complete WP ID and em-dash title.", source(h))
                continue
            wp_id, title = match.groups()
            ref = source(h)
            fields: dict[str, str] = {}
            labeled: dict[str, str] = {}
            active: str | None = None
            for line in lines[h.line:h.end]:
                label = LABEL.fullmatch(line)
                if label:
                    active = label[1]
                    if active in labeled:
                        error("DUPLICATE_FIELD", f"Repeated label: {active}", ref, wp_id)
                    labeled[active] = label[2] or ""
                elif active:
                    labeled[active] += "\n" + line
                else:
                    row = table_cells(line)
                    if row and len(row) == 2 and row[0] not in {"Field", "---"}:
                        if row[0] in fields:
                            error("DUPLICATE_FIELD", f"Repeated field: {row[0]}", ref, wp_id)
                        fields[row[0]] = row[1]
            labeled = {k: v.strip() for k, v in labeled.items()}
            supported_fields = {
                "PrimaryOwner", "Supporting owner (most frequent reviewer)", "ScopeClass",
                "Target milestone / sprint window", "Readiness node (05)",
                "Size band (indicative, no hour estimates)", "Status", "Repository reference",
            }
            supported_labels = {
                "Purpose", "Source requirements (03)", "Architecture components (02)",
                "Inputs / required contracts", "Deliverables", "Major tasks",
                "Verification work (03 planned families)", "Expected evidence artifact",
                "Risk hooks (Item 69)", "DoR / DoD", "Cut / fallback semantics", "Integration checkpoint",
            }
            for name in sorted(set(fields) - supported_fields):
                error("UNSUPPORTED_FIELD", f"Unsupported card field: {name}", ref, wp_id)
            for name in sorted(set(labeled) - supported_labels):
                error("UNSUPPORTED_FIELD", f"Unsupported card label: {name}", ref, wp_id)
            scope = fields.get("ScopeClass")
            sm = re.fullmatch(r"(F0|F1|R1|R2|S|X)(?: \(NFR class (H0|A1|S2|C3)\))?", scope or "")
            if scope and not sm:
                error("SCOPE_SYNTAX", f"Unsupported ScopeClass: {scope}", ref, wp_id)
            window = fields.get("Target milestone / sprint window")
            milestone = sprint = None
            if window:
                pieces = window.split(" / ")
                if len(pieces) != 2:
                    error("PLANNING_WINDOW", "Expected milestone / sprint window.", ref, wp_id)
                else:
                    milestone = None if pieces[0] == "—" else pieces[0]
                    sprint = pieces[1]
            owner = fields.get("PrimaryOwner")
            reviewer = fields.get("Supporting owner (most frequent reviewer)")
            def bullets(name):
                value = labeled.get(name)
                if value is None:
                    return None
                for item in value.splitlines():
                    if item.strip() and not item.startswith("- "):
                        error("LIST_SYNTAX", f"Expected bullet list for {name}.", ref, wp_id)
                return [x[2:] for x in value.splitlines() if x.startswith("- ")]
            raw_rules = labeled.get("DoR / DoD")
            def typed_refs(value, pattern, code):
                if value is not None and value != "—":
                    for token in value.split(","):
                        if not re.fullmatch(pattern, token.strip()):
                            error(code, f"Invalid reference: {token.strip()}", ref, wp_id)
                return references(value, pattern)
            catalog.work_packages.append(WorkPackage(
                id=wp_id, title=title, capability_area=current.id if current else None,
                primary_owner=resolve_owner(owner) if owner else None,
                supporting_reviewers=[resolve_owner(x.strip()) for x in reviewer.split(",")] if reviewer else None,
                purpose=labeled.get("Purpose"), scope_class=sm[1] if sm else None,
                nfr_class=sm[2] if sm else None, raw_scope=scope,
                requirement_refs=typed_refs(labeled.get("Source requirements (03)"), r"(?:FR|NFR)-[A-Z]+-\d{3}", "REQUIREMENT_SYNTAX"),
                architecture_refs=typed_refs(labeled.get("Architecture components (02)"), r"ARCH-[A-Z0-9]+-[A-Z0-9-]+", "ARCHITECTURE_SYNTAX"),
                readiness_refs=typed_refs(fields.get("Readiness node (05)"), r"(?:DN|MS|CK)-[A-Z0-9-]+", "READINESS_SYNTAX"),
                dependency_refs=references(labeled.get("Inputs / required contracts"), r"DEP-\d{3}"),
                inputs_required_contracts=labeled.get("Inputs / required contracts"),
                deliverables=bullets("Deliverables"), major_tasks=bullets("Major tasks"),
                verification_expectations=labeled.get("Verification work (03 planned families)"),
                evidence_expectations=labeled.get("Expected evidence artifact"),
                milestone=milestone, sprint_window=sprint, raw_planning_window=window,
                dor_refs=criteria(raw_rules, "DOR"), dod_refs=criteria(raw_rules, "DOD"), raw_dor_dod=raw_rules,
                cut_fallback=labeled.get("Cut / fallback semantics"), raw_planning_status=fields.get("Status"),
                size_band=fields.get("Size band (indicative, no hour estimates)"),
                repository_reference=fields.get("Repository reference"), risk_hooks=labeled.get("Risk hooks (Item 69)"),
                integration_checkpoint=labeled.get("Integration checkpoint"), provenance=ref,
            ))
    # Definitions only, not mentions or mirrored compatibility tables.
    for h in scanned:
        if h.level == 3 and h.title.startswith(("4.1 DoR", "4.2 DoD")):
            for line in lines[h.line:h.end]:
                row = table_cells(line)
                if row and re.fullmatch(r"DOR-WP-\d{2}", row[0]):
                    catalog.dor_ids.add(row[0])
                elif row and re.fullmatch(r"DOD-WP-\d{2}", row[0]):
                    catalog.dod_ids.add(row[0])
    catalog.work_packages.sort(key=lambda wp: wp.id)
    catalog.capability_areas.sort(key=lambda area: area.id)
    return catalog
