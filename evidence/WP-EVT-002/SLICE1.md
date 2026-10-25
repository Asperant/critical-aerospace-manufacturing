# WP-EVT-002 — typed event envelope foundation

Accountable owner: Asrın Dündar (Asperant), authorized development session.
Branch: wp/WP-EVT-002-typed-envelope. Base canonical main:
`a45f7f61c85604eba27af68ac99466748de2686d`. Implementation revision is the
commit containing this evidence. This is Slice 1, not WP acceptance or DONE.

## Accepted START input and bounded scope

The unedited owner assessment at
https://github.com/Asperant/critical-aerospace-manufacturing/pull/24#issuecomment-6397659998
accepts DEP-021 narrowly for WP-EVT-002's initial envelope metadata task:
`core.order-query.v1` contract_version, opaque nonblank entity id/revision strings
and reference identity semantics, with the merged schema and normal/reentrant
fixtures. No Core command/domain-event/outbox, aggregate counter, WorldID,
freshness, production publisher or broker readiness is inferred from that query.
The assessment is not a global DN-CORE-CONTRACTS readiness declaration.

This slice implements immutable typed envelope metadata, distinct event/business
correlation/direct causation/software trace roles, UUID4 generation for new events,
strict required-field decoding, operational WorldID, explicit UTC versus simulation
occurrence and UTC observation, and typed opaque entity/revision references.
Root causation is explicitly null. Simulation occurrence is finite seconds on an
explicit simulation run, not calendar time. No local-clock default or conversion
from observation to occurrence exists. See the package README for representation.

Entity references preserve all six accepted Core identity types from both real
versioned query fixtures (the data are synthetic development examples, not real
factory facts). The generic envelope does not determine business-specific entity
cardinality, mutation sensitivity or producer authentication. These remain actual
event-owner/consumer obligations. Empty reference tuples are explicit, not an
inferred substitute for required business identities.

## Focused execution evidence

Run label: RUN-EVT-002-SLICE1-LOCAL-001 (engineering label, not a sealed EvidenceID).
Toolchain: repository-pinned `uv run --project ci --locked` on Python 3.11.

- `pytest -c ci/pyproject.toml ci/tests/test_event_envelope.py -q`:
  **103 passed in 0.51s**. Families: TEST-EVT-ENVELOPE, TEST-DATA-TIME;
  concrete asset TEST-EVT-002-001. Isolated unit/fixture boundary only.
- Covered: metadata round-trip; UUID4 creation and replay identity; preserved
  correlation/causation/trace; explicit root causality; missing required fields
  including WorldID; malformed/null identity and opaque entity revisions; Core
  published reference round-trip; UTC/simulation separation; naive/non-UTC and
  ambiguous clocks; missing simulation run; nonfinite numbers; malformed version;
  duplicate/unknown fields and direct-constructor validation.
- Changed-file Pyright: **0 errors, 0 warnings, 0 informations**.
- Changed-file Ruff lint/format and `git diff --check`: recorded in the commit
  after successful execution; no broad suite or infrastructure test was run.

Initial verification exposed incorrect fixture selectors in the new Core-reference
test (102 passed, 1 failed) and five strict typing findings in its traversal. The
test now uses the actual published order/lots/components structure with typed
iteration; the final 103-case run and changed-file typing both pass. No production
contract or acceptance expectation was weakened to resolve these test defects.

## Remaining work and limitations

No production payload schema/declaration, NATS/broker, outbox, HTTP/service or
Temporal propagation, ACL, consumer adoption, state mutation or unrelated contract
change is included. This slice does not demonstrate TEST-OBS-TRACEPROP,
AV-SCEN-01/09/10, REAL time/consumer acceptance, full DN-EVT-CONTRACTS readiness,
post-merge verification or WP DoD. Requirements remain unverified at final scope.
No specification conflict was found for this bounded metadata implementation.

After pushing the implementation commit, a fresh owner-authored DEP-021 assessment
must name WP-EVT-002 and that exact SHA, preserve the accepted narrow scope and
reference artifacts available at that SHA. READY to IN_PROGRESS is then evaluated
through the supported helper using that comment and commit, not this file alone.
