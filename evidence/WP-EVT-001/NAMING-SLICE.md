# WP-EVT-001 pre-freeze naming slice

Date: 2026-10-25 (Europe/Istanbul).
Base: ca1ae23a934df9120195e1fa6b7f772999f6090c.
Branch: wp/WP-EVT-001-event-contracts.
Live queue: OK, current WP-EVT-001 IN_PROGRESS, blocked false.
Retrieved projectctl context and inspected only the existing WP-EVT-001 naming
implementation, registry, ownership model and their focused checks. The two cited
GAP-RTM-009/010 rows already state RESOLVED_BY_FINAL_HUMAN_DECISION; this slice
neither reopens their meanings nor changes canonical trace/status documents.

Finding: no actual current-entry rename is needed. core.order-query is the family,
core.order-query.v1 the versioned identity, and manufacturing-core the producer.
Human-readable names/consumer labels are distinct fields, not producer aliases.
No contract, family, producer, authority, schema, fixture or file hash was renamed
or rewritten, and the established contract-ID grammar is unchanged.

Only missing validation was added:

- One lower-case ASCII kebab-case producer-name validator shared by declaration
  parsing, programmatic registries and authority-model loading. Noncanonical aliases
  are rejected, never normalized into an authority-bearing identity.
- Programmatic registry keys must equal parsed contract IDs; declaration majors
  must match the ID's integer major even when constructing typed records directly.
- File registry JSON duplicate fields are rejected before parsing can discard an
  ambiguous identity. Existing filename/ID and duplicate family-ownership rules stay.

Focused verification, pinned `uv run --project ci --locked` toolchain:

- `pytest -c ci/pyproject.toml ci/tests/test_contract_naming.py
  ci/tests/test_contract_producer_authority.py ci/tests/test_contract_ci_gate.py -q`:
  105 passed in 1.14s (41 new naming cases, 64 focused authority/gate regressions).
- `ruff check`, `ruff format --check` and `pyright` on versioning.py, registry.py,
  authority.py and test_contract_naming.py: pass; 4 files formatted and zero type
  errors/warnings/informations.
- Existing core.order-query.v1 passes naming, authority and original file-hash/schema/
  fixture verification through the new focused exemplar test.
- `git diff --check`: pass.

Initial run: 39 tests passed and one new test expected an ownership lookup error
for manufacturing-core.order-query, which the pre-existing first-segment grammar
already rejects. The fixture now uses the syntactically valid but unregistered
manufacturing.core.order-query alias to exercise the intended exact-family check.
One additional test covers noncanonical producer names in programmatic registries.
No existing tests were edited, removed or weakened.

No CI workflow/pinned-source, envelope, broker/NATS, ACL derivation, Plane/lifecycle
or PR work. No broad/full suites, remote CI result, integration acceptance, global
freeze readiness, full WP verification or DONE is claimed. Canonical document and
architecture semantics remain unchanged; no new ChangeRequest is needed for these
scoped missing checks within the approved registry discipline.
Next smallest slice: review canonical subject/ACL prerequisites before ACL derivation.
