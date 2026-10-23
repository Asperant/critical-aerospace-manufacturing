# WP-CORE-005 Slice 2 — generic atomic mutation + outbox primitive

Implementer: Asrın Dündar's developer agent, 2026-10-23.
Branch: `wp/WP-CORE-005-domain-events-outbox`; prior commit:
`95795bb9ea5aed7aaaf9b6bf40cbaa4ebd20e4a2`. No Plane mutation, no AUTO_NEXT.

## What was added

`manufacturing_core.outbox.execute_with_outbox(connection, mutation, record)`:
within the caller's active PostgreSQL transaction it runs a caller-supplied
`mutation(connection)` and inserts an already-formed `OutboxRecord` (or one the caller
forms from the mutation's result) through the existing `OutboxRepository.insert`, in a
single savepoint. It never begins, commits or ends a transaction.

It deliberately knows nothing about `ReleaseLot`, lifecycle legality, domain revisions,
command idempotency or event construction, and it neither authorizes nor certifies the
mutation or the event. It does not touch WP-CORE-002/003 semantics.

## Proven on real PostgreSQL

`tests/persistence/test_outbox_atomic.py` uses a test-owned neutral probe table in a
test-owned schema (created and removed by the disposable admin role) and a synthetic
contract event. Cases: successful commit persists both and is invisible to other
connections before the commit; mutation failure (Python and SQL) leaves no outbox row
while the caller's earlier work survives; outbox failure (duplicate outbox ID and
duplicate event ID) rolls back the mutation while the caller's earlier outbox row
survives; caller rollback removes both; record formation from the mutation's result and
its failure; an invalid record is rejected before the mutation runs; no/autocommit
transaction is rejected without running the mutation; an attempt to commit inside the
unit is refused and nothing persists.

## Execution record (2026-10-23)

- Real PostgreSQL 18.6 from `postgres:18-alpine` (digest
  `sha256:898c60cb390d1085bc97bdd6a1ae968757421df394b071848b52b1c09c89d6a5`), a
  throwaway localhost-only container with the disposable-fixture roles; removed after use.
- `pytest -m integration` over `test_outbox_atomic.py` (11 new cases), `test_outbox.py`
  and `test_outbox_age.py`: 44 passed.
- Mutation check: replacing the savepoint with a plain block made 6 of the 11 new cases
  fail; the file was restored byte-for-byte before the final run.
- `ruff format --check` / `ruff check` on the changed files: clean. `static_ratchet.py
  check`: PASS, no new findings; existing baseline retained.
- Not run: the full persistence suite, NATS, migrations beyond the disposable fixture,
  any Plane or AUTO_NEXT operation.

## What this does NOT establish

- Not the canonical `ReleaseLot` (or any transition) atomicity acceptance proof.
- Not lifecycle eligibility, command semantics, revision calculation or idempotency.
- Not crash consistency, relay/publisher behavior, retries or delivery.
- Not integrated acceptance, DEP-022 readiness or WP DONE.

The final transition-specific proof still waits on the canonical lifecycle/command
binding (WP-CORE-002 transition guards/handlers, WP-CORE-003 command contracts,
idempotency and revision semantics). When that binding exists, one real state mutation
plus its matching outbox insert must be executed through this boundary on disposable
PostgreSQL 18 as described in `SLICE2-BLOCKED.md`.
