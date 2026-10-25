# cap-contracts — Integration Contract Registry foundation (WP-EVT-001)

The version-controlled Integration Contract Registry of the architecture
specification (02, "Integration Contract Registry"): a Git-backed semantic catalog,
not a runtime schema registry. Slice 1 provides the layout, the version rules and the
boundary-validation primitives. It does not provide the EVT message envelope, broker
or NATS behaviour, Core command contracts, the outbox, producer-ACL generation
or any INTEGRATION/FROZEN
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

## Typed event envelope foundation (WP-EVT-002, Slice 1)

`EventEnvelope` is immutable operational metadata, independent of payload schemas
and transport. Construction and strict `from_mapping`/`from_json` decoding require
every field: `event_id`, `event_type`, positive integer `schema_version`, `producer`,
`world_id`, `correlation_id`, `causation_id`, `trace_id`, `occurred_at`,
`observed_at` and `entity_refs`. Unknown/missing fields, duplicate JSON fields and
malformed identities fail closed with `EnvelopeError` without payload values.

`new_event_id()` creates a UUID4 for a new fact. Keep that EventID on retries and
replay; CorrelationID identifies the business chain, CausationID its immediate
predecessor, and TraceID the software execution (which may change on replay).
These distinct typed IDs preserve caller-supplied opaque strings without deriving
one from another. Root events explicitly use `causation_id=None`; omission fails.
WorldID is always an explicit nonblank string; nothing infers a primary world.
Metadata validation does not authenticate a producer or authorize a world.

`validate_world_scope(envelope, expected_world_id)` checks the consumer's explicit
expected scope and returns the **same envelope object** on an exact match. Missing
(`None`), non-string or blank expected IDs and mismatches raise `EnvelopeError`
with field-only messages. IDs are compared unchanged: no trimming, case folding,
Unicode normalization, coercion or implicit primary-world fallback. Existing
construction/decoding still rejects malformed or missing envelope WorldID; the
guard also rechecks its nonblank shape. It performs no transport, state mutation,
producer authentication or authorization.

`EntityReference(entity_type, id, revision)` preserves Core's opaque nonblank
identity/revision strings, including nonnumeric revisions. It does not invent an
aggregate sequence counter or prove freshness. Supply an explicit tuple of these
references, empty only for events without entity context. The library does not
infer which business events are mutation-sensitive; payload owners retain those
requirements and their event-specific constraints.

`observed_at` is an aware UTC datetime. `occurred_at` is either an aware UTC
datetime or `SimulationTime(seconds, simulation_run_id)` supplied by the
domain/simulator authority. The metadata wire representation tags occurrence as
`{"clock":"UTC","value":"...Z"}` or
`{"clock":"SIMULATION","seconds":42.5,"simulation_run_id":"run-1"}`;
simulation seconds are finite and have no implicit UTC epoch. They are not a
substitute for platform observation time. Non-UTC/naive datetimes and unknown or
ambiguous clock representations are rejected. The library never reads the local
clock or substitutes observation time for occurrence time.

This is an initial shared-library representation, not a registered production event
payload or publication binding. Existing Core schemas/fixtures and registry entries
are unchanged. HTTP/NATS/Temporal propagation, production payload/subject bindings,
outbox, runtime ACLs and REAL integrated acceptance remain subsequent work. Focused
tests: `uv run --project ci --locked pytest -c ci/pyproject.toml
ci/tests/test_event_envelope.py -q`.

### Published metadata schema and fixtures

`schemas/event-envelope.v1.schema.json` publishes the Slice-1 serialized metadata
shape as JSON Schema 2020-12, with internal references only. Every envelope field
is required, including explicit nullable root causation; envelope, occurrence and
entity-reference objects reject additional fields. Identity and revision values
remain opaque nonblank strings, not UUID-only values or numeric revisions.
Simulation seconds are finite numbers with explicit run identity; no nonnegative
constraint or UTC epoch is introduced. The UTC pattern checks Gregorian calendar
dates, leap years, clock ranges and UTC offsets without an optional `format`
plugin; the pinned toolchain has no date-time format checker installed.

`fixtures/event-envelope.utc.json` and `fixtures/event-envelope.simulation.json`
are canonical **SYNTHETIC TEST** metadata examples. The UTC example is a root; the
simulation example names its direct predecessor while retaining the business
correlation and a distinct processing trace. Both include an opaque Lot revision
and separate UTC observation time. They contain no factory observations, domain
payload, registered production event, publisher or subject declaration. Invalid
examples are generated by focused test mutations rather than duplicated files.

Parity coverage checks model-emitted JSON and published fixtures, required-field
and identity/reference negatives, closed records, calendar boundaries and distinct
clocks. The schema describes canonical wire values, not all Python decoder input
extensions: `datetime.fromisoformat` accepts additional ISO spellings, and JSON
Schema considers `1.0` an integer value whereas the existing Python model requires
an actual `int` for schema_version. Duplicate JSON keys and non-JSON NaN/Infinity
tokens also require the existing strict JSON decoder. Schema validation does not
replace Python decoding or establish universal parser-language equivalence. The
Python model, registry declarations, producer ownership and existing schemas are
unchanged; downstream adoption and REAL integrated acceptance remain pending.

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
consumers accept new payloads: consumer tests remain required. Explicit version-policy
enforcement and its CI adapter are described below.

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

## Explicit major-version policy gate

`enforce_version_policy(old_id, new_id, compatibility_result)` returns `None` only
when the version transition is permitted; otherwise it raises `ContractError`:

- Breaking change with the same major: `BREAKING_CHANGE_REQUIRES_MAJOR`.
- Verified breaking change with any higher major of the same family: allowed.
- Verified non-breaking change with the same or a higher major: allowed.
- Lower major: `VERSION_ROLLBACK`; different family: `CONTRACT_FAMILY_MISMATCH`.
- Unverifiable, missing, foreign or malformed result: `COMPATIBILITY_UNVERIFIABLE`,
  including when a major increase was proposed.

Pass a result from the existing comparison APIs, using `compare_schema_files` for
hash-verified package references or `compare_contracts` for declared authority and
semantics. The gate does not alter a breaking classification, bypass loading, mutate
versions or deprecate a contract. `Registry` independently retains its existing
replacement-existence and later-major/same-family checks. The `is_successor` helper
continues to identify exactly the next major; this gate accepts any higher major.
Neither the gate nor a passing result claims consumer acceptance or WP completion.

## CI contract gate (CHG-032)

The existing `t1-contract` job checks out full history and runs
`PYTHONPATH=packages/contracts/src uv run --project ci --locked python -m cap_contracts.ci_gate`.
`CONTRACT_BASE` comes from the PR base SHA or push-before SHA; an empty/new-branch
value uses the merge base with `origin/main`. A local invocation can supply
`--base <revision>`. Missing history fails closed; the adapter fetches no network data.

The adapter reads **committed Git blobs** at the base and `HEAD`, materializing only
registry entries, explicit approvals and pinned schema/fixture files in temporary
directories. It ignores worktree/untracked files, rejects symlinks/submodules and
reuses `Registry.verify`, `load_schema`, `compare_contracts` and
`enforce_version_policy`; it contains no schema-compatibility algorithm.

`schema-refs.json` at this package root is an array of existing `{path, sha256}`
FileRefs approving package-local dependencies. Its absence means no approved file
references (including on historical bases). Every listed file is hash-verified and
resolved, including unused approvals. Missing or duplicate approvals fail closed.
Schemas and fixtures retain their declaration pins.

Both snapshots undergo registry/schema/fixture validation. Exact unchanged
declarations and resolved documents are reported as unchanged, without claiming a
new compatibility decision for unsupported schema keywords. Changed declarations
are compared to their previous version; an added major is compared to the highest
base major of its family. A new family has no predecessor: it receives boundary
validation and an explicit added count, with no previous-version compatibility
claim. Removing a previous declaration fails closed; no removal policy is inferred.

Output is one deterministic `cap-contract-ci-v1` JSON object with counts, PASS/FAIL
and stable failure codes/stages/contract IDs. Payload values, parser exceptions and
compatibility reason text are omitted. Invalid or unverifiable changed contracts
fail even with a major increase. Only this package and its registered/pinned files
are read; unrelated CI jobs and the existing generic schema tier are unchanged.

The workflow is a pinned host-policy source. CHG-032 records its impact and requires
a supported merged-source policy refresh after eventual merge; this source-only
slice performs no installed-policy, Plane or lifecycle mutation. CI execution and
full WP acceptance remain separate evidence.

## Registered producer authority

`producer-authorities.json` records explicit producer ownership separately from
contract declarations. The initial binding comes from 02's Data / Semantic Authority
Map and Canonical Producer Rule, together with the producer-owned
`services/manufacturing-core/contracts/v1/README.md`: `manufacturing-core`, Asrın
Dündar, the `core.order-query` family, QUERY semantics and its exact read-only
authority. Its published schemas/fixtures belong under
`services/manufacturing-core/contracts/`. No other producer/family is inferred.

`ProducerAuthorities.load(path)` checks the model;
`Registry.verify_authorities(model, repo_root=...)` checks every declaration.
Producer, semantic owner, family, contract type and authority must match exactly.
Unknown producers/families, missing/placeholder metadata, duplicate producers or
families, overlapping source ownership and consumer claims fail closed. Root schema
and fixture paths must belong to the registered producer, and physical containment
is checked when `repo_root` is supplied. Shared transitive schema libraries remain
subject to the existing explicit reference approvals and hash verification.

The CI gate requires the candidate's committed model and performs these checks
before schema comparison or unchanged-contract selection. Existing baseline models
are validated independently; a historical base predating the model is checked
against the explicit candidate model, with no declaration exempted. Missing candidate
models and malformed/conflicting registrations fail closed. The Git snapshot reader
includes the model as a regular blob and retains its symlink rejection.

Declaration parsing and schema/fixture verification remain separate primitives;
callers outside the gate invoke `verify_authorities` explicitly. These are static
catalog and artifact-ownership checks, not authenticated publisher identity, runtime
authorization, broker enforcement or ACL derivation. A package/service cannot obtain
a registered family's authority merely by editing its declaration fields or placing
foreign files behind a producer label. Changing the ownership model itself requires
canonical ownership evidence and applicable docs/09 change control; it is not a
self-registration API. No Core schema, fixture or declaration changes in this slice.

## Pre-freeze naming validation

The existing names are already aligned: `core.order-query` is the contract family,
`core.order-query.v1` is its versioned identity, and `manufacturing-core` is its
registered producer. These fields represent different concepts; no alias or rename
is introduced. Human titles, semantic-owner names and existing consumer display
labels retain their meaning and spelling.

The established contract-ID grammar is unchanged. Declaration `version` must equal
the parsed ID major, and authority-family bindings match the parsed family exactly.
Producer machine identifiers use lower-case ASCII kebab case
(`[a-z][a-z0-9]*(?:-[a-z0-9]+)*`), shared by declarations and ownership registration.
Case folding, underscore/space substitution, Unicode lookalikes and implicit aliases
are rejected rather than normalized.

A programmatic registry key must equal its declaration's exact ID, with a matching
integer major and canonical producer name. File-backed registries retain their exact
`<contract_id>.json` filename rule and now reject duplicate JSON fields before a
last-value interpretation can hide an ambiguous identity. Duplicate family ownership
remains rejected by the existing producer-authority model. Existing declarations,
producer bindings, schemas, fixtures and their hashes are unchanged.

## Versioned StreamDefinition and subject bindings

`StreamDefinitions(mapping, registry, authorities)` validates the definition-only
`cap-stream-definitions-v1` catalog (`schema_version`, nonempty `streams`). Use this
catalog constructor for the global ownership check; `StreamDefinition.from_mapping`
and `SubjectBinding.from_mapping` validate individual records against the same
registry and producer-ownership model. Typed records are immutable after validation.
`to_json()` emits sorted, compact JSON; input order has no semantic significance.
These mapping APIs perform no broker operations or filesystem loading; the strict
local file loader is described below.

Each stream requires the specification's complete minimum metadata: `stream_id`,
`stream_class`, `semantic_owner`, `allowed_publishers`, `known_consumers`,
`partition_key_policy`, `ordering_scope`, `retention_class`, `replay_policy`,
`schema_family`, `data_classification`, `message_size_class`, `dlq_policy`, plus
integer `version` and nonempty `bindings`. Missing/unknown fields, duplicate names,
blank/placeholder metadata and undeclared consumers fail closed. Policy strings
are explicit semantic declarations, not inferred NATS configuration or validated
runtime settings. Consumers retain the registry's exact display labels.

Each binding requires `binding_id`, integer `version`, `contract_id`, `schema_family`,
`subject` and `canonical_producer`. Binding identities reuse `<family>.v<major>`;
family and major must exactly match the referenced registered contract. In v1 there
is one active binding per contract version. A stream's own version must match its
`stream_id` major; stream-definition and payload versions are independent.

Subjects are exact lower-case ASCII dot-separated literals, with at least two
segments. Segments follow `[a-z][a-z0-9]*(?:-[a-z0-9]+)*`. No case folding, aliases,
whitespace, empty segments, `*`, `>` or inline wildcard override is accepted. The
subject need not encode the family/version: its explicit binding is authoritative.
This format defines no production subject namespace. Canonical wildcard ownership
is not defined by this format and would require a separate explicit contract.

A binding resolves one exact contract version and validates its registered producer,
owner, authority and source ownership with `ProducerAuthorities.validate`. Its
producer must match exactly; stream publishers must equal the bound producers,
with no extra grants. Stream owner/family must match every bound declaration.
Duplicate subjects anywhere in the active catalog are rejected even for the same
producer; duplicate binding and stream identities are also rejected. A changed
owner cannot hide behind another stream or binding version.

This initial subset supports ASYNC EVENT / DOMAIN_EVENT and ASYNC COMMAND /
WORK_COMMAND. Retention classes are DOMAIN_CRITICAL/DOMAIN_STANDARD for events and
WORK_OPERATIONAL for commands; classifications are PUBLIC_INTERNAL, INTERNAL or
SENSITIVE. Other classes, including telemetry and Oracle, fail closed until their
specific binding contracts are implemented. The real `core.order-query.v1` remains
a synchronous query and cannot be registered as a publishable event. Tests use
synthetic async contracts; no production stream or subject is registered here.

Registry hash/schema/reference verification remains a separate prerequisite via
`Registry.verify` and the existing gate. This model does not replace that verification
or certify artifact validity, authenticated publishers, NATS/JetStream readiness,
consumer integration, ACL enforcement or freeze readiness. Approved production
bindings remain subsequent work; final ACL derivation requires those explicit
validated bindings.

## Local StreamDefinition catalog loading and gate validation

`StreamDefinitions.load(repo_root, registry, authorities)` reads only
`packages/contracts/stream-definitions.json` beneath the trusted repository root.
This fixed package location is the approved catalog source; arbitrary filenames,
includes, URL fetching and directory discovery are unsupported. Every path component
below the root must be a regular directory, ending in a regular UTF-8 JSON file.
Symlinks (including dangling links and parent-directory links), directories in place
of the file, malformed JSON, duplicate JSON keys at any depth and nonfinite JSON
constants are rejected. The standalone loader rejects a missing file with
`STREAM_CATALOG_MISSING`.

The entire document passes through the existing `StreamDefinitions` model. No
partial catalog is returned on failure: every binding must resolve its exact
contract family/version and registered producer, and global identity/subject
ownership checks apply across all streams. `to_json()` retains deterministic
sorting of streams, bindings, publisher/consumer lists and object keys.

The existing contract CI entrypoint includes the catalog's committed Git blob in
each snapshot and validates it after the registry's authority, schema, reference,
fixture and hash checks. Present catalogs are always checked, including unchanged
ones. A malformed catalog cannot be hidden behind the unchanged-contract shortcut
or repaired with an uncommitted worktree copy. The existing deterministic report
uses stable failure codes and stages without catalog contents or payload values;
its existing counts still describe contract declarations.

Pre-catalog history and packages without registered subject bindings may omit the
file; absence registers no bindings and certifies no subject readiness. Once the
baseline contains a catalog, candidate removal fails with `STREAM_CATALOG_REMOVED`.
Empty, incomplete or invalid present catalogs fail closed. No production catalog is
introduced by this slice because the real Core exemplar is a synchronous query.
No workflow, runtime configuration, broker stream or final ACL is changed.

## Pure publisher permissions

`PublisherPermissions(validated_catalog, registry, authorities)` revalidates the
catalog against the supplied canonical registry/ownership snapshot and derives
`cap-publisher-permissions-v1`: sorted producer records with sorted exact subject
lists. Only each binding's canonical producer receives its subject. Consumer labels,
stream consumer lists, wildcard patterns and implicit aliases confer no publishing
permission. `allows_publish(producer, subject)` denies unknown names/subjects,
patterns and malformed inputs; `to_json()` is deterministic.

This is a semantic policy projection for later runtime application, not a NATS
user/account configuration, authenticated service-identity binding, subscribe ACL,
stream provisioner or live installation. Callers retain the existing registry
artifact/hash/reference verification prerequisites. Real production bindings and
broker enforcement remain external integration work; synthetic unit fixtures are
not runtime acceptance evidence.
