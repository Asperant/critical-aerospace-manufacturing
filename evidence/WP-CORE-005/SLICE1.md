# WP-CORE-005 Slice 1 — event contracts

Owner/implementer: Asrın Dündar. Date: 2026-10-23.
Branch: `wp/WP-CORE-005-domain-events-outbox`; base: `3de9cf0393fa38ba4bc5e4e52f51c4c9563a7df2`.

Implements the initial bounded part of “define event payloads per accepted
transition”: typed/versioned LotReleased, MaterialHoldApplied,
QualityExcursionConfirmed and ScheduleActivated facts, canonical envelope metadata,
opaque aggregate revisions, JSON Schema and four SYNTHETIC TEST fixtures.
See `services/manufacturing-core/contracts/v1/domain-events.md` for source bindings,
namespace/identity rules and the initial closed v1 compatibility boundary.

Requirement trace: FR-CORE-014 (partial payload contracts), FR-CORE-015 (pending).
Verification family: TEST-EVT-SCHEMA, isolated contract checks only. The canonical
REAL-boundary acceptance requirements are not satisfied by these fixture tests.
Architecture: ARCH-CORE-DB / ARCH-CORE-OUTBOX / ARCH-EVT-OUTBOX preserved; no runtime
boundary or authority change. Initial additive contract implementation is within
approved WP scope (09 §3–4); no existing contract semantics are changed.

Executed checks:

- `.venv/bin/python -m pytest services/manufacturing-core/tests/test_event_contract.py services/manufacturing-core/tests/test_query_contract.py -q`
  — final **100 passed** (0.43 s); schema/model equality, fixture round trips,
  required identity/version/metadata, malformed payloads, namespace/producer/type
  rejection, aggregate binding, initial-version compatibility and existing query
  contract regression checks.
- Initial run: **4 failed, 96 passed**. JSON Schema accepted timezone-free
  timestamps because optional date-time format validation was unavailable in the
  installed validator. Added an explicit timezone constraint to the published
  schema and regenerated it; the same negative tests then passed.
- `ci/.venv/bin/ruff check services/manufacturing-core/src/manufacturing_core/events_v1.py services/manufacturing-core/tests/test_event_contract.py`
  — passed; formatter check for the same files passed (2 files formatted).
- `ci/.venv/bin/pyright --pythonpath .venv/bin/python --project services/manufacturing-core/pyrightconfig.json services/manufacturing-core/src/manufacturing_core/events_v1.py services/manufacturing-core/tests/test_event_contract.py`
  — 0 errors, 0 warnings.

Not implemented/executed: remaining event families, mutation/outbox persistence,
relay/retries, PostgreSQL crash consistency, metrics, real broker integration,
post-merge validation or integrated acceptance. No claim of CONTRACT_READY,
COMPONENT_READY, INTEGRATION_READY or WP DONE. Existing AUTO_PREPARATION remains
historical START planning evidence; it is not product verification evidence.

DEP-022 remains an uncertified HARD INTEGRATION gate requiring exact lifecycle
binding and atomic mutation/outbox tests on real PostgreSQL. No HARD START gate
was present in the fresh live queue/context. WP-CORE-001 remains deferred
VALIDATING + BLOCKED on downstream integrated acceptance evidence.

Next bounded work: bind the next exact canonical transition payloads before
expanding the catalog; once the required lifecycle contract is concretely bound,
implement the smallest atomic mutation/outbox slice. No specification conflict
identified in this bounded contract work. Commit/push/Plane transition outcomes
are reported separately; this document does not assert their success in advance.
