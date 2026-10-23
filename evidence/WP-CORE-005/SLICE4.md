# WP-CORE-005 Slice 4 — pending outbox age diagnostic

Implementer: Asrın Dündar's developer agent, 2026-10-23.
Branch: `wp/WP-CORE-005-domain-events-outbox`; base: `d559dde3035348f7459825f6ca11a2b0cf28621a`.
Fresh queue/context confirmed Asrın's WP-CORE-005 IN_PROGRESS; Plane unchanged.

Exact canonical basis: 01 NFR-PERF-003 (lines 171143–171158) measures committed
outbox -> durable broker publication, p95 <= 2s / p99 <= 5s under WP-NORMAL with
healthy dependencies. 02 Event Streaming Infrastructure (line 1571) requires
pending count and oldest-pending age. This slice implements the latter diagnostic
only; no completed publication latency or performance acceptance is claimed.

Added `OutboxPendingAge` and `outbox_pending_age` to existing observability.py,
using its dataclass / manufacturing_core logger / correlation / sorted JSON
conventions. One SQL snapshot selects count/min/max(created_at) for PENDING rows.
Reference time is explicit and timezone-aware, normalized to UTC. Age is seconds
since persisted creation time, not domain occurred_at or simulation time.
Zero pending rows return count=0, age=None; same rows/reference give the same
result. Any future timestamp or failed database read raises, logs FAILED without
exception details and never becomes a successful zero. No schema change, state
mutation, transaction completion, exporter, scheduler, relay or broker is added.

Executed verification on the disposable rootless PostgreSQL 18.6 test server:

`CI_PG_DSN=<disposable-loopback-DSN> CORE_TEST_DISPOSABLE=1 ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_outbox_age.py services/manufacturing-core/tests/persistence/test_observability_integration.py services/manufacturing-core/tests/test_observability.py -q`

Result: **16 passed, 0 failed** (0.20s). Ten new diagnostic cases cover empty,
single/multiple pending rows, zero age, repeated/reference-time calculations,
equivalent timezone offsets, naive/future timestamp rejection, published-only and
mixed status exclusion, structured logs and database failure propagation.
Six existing observability cases also passed. Test data is SYNTHETIC TEST.

Published-row cases temporarily relax the pending-only status constraint inside
a migration-role transaction in the disposable fixture database, then roll back
both DDL and synthetic data. This exercises the exclusion predicate without
adding or claiming a production publication transition. Runtime/schema policy
is unchanged. Other age queries use the restricted runtime test connection.

Scoped Ruff lint/format passed for observability.py and test_outbox_age.py.
Scoped Pyright with `--pythonpath ci/.venv/bin/python --project services/manufacturing-core/pyrightconfig.json`
and those same two paths: 0 errors, 0 warnings. Evidence diff hygiene checked.
The disposable PostgreSQL server was stopped after verification.

Remaining blockers unchanged: ReleaseLot atomic domain mutation/outbox proof
needs exact lifecycle/command binding and DN-CORE-LIFECYCLE@COMPONENT_READY at
DEP-022's integration gate. Relay needs exact canonical publication binding and
an evidenced real JetStream path (Slice 3 blocker). Crash-consistency/integrated
acceptance, completed-delay measurement and broader event coverage remain pending.
Owner-executable scope has not been exhausted/certified: remaining canonical
event-contract coverage and verification/trace work require their own scoped
assessment; this slice is not a downstream-only closeout or WP DONE assessment.
