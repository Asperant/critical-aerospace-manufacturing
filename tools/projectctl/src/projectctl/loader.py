from pathlib import Path

from .parsers.wbs import Catalog, WBS_PATH, parse_wbs


def find_root(start: Path) -> Path:
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / WBS_PATH).is_file():
            return candidate
    raise ValueError("Repository root not found; use --root.")


def load(root: Path) -> Catalog:
    from .parsers.schedule import load_schedule
    from .diagnostics import Diagnostic
    from .enums import Severity
    catalog = parse_wbs((root / WBS_PATH).read_text(encoding="utf-8"), WBS_PATH)
    try:
        catalog.schedule = load_schedule(root)
    except (OSError, ValueError) as exc:
        catalog.diagnostics.append(Diagnostic(code="SCHEDULE_INPUT", severity=Severity.ERROR, message=str(exc)))
    return catalog
