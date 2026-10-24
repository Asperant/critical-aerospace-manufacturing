# cap-contracts — Integration Contract Registry foundation (WP-EVT-001)

The version-controlled Integration Contract Registry of the architecture
specification (02, "Integration Contract Registry"): a Git-backed semantic catalog,
not a runtime schema registry. Slice 1 provides the layout, the version rules and the
boundary-validation primitives. It does not provide the EVT message envelope, broker
or NATS behaviour, Core command contracts, the outbox, the compatibility
(breaking-change) detector, producer-ACL generation or any INTEGRATION/FROZEN
behaviour.

## Layout

- `registry/<contract_id>.json` — one declaration per contract version; the file name
  is the contract ID. Only `.json` declarations and this README are allowed there.
- Schemas and fixtures stay where the canonical producer owns them. A declaration
  references each by repository-relative path and SHA-256, so drift from what was
  registered is detected (`SCHEMA_DRIFT`).
- `src/cap_contracts/` — `versioning` (IDs and version rules), `registry`
  (declarations, loading, verification) and `boundary` (payload validation).

## Declaration fields

`contract_id`, `name`, `contract_type` (QUERY, COMMAND, EVENT, SNAPSHOT, ARTIFACT or
HEALTH, the six contract classes), `version`, `semantic_owner`, `canonical_producer`
(exactly one string), `declared_consumers`, `purpose`, `input_schema` (optional),
`output_schema`, `fixtures`, `authority_level`, `sync_semantics` (SYNC or ASYNC),
`security_classification`, `semantics` (optional free-text revision, ordering, errors
and world semantics) and `deprecation` (`status` ACTIVE or DEPRECATED, plus
`replacement`). Unknown or missing fields are rejected.

## Version rules

- A contract ID is `<family>.v<major>`, lower-case, no leading zero, for example
  `core.order-query.v1`; `version` must equal the major.
- A breaking change (including an authority change) is a new major, hence a new
  contract ID and a new declaration. A declaration is never edited into a breaking
  shape.
- A successor is exactly the next major of the same family. A DEPRECATED contract
  names a replacement that exists in the registry and is a later major of the same
  family; an ACTIVE contract names none.

## Boundary validation

`BoundaryValidator(declaration, repo_root).validate(payload, role="producer" | "consumer")`
checks a payload against the declared output schema (JSON Schema 2020-12), and
`validate_request` checks a request against the input schema. Violations list JSON
Pointer paths and schema keywords only, never payload values. A missing file, hash
mismatch, invalid schema or unknown role fails closed.

## Exemplar

`registry/core.order-query.v1.json` registers the already-merged `core.order-query.v1`
Core query contract as the first exemplar. Registering it is not a readiness
declaration: it does not make DN-CORE-CONTRACTS CONTRACT_READY.

Verification: `Registry.load(...).verify(repo_root)` checks hashes, schema validity
and that every fixture validates. The tests run in the `CI tooling tests` CI step.
