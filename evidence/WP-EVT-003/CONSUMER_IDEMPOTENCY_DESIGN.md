# WP-EVT-003 Slice 1 — Consumer idempotency design

Date: 2026-10-24. Owner: Asrın Dündar. Supporting reviewer: Batuhan Kaya.
Scope: the first canonical task, `design dedup key and retention`.
Design baseline: `1c03d456df3308d495796538d59390e14594bb9c`.
This is a scoped implementation design derived from the sources below, not a
replacement canonical specification or a change to event contracts. No product
code, adapters, migration, runtime execution or acceptance evidence is produced.
Tests: **NOT_EXECUTED**. Whole-WP acceptance: **NOT_VERIFIED**.

## Exact source and acceptance references

- [FR-EVT-005](../../docs/01_Master_Project_Specification.md):
  the requirement row at line 169914 requires at-least-once delivery without
  duplicating protected domain effects.
- [WP-EVT-003](../../docs/04_Work_Breakdown_Structure.md#wp-evt-003--idempotent-consumer-framework),
  lines 836–877: design dedup key and retention; deliver processed-message ledger,
  consumer base library and real-JetStream duplicate/out-of-order suite; later
  adoption in Twin, Vision, AI, Scheduler and Automation.
- [ARCH-EVT-CONSUMER allocation and FR-EVT-005 acceptance](../../docs/03_Requirements_Traceability_Matrix.md),
  allocation row at line 863 and requirement block at lines 4166–4177:
  `TEST-EVT-CONSUMER-IDEMP`, `RES-DUP-001`, `AV-SCEN-05`;
  final boundary `REAL`, evidence target `EV-L4`, environments
  `CI + INTEGRATION + EVALUATION`.
- [Consumer delivery mechanism](../../docs/02_System_Architecture_Specification.md),
  lines 1569–1585: `event_id` identity, inbox pattern, projection and ledger local
  commit before ACK; retry/re-drive identity preservation; replay protection;
  aggregate ordering/gap detection. Lines 1200–1207 define normal duplicate
  delivery and limited retry/quarantine handling.
- [Exact verification-family rows](../../docs/03_Requirements_Traceability_Matrix.md),
  lines 2197, 2307 and 2365: real NATS JetStream in CI, duplicate/out-of-order
  scenario in INTEGRATION, protected-effect suite aggregation in EVALUATION.
  This design does not satisfy those execution obligations. No JetStream run is
  required or claimed for this design slice.

## Identity and ledger scope

The dedup identity is the original immutable **`event_id`**. Broker sequence,
delivery attempt, correlation ID, timestamp, payload hash and aggregate version
must never replace it. Retry and DLQ re-drive preserve the original ID.

The logical ledger key is **`(consumer_scope, event_id)`**, enforced by a durable
database uniqueness constraint. `consumer_scope` identifies one stable logical
handler and its target store/projection generation within the owning service.
It is configured by the adapter, not selected by an incoming message. Replicas,
workers, restarts, deployments, retries and broker subscription recreation that
serve that same target use the same scope. A delivery attempt or process ID must
never create a new scope. Different independent consumers each process the same
event once in their own scope; one consumer's ledger cannot suppress another.

Each consumer owns its ledger in its own local transactional store; this design
does not introduce a shared cross-service database authority. The minimum logical
processed record contains the composite key and local commit-associated processing
metadata, including `processed_at`. That timestamp describes processing, not domain
occurrence or simulation time. Physical table/type/index names and scope encoding
are later implementation details; no external event-envelope schema changes.

A rebuild/shadow projection has a distinct, explicitly bound target generation
and ledger scope. This permits reconstruction while retaining the live target's
dedup history. Changing scope is never a way to re-enable a protected live effect.
World/branch and replay-target admission remain adapter responsibilities; the scope
must not bypass them. No new claim about global event-ID generation is made.

## Transaction, duplicates and concurrent delivery

For an admitted event, the canonical order is:

1. Receive and validate delivery context; begin the consumer's local transaction.
2. Check the processed ledger for `(consumer_scope, event_id)`.
3. If absent, validate ordering and perform the local domain/projection update.
4. Insert the processed record under the unique composite key.
5. Commit the local update and processed record together.
6. Only after successful commit, ACK/checkpoint the delivery.

A committed duplicate performs no domain update and creates no second processed
record. ACK follows successful confirmation of that committed record. An
uncommitted record or a failed lookup never proves completion and never authorizes
an ACK. A ledger-store outage fails processing rather than falling back to an
in-memory dedup set.

The unique key is the final concurrent-duplicate arbiter, not an unchecked
check-then-insert convention. Two workers may initially observe absence, but only
one may commit the effect plus processed record. A losing uniqueness attempt
rolls back its **entire transaction**, including its tentative local update, then
reads the committed record in a fresh transaction before treating delivery as a
duplicate. A lock/deadlock/serialization failure requires rollback and retry;
it must not be reclassified as successful dedup without committed proof. Ordering
state also needs transactional concurrency control within its aggregate scope;
event uniqueness alone does not serialize distinct events for one aggregate.

The adapter's domain effect and the ledger write must use the **same local
transaction and connection**. A handler must not independently commit, mutate
another service's canonical state or perform an irreversible external action
inside this callback. Where processing emits work, the local outbox intent is
written atomically with the local update and ledger; remote delivery/execution is
outside this transaction and retains its own protected-action idempotency,
authorization and effect-verification obligations. The primitive cannot claim
atomicity across a database, broker and external action.

| Failure point | Required result |
|---|---|
| Before commit, including handler/ledger failure | Roll back both local effect and ledger; no success ACK; retry can process the original ID. |
| Commit succeeds; crash or ACK failure follows | Redelivery sees committed ledger, skips effect and ACKs; state converges. |
| Commit outcome is unknown to caller | Do not claim success or repeat an external effect; resolve through durable ledger on retry before ACK. |
| Two copies race | At most one effect-plus-ledger transaction commits; loser rolls back and confirms winner or retries. |

## Retry, replay and ordering

Transient failure retries preserve the key and do not pre-mark an event processed.
Permanent/poison events follow limited retry, quarantine/DLQ and controlled
resolution/re-drive; the shared primitive must not invent retry counts or backoff
durations. Quarantine is not evidence that the domain effect committed. Terminal
broker disposition requires the adapter's durable quarantine policy and must not
masquerade as a successful processed record.

Replay delivery is explicit context associated with the governed `ReplayRun` and
target, never inferred from arrival time or a modified payload/event ID. Operational
side-effect adapters reject arbitrary historical replay **before** dispatching the
handler, regardless of whether the ledger contains the event. Replay to a permitted
rebuild/shadow projection uses its bound target scope and cannot emit live protected
actions or external notifications. Dedup alone is not replay authorization.

There is no global event order. A duplicate `event_id` is resolved by the ledger;
for a new ID, the adapter checks the declared aggregate/partition scope and
`aggregate_version`. A forward version gap cannot be silently applied as current.
Buffering, marking stale, reconciliation or authoritative reload is required;
Twin specifically marks the affected projection not-fresh. Older versions cannot
blindly overwrite newer state. Adapter-specific handling must distinguish safely
ignored stale input from still-required domain work. A buffered/unresolved gap
must not get a successful processed record: either defer without success ACK or
atomically persist a durable pending handoff whose completion remains trackable.
The latter handoff is outside this first code slice. No timeout or permissible gap
size is invented here.

## Retention and replay after retention

The cited canonical sources define no numeric processed-ledger TTL, deletion age,
maximum retry/redelivery age or replay horizon. Broker retention classes are not
processed-ledger retention limits. Published facts do not expire semantically when
broker retention ends.

The requirement boundary is: removal of dedup proof must never permit another
protected effect for the same logical consumer and event. Therefore this design
authorizes **no automatic age-based ledger deletion** until a retention policy can
demonstrate that boundary across redelivery, re-drive, restart, restore and replay.
This is a conservative implementation constraint pending the decisions below,
not a newly asserted canonical infinite-retention requirement or a chosen TTL.

Deleting a row makes a late delivery indistinguishable from first processing in
that ledger. A longer-lived archive or older broker message can then cause a
second effect; keeping the same `event_id` alone does not prevent it. Live-side
replay rejection remains mandatory even when the row is gone. Projection rebuilds
use an explicitly separate target, not deletion of the live ledger. Any future
cleanup/compaction must preserve sufficient durable dedup proof or an evidenced
admission boundary that rejects every unsafe old delivery; elapsed time alone is
not proof. No cleanup code belongs in the next smallest slice.

## Shared primitive and adapter boundary

The common primitive provides consumer-scoped durable duplicate detection, the
transaction/effect/ledger discipline, concurrent-conflict handling and explicit
outcomes sufficient to ACK only committed processing or a confirmed duplicate.
It accepts the adapter's stable scope, original event identity, validated delivery
context and local transactional callback. It does not prescribe a service's
business transitions, event schema, subscription topology or replay permission.

| Adapter | Responsibilities retained by the owning service |
|---|---|
| Twin | Projection target/generation, ordering and freshness, rebuild admission; no manufacturing authority. |
| Vision | Inspection/perception-local effects and publication intent; no direct canonical manufacturing mutation. |
| AI | Local intelligence records/proposals; no independent protected execution. |
| Scheduler | Candidate-plan state; a consumed event does not activate a schedule. |
| Automation | Governed workflow dispatch, replay rejection, exact approval binding, authorization and verified effects. |

All adapters retain world/branch admission and payload validation. Each must use
the primitive in its own transaction; merely calling a dedup lookup around an
independently committed handler is not adoption. No adapter code is supplied here.

## Unresolved decisions and next slice

**OWNER_DECISION_REQUIRED — Asrın, with applicable consumer owners:** numeric
ledger retention/cleanup policy and proof of safe old-delivery rejection; admitted
retry/re-drive/replay horizons; final stable scope registration/target-generation
lifecycle; adapter-specific gap/stale dispositions and retry/quarantine limits
where the cited canonical sources provide no exact value. None may be replaced
with an invented duration, count or automatic scope rotation. These do not prevent
an isolated primitive slice with cleanup disabled and unresolved deliveries failing
closed; they do prevent claiming completed production policies or final acceptance.

Next smallest code slice: a local PostgreSQL processed-ledger primitive with the
composite unique key and transactional callback, plus focused real-database tests
for rollback, concurrent duplicates and committed-redelivery handling. No consumer
adoption, replay orchestration, ledger purge or external effect execution in that
slice. Broker ACK integration and real-JetStream acceptance remain later work under
DEP-023/024/025 at their actual INTEGRATION gates. Planned tests in this document
are **NOT_EXECUTED**; no test success or requirement verification is asserted.
