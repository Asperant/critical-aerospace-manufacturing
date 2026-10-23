# Transactional consumer ledger — WP-EVT-003 Slice 2

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
transaction/savepoint. No broker acknowledgement behavior is implemented.

```python
with connection.transaction():
    outcome = ProcessedMessageLedger("consumer_private").process(
        connection, "projection/live-v1", event_id, update_local_projection
    )
# Only successful exit proves commit; no ACK integration exists in this slice.
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

There is no TTL, purge, transport, ACK/NACK, retry, ordering/gap handler or service
adapter. The Slice 1 design and its unresolved retention decisions remain binding.

## Focused checks

Use the repository's locked `ci` toolchain:

```sh
uv run --project ci --locked ruff check packages/event-consumer
uv run --project ci --locked ruff format --check packages/event-consumer
uv run --project ci --locked pyright --project packages/event-consumer/pyrightconfig.json
EVT_TEST_DISPOSABLE=1 uv run --project ci --locked python -m pytest \
  -c packages/event-consumer/pyproject.toml packages/event-consumer/tests -m integration -q
```

Supply `CI_PG_DSN` for a disposable real PostgreSQL 18+ admin connection. Tests
create and finally drop their own database/roles. No default credentials or
shared production database are supported. This suite verifies the local database
primitive, not the real-JetStream final acceptance families.
