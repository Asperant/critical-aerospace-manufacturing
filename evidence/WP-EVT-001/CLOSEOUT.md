# WP-EVT-001 owner implementation and acceptance assessment

Accountable owner: Asrın Dündar, acting through the authorized development session.
Assessment date: 2026-10-25. Implementation branch:
wp/WP-EVT-001-event-contracts. This is a scope assessment, not a DONE certificate.

Owner-executable implementation work: NONE

## Canonical scope review (one review after the final implementation batch)

Reviewed WP-EVT-001's WBS card, FR-EVT-001/006/008, NFR-DATA-005,
DN-EVT-CONTRACTS/DEP-021/023/031 and applicable DOD-WP-01/02/03/05/06/12.
Registry/layout, producer/consumer boundary primitives, pinned local references,
resolved compatibility, major-version enforcement, CI adapter, explicit producer
ownership, naming validation and the StreamDefinition catalog are implemented in
packages/contracts. The final batch adds pure PublisherPermissions from validated
canonical bindings, with current-registry revalidation and exact default-deny
lookup. Consumers acquire no publish rights by appearing in consumer metadata.

The projection emits deterministic cap-publisher-permissions-v1 JSON: producers
and their exact owned subjects. It does not infer broker users/accounts, install
ACLs, provision streams, introduce runtime subjects or grant subscribe authority.
The existing real core.order-query.v1 remains a synchronous read contract. Async
unit inputs are synthetic and are not promoted to production bindings.

No further implementation inside this WP can truthfully supply missing external
production contracts, broker enforcement or integrated acceptance. Envelope
implementation belongs to WP-EVT-002; Core events/outbox and actual consumer
adoption belong to their respective work packages. Expanding those here would
cross the requested work-package/runtime boundary.

## Evidence and focused verification

RUN-EVT-001-LOCAL-001 identifies this scoped development execution and the historical
slice runs below, not a sealed EvidenceID or final acceptance run.

- Final batch: pinned `uv run --project ci --locked pytest -c ci/pyproject.toml
  ci/tests/test_contract_publisher_permissions.py
  ci/tests/test_contract_subject_bindings.py
  ci/tests/test_contract_stream_catalog.py -q`: 86 passed in 1.03s; 18 projection
  cases plus 68 focused binding/catalog regressions.
- Changed permissions.py, package __init__.py and projection tests: Ruff check,
  Ruff format check and Pyright pass, zero type errors/warnings/informations.
- `projectctl validate`: PASS after scoped WBS/RTM reconciliation.
- `check_test_strategy.py`: PASS, 99 test files / 17 suites / zero violations.
- `git diff --check`: PASS.
- Prior actual runs, limitations and implementation bases are preserved in SLICE1,
  COMPATIBILITY-SLICE, SCHEMA-REFERENCE-SLICE, RESOLVED-COMPATIBILITY-SLICE,
  VERSION-RULE-SLICE, CI-GATE-SLICE, PRODUCER-AUTHORITY-SLICE, NAMING-SLICE,
  SUBJECT-BINDING-SLICE and STREAM-CATALOG-SLICE in this directory.

No broad local suite was run for this batch. Remote required CI, merge and
post-merge validation must be checked against their actual revisions; their future
success is not asserted in this committed assessment.

## Acceptance disposition and exact limitations

| Criterion | Disposition | Assessment |
|---|---|---|
| DOD-WP-01 | PENDING | Owner registry/policy primitives exist; full cross-boundary behavior and production event/subject bindings are not demonstrated. |
| DOD-WP-02 | PASS | Scoped WBS reference and FR-EVT-001/006/008, NFR-DATA-005 trace refs/runs are reconciled; evidence remains EVIDENCE_PENDING, final measurements remain unobserved. |
| DOD-WP-03 | PENDING | Actual current-head required CI and post-merge runs must supply the result. |
| DOD-WP-05 | PENDING | Real downstream services, broker authority installation and integrated scenario acceptance remain unverified. |
| DOD-WP-06 | N/A | This package is pure contract/policy tooling, with deterministic redacted gate errors; it creates no runtime service or health endpoint. Runtime observability belongs to actual consumers/runtime WPs. |
| DOD-WP-12 | PASS | Synthetic examples are unit evidence only; no milestone, integration, freeze or final evidence claim is derived from them. |

DN-EVT-CONTRACTS is explicitly the envelope + domain events + IC registry node.
This WP's registry/policy subset does not establish the complete node at
CONTRACT_READY. In particular, DEP-031 cannot unlock TWIN-001 merely because this
registry merges; the required envelope/domain-event version, tests and example
fixture must actually exist and be accepted for that consumer. DEP-023 also
requires that complete contract before event-spine integration. The query-only
START exemplar accepted under DEP-021 does not globally promote Core readiness.

External integrated acceptance includes DN-RT-NATS@INTEGRATION_READY (DEP-025),
DN-CORE-OUTBOX@INTEGRATION_READY (DEP-024), production async declarations and real
consumer adoption. These are not manufactured by this package. A post-merge
VALIDATING + BLOCKED/deferred assessment is appropriate only when the actual
lifecycle, merged PR, successful post-merge CI and source-binding checks support
it; no deferred slot release is claimed here in advance.

CHG-032 requires the supported policy/reference refresh from clean merged main
before affected lifecycle/deferred-wait evaluation. This session observed that
administrator authentication is required for privileged installer execution;
there is no credential/authentication repair in scope. Failure to perform that
refresh is an operational closeout blocker, not a reason to waive policy checks.
