"""cap-trace: machine-readable trace registry and trace linter (WP-GOV-002)."""

from .drift import Drift, compare
from .lint import Finding, RegistryError, lint, lint_files
from .model import APPLICABILITY, RELATIONS, SCHEMA_ID, Edge
from .seed import SeedError, build, dump, parse_records, repo_paths

__all__ = [
    "APPLICABILITY",
    "RELATIONS",
    "SCHEMA_ID",
    "Drift",
    "Edge",
    "Finding",
    "RegistryError",
    "SeedError",
    "build",
    "compare",
    "dump",
    "lint",
    "lint_files",
    "parse_records",
    "repo_paths",
]
