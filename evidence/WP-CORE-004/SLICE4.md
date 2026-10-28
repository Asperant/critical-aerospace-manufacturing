# WP-CORE-004 slice 4 — relational split/merge lineage persistence

Owner: Asrın Dündar (Asperant). Date: 24 October 2026.
Implementation revision: the commit containing this evidence on
`wp/WP-CORE-004-temporal-genealogy`, starting from
`e0da2ec387d5ccfee428dd147028fcd851446b71`.

## Scope and canonical trace

Only persistence of Slice 3 `LotLineageHistory` / `LotLineageEvent` /
`LotMembershipSnapshot` values is implemented. Canonical basis remains WP-CORE-004,
FR-CORE-010/011, Item 09 and Item 25, WL-INV-01/02/03 and KG-INV-04, with the
existing Core authority and temporal semantics unchanged. This is additive internal
storage (C1), not a new published event/command/query contract or authority.

The Core migration chain's `0007_lot_lineage.sql` revision stores a world-keyed closure marker,
ordered immutable event facts, ordered roots/children, component memberships and
parent references relationally. No serialized-component identities are cloned.
Existing canonical lots/components are foreign-key references; storage does not
create them, update current membership, or decide merge eligibility. Parent/child
edges retain their source event, revision, reason and separate occurrence,
effectivity and recording instants. PostgreSQL timestamptz preserves instants,
not input timezone spelling. Tuple positions preserve supplied delivery order,
including complete histories delivered in reverse causal order. Causal ordering
continues to be checked by the existing domain model, not a new global sequence.

`LotLineageRepository.create` and `append` revalidate nested values and the complete
history, including constructed models, before inserts. The world key identifies
one complete local closure; roots cannot be replaced. Per-world transaction locks
serialize supported create/append paths. Unique keys and references preserve
identities and linkage; the model retains all conservation/ancestry checks.
Only SELECT/INSERT is granted to runtime. No update/delete/upsert API exists.
Savepoints roll back failed writes; the caller controls the enclosing transaction.

The current-main Alembic chain applies this revision after the rework persistence
revision, using the shared migration lock and checksum ledger. RTM realization
references now point to the repository while retaining ALLOCATED coverage and
NOT_YET_EXECUTED final acceptance; no accepted EvidenceID is invented.

## Executed focused verification

Pinned `ci/.venv`; real PostgreSQL 18.6, private temporary Unix-socket cluster,
no TCP listener, synthetic domain fixtures. The fixture created and dropped its
own isolated databases with separate nonadministrative migrator/runtime roles.
This is not real factory data or integrated producer evidence.

| Check | Actual result |
|---|---|
| `ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_lineage_persistence.py -m integration -q` with `CORE_TEST_DISPOSABLE=1` and disposable `CI_PG_DSN` | 30 passed in 0.56 s (historical scoped run) |
| `ci/.venv/bin/ruff check` on lineage repository, scoped runner and focused DB test | All checks passed |
| `ci/.venv/bin/ruff format --check` on those three Python files | 3 files already formatted |
| `ci/.venv/bin/pyright --project services/manufacturing-core/pyrightconfig.json --pythonpath ci/.venv/bin/python` | 0 errors, 0 warnings |
| `projectctl validate --json` after scoped RTM edits | Exit 0 / PASS |
| `git diff --check` | PASS |

The 30 DB cases cover valid split and merge, empty history, four-generation
round-trip, reversed delivery order, append prefix retention, duplicate create/
append rejection, runtime UPDATE/DELETE/TRUNCATE denial, unknown ancestry,
conservation loss, backwards effectivity, double consumption, world mismatch and
self ancestry through create/append, mid-write foreign-key failures with no partial
rows on either path, enclosing rollback of successful create/appends, and migration
replay. Existing canonical component membership is explicitly checked unchanged.
An initial local type-check caught an optional fetch result in the test count
helper; it was corrected and the focused DB/static checks rerun successfully.

## Remaining scope

No blocker remains for Slice 4. Genealogy exposure queries and WP-NORMAL query
performance checks remain later canonical work. Protected execution, policy and
real canonical producer/consumer binding remain at their existing boundaries;
DEP-029 is unchanged and integrated readiness/whole-WP DoD is not claimed.
No lifecycle/Plane write, AUTO_NEXT, deployment, protected execution, unrelated
Core refactor or broad/full test suite was performed. The two pre-existing
untracked Asrın audit files were untouched.
