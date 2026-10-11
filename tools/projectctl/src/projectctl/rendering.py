from collections import Counter
import json

from rich.console import Console

from .diagnostics import Diagnostic, ordered
from .enums import Severity
from .parsers.wbs import Catalog


def summary(catalog: Catalog, diagnostics: list[Diagnostic]) -> dict:
    return {
        "source": catalog.source_path,
        "parser": "canonical-wbs-v1",
        "execution_status": "UNAVAILABLE (documentation only)",
        "wp_count": len({wp.id for wp in catalog.work_packages}),
        "owner_distribution": dict(sorted(Counter(
            wp.primary_owner.canonical_name or "UNRESOLVED"
            for wp in catalog.work_packages if wp.primary_owner
        ).items())),
        "capability_count": len({area.id for area in catalog.capability_areas}),
        "validation": "FAIL" if any(d.severity == Severity.ERROR for d in diagnostics) else "PASS",
        "diagnostics": [d.model_dump(mode="json") for d in ordered(diagnostics)],
    }


def emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


def emit_summary(payload: dict) -> None:
    console = Console(highlight=False, markup=False)
    for key, value in payload.items():
        if key != "diagnostics":
            console.print(f"{key}: {value}")
    for diagnostic in payload["diagnostics"]:
        console.print(f"{diagnostic['severity']} {diagnostic['code']}: {diagnostic['message']}")
