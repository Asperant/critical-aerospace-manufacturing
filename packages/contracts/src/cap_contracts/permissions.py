"""Pure publish permissions from canonical bindings, never runtime broker ACLs."""

import json
from dataclasses import asdict, dataclass

from .authority import ProducerAuthorities
from .errors import ContractError
from .registry import Registry
from .streams import StreamDefinitions


@dataclass(frozen=True)
class PublisherPermission:
    producer: str
    subjects: tuple[str, ...]


class PublisherPermissions:
    """Exact allowlist; consumer membership never confers publish authority."""

    def __init__(
        self,
        catalog: StreamDefinitions,
        registry: Registry,
        authorities: ProducerAuthorities,
    ) -> None:
        if type(catalog) is not StreamDefinitions:
            raise ContractError("PUBLISHER_PERMISSIONS_UNVERIFIABLE")
        # Revalidate against the supplied current registry/ownership snapshot. No
        # artifact loading or runtime identity inference occurs in this projection.
        validated = StreamDefinitions(
            json.loads(catalog.to_json()), registry, authorities
        )
        subjects: dict[str, list[str]] = {}
        for definition in validated.definitions:
            for binding in definition.bindings:
                subjects.setdefault(binding.canonical_producer, []).append(
                    binding.subject
                )
        self._entries = tuple(
            PublisherPermission(producer, tuple(sorted(owned)))
            for producer, owned in sorted(subjects.items())
        )

    @property
    def entries(self) -> tuple[PublisherPermission, ...]:
        return self._entries

    def allows_publish(self, producer: object, subject: object) -> bool:
        """Deny unknown names, patterns and non-string inputs without normalization."""
        if not isinstance(producer, str) or not isinstance(subject, str):
            return False
        return any(
            entry.producer == producer and subject in entry.subjects
            for entry in self._entries
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "schema_version": "cap-publisher-permissions-v1",
                "publishers": [asdict(entry) for entry in self._entries],
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
