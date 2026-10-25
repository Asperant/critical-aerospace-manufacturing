"""Boundary validation primitives: check a payload against its declared schema.

The same check serves the producer (before sending) and the consumer (on receipt).
Failures name JSON-pointer paths and schema keywords only, never payload values, so
a violation can be logged safely. Anything that cannot be verified fails closed.
"""

from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

from .errors import ContractError
from .registry import ContractDeclaration, FileRef, load_schema

BoundaryRole = Literal["producer", "consumer"]
_ROLES = ("producer", "consumer")
_MAX_REPORTED = 20


class ContractViolation(ContractError):
    """The payload does not satisfy the contract's schema."""

    def __init__(
        self, contract_id: str, role: str, violations: tuple[str, ...]
    ) -> None:
        super().__init__(
            "SCHEMA_VIOLATION", f"{contract_id} {role}: " + "; ".join(violations)
        )
        self.contract_id = contract_id
        self.role = role
        self.violations = violations


def _check(
    validator: Draft202012Validator, instance: object, contract_id: str, role: str
) -> None:
    if role not in _ROLES:
        raise ContractError(
            "BOUNDARY_ROLE_INVALID", "role must be producer or consumer"
        )
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (list(error.absolute_path), error.validator or ""),
    )
    if errors:
        found = tuple(
            dict.fromkeys(
                f"/{'/'.join(str(part) for part in error.absolute_path)} [{error.validator}]"
                for error in errors
            )
        )
        raise ContractViolation(contract_id, role, found[:_MAX_REPORTED])


class BoundaryValidator:
    """Validators for one registered contract, built from hash-verified schema files."""

    def __init__(
        self,
        declaration: ContractDeclaration,
        repo_root: Path,
        *,
        schema_refs: tuple[FileRef, ...] = (),
    ) -> None:
        self.contract_id = declaration.contract_id
        schema: dict[str, Any] = load_schema(
            declaration.output_schema, repo_root, schema_refs=schema_refs
        )
        self._payload = Draft202012Validator(schema)
        self._request: Draft202012Validator | None = None
        if declaration.input_schema is not None:
            request = load_schema(
                declaration.input_schema, repo_root, schema_refs=schema_refs
            )
            self._request = Draft202012Validator(request)

    def validate(self, instance: object, *, role: str) -> None:
        """Check a payload against the contract's output schema."""
        _check(self._payload, instance, self.contract_id, role)

    def validate_request(self, instance: object, *, role: str) -> None:
        """Check a request against the input schema; a contract without one fails closed."""
        if self._request is None:
            raise ContractError("NO_INPUT_SCHEMA", self.contract_id)
        _check(self._request, instance, self.contract_id, role)
