# WP-EVT-003 — owner implementation and acceptance assessment

Accountable owner: Asrın Dündar (Asperant). Date: 2026-10-24.
Assessment revision: this file's containing commit. Design baseline:
`a06927b9ea0abf19d07f76b457faa125f5f4930d`; ledger baseline:
`426013b597d364b76da3615b18fcaa1e41b3ed28`.

## Implemented scope

The common framework in `packages/event-consumer/` now provides validated original
identity, a delivery-local transaction around the existing caller-transaction-owned
ledger, atomic effect/processed-record commit and ACK confirmation only after
commit. Concurrent duplicates serialize before the callback and remain protected
by `(consumer_scope, event_id)` uniqueness. Processing/commit failures roll back and
NAK; ACK failure never erases committed dedup proof. Cancellation settles a running
database transaction without ACK; local shutdown retains the durable consumer.

The JetStream boundary requires explicit external stream/subject/durable,
delivery policy, ACK wait, delivery limit and ACK timeout configuration. It creates
no production streams or ACLs, rejects mismatched existing durable configuration,
and has no hidden retry loop. Generic admission/effect/identity hooks let each
downstream owner supply its real contract, authority, world/branch and order rules.
Replay is denied by default and requires an admitted separate scope/target and
ReplayRun context when enabled. Gap handling is an explicit non-destructive
adapter admission failure; no generic application ordering policy was invented.

The existing t1-static, t1-unit and t1-integration jobs now run the package checks.
Logs carry scope/event/correlation/outcome/duration; local outcome counters are
inspectable through `health()`. The README describes deployment, shutdown,
rollback, poison-message resolution and ledger preservation. No TTL/retention
worker was added. Deletion before the possible replay/redelivery horizon can
permit repeated effects; numeric horizons remain a canonical owner decision.

## Real acceptance and its limits

`RUN-EVT-003-LOCAL-001` is the final local run recorded alongside this assessment
in `LOCAL-VERIFICATION.json`. It uses an isolated real PostgreSQL 18 instance and
real NATS JetStream 2.10.22 (the repository integration-server version), not a fake
bus. The database fixture creates/drops its own database and restricted roles;
each broker test creates/deletes a uniquely named file-backed stream and durable
in a disposable server. The application events/effect rows are synthetic test
probes; they are not factory observations or accepted protected manufacturing
execution. The two pre-existing audit files are excluded from changes.

The focused suite contains 39 cases: six pure checks, 20 PostgreSQL ledger/migration
cases and 13 real PostgreSQL+JetStream cases. Tests cover first commit before ACK
(observed through a separate DB connection), duplicate and concurrent delivery,
scope independence, callback/database/deferred-commit failure, NAK and repair/retry,
durable reconnect/redelivery, process exit code 71 after commit before ACK, consumer
restart, cancelled processing, bounded shutdown, replay isolation/live rejection,
identity validation and gap deferral. In the real crash test a separate consumer
process terminates before sending ACK; the next process sees `num_delivered >= 2`
and the committed ledger suppresses a second effect. Real ACK pending returns to
zero after the successful duplicate acknowledgement.

| Canonical obligation | Actual scope and remaining evidence |
|---|---|
| TEST-EVT-CONSUMER-IDEMP | Real broker/DB common-framework suite supplied; final CI binds the run to its exact head. |
| AV-SCEN-05 | WP-owned duplicate/out-of-order boundary exercised with real infrastructure and synthetic adapter probes. Actual downstream manufacturing projections/commands and scenario composition remain unverified. |
| RES-DUP-001 | Consumer duplicate/crash/restart contribution supplied. Full protected-effect aggregation including Automation retry/restart is not this probe suite and remains outstanding. |
| DEP-023 | Actual event-contract fixtures and consumers at CONTRACT_READY are not certified here. |
| DEP-024 | Actual Core outbox → NATS → promised application consumer INTEGRATION_READY evidence is not supplied by the probe. |
| DEP-025 | Real isolated JetStream is proven locally/in CI; deployed operational routing/runtime INTEGRATION_READY evidence remains separate. |

The checkout has no Twin, Vision, AI, Scheduler or Automation consumer application.
The generic hooks and runbook are executable now; their actual application-owned
admission, local effects, subscriptions and scenario participation cannot be
implemented as invented business semantics in this WP. The corresponding service
owners must provide their real integrations. Full RES-DUP-001 aggregation is
Batuhan's WP-TEST-004 verification work; AV-SCEN-05 integration coordination remains
Asrın's scenario work with the actual participating service owners. This is a
downstream integrated-acceptance wait, not a new START gate or a producer-DONE rule.

## Completion assessment

Owner-executable framework implementation is complete once the final local and
current-head required CI gates pass. No further in-scope primitive/transport work
is identified; downstream service implementation and integrated acceptance must
remain in their owning work packages. Final requirement acceptance is **NOT
VERIFIED**, and WP-EVT-003 must **not** become DONE on the strength of this probe
suite. The WBS repository reference and FR-EVT-005 trace now name real artifacts
and scoped execution while retaining EVIDENCE_PENDING and the unchanged REAL /
EV-L4 / CI + INTEGRATION + EVALUATION acceptance target.

| DoD area | Assessment |
|---|---|
| DOD-WP-01 | Ledger, library and real duplicate/order-boundary suite exist; promised application adoption still needs actual consumer evidence. |
| DOD-WP-02 | Same-PR implementation/test trace references supplied; accepted requirement coverage withheld. |
| DOD-WP-03 | Required final-head CI must be observed before merge; exact run IDs/results belong to the attributable PR assessment. |
| DOD-WP-04 | Relevant rollback, duplication, timeout/cancellation, unavailable database, replay/order rejection and crash paths exercised. |
| DOD-WP-05 | Downstream actual-consumer usability and complete integrated scenario/evaluation evidence missing; post-merge real framework validation still required. |
| DOD-WP-06/07 | Structured logging, counters and operator/developer runbook supplied for the library boundary. |
| DOD-WP-12 | No synthetic application probe is represented as complete integrated manufacturing acceptance. |

After normal merge, validate the actual merged source with the same full suite
against isolated real processes, verify package source hashes and successful main
CI, then record the actual result in the PR. If these pass and the downstream
evidence above remains absent, the appropriate existing projection is
`VALIDATING + BLOCKED / WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE`.
An attributable PR assessment and verified blocker audit are mandatory; this
document alone does not release an execution slot or certify the deferment.

## Verification provenance

Only the final local required run is designated `RUN-EVT-003-LOCAL-001`.
Earlier development runs exposed lint/type issues and a NATS client fetch
cancellation coroutine warning. Bounded fetch settlement corrected that warning;
the final test command treats RuntimeWarning as an error. No required CI retry
loop, test deletion, quarantine or weakened assertion was used.
