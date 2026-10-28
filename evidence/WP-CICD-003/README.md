# WP-CICD-003 — Automated migration execution in the deployment path: evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın (advisory, CHG-018) · F1 · M2/S3–S4 ·
readiness node DN-PLAT-CD · requirement NFR-DEP-004 (A1).

## What was added

| Deliverable (04) | Realization |
|---|---|
| migration stage in CD | `tools/release/src/cap_release/migrations.py` wired into `deploy`: a release that declares a migration set (`release/images.json`) binds its newest version and the migrate stage runs it between preflight and rollout |
| migration status surface | `python -m cap_release migration-status`: one JSON line per set with `state` (EMPTY, BEHIND, CURRENT, DIVERGED, UNREADABLE), applied and pending versions; exit 0, 1 or 2 |
| failure handling and halt semantics | documented in `release/README.md` and in the module: halt before any apply on a diverged ledger, an unreadable database or a mismatched target; halt before the rollout on a failed apply with the position left; the schema is never reverted by a rollback |

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `tools/release/tests/test_migrations.py` (TEST-CICD-003-001, 29 tests) | TEST-DEP-MIGRATION | FIXTURE_ALLOWED (a fake backend; the tooling's failure messages with a fake tooling package) | CI t1-unit |
| `tools/release/tests/test_migrations_real.py` (TEST-CICD-003-002, 7 tests) | TEST-DEP-MIGRATION | REAL PostgreSQL 18, a disposable database, a migration role and a restricted runtime role | CI t1-integration |

Local at the branch head: 131 release tests (the integration ones deselected) and the 7 REAL
tests passed, `ruff`, strict `pyright`, the static ratchet, the test-strategy check,
`projectctl validate` and the trace lint pass.

## Findings

- **The Core CLI hides what the stage must know.** It prints one fixed sentence for every failure
  and `--status` fails the same way for an empty database and for a connection error, so the stage
  would have to treat a first deployment as an outage or an outage as a first deployment. The
  stage uses the tooling's Python API and surfaces only its own fixed messages and exception class
  names, never a connection string.
- **A real database corrected an assumption.** On an empty database the tooling raises `ValueError`
  (its role contract) at connect time, not `UndefinedTable`; the first REAL run failed all five
  tests, which also showed that the local helper started PostgreSQL 16 while the tooling requires
  18. The stage now surfaces the tooling's fixed contract messages.
- **A design error from WP-CICD-002 is fixed here.** There the schema target was bound only when its
  owner image was released, to keep `SUCCEEDED` possible before migrations ran; now that they run
  it is bound from the declared migration sets.

## Known limitations

- No application image carries Core yet; the migrations run from the release checkout.
- Forward only: no schema reversion, and a Contract-phase (destructive) migration needs its own
  decision.
- The shared-host run uses a disposable database, not the Integration database.
- TEST-DEP-MIGRATION at INTEGRATION on a real release deployment and the NFR-DEP-004 measurement
  are open; EvidenceState is EVIDENCE_PENDING and `observed` stays null.
