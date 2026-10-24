# cap-contracts — Integration Contract Registry foundation (WP-EVT-001)

The version-controlled Integration Contract Registry of the architecture
specification (02, "Integration Contract Registry"): a Git-backed semantic catalog,
not a runtime schema registry. Slice 1 provides the layout, the version rules and the
boundary-validation primitives. It does not provide the EVT message envelope, broker
or NATS behaviour, Core command contracts, the outbox, the CI compatibility
gate, producer-ACL generation or any INTEGRATION/FROZEN
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

## Pure compatibility comparison

`compare_schemas(old, new)` returns an immutable `CompatibilityResult` with
`breaking`, `unverifiable` reasons and `compatible` (true only when both are empty).
Optional property additions, including nested object/array items, are non-breaking
under the architecture policy. Required-field removal or relaxation, required
additions, field removal, type/constraint/enum changes and changed annotations
(including descriptions of units or identifier meaning) are conservatively breaking.

`compare_contracts(old_declaration, new_declaration, old_output_schema=...,
new_output_schema=..., old_input_schema=..., new_input_schema=...)` also compares
canonical producer, owner, authority and declared semantics. A new major never
hides a breaking result. Callers supply schema documents loaded/hash-verified with
the existing registry primitives; the comparison itself performs no I/O or writes.
Missing declared documents, unrelated families or reversed versions fail closed.

The bounded schema subset supports explicit types, properties, required fields,
boolean additionalProperties, items, enum/const and scalar/collection constraints.
Local references are resolved before comparing their effective shape (see below).
General composition, formats, alternate dialects, unknown keywords and schemas
without explicit types remain unverifiable even when unchanged. The Core output
exemplar still has unsupported keywords, including `$id`; this slice does not
certify its compatibility. Unverifiable
results must never be accepted as compatible. Semantic changes absent from declared
metadata cannot be inferred. Optional-addition policy is not proof that strict old
consumers accept new payloads: consumer tests remain required. CI integration and
version-policy enforcement are later slices.

## Local schema references

`load_schema(ref, repo_root, schema_refs=(...))`,
`BoundaryValidator(declaration, repo_root, schema_refs=(...))` and
`Registry.verify(repo_root, schema_refs=(...))` accept an explicit tuple of `FileRef`
approvals for referenced files. Each approval pins a repository-relative file path
and SHA-256; root schemas keep their existing declaration pins. No registry declaration
fields or producer-owned schemas change. Example: a schema at
`packages/contracts/schemas/order.json` may use `$ref: "common.json#/$defs/Id"`
when `packages/contracts/schemas/common.json` has an approved `FileRef`.

References are resolved offline relative to the physical document's package path,
not retrieved from a root `$id` (which remains an identifier). Internal `#` JSON
Pointers are also supported for producer-owned schemas outside the package, including
the Core exemplar. Every loaded document is hash-verified and schema-checked before
expansion. Expansion validates even unused definitions, produces a fresh document
and checks its validity before any boundary payload is accepted. Ref siblings keep
their evaluation scope, including `unevaluatedProperties`.

File references require canonical relative paths: no absolute paths, schemes,
remote URLs, `.`/`..`, percent encodings, backslashes or query strings. File targets
and package-root schema paths must remain physically within `packages/contracts`
after symlink resolution. Missing files/pointers, duplicate approvals, drift, cycles,
anchors, dynamic references, nested `$id` rebasing and alternate dialects fail closed.
Expansion is limited to 10,000 schema-node visits and Python recursion depth; exceeding
either limit fails closed. JSON Pointer dictionary keys and canonical array indices
are supported. Payload constants/examples are not traversed as schemas.

Reference resolution does not certify consumer compatibility or full WP acceptance.
The detector now supports resolved local definitions as described below.

## Resolved-definition compatibility

`compare_schemas(old, new)` resolves internal JSON Pointer references using the
existing offline resolver before comparison. `compare_contracts` uses this same
comparison for supplied input/output documents and retains its authority/semantic
checks. Raw file references have no approval context and remain unverifiable.

`compare_schema_files(old_ref, new_ref, old_repo_root=..., new_repo_root=...,
old_schema_refs=(...), new_schema_refs=(...))` loads each version with the existing
pinned-file loader, then compares effective shapes. Root and transitive dependency
hashes, approval, package containment and cycle checks remain mandatory. Separate
repository roots/pin sets permit comparing two checked-out versions. Loading errors
return `unverifiable` reasons labelled `old` or `new`; they never imply compatibility.

After resolution and schema validation, definition containers are removed from the
comparison shape. Single-branch `allOf` wrappers are flattened only with annotation
siblings whose keys do not conflict. Validation siblings and multiple branches
remain unverifiable: moving validation keywords between schema scopes can change
their meaning. All remaining keywords retain the existing bounded-subset rules.

Effective optional property additions remain non-breaking. Required removals,
field/type/constraint or declared semantic changes inside referenced targets are
breaking. A reference-target rename with identical shape/annotations is compatible;
changing the referenced shape is assessed by the same rules as inline schemas.
Equal unresolved reference strings are never accepted as compatibility proof.
Missing/invalid/cyclic references fail closed even when both versions are identical,
and unused definitions are still inspected by the resolver before being removed.
