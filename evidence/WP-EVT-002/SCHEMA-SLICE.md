# WP-EVT-002 — envelope metadata schema and canonical fixtures

Accountable owner: Asrın Dündar (Asperant), authorized development session.
Branch: wp/WP-EVT-002-typed-envelope. Slice-1 base:
`fb552ba17acf62a009046794b5a87f7f9b2f8139`. This evidence belongs to its
containing implementation commit; it is not full WP acceptance or DONE.

## Scope and artifacts

The existing typed model is unchanged. The new JSON Schema 2020-12 artifact is
`packages/contracts/schemas/event-envelope.v1.schema.json`; internal `$defs` reuse
nonblank identity, typed opaque reference and explicit UTC/simulation occurrence
shapes. All eleven envelope fields are required; null root causation is explicit.
Nested records are closed. SchemaVersion is a positive integer; entity revisions
remain opaque strings. Simulation seconds have a finite binary64 range and no
invented nonnegative restriction or UTC epoch. UTC calendar/clock validity is
encoded in the schema pattern rather than relying on an unavailable optional
date-time format checker in the pinned toolchain.

`packages/contracts/fixtures/event-envelope.utc.json` and
`packages/contracts/fixtures/event-envelope.simulation.json` are canonical
**SYNTHETIC TEST** metadata examples, not factory observations or production event
declarations. The UTC fixture is a root; the simulation fixture uses the UTC
fixture's EventID as direct causation, preserves their business correlation and
has its own EventID and software TraceID. Both preserve explicit WorldID, opaque
entity/revision and UTC observation. No payload schemas, registry/producer
declarations, HTTP propagation, NATS/broker, outbox or ACL are added.

The accepted consumer-limited DEP-021 scope from the READY and START assessments
remains unchanged. No lifecycle operation, PR or new readiness declaration is
part of this slice. Existing Core contracts and all prior schemas are unchanged.

## Actual focused verification

Run label: RUN-EVT-002-SCHEMA-LOCAL-001 (engineering label, not a sealed EvidenceID).
Repository-pinned toolchain: `uv run --project ci --locked`, Python 3.11.

- `pytest -c ci/pyproject.toml ci/tests/test_event_envelope.py -q`:
  **156 passed in 0.61s**. Existing TEST-EVT-002-001 asset covers planned
  TEST-EVT-ENVELOPE / TEST-DATA-TIME families at isolated unit/fixture boundary.
- Changed-file Pyright (`ci/tests/test_event_envelope.py`):
  **0 errors, 0 warnings, 0 informations**.
- Changed-file Ruff lint/format and `git diff --check` passed before commit.

Tests schema-check the artifact, compare required/model field sets, independently
validate model output, decode and round-trip both fixtures, and preserve all four
ID roles, world, opaque reference/revision and clock meanings. Existing and new
mutations check missing fields (including WorldID), malformed identities and
revisions, closed top-level/nested records, malformed reference arrays, missing
simulation scope, calendar/leap-year boundaries and UTC-only clocks. Both standard
schema validation and the Python model reject the requested negative cases.
Negative fixtures are generated in tests, not committed as redundant full records.

The first focused run passed all 156 tests; changed-file typing initially found
eight partially typed methods from jsonschema's annotations. A local typed
Protocol/cast describes that existing test validator API without changing runtime
behavior or suppressing checks. Final focused tests and typing passed as above.
No broad/full suite, infrastructure test or scenario was run.

## Parity boundary and remaining obligations

This is canonical-wire and named-negative-case parity, not a universal equivalence
proof for the Python and JSON Schema input languages. The unchanged Python ISO
decoder permits additional timestamp spellings outside the published canonical
wire pattern. JSON Schema integer values include `1.0`, while Python's existing
model insists on an actual `int`. Duplicate-key and non-JSON NaN/Infinity token
checks remain in strict JSON decoding; JSON Schema is not a text parser. Consumers
must retain Python semantic/decoder validation; the standalone schema is not a
replacement for it. These limits are also published in the package README.

Production event-specific entity/cardinality, publisher authentication, subject
binding, HTTP/NATS/Temporal propagation and actual downstream adoption remain
unimplemented/unverified. This slice certifies no REAL acceptance, complete
DN-EVT-CONTRACTS readiness, requirement verification, post-merge evidence or WP
DoD. No canonical scope/architecture conflict was found for this publication.
