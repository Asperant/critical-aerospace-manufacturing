"""Git-backed Integration Contract Registry: layout, declarations and verification.

Layout: one JSON declaration per contract version in a registry directory, named
``<contract_id>.json``. A declaration carries a subset of the registry fields of the
02 architecture specification and points at schema and fixture files by repository
path plus SHA-256, so the producer's files stay where the producer owns them and any
drift from what was registered is detected. This is a semantic governance catalog,
not a runtime schema registry.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jsonschema import Draft202012Validator

from .errors import ContractError
from .references import resolve_references
from .versioning import ContractVersion, is_later_major, parse_contract_id

if TYPE_CHECKING:
    from .authority import ProducerAuthorities

CONTRACT_TYPES = frozenset(
    {"QUERY", "COMMAND", "EVENT", "SNAPSHOT", "ARTIFACT", "HEALTH"}
)
SYNC_SEMANTICS = frozenset({"SYNC", "ASYNC"})
DEPRECATION_STATUSES = frozenset({"ACTIVE", "DEPRECATED"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED: tuple[str, ...] = (
    "contract_id",
    "name",
    "contract_type",
    "version",
    "semantic_owner",
    "canonical_producer",
    "declared_consumers",
    "purpose",
    "output_schema",
    "fixtures",
    "authority_level",
    "sync_semantics",
    "security_classification",
    "deprecation",
)
_OPTIONAL: tuple[str, ...] = ("input_schema", "semantics")


def _text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ContractError(
            "FIELD_INVALID", f"{key} must be a non-blank trimmed string"
        )
    return value


@dataclass(frozen=True)
class FileRef:
    """Repository-relative path of a producer-owned file and its SHA-256."""

    path: str
    sha256: str

    @staticmethod
    def from_value(value: object, where: str) -> "FileRef":
        if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
            raise ContractError("FILE_REF_INVALID", f"{where} must be {{path, sha256}}")
        path, digest = value["path"], value["sha256"]
        parts = path.split("/") if isinstance(path, str) else []
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or "\\" in path
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ContractError(
                "FILE_REF_INVALID", f"{where} path must be repository-relative"
            )
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ContractError(
                "FILE_REF_INVALID", f"{where} sha256 must be 64 lower-case hex"
            )
        return FileRef(path, digest)

    def read(self, repo_root: Path) -> bytes:
        """Read the file, requiring it to be inside ``repo_root`` and to match the hash."""
        root = repo_root.resolve()
        target = (root / self.path).resolve()
        if root not in target.parents:
            raise ContractError("FILE_REF_ESCAPES_ROOT", self.path)
        try:
            raw = target.read_bytes()
        except OSError:
            raise ContractError("FILE_MISSING", self.path) from None
        if hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ContractError(
                "SCHEMA_DRIFT", f"{self.path} differs from the registered hash"
            )
        return raw


@dataclass(frozen=True)
class Deprecation:
    status: str
    replacement: str | None

    @staticmethod
    def from_value(value: object) -> "Deprecation":
        if not isinstance(value, dict) or set(value) != {"status", "replacement"}:
            raise ContractError("DEPRECATION_INVALID", "expected {status, replacement}")
        status, replacement = value["status"], value["replacement"]
        if status not in DEPRECATION_STATUSES:
            raise ContractError(
                "DEPRECATION_INVALID", "status must be ACTIVE or DEPRECATED"
            )
        if status == "ACTIVE" and replacement is not None:
            raise ContractError(
                "DEPRECATION_INVALID", "an ACTIVE contract has no replacement"
            )
        if status == "DEPRECATED":
            if not isinstance(replacement, str):
                raise ContractError(
                    "DEPRECATION_INVALID", "DEPRECATED needs a replacement ID"
                )
            parse_contract_id(replacement)
        return Deprecation(status, replacement)


@dataclass(frozen=True)
class ContractDeclaration:
    contract_id: str
    name: str
    contract_type: str
    version: int
    semantic_owner: str
    canonical_producer: str
    declared_consumers: tuple[str, ...]
    purpose: str
    input_schema: FileRef | None
    output_schema: FileRef
    fixtures: tuple[FileRef, ...]
    authority_level: str
    sync_semantics: str
    security_classification: str
    semantics: Mapping[str, str]
    deprecation: Deprecation

    @property
    def parsed_id(self) -> ContractVersion:
        return parse_contract_id(self.contract_id)

    @staticmethod
    def from_mapping(data: object) -> "ContractDeclaration":
        if not isinstance(data, dict):
            raise ContractError("DECLARATION_INVALID", "declaration must be an object")
        record: dict[str, Any] = dict(data)
        unknown = set(record) - set(_REQUIRED) - set(_OPTIONAL)
        missing = set(_REQUIRED) - set(record)
        if unknown:
            raise ContractError("UNKNOWN_FIELD", ", ".join(sorted(unknown)))
        if missing:
            raise ContractError("FIELD_MISSING", ", ".join(sorted(missing)))
        parsed = parse_contract_id(record["contract_id"])
        version = record["version"]
        if type(version) is not int or version != parsed.major:
            raise ContractError("VERSION_MISMATCH", "version must equal the ID's major")
        contract_type = _text(record, "contract_type")
        if contract_type not in CONTRACT_TYPES:
            raise ContractError("CONTRACT_TYPE_INVALID", contract_type)
        sync = _text(record, "sync_semantics")
        if sync not in SYNC_SEMANTICS:
            raise ContractError("SYNC_SEMANTICS_INVALID", sync)
        # Exactly one canonical producer per semantic fact (02 Canonical Producer Rule).
        producer = record["canonical_producer"]
        if not isinstance(producer, str):
            raise ContractError(
                "PRODUCER_NOT_SINGULAR", "exactly one canonical producer"
            )
        producer = _text(record, "canonical_producer")
        consumers = record["declared_consumers"]
        if (
            not isinstance(consumers, list)
            or not all(
                isinstance(c, str) and c.strip() and c == c.strip() for c in consumers
            )
            or len(set(consumers)) != len(consumers)
        ):
            raise ContractError(
                "CONSUMERS_INVALID", "unique non-blank strings required"
            )
        fixtures = record["fixtures"]
        if not isinstance(fixtures, list) or not fixtures:
            raise ContractError("FIXTURES_INVALID", "at least one fixture is required")
        fixture_refs = tuple(
            FileRef.from_value(item, "fixtures[]") for item in fixtures
        )
        if len({ref.path for ref in fixture_refs}) != len(fixture_refs):
            raise ContractError("FIXTURES_INVALID", "duplicate fixture path")
        semantics = record.get("semantics", {})
        if not isinstance(semantics, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and k and v.strip()
            for k, v in semantics.items()
        ):
            raise ContractError(
                "SEMANTICS_INVALID", "string-to-string mapping required"
            )
        input_value = record.get("input_schema")
        return ContractDeclaration(
            contract_id=parsed.contract_id,
            name=_text(record, "name"),
            contract_type=contract_type,
            version=version,
            semantic_owner=_text(record, "semantic_owner"),
            canonical_producer=producer,
            declared_consumers=tuple(consumers),
            purpose=_text(record, "purpose"),
            input_schema=None
            if input_value is None
            else FileRef.from_value(input_value, "input_schema"),
            output_schema=FileRef.from_value(record["output_schema"], "output_schema"),
            fixtures=fixture_refs,
            authority_level=_text(record, "authority_level"),
            sync_semantics=sync,
            security_classification=_text(record, "security_classification"),
            semantics=dict(semantics),
            deprecation=Deprecation.from_value(record["deprecation"]),
        )


def _read_schema(ref: FileRef, repo_root: Path) -> dict[str, Any]:
    """Load a hash-verified JSON Schema (2020-12) and check that it is itself valid."""
    raw = ref.read(repo_root)
    try:
        schema = json.loads(raw)
    except ValueError:
        raise ContractError("SCHEMA_INVALID", f"{ref.path} is not JSON") from None
    if not isinstance(schema, dict):
        raise ContractError("SCHEMA_INVALID", f"{ref.path} is not a schema object")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception:
        raise ContractError(
            "SCHEMA_INVALID", f"{ref.path} is not a valid 2020-12 schema"
        ) from None
    return schema


def load_schema(
    ref: FileRef, repo_root: Path, *, schema_refs: tuple[FileRef, ...] = ()
) -> dict[str, Any]:
    """Load and expand a hash-verified schema using explicitly pinned package files."""
    approved = {item.path: item for item in schema_refs}
    if len(approved) != len(schema_refs):
        raise ContractError("SCHEMA_REF_AMBIGUOUS", "duplicate approved schema path")
    package_root = repo_root.resolve() / "packages" / "contracts"
    if (
        ref.path.startswith("packages/contracts/")
        and package_root not in (repo_root / ref.path).resolve().parents
    ):
        raise ContractError(
            "SCHEMA_REF_FORBIDDEN", "root schema escapes contracts package"
        )
    schema = _read_schema(ref, repo_root)

    def load_local(path: str) -> dict[str, Any]:
        target = approved.get(path)
        if target is None:
            raise ContractError(
                "SCHEMA_REF_UNAPPROVED", "schema needs an explicit hash pin"
            )
        resolved = (repo_root / path).resolve()
        if package_root not in resolved.parents:
            raise ContractError(
                "SCHEMA_REF_FORBIDDEN", "schema escapes contracts package"
            )
        return _read_schema(target, repo_root)

    expanded = resolve_references(schema, document_path=ref.path, load_local=load_local)
    try:
        Draft202012Validator.check_schema(expanded)
    except Exception:
        raise ContractError(
            "SCHEMA_REF_INVALID", "expanded schema is invalid"
        ) from None
    return expanded


class Registry:
    """Declarations loaded from one directory, with cross-declaration rules checked."""

    def __init__(self, declarations: Mapping[str, ContractDeclaration]) -> None:
        self._declarations = dict(declarations)
        for declaration in self._declarations.values():
            self._check_deprecation(declaration)

    def _check_deprecation(self, declaration: ContractDeclaration) -> None:
        replacement = declaration.deprecation.replacement
        if replacement is None:
            return
        target = self._declarations.get(replacement)
        if target is None:
            raise ContractError(
                "REPLACEMENT_UNKNOWN", f"{declaration.contract_id} -> {replacement}"
            )
        if not is_later_major(declaration.parsed_id, target.parsed_id):
            raise ContractError(
                "REPLACEMENT_NOT_LATER_MAJOR",
                f"{declaration.contract_id} -> {replacement}",
            )

    @classmethod
    def load(cls, directory: Path) -> "Registry":
        declarations: dict[str, ContractDeclaration] = {}
        for path in sorted(directory.iterdir()):
            if path.name == "README.md":
                continue
            if path.suffix != ".json" or not path.is_file():
                raise ContractError("REGISTRY_ENTRY_UNEXPECTED", path.name)
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                raise ContractError(
                    "DECLARATION_INVALID", f"{path.name} is not JSON"
                ) from None
            declaration = ContractDeclaration.from_mapping(raw)
            if path.stem != declaration.contract_id:
                raise ContractError("FILE_NAME_MISMATCH", path.name)
            declarations[declaration.contract_id] = declaration
        return cls(declarations)

    def contract_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._declarations))

    def get(self, contract_id: str) -> ContractDeclaration:
        try:
            return self._declarations[contract_id]
        except KeyError:
            raise ContractError("CONTRACT_UNKNOWN", contract_id) from None

    def verify_authorities(
        self, authorities: "ProducerAuthorities", *, repo_root: Path | None = None
    ) -> None:
        """Validate every declaration, including unchanged/deprecated versions."""
        for contract_id in self.contract_ids():
            authorities.validate(self.get(contract_id), repo_root=repo_root)

    def verify(self, repo_root: Path, *, schema_refs: tuple[FileRef, ...] = ()) -> None:
        """Every referenced file exists, matches its hash, and every fixture validates."""
        for declaration in self._declarations.values():
            if declaration.input_schema is not None:
                load_schema(
                    declaration.input_schema, repo_root, schema_refs=schema_refs
                )
            schema = load_schema(
                declaration.output_schema, repo_root, schema_refs=schema_refs
            )
            validator = Draft202012Validator(schema)
            for fixture in declaration.fixtures:
                raw = fixture.read(repo_root)
                try:
                    instance = json.loads(raw)
                except ValueError:
                    raise ContractError(
                        "FIXTURE_INVALID", f"{fixture.path} is not JSON"
                    ) from None
                if not validator.is_valid(instance):
                    raise ContractError("FIXTURE_INVALID", fixture.path)
