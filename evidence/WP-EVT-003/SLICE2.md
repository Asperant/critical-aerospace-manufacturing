# WP-EVT-003 Slice 2 — Local PostgreSQL ledger

Date: 2026-10-24. Owner: Asrın Dündar. Branch:
`wp/WP-EVT-003-idempotent-consumer`. Design baseline:
`a06927b9ea0abf19d07f76b457faa125f5f4930d`.

Scope: isolated implementation under FR-EVT-005 / ARCH-EVT-CONSUMER, following
[Slice 1](CONSUMER_IDEMPOTENCY_DESIGN.md). No HARD START dependency; DEP-023/024/025
remain gates at INTEGRATION, not satisfied by this slice's database tests.

## Implementation and transaction contract

`packages/event-consumer/` contains the typed processed-message primitive and
`0001_processed_message.sql`. Each consumer installs it in its private schema;
the unique primary key is `(consumer_scope, event_id)`, with local `processed_at`
metadata. The migration follows the existing numbered-SQL/checksum replay and
separate migration/runtime-role convention; runtime receives ledger SELECT/INSERT.

`ProcessedMessageLedger.process(connection, consumer_scope, event_id, effect)`
returns PROCESSED or DUPLICATE. Caller owns the active READ COMMITTED transaction
and every commit/rollback. Callback effects use the same connection. On any
exception the caller must roll back the entire transaction. PROCESSED is staged
work, not execution/commit evidence. A transaction-scoped advisory lock serializes
the same key before invoking the callback; a separate fresh-snapshot read detects
a committed winner. Rollback of the winner allows the contender to process.
The unique primary key remains the final storage invariant. This selects a
serialization mechanism within Slice 1's concurrent-duplicate safety requirement.

## Actual verification

Real disposable PostgreSQL 18, run as Asrın using existing local PostgreSQL 18
binaries and a newly initialized private cluster; Unix socket only, 32 MiB shared
buffers and 12 maximum connections. No Docker/platform stack was launched.
The fixture creates a fresh database and separate restricted login identities,
then drops them. The temporary cluster is stopped after the checks.

Commands used (the temporary socket path is local run configuration, not a secret):

```sh
uv run --project ci --locked ruff check packages/event-consumer
uv run --project ci --locked ruff format --check packages/event-consumer
uv run --project ci --locked pyright --project packages/event-consumer/pyrightconfig.json
CI_PG_DSN='host=/tmp/asrin-evt003-pg18-7zaGcX port=55483 user=asrin dbname=postgres' \
EVT_TEST_DISPOSABLE=1 uv run --project ci --locked python -m pytest \
  -c packages/event-consumer/pyproject.toml packages/event-consumer/tests \
  -m integration -q --tb=short
```

Results: Ruff lint PASS; six Python files format-clean; Pyright 0 errors/warnings;
**20 PostgreSQL cases passed**. Coverage includes first delivery, same-scope
duplicate, independent scopes, callback exception rollback, ledger CHECK-constraint
failure rolling back the callback effect, caller rollback, committed redelivery,
concurrent winner commit and winner rollback, transaction/isolation guards,
migration replay/checksum mismatch, composite-key/nonblank constraints and denied
runtime mutation/DDL/migration-ledger access. Concurrent tests observe an actual
server advisory-lock wait before releasing the first transaction.

Initial development checks failed on lint/type issues, fixture transaction
initialization and test context scoping; a subsequent run had 19 passing cases
and one rollback-test scoping failure. Those test/code issues were corrected;
the final run above passed all 20 without skips. No failing test was removed or
weakened to obtain the result.

## Limits and remaining work

No JetStream, ACK/NACK, retry loop, gap handling, consumer adapter, retention worker
or automatic deletion was implemented. Retention/horizon owner decisions remain
open. The package's focused suite is runnable with the locked toolchain; automatic
CI wiring is not added in this slice. Final TEST-EVT-CONSUMER-IDEMP, AV-SCEN-05 and
RES-DUP-001 evidence, real broker integration, consumer adoption and post-merge
validation remain outstanding. No final requirement verification or whole-WP DONE
is claimed. No canonical specification was changed. The two pre-existing untracked
audit files were left untouched.
