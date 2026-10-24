"""Static producer ownership bindings; this is not publisher authentication or ACLs."""

import copy
import json
from pathlib import Path
from typing import Any

from .errors import ContractError
from .registry import CONTRACT_TYPES, ContractDeclaration, FileRef
from .versioning import parse_contract_id


def _text(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value == value.strip()
        and value.upper()
        not in {"UNKNOWN", "UNVERIFIABLE", "TBD", "TBD_BY_IMPLEMENTATION"}
    )


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("AUTHORITY_MODEL_INVALID")
        result[key] = value
    return result


class ProducerAuthorities:
    """An explicit, fail-closed ownership model separate from contract claims."""

    def __init__(self, value: object) -> None:
        self._producers: dict[str, dict[str, Any]] = {}
        self._families: dict[str, str] = {}
        if (
            not isinstance(value, dict)
            or set(value) != {"schema_version", "producers"}
            or value["schema_version"] != "cap-producer-authorities-v1"
            or not isinstance(value["producers"], list)
            or not value["producers"]
        ):
            raise ContractError("AUTHORITY_MODEL_INVALID")
        roots: list[tuple[str, str]] = []
        for source in value["producers"]:
            if (
                not isinstance(source, dict)
                or set(source)
                != {"producer", "semantic_owner", "source_roots", "contracts"}
                or not _text(source["producer"])
                or not _text(source["semantic_owner"])
                or not isinstance(source["source_roots"], list)
                or not source["source_roots"]
                or not isinstance(source["contracts"], list)
                or not source["contracts"]
            ):
                raise ContractError("AUTHORITY_MODEL_INVALID")
            producer = source["producer"]
            if producer in self._producers:
                raise ContractError("PRODUCER_AUTHORITY_CONFLICT")
            for root in source["source_roots"]:
                if (
                    not _text(root)
                    or not root.endswith("/")
                    or "\\" in root
                    or root.split("/")[0] not in {"services", "packages"}
                    or len(root.split("/")) < 3
                    or any(part in {"", ".", ".."} for part in root[:-1].split("/"))
                ):
                    raise ContractError("AUTHORITY_MODEL_INVALID")
                if any(
                    root.startswith(existing) or existing.startswith(root)
                    for existing, _ in roots
                ):
                    raise ContractError("PRODUCER_AUTHORITY_CONFLICT")
                roots.append((root, producer))
            for binding in source["contracts"]:
                if (
                    not isinstance(binding, dict)
                    or set(binding) != {"family", "contract_type", "authority_level"}
                    or not _text(binding["family"])
                    or not _text(binding["authority_level"])
                    or not _text(binding["contract_type"])
                    or binding["contract_type"] not in CONTRACT_TYPES
                ):
                    raise ContractError("AUTHORITY_MODEL_INVALID")
                try:
                    family = parse_contract_id(binding["family"] + ".v1").family
                except ContractError:
                    raise ContractError("AUTHORITY_MODEL_INVALID") from None
                if family in self._families:
                    raise ContractError("PRODUCER_AUTHORITY_CONFLICT")
                self._families[family] = producer
            self._producers[producer] = copy.deepcopy(source)

    @classmethod
    def load(cls, path: Path) -> "ProducerAuthorities":
        try:
            return cls(
                json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object)
            )
        except (OSError, ValueError):
            raise ContractError("AUTHORITY_UNVERIFIABLE") from None

    def validate(
        self, declaration: ContractDeclaration, *, repo_root: Path | None = None
    ) -> None:
        producer = declaration.canonical_producer
        if producer in declaration.declared_consumers:
            raise ContractError("CONSUMER_AUTHORITY_CLAIM")
        source = self._producers.get(producer)
        if source is None:
            raise ContractError("PRODUCER_UNKNOWN")
        family = declaration.parsed_id.family
        owner = self._families.get(family)
        if owner is None:
            raise ContractError("AUTHORITY_UNVERIFIABLE")
        if owner != producer:
            raise ContractError("PRODUCER_AUTHORITY_MISMATCH")
        binding = next(item for item in source["contracts"] if item["family"] == family)
        if (
            declaration.semantic_owner != source["semantic_owner"]
            or declaration.contract_type != binding["contract_type"]
            or declaration.authority_level != binding["authority_level"]
        ):
            raise ContractError("PRODUCER_AUTHORITY_MISMATCH")
        refs = (declaration.output_schema, *declaration.fixtures)
        if declaration.input_schema is not None:
            refs = (*refs, declaration.input_schema)
        for ref in refs:
            FileRef.from_value(
                {"path": ref.path, "sha256": ref.sha256}, "authority_source"
            )
            matching = [
                root for root in source["source_roots"] if ref.path.startswith(root)
            ]
            if not matching:
                raise ContractError("PRODUCER_SOURCE_MISMATCH")
            if repo_root is not None:
                root = repo_root.resolve()
                target = (root / ref.path).resolve()
                if not any(
                    root / allowed.rstrip("/") in target.parents for allowed in matching
                ):
                    raise ContractError("PRODUCER_SOURCE_MISMATCH")
