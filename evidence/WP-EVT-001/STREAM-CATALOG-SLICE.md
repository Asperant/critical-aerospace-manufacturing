# WP-EVT-001 local StreamDefinition catalog loading and gate slice

Date: 2026-10-25 (Europe/Istanbul).
Base: 90a5df5de32464652520dbd563213997aad0dbdf.
Branch: wp/WP-EVT-001-event-contracts.
Live cap-plane-queue: OK / CURRENT, WP-EVT-001 IN_PROGRESS, blocked false.
Retrieved projectctl context for WP-EVT-001 and inspected its existing registry,
StreamDefinition contract and CI adapter. No Plane/lifecycle writes performed.

Implements the previously documented next slice of the existing StreamDefinition
catalog foundation. Canonical scope remains 01 StreamDefinition minimum metadata,
Canonical Producer Ownership and Contract Naming; 02 registry/versioning and
WP-EVT-001's contracts/compatibility/authority deliverables. The fixed local catalog
location is an implementation detail; no authority, protocol semantics, canonical
specification or policy-pinned source is changed. No change-control ID required.

The strict loader accepts only packages/contracts/stream-definitions.json beneath
the trusted repository root. It rejects nonregular files, parent/file symlinks,
missing files, malformed/non-UTF-8 JSON, duplicate fields and nonfinite constants.
No alternate filenames, external references, includes or directory discovery are
supported. Every present entry goes through the existing StreamDefinition model;
any invalid entry prevents returning a catalog. Existing global binding/subject
ownership, producer, family/version and metadata checks are reused, not duplicated.

The existing CI adapter materializes only the committed approved catalog blob,
rejects unsupported Git source modes, and preserves invalid directory inputs for
rejection rather than treating them as missing. Both baseline and candidate
catalogs are checked before unchanged-contract selection, after existing hash,
fixture, local-schema-reference and authority verification. Failures retain the
existing deterministic stage/code-only report. Worktree replacements are ignored.

Explicit absence policy: pre-catalog snapshots and packages with no bindings may
omit the catalog; omission does not certify subject readiness. The standalone loader
still rejects missing files. Once the baseline has a catalog, removing it from the
candidate is rejected. Present empty or incomplete catalogs are invalid. No real
production bindings are invented from the synchronous core.order-query.v1 exemplar.

Focused checks using the pinned uv CI tooling:

- pytest -c ci/pyproject.toml ci/tests/test_contract_stream_catalog.py
  ci/tests/test_contract_subject_bindings.py ci/tests/test_contract_ci_gate.py -q:
  97 passed in 1.46s (26 new catalog cases; 71 focused model/gate regressions).
- New cases cover valid multi-entry loads/gates, global duplicate IDs and conflicting
  subjects, unknown producers, malformed entries/JSON, version/family mismatch,
  deterministic order/reporting, one-invalid-entry atomic rejection, source/path
  restrictions, duplicate JSON fields, absent/removal policy, drift preservation
  and committed CLI snapshots with redacted failures.
- ruff check / ruff format --check on streams.py, ci_gate.py and the new test: pass;
  three files already formatted.
- pyright on the same three changed Python files: zero errors/warnings/informations.
- git diff --check: pass.

Initial run: 16 new cases passed, 9 failed because the synthetic file-backed test
records omitted required fixture payloads. Added real hash-pinned synthetic fixture
files so registry verification can succeed before reaching the catalog assertions.
The final run includes an additional unknown registered-producer test and positive
CLI assertions. No existing test was edited, removed or weakened.

No ACL derivation, envelope, NATS runtime, stream/subject creation, CI workflow edit,
PR, broad/full suite or Plane/lifecycle change. No remote CI, integrated consumer
acceptance, runtime readiness, freeze readiness or full WP completion is claimed.
Next smallest slice: pure publisher-permission projection from a validated catalog;
production ACL enforcement still requires explicit production bindings and runtime
identity contracts.
