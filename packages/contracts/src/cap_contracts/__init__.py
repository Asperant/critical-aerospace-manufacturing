"""Integration Contract Registry foundation and compatibility comparison (WP-EVT-001)."""

from .boundary import BoundaryRole, BoundaryValidator, ContractViolation
from .compatibility import (
    CompatibilityResult,
    compare_contracts,
    compare_schema_files,
    compare_schemas,
    enforce_version_policy,
)
from .errors import ContractError
from .registry import (
    ContractDeclaration,
    Deprecation,
    FileRef,
    Registry,
)
from .versioning import ContractVersion, is_successor, parse_contract_id

__all__ = [
    "BoundaryRole",
    "BoundaryValidator",
    "CompatibilityResult",
    "compare_contracts",
    "compare_schemas",
    "compare_schema_files",
    "enforce_version_policy",
    "ContractDeclaration",
    "ContractError",
    "ContractVersion",
    "ContractViolation",
    "Deprecation",
    "FileRef",
    "Registry",
    "is_successor",
    "parse_contract_id",
]
