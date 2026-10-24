# WP-CORE-004 slice 1 — immutable rework execution history

Owner: Asrın Dündar (Asperant). Date: 24 October 2026.
Implementation revision: the Git commit containing this evidence.
Branch: `wp/WP-CORE-004-temporal-genealogy`; starting head
`fae8fa7bf10d379f64e60720c3615ce77b448fa2`.

This is one internal domain-value capability within the prepared first task,
"implement ReworkDirective execution without overwriting history". It supplies
the history representation, not completion of that entire task or WP. Scope is
FR-CORE-009, ARCH-CORE-DOMAIN / ARCH-CORE-GENEALOGY, WL-INV-01/04/05. The
canonical requirement wording and authority boundaries are unchanged.

## Implemented capability

`manufacturing_core.rework` records a component-scoped explicit ReworkDirective
snapshot and distinct execution records. `ComponentExecutionHistory.append_rework`
returns validated extended history, retaining the original route snapshot and
every prior segment. Repeated route visits have separate execution identities.
Directive provenance retains reason, inspection, origin execution/route context,
return visit, required route identity/revision, optional defect/incident, current
rework count and approval/policy states. These states/counts are caller-supplied
provenance, not execution permission or policy evaluation.

Frozen nested values and tuples prevent ordinary in-place modification. Local
validation rejects duplicate directive/execution identities, missing or
self-referential origins, invalid return visits, route/revision mismatches,
cross-component records, empty segments and malformed intervals. Timestamps
are timezone-aware occurrence times; tuple order is append order, not a claim
about broker arrival ordering. Lot references are historical, not active
membership updates. Numeric limits, revision allocation and state taxonomies
are not invented.

This pure value operation does not execute ExecuteApprovedReworkDirective,
authenticate an approval, enforce policy limits, start physical execution,
persist facts, or change canonical material state. There is no external
command/schema publication, migration, database write or lifecycle change.

## Focused verification actually executed

Environment: existing `ci/.venv`, Python 3.11.16, Pydantic 2.14.1. All values
are synthetic development fixtures; there is no real-lineage integration claim.

| Command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/test_rework.py -q` | 23 passed in 0.08 s |
| `ci/.venv/bin/ruff check services/manufacturing-core/src/manufacturing_core/rework.py services/manufacturing-core/tests/test_rework.py` | All checks passed |
| `ci/.venv/bin/ruff format --check services/manufacturing-core/src/manufacturing_core/rework.py services/manufacturing-core/tests/test_rework.py` | 2 files already formatted |
| `ci/.venv/bin/pyright --project services/manufacturing-core/pyrightconfig.json --pythonpath ci/.venv/bin/python` | 0 errors, 0 warnings |
| `projectctl validate --json` | PASS; 634 existing canonical diagnostics, zero errors |
| `git diff --check` | PASS |

The tests cover two appended rework cycles and JSON round-trip retention,
unchanged earlier snapshots, separate repeated-visit identities, missing
directives, malformed references, duplicate identities, strict nonnegative
counts, aware/nonnegative time intervals, immutability and rejected extra
Oracle fields. This is only the internal rework-history part of
TEST-CORE-GENEALOGY. TEST-CORE-STATEMACHINE protected/lifecycle transitions,
BENCH-E2E-001 and integrated acceptance were not executed or claimed.

## Trace and remaining work

FR-CORE-009 REALIZED_BY now references the actual module, annotated as an
internal value foundation only. VERIFIED_BY families are retained. Whole-
requirement coverage remains ALLOCATED and accepted evidence remains
NOT_YET_EXECUTED: focused unit results do not satisfy the requirement's final
REAL boundary / EV-L5 evidence target. This document supplies only the executed
local subset, not an invented accepted EvidenceID or full-WP verification.

The next owner slice can add append-only relational persistence for these facts
with real disposable PostgreSQL rollback/concurrency tests. No such persistence,
split/merge, exposure queries or workload measurement is included here. Protected
command integration still requires actual lifecycle/authorization binding and
DEP-029 DN-CORE-LIFECYCLE COMPONENT_READY with real lineage, unchanged. Full
DoD, integrated tests, remote CI/post-merge acceptance and DONE remain pending.
No blocker prevents this completed internal value slice. No Plane/lifecycle
change or AUTO_NEXT invocation was performed; the two pre-existing untracked
Asrın audit files were left untouched.
