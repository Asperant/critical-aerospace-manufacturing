# WP-CORE-004 slice 2 — append-only relational rework history

Owner: Asrın Dündar (Asperant). Date: 24 October 2026.
Implementation revision: the commit containing this evidence, on
`wp/WP-CORE-004-temporal-genealogy`, starting from
`5a858a9facf3b384f8cd3af74be923fad63166e5`.

This is historical slice evidence from the workstream branch. The current-main
implementation incorporates the same SQL through shared Alembic revisions
`0006_rework_history`/`0007_lot_lineage`; see
`CURRENT-MAIN-LOCAL-VALIDATION.md` for the current migration-chain rerun.

## Exact scope

Persist Slice 1's unchanged internal immutable values relationally. New tables
store history identity, directive snapshots, ordered segments, route-visit
snapshots and execution records. All Slice 1 fields are reconstructed, including
optional defect/incident references, opaque revisions, approval/policy provenance,
counts and aware occurrence times. `numeric` retains nonnegative integer rework
counts without introducing an arbitrary bigint policy limit. Original route
definitions and original execution/history rows are not overwritten.

`ReworkHistoryRepository` has create/read/append operations only. Foreign keys
preserve component, lot, equipment, segment/directive and prior-execution linkage.
Create/append acquire a per-component transaction advisory lock, validate models
and insert all related rows within a transaction/savepoint. Duplicate identities
are errors; no upsert or replacement is available. The runtime role receives only
SELECT/INSERT on the history tables, no UPDATE/DELETE/TRUNCATE or ledger access.
Caller rollback remains authoritative; no protected command or authorization
decision is inferred from a successful history write.

The additive migration has a scoped checksum/runtime-role ledger because the
unchanged original runner intentionally accepts exactly its initial migration.
The new runner first verifies/applies that original migration, then applies its
own SQL atomically under the existing migration lock. This does not choose or
replace the shared migration framework or implement WP-CORE-007/CD wiring.

Class C1 derived implementation/additive migration within approved scope; no
canonical requirement, dependency, public contract or authority semantics change.
FR-CORE-009 REALIZED_BY now points to the repository implementation. Whole-
requirement coverage remains ALLOCATED and final acceptance NOT_YET_EXECUTED:
partial persistence tests do not satisfy protected execution or EV-L5 acceptance.

## Executed focused verification

PostgreSQL 18.6 (Ubuntu 18.6-0ubuntu0.26.04.1), Python 3.11.16, existing
`ci/.venv` toolchain. A fresh private Unix-socket cluster used 16 MB shared buffers,
20 maximum connections and no TCP listener. Local trust authentication was confined
to its private socket directory: this verifies actual database-role privileges,
not password authentication or Keycloak. Fixtures created separate restricted
migration/runtime identities and a separate rework test database, leaving the
initial-schema test database unchanged. Data are synthetic development fixtures,
not real factory data or actual canonical lifecycle lineage.

| Command | Actual result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_rework_persistence.py -m integration -q` with explicit disposable `CI_PG_DSN` / `CORE_TEST_DISPOSABLE=1` | 24 passed in 0.48 s; exit 0 |
| `ci/.venv/bin/ruff check` on the two new Python modules and new DB test file | All checks passed |
| `ci/.venv/bin/ruff format --check` on those three Python files | 3 files already formatted |
| `ci/.venv/bin/pyright --project services/manufacturing-core/pyrightconfig.json --pythonpath ci/.venv/bin/python` | 0 errors, 0 warnings |
| `projectctl validate --json` after the scoped RTM reference update | PASS; 634 existing canonical diagnostics, zero errors |
| `git diff --check` | PASS |

The DB cases prove committed two-cycle append/read round-trips from another read-only
connection, preserved directive-origin linkage, null optional references, counts
above bigint range, unchanged current route definitions, rejection of history
replacement and duplicate directive replay, denial of UPDATE/DELETE/TRUNCATE on
all five tables, atomic rollback after a late foreign-key failure during create
and append, outer-transaction rollback, missing-history rejection and checksum-
verified migration replay/tamper rejection. Failed append savepoints leave the
caller transaction usable. This is a focused TEST-CORE-GENEALOGY persistence
subset, not TEST-CORE-STATEMACHINE or integrated scenario acceptance.

The first disposable bootstrap failed before tests because the extracted native
`initdb` needed its matching `libpq` library path. Supplying that path only to the
test server processes fixed the setup; no product code/test assertion was weakened.
The failed bootstrap log remains at `/tmp/asrin-core004-slice2-8_1i5v0y/init.log`;
the first successful run logs are at `/tmp/asrin-core004-slice2-2dvz2nck/` (24 passed
in 0.47 s). After strengthening the committed round-trip case to cover two rework
cycles, the final focused run passed as recorded above; its logs are at
`/tmp/asrin-core004-slice2-tudxbgwo/`. The disposable
server was stopped, fixture databases/roles were dropped and cluster data removed.
No full/broad test suite or shared platform was launched.

## Remaining boundary

No blocker remains for this persistence slice. Split/merge behavior is the next
canonical task and is unimplemented. Exposure queries and scale checks remain
later work. Protected rework execution/lifecycle integration still requires
DEP-029 DN-CORE-LIFECYCLE COMPONENT_READY and real-lineage evidence. No Plane,
lifecycle, protected execution, product deployment or AUTO_NEXT action was run.
Full-WP DoD, remote CI/post-merge and integrated acceptance are not claimed. The
two existing untracked Asrın audit files are untouched.
