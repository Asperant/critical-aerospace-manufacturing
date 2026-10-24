"""Integration Contract Registry foundation (WP-EVT-001 slice 1)."""

from .boundary import BoundaryRole, BoundaryValidator, ContractViolation
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
