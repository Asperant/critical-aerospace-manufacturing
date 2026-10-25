"""Integration Contract Registry foundation and compatibility comparison (WP-EVT-001)."""

from .authority import ProducerAuthorities
from .boundary import BoundaryRole, BoundaryValidator, ContractViolation
from .compatibility import (
    CompatibilityResult,
    compare_contracts,
    compare_schema_files,
    compare_schemas,
    enforce_version_policy,
)
from .envelope import (
    CausationID,
    CorrelationID,
    EntityID,
    EntityReference,
    EntityRevision,
    EnvelopeError,
    EventEnvelope,
    EventID,
    SimulationTime,
    TraceID,
    new_event_id,
)
from .errors import ContractError
from .permissions import PublisherPermission, PublisherPermissions
from .registry import (
    ContractDeclaration,
    Deprecation,
    FileRef,
    Registry,
)
from .streams import StreamDefinition, StreamDefinitions, SubjectBinding
from .versioning import ContractVersion, is_successor, parse_contract_id

__all__ = [
    "CausationID",
    "CorrelationID",
    "EntityID",
    "EntityReference",
    "EntityRevision",
    "EnvelopeError",
    "EventEnvelope",
    "EventID",
    "SimulationTime",
    "TraceID",
    "new_event_id",
    "BoundaryRole",
    "BoundaryValidator",
    "CompatibilityResult",
    "compare_contracts",
    "compare_schemas",
    "compare_schema_files",
    "enforce_version_policy",
    "ContractDeclaration",
    "ContractError",
    "PublisherPermission",
    "PublisherPermissions",
    "ContractVersion",
    "ContractViolation",
    "Deprecation",
    "FileRef",
    "Registry",
    "StreamDefinition",
    "StreamDefinitions",
    "SubjectBinding",
    "ProducerAuthorities",
    "is_successor",
    "parse_contract_id",
]
