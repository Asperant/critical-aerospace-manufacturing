# WP-CORE-008 DoD Assessment — 2026-10-29

Assessment is bound to merged PR #207 at
`6a7c17215223af56c981f6d8cbf9a560fb0d4911`, dependency closure PRs #208/#209,
current main `ee060997b611fae16d6c4f13c0d85cebafaf17e7`, the real runtime
evidence, and the focused AV-SCEN/checker bundle in this directory. It is an
evidence assessment, not an owner self-certification and not a workflow
transition.

| Criterion | Assessment | Exact basis / remaining condition |
| --- | --- | --- |
| DOD-WP-01 | PASS for technical slice | AV-SCEN-01/03 executable drivers, the fail-closed consistency checker, and real evidence references now exist. The references explicitly scope the result to the implemented Core/outbox/JetStream/Twin/BFF/UI slice; the full canonical AV portfolio is not claimed. |
| DOD-WP-02 | PASS for technical closure PR | The closure PR updates the four WP-CORE-008 §17 source rows with `REALIZED_BY`, `EXECUTED_AS`, and the real `EVIDENCED_BY` bundle; `traceability/` is regenerated from §17 in the same PR. Historical PR #207 is not rewritten. |
| DOD-WP-03 | PASS | Exact-main CI run `40909586750`, projectctl regression `40909586938`, and release run `40909586582` succeeded without a retry/quarantine claim. The closure PR must pass its own required CI. |
| DOD-WP-05 | PASS for exercised slice | Both focused drivers ran against the healthy current-main runtime with real PostgreSQL/NATS/JetStream/Twin and live Keycloak/UI surfaces; the authenticated browser result is bound from the prior real run. The scripts do not claim the unimplemented Vision/RCA/Scheduler/Automation path. |
| DOD-WP-06 | PASS for exercised slice | The machine-readable manifests and checker assert WorldID, CommandID, EventID, correlation/causation, revisions, outbox publication, JetStream consumer delivery, Twin freshness, Keycloak and UI results. |
| DOD-WP-12 | PASS | The final evidence is real runtime evidence; setup lots are explicitly identified as deterministic fixture setup and are not described as factory data. |

## Gate result

`WP-CORE-008 = HUMAN_DECISION / not DONE`.

`projectctl check-done WP-CORE-008` remains `UNKNOWN` because the tool is
fail-closed and does not mechanically certify the accountable owner's DoD
assessment. The technical deliverable/trace/evidence gaps above are closed for
the documented runtime slice; no owner approval or acceptance is invented here.

The exact remaining human action is listed in
`evidence/WP-CORE-008/HUMAN-CERTIFICATION-CHECKLIST.md`. It must confirm the
scope boundary and decide whether this technical slice satisfies the package's
selected DoD without claiming the wider AV portfolio. After the owner records
that certification in the canonical evidence record, rerun `projectctl
check-done WP-CORE-008`.

The same read-only gate was run for the materially affected
`WP-CORE-002`, `WP-CORE-003`, `WP-CORE-005`, `WP-EVT-003`, `WP-TWIN-001`, and
`WP-UI-002`; each returned `UNKNOWN` for the same unavailable accountable DoD
and trace assessment. This prevents the integration evidence from being
misreported as DONE for those packages.
