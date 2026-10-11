from collections import Counter
import re

from ..diagnostics import Diagnostic
from ..enums import Severity
from ..models import resolve_owner


def validate_requirements(wbs, catalog):
    diagnostics = []
    def issue(code, message, source=None, identity=None, severity=Severity.ERROR):
        diagnostics.append(Diagnostic(code=code, severity=severity, message=message, source=source, record_id=identity))
    records = {r.id: r for r in catalog.requirements}
    counts = Counter(r.id for r in catalog.requirements)
    if len(records) != 306 or len(catalog.requirements) != 306:
        issue("REQUIREMENT_COUNT", f"Expected 306 unique requirements; observed {len(records)} unique / {len(catalog.requirements)} records")
    for identity, count in counts.items():
        if count != 1:
            issue("DUPLICATE_REQUIREMENT", "Duplicate canonical definition", identity=identity)
    kinds = Counter(r.kind.value for r in catalog.requirements)
    if kinds != {"FR": 186, "NFR": 120}:
        issue("REQUIREMENT_KINDS", f"Expected FR 186 / NFR 120; observed {dict(kinds)}")
    fr_classes = Counter(r.scope_class.value for r in catalog.requirements if r.scope_class)
    nfr_classes = Counter(r.quality_class.value for r in catalog.requirements if r.quality_class)
    if fr_classes != {"F0": 17, "F1": 159, "R1": 10}:
        issue("FR_CLASSES", str(dict(fr_classes)))
    if nfr_classes != {"H0": 52, "A1": 41, "S2": 23, "C3": 4}:
        issue("NFR_CLASSES", str(dict(nfr_classes)))
    for requirement in catalog.requirements:
        if not re.fullmatch(r"(?:FR|NFR)-[A-Z]+-\d{3}", requirement.id):
            issue("REQUIREMENT_ID", "Malformed identity", requirement.provenance, requirement.id)
        if requirement.primary_owner.canonical_name is None:
            issue("REQUIREMENT_OWNER", "Unknown canonical owner", requirement.provenance, requirement.id)
        if requirement.revision is None or requirement.catalog_status is None:
            issue("REQUIREMENT_FIELDS_MISSING", "Canonical per-record revision/status absent; no defaults assigned", requirement.provenance, requirement.id, Severity.WARNING)
        if requirement.kind == "NFR" and requirement.verification_codes is None:
            issue("NFR_METADATA_MISSING", "Structured canonical measurement/verification/evidence fields absent; RTM remains a projection", requirement.provenance, requirement.id, Severity.WARNING)
    for wp in wbs.work_packages:
        for identity in wp.requirement_refs or []:
            if identity not in records:
                issue("WBS_REQUIREMENT_REFERENCE", f"Unknown requirement: {identity}", wp.provenance, wp.id)
    if Counter(t.requirement_id for t in catalog.traces) != counts:
        issue("TRACE_IDENTITIES", "Trace identities must equal the canonical requirement multiset")
    if Counter(r[0] for r in catalog.index_assertions) != counts:
        issue("RTM_INDEX_IDENTITIES", "RTM View A identities differ from canonical catalog")
    for trace in catalog.traces:
        requirement = records.get(trace.requirement_id)
        if requirement is None:
            continue
        meta = trace.assertions.get("meta", {})
        expected_class = requirement.scope_class or requirement.quality_class
        if meta.get("class") != expected_class or resolve_owner(meta.get("owner", "")).canonical_name != requirement.primary_owner.canonical_name:
            issue("TRACE_META_CONFLICT", "RTM class/owner disagrees with 01", trace.provenance, requirement.id)
        line = re.search(r"\bL(\d+)\b", meta.get("anchor", ""))
        if line and (int(line[1]) > len(catalog.master_lines) or requirement.id not in catalog.master_lines[int(line[1]) - 1]):
            issue("STALE_CITATION", f"RTM anchor {meta['anchor']} does not point to {requirement.id}; stable identity retained", trace.provenance, requirement.id, Severity.WARNING)
    for row in catalog.index_assertions:
        requirement = records.get(row[0])
        if requirement and (row[1] != (requirement.scope_class or requirement.quality_class) or resolve_owner(row[2]).canonical_name != requirement.primary_owner.canonical_name):
            issue("RTM_INDEX_CONFLICT", "View A class/owner differs from 01", identity=row[0])
    return diagnostics
