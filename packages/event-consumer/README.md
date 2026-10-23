# Idempotent consumer framework — WP-EVT-003

`ProcessedMessageLedger(schema).process(connection, consumer_scope, event_id, effect)`
returns `Outcome.PROCESSED` or `Outcome.DUPLICATE`. PROCESSED means the effect and
ledger row are staged in the caller's transaction; it does **not** mean committed.

The caller supplies a psycopg `Connection[DictRow]` with `dict_row`, an already
active **READ COMMITTED** transaction, a stable logical consumer scope and the
original event ID. Replicas processing the same target must use the same scope.
The callback receives that same connection and must only perform transactional
local effects. It must not commit/rollback or execute remote/irreversible actions.
The caller must roll back the whole transaction on **any** exception, including a
Python callback exception. Catching an exception and committing partial work is
outside the API contract. The primitive never commits, rolls back or opens a
transaction/savepoint. The higher-level `Consumer` boundary below owns delivery commit/ACK sequencing.

```python
with connection.transaction():
    outcome = ProcessedMessageLedger("consumer_private").process(
        connection, "projection/live-v1", event_id, update_local_projection
    )
# Only successful exit proves commit.
```

Duplicate contenders acquire the same transaction-scoped PostgreSQL advisory
lock **before** the ledger read/callback. The subsequent statement obtains a fresh
READ COMMITTED snapshot after waiting. Once the winner commits, the contender
skips the callback; if the winner rolls back, the contender can process. A durable
`PRIMARY KEY (consumer_scope, event_id)` also enforces storage uniqueness. Hash
collisions serialize extra keys without conflating their ledger identities.
Locks live until the caller transaction ends; callers should keep transactions
short. Distinct keys acquired in inconsistent order can deadlock: the database
error propagates to the caller. No retry loop is supplied.

## Migration and ownership

Use `cap_event_consumer.migrate.migrate(connection, private_schema, runtime_role)`
inside a caller-owned migration transaction on PostgreSQL 18+. Provision the
private schema with a restricted migration owner, revoke PUBLIC privileges and
provide a distinct restricted runtime role that cannot inherit the migration
identity. The package provisions no shared database/schema or roles.

The existing repository convention is retained: numbered packaged SQL,
SHA-256-verified migration replay, separate migration/runtime identities and
runtime SELECT/INSERT on the ledger. `consumer_schema_migration` records version,
checksum and runtime role in the same private schema. Replay returns False only
for a matching migration record. Neither migration nor runtime helper commits
or rolls back on behalf of the caller. Runtime receives no ledger UPDATE/DELETE
privilege through this migration. `processed_at` is local transaction-time
metadata, not event occurrence/simulation time or proof of commit by itself.

There is no TTL or purge. The Slice 1 design and its unresolved retention decisions
remain binding. Deleting ledger proof before every possible redelivery/replay
horizon permits repeated effects; broker retention alone is not a safe purge rule.

## Focused checks

Use the repository's locked `ci` toolchain:

```sh
uv run --project ci --locked ruff check packages/event-consumer
uv run --project ci --locked ruff format --check packages/event-consumer
uv run --project ci --locked pyright --project packages/event-consumer/pyrightconfig.json
EVT_TEST_DISPOSABLE=1 uv run --project ci --locked python -m pytest \
  -c packages/event-consumer/pyproject.toml packages/event-consumer/tests -m integration -q
```

Supply `CI_PG_DSN` for a disposable real PostgreSQL 18+ admin connection and
`CI_NATS_URL` for a disposable JetStream-enabled NATS server. Tests
create and finally drop their own database/roles. No default credentials or
shared production database are supported. The suite exercises real DB and broker mechanics; full downstream integrated
scenario acceptance remains separate, as recorded in the WP evidence.


## Delivery and JetStream boundary

`Consumer(ledger, scope, connect, admit, effect, identify=identify_json)` adds the
transaction-owning delivery boundary around the caller-transaction-owned ledger.
`connect` must return a fresh IDLE psycopg `Connection[DictRow]`. The framework
closes it after each delivery. `identify(bytes) -> Event` must validate the owning
adapter's published contract; the provided JSON helper validates only event
object/identity and cannot replace full schema validation. `admit(conn, event,
context)` validates world/branch, ordering and application eligibility for a new
effect, in the same local transaction; `effect` uses that connection. Neither
callback may commit, roll back or perform irreversible remote actions.

`handle(delivery, context)` receives the original bytes, identifies the event,
commits the local effect plus ledger, then ACKs. Processing/commit failure rolls
back and NAKs, propagating the error. ACK failure never undoes a committed effect;
durable redelivery consults the ledger. Cancellation settles an in-flight DB
transaction but does not ACK that delivery. A callback must itself terminate;
Python threads cannot be forcibly stopped. Connection/statement/lock timeouts are
operator/adapter configuration, not invented here. `health()` reports local
outcome counters; structured logs include scope, identity, correlation, outcome
and duration without logging event payloads, DSNs or exception details. Those
counters are not a claim of external broker/database health.

`JetStreamConsumer.bind(js, Binding(...), consumer, context, ack_timeout=...)`
requires explicit **stream, subject, durable, ack_wait, max_deliver and
deliver_policy**, plus an ACK confirmation timeout. The owning runtime supplies
these bindings; no production stream/subject/ACL is hard-coded or provisioned.
Binding verifies an existing durable's relevant configuration rather than
silently editing it. The stream must already exist. `receive_once(timeout=...)`
fetches one message; successful processing uses explicit `ack_sync` after commit.
No internal retry loop is added: NAK/ACK-timeout redelivery follows the configured
server durable. Callers own connection authentication, reconnect policy and
bounded worker supervision. `close()` stops local receives, cancels/settles active
work and unsubscribes while retaining the server durable. A pending fetch is
settled within its configured finite timeout; its unACKed message can redeliver.
The boundary does not close the caller's NATS connection or delete broker state.

## Adapter obligations and operational recovery

| Consumer | Generic hook available | Remaining application-owned integration |
|---|---|---|
| Twin | Transactional projection and isolated replay-target callback | Real projector, aggregate sequence/freshness/rebuild policy |
| Vision | Local inspection-result effect and local outbox intent | Inspection contract and result publication |
| AI | Local investigation/proposal effect | Evidence/RCA schema and read/propose authority checks |
| Scheduler | Local candidate-plan effect | Planning contract; activation remains separately governed |
| Automation | Local workflow intent, live-only replay rejection | Exact approval binding, authorization and effect verification |

No such application consumer is implemented in the current checkout. Its owner
supplies contract/world admission, callbacks, private schema, stable scope and
runtime bindings. This library never directly mutates another service's state.
No claim of those downstream services' adoption is made.

`DeliveryContext` is trusted adapter input, never a payload flag. Replay is rejected
by default. A rebuild adapter may enable it only for a bound, separate shadow
scope/target and a governed ReplayRun; it must reject invalid targets in admission
and prohibit live protected effects. Original event identity remains unchanged.
A version gap must cause explicit adapter deferral/reconciliation/stale marking;
raising `AdmissionError` rolls back and NAKs rather than silently applying or
marking the event processed. Duplicate committed events skip the effect callback.
The library supplies no destructive gap/stale policy or implicit replay permission.

For a stuck/poison delivery, inspect structured failure/counter and durable pending
state, repair the contract/dependency/adapter cause, then use the owning service's
controlled redrive with the original identity. This package does not invent a DLQ
or discard on `max_deliver` exhaustion: operators must inspect the configured
server advisories/pending state and use the platform's governed resolution path.
Keep old ledger rows on restart/upgrade. Rollback of an application deployment
must preserve the ledger/schema and scope identity; changing scope to bypass dedup
can repeat an effect. Do not drop the migration or truncate a live ledger.
