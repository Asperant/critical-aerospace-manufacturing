# WP-EVT-002 — final currently executable owner-scope assessment

Accountable owner: Asrın Dündar (Asperant), authorized development session.
Assessment date: 2026-10-25. Branch: wp/WP-EVT-002-typed-envelope.
Assessed implementation/trace head: `354671b7e04f831a03139f50176a7fa1604a87d0`.
Current main incorporated without conflict:
`13477c59ccf2936421095ee06dbe053f2de1b9b4`, followed by
`328052282fb3e5b660fb9be2009d24feb6a74dc5` (observability coverage metadata).
Assessment revision is this file's containing commit, not a fabricated self-hash.

Owner-executable implementation work: NONE

This means no further implementation is currently executable with the published
bindings. It does not mean every canonical deliverable is implemented: actual
HTTP/NATS/Temporal context propagation remains unimplemented until the external
producer/consumer/transport contracts and hooks exist. These obligations remain
owned by WP-EVT-002, with real downstream adoption and verification still required.
This is not a DONE assessment, global readiness assertion or slot-release proof.

## Implemented scope and exact source evidence

The typed envelope, explicit EventID/business-correlation/direct-causation/software
trace roles, UTC versus simulation clock semantics, opaque identity/revision
references and strict required-field validation are in
`packages/contracts/src/cap_contracts/envelope.py` and its package exports.
`packages/contracts/schemas/event-envelope.v1.schema.json` and the canonical
`packages/contracts/fixtures/event-envelope.utc.json` /
`packages/contracts/fixtures/event-envelope.simulation.json` publish metadata-only
contracts. `validate_world_scope` provides exact consumer expected-world checking
without coercion or metadata mutation. These are library primitives, not runtime
adapters, production payloads, authenticated publishing authority or state changes.

Historical implementation commits are `fb552ba17acf62a009046794b5a87f7f9b2f8139`,
`82d108ce844dc501c7ee876def836b6dcd624abf` and
`ea8f6043b23588b496eda593e8c306b0b5c3c357`. Tests are
`ci/tests/test_event_envelope.py`, asset TEST-EVT-002-001, planned families
TEST-EVT-ENVELOPE / TEST-DATA-TIME. Exact per-slice commands/results are preserved
in SLICE1.md, SCHEMA-SLICE.md and WORLD-SCOPE-SLICE.md in this directory.
TRACE-RECONCILIATION.md at `354671b7e04f831a03139f50176a7fa1604a87d0` maps those
artifacts and executions to FR-EVT-002/003/004 and NFR-DATA-008. All four remain
EVIDENCE_PENDING; the persisted-evidence metric remains unobserved. No sealed
EvidenceID, accepted measurement or VERIFIED requirement is manufactured.

The schema describes canonical wire values. Previously documented Python/schema
input-language differences, strict JSON parsing responsibilities and event-specific
payload/cardinality obligations remain unchanged; see SCHEMA-SLICE.md and README.

## Final focused development verification

After incorporating current main, the following checks actually ran using the
repository-pinned `uv run --project ci --locked` Python 3.11 toolchain:

- `pytest -c ci/pyproject.toml ci/tests/test_event_envelope.py -q`:
  **181 passed in 0.64s**. These are overlapping historical suite coverage plus
  a fresh final local execution, not 181 additional independent research trials.
- Ruff check and Ruff format check on the envelope module, package exports and
  focused test file: **PASS**; three files already formatted.
- Pyright on those same three files: **0 errors, 0 warnings, 0 informations**.
- `projectctl validate --json`: **PASS**.
- `projectctl catalog-lint --base origin/main --json`: **PASS**; canonical source
  gaps remain unresolved and neither readiness nor accepted evidence is certified.
- `git diff --check origin/main`: **PASS**. Actual PR changes were checked for
  secrets and forbidden runtime/generated artifacts; no secrets were found.

No broad/full local suite or infrastructure test was run. Current assessment-head
PR CI and actual merge-revision checks must be observed from GitHub, not inferred
from earlier successful implementation-head CI. No test retry cycle is requested.

## Remaining external inputs and unaccepted obligations

| Area | Exact missing input / evidence | Responsible interface |
|---|---|---|
| HTTP propagation | Bound backend producer/consumer request/response contracts, trusted context rules and real adapters; current BFF overview ports have no production backend adapter, and Core query v1 is transport-independent | Asrın's backend/service integration surfaces, with applicable runtime/identity owners |
| NATS propagation | Production event producer/outbox publication, exact subject/stream/durable/publisher bindings and adopted application consumer; EVT-001 supplies static policy and EVT-003 generic JetStream hooks only | Core/event producer owners and Yavuz's broker/runtime integration |
| Temporal propagation | Actual workflow/activity context contracts and hooks/interceptors; no runnable bound workflow target exists in the scoped source | Batuhan's durable workflow/Automation interface, with shared context owned here |
| Trace acceptance | TEST-OBS-TRACEPROP and actual CorrelationID/CausationID/TraceID/WorldID preservation through the above boundaries | Participating producer, transport and consumer owners |
| Time acceptance | Formal persisted UTC/simulation-time evidence and the NFR-DATA-008 zero-ambiguity measurement on its required REAL boundary | Persisting/evidence owners, with NFR owner Yavuz |
| Integrated acceptance | AV-SCEN-01/09/10, real downstream consumer adoption and actual scope enforcement | Participating scenario/consumer owners |
| Operation and release | Applicable runtime correlation logs/health and operator runbooks; required current-head CI, actual merge and post-merge verification | Runtime/service owners and this WP's delivery/evidence work |

No new HARD START edge is invented. DEP-021 was accepted narrowly for this WP's
initial Core identity/revision input, not as global DN-CORE-CONTRACTS readiness.
DN-EVT-CONTRACTS requires envelope plus domain events plus registry: publishing
this envelope alone cannot certify the whole node or unlock Twin/other consumers.
DN-CORE-OUTBOX / DN-RT-NATS integration inputs relate to DEP-024/025 on the event
spine; they are not falsely recast as this WP's own inbound START edges.

| Criterion | Actual disposition |
|---|---|
| DOD-WP-01 | PARTIAL: shared definitions/validation exist; real propagation deliverables remain unimplemented pending bindings. |
| DOD-WP-02 | PASS for scoped trace reconciliation only; all four requirements remain EVIDENCE_PENDING. |
| DOD-WP-03 | PENDING actual current assessment-head required CI and post-merge checks. |
| DOD-WP-04 | PARTIAL: isolated metadata/world negatives pass; real boundary failures remain unverified. |
| DOD-WP-06 | PENDING applicable runtime observability acceptance; no runtime capability endpoint is invented for this pure library. |
| DOD-WP-07 | PARTIAL: library documentation exists; runtime operator/runbook acceptance remains pending. |
| DOD-WP-12 | PASS for this scoped work: synthetic fixtures are labeled and never promoted to final REAL/scenario evidence. |

## Closeout and parking constraints

The implementation/evidence PR can be technically reviewed and merged when its
actual applicable PR gates pass. Successful merge is not WP completion. Required
post-merge verification is the exact merge-revision envelope test/static/trace
checks and successful main CI, with the unresolved real acceptance still explicit.

Any BLOCKED operation must use the actual reason and supported evidence. Missing
bindings still block **implementation of propagation**, not just collection of an
already implemented path's acceptance evidence. They cannot be relabeled as an
acceptance-only wait merely to release an implementation slot. The supported
deferred proof must decide whether the genuine remaining wait is eligible at the
actual lifecycle; this document does not assert CHG-022/CHG-024 eligibility. No
UNBLOCKED/BLOCKED cycle, fabricated own-edge readiness, waived DoD, global node
promotion or DONE is authorized by this assessment.
