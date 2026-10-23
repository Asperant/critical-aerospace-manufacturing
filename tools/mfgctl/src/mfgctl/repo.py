"""Repository root discovery with explicit, inspectable precedence (DX-INV-10).

1. ``MFGCTL_REPO_ROOT`` if set: it must point at the repository root, otherwise
   discovery fails instead of silently falling back.
2. Otherwise the current directory and its parents are searched.

The markers match projectctl's root discovery so both tools agree on the root.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

ENV_ROOT = "MFGCTL_REPO_ROOT"
MARKERS = ("AGENTS.md", "docs/04_Work_Breakdown_Structure.md")


class RepoNotFoundError(Exception):
    """The repository root could not be determined."""


def is_repo_root(path: Path) -> bool:
    return all((path / marker).is_file() for marker in MARKERS)


def find_repo_root(start: Path, environ: Mapping[str, str]) -> Path:
    override = environ.get(ENV_ROOT)
    if override:
        root = Path(override).expanduser().resolve()
        if not is_repo_root(root):
            raise RepoNotFoundError(
                f"{ENV_ROOT}={override} is not the repository root "
                f"(expected {' and '.join(MARKERS)})"
            )
        return root
    start = start.resolve()
    for candidate in (start, *start.parents):
        if is_repo_root(candidate):
            return candidate
    raise RepoNotFoundError(
        f"no repository root above {start}; run mfgctl inside the repository "
        f"or set {ENV_ROOT}"
    )
