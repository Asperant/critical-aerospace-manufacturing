# WP-CORE-003 technical DoD assessment

Assessment basis: merged implementation PR #128, its recorded real PostgreSQL
acceptance, and current-main CI at `38e93b331c77c21864ed67c18bf7f23ce504dbaf`.
This assessment closes the WP's selected technical DoD. It does not claim the
separately scoped DEP-027/DEP-028 consumer integrations or FR-CORE-005's complete
EV-L4 cross-package evaluation.

| Criterion | Result | Evidence |
|---|---|---|
| DOD-WP-01 | PASS | The v1 typed hold/release/dispatch/maintenance command contracts, idempotency ledger, revision/freshness validation, durable outcomes and query surface exist. `repo:packages/contracts/registry/core.operational-command.v1.json` `repo:services/manufacturing-core/src/manufacturing_core/commands.py` `repo:services/manufacturing-core/src/manufacturing_core/command_persistence.py` `repo:services/manufacturing-core/src/manufacturing_core/query_v1.py` `pr:128` |
| DOD-WP-02 | PASS | PR #128 updated requirement trace edges. Current trace validation passes while retaining the incomplete EV-L4 acceptance as pending/not executed; this package does not promote it. `repo:traceability/trace_edges.yaml` `repo:docs/03_Requirements_Traceability_Matrix.md` `run:45634165229` `pr:128` |
| DOD-WP-03 | PASS | Current-main CI at the bound SHA completed successfully: `ci` run 45634165229 (including t1-contract, t1-static, t1-unit and ci-gate), `projectctl-full-regression` run 45634165211 and `release` run 45634165444. The CI flake gate reported zero active quarantines and no retry-until-green. `run:45634165229` `run:45634165211` `run:45634165444` |
| DOD-WP-04 | PASS | The implementation exercises stale/conflict/unresolved outcomes, malformed and unknown versions, context mismatch, duplicate/retry/restart, same-key/different-payload conflict, and persistence failure paths; real PostgreSQL acceptance is recorded in the WP verification artifact and PR #128. `repo:evidence/WP-CORE-003/LOCAL-VERIFICATION.md` `repo:services/manufacturing-core/tests/test_commands.py` `repo:services/manufacturing-core/tests/persistence/test_command_persistence.py` `pr:128` |
| DOD-WP-06 | PASS | Credential-free structured command telemetry carries correlation/outcome/duration and the Core health surface checks runtime database access. `repo:services/manufacturing-core/src/manufacturing_core/observability.py` `run:45634165229` |
| DOD-WP-07 | PASS | The operator/developer README records the command outcome, migration/runtime role, verification and limitations. `repo:services/manufacturing-core/README.md` `pr:128` |
| DOD-WP-12 | PASS | Test probes and synthetic effects are identified as development evidence; no integrated manufacturing or final research result is claimed. `repo:evidence/WP-CORE-003/LOCAL-VERIFICATION.md` `pr:128` |

The current RTM remains authoritative for the broader FR-CORE-005 EV-L4
evaluation. Downstream Automation acceptance and integrated scenarios stay open
at their own scopes; this WP assessment makes no readiness or capability claim.
