from pathlib import Path

from .parsers.wbs import Catalog, WBS_PATH, parse_wbs


def find_root(start: Path) -> Path:
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / "AGENTS.md").is_file() and (candidate / WBS_PATH).is_file():
            return candidate
    raise ValueError("Repository root not found; use --root.")


def load(root: Path) -> Catalog:
    return parse_wbs((root / WBS_PATH).read_text(encoding="utf-8"), WBS_PATH)
