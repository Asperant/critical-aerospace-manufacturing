"""Contract identity and version rules.

A contract ID is ``<family>.v<major>``, for example ``core.order-query.v1``. A
breaking change (02 "Contract Versioning and Compatibility") is expressed only as a new
major, that is a new contract ID; the previous major is deprecated, never edited in
place. Deciding whether a concrete schema change is breaking belongs to the
pure comparison functions in ``compatibility``; this module only handles IDs.
"""

import re
from dataclasses import dataclass

from .errors import ContractError

_CONTRACT_ID = re.compile(
    r"^(?P<family>[a-z][a-z0-9]*(?:\.[a-z][a-z0-9-]*)+)\.v(?P<major>[1-9][0-9]*)$"
)


@dataclass(frozen=True)
class ContractVersion:
    family: str
    major: int

    @property
    def contract_id(self) -> str:
        return f"{self.family}.v{self.major}"


def parse_contract_id(value: object) -> ContractVersion:
    """Parse a contract ID; anything that is not a canonical ID is rejected."""
    if not isinstance(value, str):
        raise ContractError("CONTRACT_ID_INVALID", "contract ID must be a string")
    match = _CONTRACT_ID.fullmatch(value)
    if match is None:
        raise ContractError(
            "CONTRACT_ID_INVALID",
            "expected <family>.v<major>, lower-case, no leading zero",
        )
    return ContractVersion(match["family"], int(match["major"]))


def is_successor(older: ContractVersion, newer: ContractVersion) -> bool:
    """``newer`` is the next major of the same family; skipped majors are not allowed."""
    return newer.family == older.family and newer.major == older.major + 1


def is_later_major(older: ContractVersion, newer: ContractVersion) -> bool:
    """Same family, higher major; the rule for naming a deprecation replacement."""
    return newer.family == older.family and newer.major > older.major
