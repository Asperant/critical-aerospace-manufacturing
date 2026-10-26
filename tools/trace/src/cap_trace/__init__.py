"""cap-trace: machine-readable trace registry and trace linter (WP-GOV-002)."""

from .drift import Drift, compare
from .lint import RegistryError, lint, lint_files
from .model import APPLICABILITY, RELATIONS, SCHEMA_ID, Edge, Finding
from .references import coverage, resolve
from .seed import SeedError, build, dump, parse_records, repo_paths
from .sources import Index, tokens

__all__ = [
    "APPLICABILITY",
    "RELATIONS",
    "SCHEMA_ID",
    "Drift",
    "Edge",
    "Finding",
    "RegistryError",
    "SeedError",
    "Index",
    "build",
    "compare",
    "coverage",
    "dump",
    "lint",
    "lint_files",
    "parse_records",
    "repo_paths",
    "resolve",
    "tokens",
]
