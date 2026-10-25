"""Versioned, concrete subject definitions; no broker bindings or ACL generation."""

import json
import re
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .authority import ProducerAuthorities
from .errors import ContractError
from .registry import Registry
from .versioning import parse_contract_id, validate_producer_name

STREAM_CATALOG_PATH = "packages/contracts/stream-definitions.json"


def _catalog_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("STREAM_CATALOG_INVALID")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ContractError("STREAM_CATALOG_INVALID")


_TOKEN = r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*"
_SUBJECT = re.compile(rf"{_TOKEN}(?:\.{_TOKEN})+")
_BINDING_FIELDS = {
    "binding_id",
    "version",
    "contract_id",
    "schema_family",
    "subject",
    "canonical_producer",
}
_STREAM_TEXT = {
    "stream_id",
    "stream_class",
    "semantic_owner",
    "schema_family",
    "partition_key_policy",
    "ordering_scope",
    "retention_class",
    "replay_policy",
    "data_classification",
    "message_size_class",
    "dlq_policy",
}
_STREAM_FIELDS = _STREAM_TEXT | {
    "version",
    "allowed_publishers",
    "known_consumers",
    "bindings",
}
_RETENTION = {
    "DOMAIN_EVENT": {"DOMAIN_CRITICAL", "DOMAIN_STANDARD"},
    "WORK_COMMAND": {"WORK_OPERATIONAL"},
}


def _record(value: object, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ContractError(
            "STREAM_DEFINITION_INVALID", "exact declared fields required"
        )
    return value


def _text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or value.upper() in {"UNKNOWN", "UNVERIFIABLE", "TBD", "TBD_BY_IMPLEMENTATION"}
    ):
        raise ContractError(
            "STREAM_DEFINITION_UNVERIFIABLE", "explicit metadata required"
        )
    return value


def _names(value: object, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ContractError("STREAM_DEFINITION_INVALID", "explicit list required")
    names = tuple(_text(item) for item in value)
    if len(set(names)) != len(names):
        raise ContractError("STREAM_DEFINITION_INVALID", "duplicate metadata")
    return tuple(sorted(names))


@dataclass(frozen=True)
class SubjectBinding:
    binding_id: str
    version: int
    contract_id: str
    schema_family: str
    subject: str
    canonical_producer: str

    @classmethod
    def from_mapping(
        cls, value: object, registry: Registry, authorities: ProducerAuthorities
    ) -> "SubjectBinding":
        record = _record(value, _BINDING_FIELDS)
        identity = parse_contract_id(record["binding_id"])
        contract = parse_contract_id(record["contract_id"])
        family = _text(record["schema_family"])
        if identity.family != family or contract.family != family:
            raise ContractError("SUBJECT_FAMILY_MISMATCH")
        if (
            type(record["version"]) is not int
            or record["version"] != identity.major
            or contract.major != identity.major
        ):
            raise ContractError("SUBJECT_VERSION_MISMATCH")
        subject = _text(record["subject"])
        # v1 supports exact literals only; an inline flag cannot authorize wildcards.
        if _SUBJECT.fullmatch(subject) is None:
            raise ContractError(
                "SUBJECT_INVALID", "canonical concrete literal required"
            )
        producer = validate_producer_name(record["canonical_producer"])
        declaration = registry.get(contract.contract_id)
        authorities.validate(declaration)
        if producer != declaration.canonical_producer:
            raise ContractError("SUBJECT_PRODUCER_MISMATCH")
        if declaration.sync_semantics != "ASYNC" or declaration.contract_type not in {
            "EVENT",
            "COMMAND",
        }:
            raise ContractError(
                "STREAM_CONTRACT_UNSUPPORTED", "async event or command required"
            )
        return cls(
            identity.contract_id,
            identity.major,
            contract.contract_id,
            family,
            subject,
            producer,
        )


@dataclass(frozen=True)
class StreamDefinition:
    stream_id: str
    version: int
    stream_class: str
    semantic_owner: str
    allowed_publishers: tuple[str, ...]
    known_consumers: tuple[str, ...]
    schema_family: str
    partition_key_policy: str
    ordering_scope: str
    retention_class: str
    replay_policy: str
    data_classification: str
    message_size_class: str
    dlq_policy: str
    bindings: tuple[SubjectBinding, ...]

    @classmethod
    def from_mapping(
        cls, value: object, registry: Registry, authorities: ProducerAuthorities
    ) -> "StreamDefinition":
        record = _record(value, _STREAM_FIELDS)
        text = {key: _text(record[key]) for key in sorted(_STREAM_TEXT)}
        identity = parse_contract_id(text["stream_id"])
        if type(record["version"]) is not int or record["version"] != identity.major:
            raise ContractError("SUBJECT_VERSION_MISMATCH")
        if text["stream_class"] not in _RETENTION:
            raise ContractError("STREAM_CLASS_UNSUPPORTED")
        if text["retention_class"] not in _RETENTION[text["stream_class"]] or text[
            "data_classification"
        ] not in {"PUBLIC_INTERNAL", "INTERNAL", "SENSITIVE"}:
            raise ContractError("STREAM_DEFINITION_UNVERIFIABLE")
        if not isinstance(record["bindings"], list) or not record["bindings"]:
            raise ContractError("STREAM_DEFINITION_UNVERIFIABLE", "bindings required")
        bindings = tuple(
            sorted(
                (
                    SubjectBinding.from_mapping(item, registry, authorities)
                    for item in record["bindings"]
                ),
                key=lambda item: item.binding_id,
            )
        )
        publishers = _names(record["allowed_publishers"], nonempty=True)
        for producer in publishers:
            validate_producer_name(producer)
        if set(publishers) != {binding.canonical_producer for binding in bindings}:
            raise ContractError("SUBJECT_PRODUCER_MISMATCH")
        consumers = _names(record["known_consumers"])
        expected_type = "EVENT" if text["stream_class"] == "DOMAIN_EVENT" else "COMMAND"
        for binding in bindings:
            declaration = registry.get(binding.contract_id)
            if binding.schema_family != text["schema_family"]:
                raise ContractError("SUBJECT_FAMILY_MISMATCH")
            if (
                declaration.semantic_owner != text["semantic_owner"]
                or declaration.contract_type != expected_type
            ):
                raise ContractError("SUBJECT_PRODUCER_MISMATCH")
            if not set(consumers) <= set(declaration.declared_consumers):
                raise ContractError("STREAM_CONSUMER_UNDECLARED")
        # Enforce ownership even when a single definition is constructed directly.
        _unique(bindings)
        return cls(
            **text,
            version=identity.major,
            allowed_publishers=publishers,
            known_consumers=consumers,
            bindings=bindings,
        )


def _unique(bindings: tuple[SubjectBinding, ...]) -> None:
    identities: set[str] = set()
    subjects: set[str] = set()
    for binding in bindings:
        if binding.subject in subjects:
            raise ContractError("SUBJECT_OWNERSHIP_CONFLICT")
        if binding.binding_id in identities:
            raise ContractError("SUBJECT_BINDING_DUPLICATE")
        identities.add(binding.binding_id)
        subjects.add(binding.subject)


class StreamDefinitions:
    """Validated catalog. All active definitions share a single ownership check."""

    def __init__(
        self, value: object, registry: Registry, authorities: ProducerAuthorities
    ) -> None:
        record = _record(value, {"schema_version", "streams"})
        if (
            record["schema_version"] != "cap-stream-definitions-v1"
            or not isinstance(record["streams"], list)
            or not record["streams"]
        ):
            raise ContractError("STREAM_DEFINITION_UNVERIFIABLE")
        definitions = tuple(
            sorted(
                (
                    StreamDefinition.from_mapping(item, registry, authorities)
                    for item in record["streams"]
                ),
                key=lambda item: item.stream_id,
            )
        )
        if len({item.stream_id for item in definitions}) != len(definitions):
            raise ContractError("STREAM_DEFINITION_DUPLICATE")
        _unique(
            tuple(
                binding for definition in definitions for binding in definition.bindings
            )
        )
        self._definitions = definitions

    @property
    def definitions(self) -> tuple[StreamDefinition, ...]:
        return self._definitions

    @classmethod
    def load(
        cls, repo_root: Path, registry: Registry, authorities: ProducerAuthorities
    ) -> "StreamDefinitions":
        """Load the single approved package catalog; no includes or symlinks.

        The repository root is the caller's trusted anchor. Every component below
        it must be a regular directory, ending in a regular UTF-8 JSON file.
        Missing catalogs are errors here; historical absence is handled by CI.
        """
        try:
            path = repo_root.resolve()
            parts = Path(STREAM_CATALOG_PATH).parts
            for index, part in enumerate(parts):
                path = path / part
                mode = path.lstat().st_mode
                expected = stat.S_ISREG if index == len(parts) - 1 else stat.S_ISDIR
                if not expected(mode):
                    raise ContractError("STREAM_CATALOG_SOURCE_INVALID")
            value = json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_catalog_object,
                parse_constant=_nonfinite,
            )
        except FileNotFoundError:
            raise ContractError("STREAM_CATALOG_MISSING") from None
        except (OSError, ValueError, UnicodeError) as error:
            if isinstance(error, ContractError):
                raise
            raise ContractError("STREAM_CATALOG_INVALID") from None
        return cls(value, registry, authorities)

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema_version": "cap-stream-definitions-v1",
                "streams": [asdict(item) for item in self._definitions],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
