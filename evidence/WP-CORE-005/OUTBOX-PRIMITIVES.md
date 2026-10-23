# WP-CORE-005 — outbox primitives only

Implementer: Asrın Dündar's developer agent, 2026-10-23.
Branch: `wp/WP-CORE-005-domain-events-outbox`; prior commit:
`a0cae2eb20d62af923cee38eae8520530e3fb941`.
Fresh live queue confirmed WP-CORE-005 IN_PROGRESS for Asrın; no Plane mutation.
Exact WP context was retrieved. Canonical basis: FR-CORE-014/015;
02 Architecture line 1571 defines owning-service outbox metadata and atomic
state/event persistence. This change implements only the outbox storage primitive.

`0002_outbox.sql` adds core.outbox. It stores the complete already-formed event;
generated columns preserve identity, type/namespace, schema version, aggregate
identity/revision and payload without competing writable copies. Outbox/event IDs
are independently unique. Creation time and outbox ID are explicit caller inputs;
no wall-clock or revision allocation occurs. Initial publication metadata is
PENDING / zero attempts / no error; no publishing behavior is implemented.

`OutboxRecord` validates the existing Slice 1 event contract. The repository
revalidates input, requires an active caller transaction, inserts or reads a fact,
and never begins/commits/rolls back or creates a savepoint. Duplicate-ID errors
propagate; no command idempotency policy is inferred. Domain existence, acceptance,
eligibility and lifecycle/revision mutation remain outside this API. SQL protects
storage/type/identity binding, not the entire application event schema.

Migration conventions preserved: advisory lock, separate restricted migration and
runtime identities, checksummed ledger, atomic ordered application. Existing
0001_domain SQL is unchanged; its valid ledger upgrades to 0002. Runtime gets
SELECT/INSERT on outbox, no UPDATE/DELETE/DDL. Existing migration/security tests
were adjusted for the added table and the now-multiple ledger rows, not weakened.

Executed verification:

- Disposable real PostgreSQL **18.6**, run as Asrın on loopback using Ubuntu
  packages extracted under `/tmp/asrin-core005-pg18`; no root installation,
  Docker, shared database or service modification. Test fixture created/dropped
  its own database and separate restricted roles. The temporary server was stopped.
- `CI_PG_DSN=<disposable-loopback-DSN> CORE_TEST_DISPOSABLE=1 ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_outbox.py services/manufacturing-core/tests/persistence/test_persistence.py -m integration -q`
  — **49 passed, 0 failed** (0.44s). Includes all four fact round trips,
  uniqueness, invalid models/raw records, identity binding, caller rollback,
  cross-connection visibility after caller commit, absence of implicit commit,
  autocommit rejection, initial migration, upgrade/replay and privilege negatives.
- Scoped Ruff lint and format checks on outbox.py, migrate.py, test_outbox.py,
  test_persistence.py: passed. Scoped Pyright with
  `--pythonpath ci/.venv/bin/python --project services/manufacturing-core/pyrightconfig.json`
  and those same four paths: 0 errors, 0 warnings. Diff hygiene passed.
- Initial command with workspace `.venv` could not collect tests (missing
  psycopg); its type check reported 12 missing imports. Corrected to the existing
  CI environment without changing dependencies. Initial real PostgreSQL run:
  47 passed; two additional caller-transaction tests produced the final 49.
  One intermediate Ruff nested-context finding was fixed before final checks.

No product lifecycle/command semantics, domain mutation, relay, retries,
publishing, metrics or instrumentation added. No atomic manufacturing-transition
proof, crash-consistency/delivery evidence, integrated acceptance or WP DONE
claim. Prior Slice 2 blocker remains: exact lifecycle/ReleaseLot command binding
and DN-CORE-LIFECYCLE@COMPONENT_READY at DEP-022's INTEGRATION gate.

Next CORE-005-owned slice: the outbox relay/publication boundary, with its exact
broker contract and focused tests, scoped separately before implementation.
Commit/push outcomes are reported separately; this record does not pre-certify them.
