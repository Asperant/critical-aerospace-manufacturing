from collections import Counter
import re

from ..diagnostics import Diagnostic, ordered
from ..enums import Severity, ScopeClass
from ..parsers.wbs import AREA, Catalog, WP_ID
from .identity import validate_identity

EXPECTED_OWNERS = {"Asrın Dündar": 74, "Selman Özdemir": 17, "Batuhan Kaya": 32, "Yavuz Gümüş": 57}


def validate(catalog: Catalog) -> list[Diagnostic]:
    diagnostics = list(catalog.diagnostics) + validate_identity(catalog)

    def error(code, message, record=None, source=None):
        diagnostics.append(Diagnostic(code=code, severity=Severity.ERROR, message=message,
                                      record_id=record, source=source))

    ids = {wp.id for wp in catalog.work_packages}
    if len(ids) != 180:
        error("WP_COUNT", f"Expected 180 unique WPs; observed {len(ids)}.")
    owners = Counter(wp.primary_owner.canonical_name for wp in catalog.work_packages if wp.primary_owner)
    if dict(owners) != EXPECTED_OWNERS:
        error("OWNER_DISTRIBUTION", f"Expected {EXPECTED_OWNERS}; observed {dict(sorted(owners.items(), key=lambda x: x[0] or ''))}.")
    areas = Counter(a.id for a in catalog.capability_areas)
    if len(areas) != 29:
        error("AREA_COUNT", f"Expected 29 capability areas; observed {len(areas)}.")
    for a in catalog.capability_areas:
        if areas[a.id] > 1:
            error("DUPLICATE_AREA", "Capability area has multiple definitions.", a.id, a.provenance)
        observed = sum(wp.capability_area == a.id for wp in catalog.work_packages)
        if observed != a.declared_wp_count:
            error("AREA_MEMBER_COUNT", f"Heading declares {a.declared_wp_count}; observed {observed}.", a.id, a.provenance)
    indexed = Counter()
    for row, source in catalog.area_rows:
        if len(row) != 6 or not re.fullmatch(WP_ID, row[0]):
            error("AREA_INDEX_SYNTAX", "Expected six cells and a complete WP ID.", row[0], source)
            continue
        indexed[row[0]] += 1
        matches = [wp for wp in catalog.work_packages if wp.id == row[0]]
        if len(matches) != 1:
            error("AREA_INDEX_REFERENCE", "Area index must resolve to exactly one WP card.", row[0], source)
            continue
        wp = matches[0]
        index_scope = wp.scope_class
        if wp.nfr_class:
            index_scope = f"{wp.scope_class} / {wp.nfr_class}"
        expected = [wp.id, wp.title, wp.primary_owner.source_spelling if wp.primary_owner else None,
                    index_scope, wp.milestone or "—", (wp.size_band or "").split(" ")[0]]
        if row != expected:
            error("AREA_INDEX_CONFLICT", "Area index disagrees with WP card fields.", wp.id, source)
        enclosing = AREA.fullmatch(source.heading)
        if enclosing is None or enclosing[2] != wp.capability_area:
            error("AREA_INDEX_MEMBERSHIP", "Index row is outside the WP's capability area.", wp.id, source)
    for wp in catalog.work_packages:
        if wp.capability_area not in areas or wp.capability_area != wp.id.rsplit("-", 1)[0]:
            error("AREA_MEMBERSHIP", "WP prefix must match its enclosing capability area.", wp.id, wp.provenance)
        if indexed[wp.id] != 1:
            error("AREA_INDEX_MEMBERSHIP", "WP must occur exactly once in its area index.", wp.id, wp.provenance)
        if wp.scope_class not in set(ScopeClass):
            error("SCOPE_CLASS", "Scope class is missing or invalid.", wp.id, wp.provenance)
        for refs, known, code in [(wp.dor_refs, catalog.dor_ids, "DOR_REFERENCE"),
                                  (wp.dod_refs, catalog.dod_ids, "DOD_REFERENCE")]:
            if refs is None or not refs or set(refs) - known:
                error(code, "Criterion references must resolve to WBS section 4 definitions.", wp.id, wp.provenance)
        if wp.milestone is not None and not re.fullmatch(r"M[0-8]", wp.milestone):
            error("MILESTONE_SYNTAX", "Invalid milestone reference syntax.", wp.id, wp.provenance)
        # Other documents' ID existence is deliberately outside this increment.
        for refs, pattern, code in [
            (wp.requirement_refs, r"(?:FR|NFR)-[A-Z]+-\d{3}", "REQUIREMENT_SYNTAX"),
            (wp.dependency_refs, r"DEP-\d{3}", "DEPENDENCY_SYNTAX"),
        ]:
            if any(not re.fullmatch(pattern, ref) for ref in refs or []):
                error(code, "Invalid reference syntax.", wp.id, wp.provenance)
    return ordered(diagnostics)
