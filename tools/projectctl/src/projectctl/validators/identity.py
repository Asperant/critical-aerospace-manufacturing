from collections import Counter
import re

from ..diagnostics import Diagnostic
from ..enums import Severity
from ..parsers.wbs import Catalog, WP_ID


def validate_identity(catalog: Catalog) -> list[Diagnostic]:
    diagnostics = []
    counts = Counter(wp.id for wp in catalog.work_packages)
    for wp in catalog.work_packages:
        for code, condition, message in [
            ("WP_ID_SYNTAX", not re.fullmatch(WP_ID, wp.id), "Invalid complete WP ID."),
            ("DUPLICATE_WP", counts[wp.id] > 1, "WP ID has multiple definitions."),
            ("OWNER_UNRESOLVED", wp.primary_owner is None or wp.primary_owner.canonical_name is None,
             "Primary owner is missing or unknown."),
            ("REVIEWER_UNRESOLVED", any(o.canonical_name is None for o in wp.supporting_reviewers or []),
             "Supporting reviewer is unknown."),
        ]:
            if condition:
                diagnostics.append(Diagnostic(code=code, severity=Severity.ERROR, message=message,
                                              record_id=wp.id, source=wp.provenance))
    return diagnostics
