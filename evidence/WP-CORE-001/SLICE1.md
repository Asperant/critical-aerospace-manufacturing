# WP-CORE-001 — pure domain slice verification

Owner: Asrın Dündar (Asperant). Implementation revision: the Git commit
containing this evidence. Branch: `wp/WP-CORE-001-domain-model`.

Scope follows `READY.md` start-slice acceptance and canonical WBS WP-CORE-001
(FR-CORE-001/002/013). No inbound dependency edges apply to this initial slice.

Implemented frozen, typed Pydantic domain models for ProductionOrder, Lot,
SerializedComponent, Equipment, ManufacturingRoute and RouteVisit. IDs,
references and revisions are required strict nonblank strings; no UUID scheme,
numeric revision counter or automatic revision allocation is asserted. Revisions
remain opaque tokens; freshness and concurrency checks are outside this slice.
Routes preserve tuple order and reject duplicate visit IDs or a mismatched
parent route. Repeated operation classes retain distinct visit identities.
Local complete-set reference validation rejects duplicate entity identities and
missing order/lot/route/equipment targets. It is not a published query contract
or an authority to change manufacturing state.

## Executed focused checks

Using the existing pinned `ci/.venv` toolchain on this branch:

| Command | Actual result |
|---|---|
| `PYTHONPATH=ci:ci/scripts ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests -q -p pytest_quarantine` | 47 passed; 0 failed; 0 quarantine entries applied |
| `ci/.venv/bin/ruff check services/manufacturing-core` | All checks passed |
| `ci/.venv/bin/ruff format --check services/manufacturing-core` | 3 files already formatted |
| `ci/.venv/bin/pyright --project services/manufacturing-core/pyrightconfig.json --pythonpath ci/.venv/bin/python` | 0 errors, 0 warnings |
| `git diff --check` | Passed |

An initial direct Pyright invocation could not resolve the new service package.
The service-local configuration now declares `src`; the focused rerun above
passed. No failing test was removed or weakened. The CI unit job now runs these
tests and the service-local type check; remote CI is not claimed passed here.

TEST-CORE-DOMAIN coverage: valid/invalid/missing identity, revision and reference
values, immutable identity, JSON round trips, ordered reentrant visits, duplicate
visits and parent-route mismatch, complete-set reference consistency and
duplicate serialized identity rejection. TEST-CORE-GENEALOGY coverage is only
the identity/visit foundation, not split/merge or temporal history verification.
Unknown fields (including simulated Oracle state) are rejected, but this is not
full TEST-ARCH-BOUNDARY or security-suite verification.

No database, migration, API, protected mutation, simulator integration, query
contract publication, or runtime execution was implemented. Full-WP DoD,
CONTRACT_READY, integration/auth/security/scenario/benchmark verification and
post-merge acceptance remain NOT_YET_EXECUTED / NOT_ACCEPTED. No full-WP DONE
claim is made. The next persistence slice must first check actual runtime and
role prerequisites and coordinate migration/role wiring with WP-CORE-007.
