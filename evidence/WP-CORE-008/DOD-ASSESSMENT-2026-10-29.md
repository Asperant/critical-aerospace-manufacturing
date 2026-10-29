# WP-CORE-008 DoD Assessment — 2026-10-29

Assessment is bound to merged PR #207 at
`6a7c17215223af56c981f6d8cbf9a560fb0d4911`, dependency closure PRs #208/#209,
the historical runtime execution/source-main SHA
`ee060997b611fae16d6c4f13c0d85cebafaf17e7`, the real runtime evidence, and the
focused AV-SCEN/checker bundle in this directory. That historical SHA is not
the current main revision. Technical closure PR #210
(`wp/WP-CORE-008-dod-closure`) merged at
`6299ab02491a9b7336b3637334ed461ce510ec21`, which is also the current GitHub
`main` SHA at this assessment refresh. Its body declares `FR-CORE-003`,
`FR-CORE-006`, `FR-TWIN-010`, and `NFR-REL-010` after the TL-13
`Requirements (...):` field. It is an
evidence assessment, not an owner self-certification and not a workflow
transition.

| Criterion | Assessment | Exact basis / remaining condition |
| --- | --- | --- |
| DOD-WP-01 | PASS for technical slice | AV-SCEN-01/03 executable drivers, the fail-closed consistency checker, and real evidence references now exist. The references explicitly scope the result to the implemented Core/outbox/JetStream/Twin/BFF/UI slice; the full canonical AV portfolio is not claimed. |
| DOD-WP-02 | PASS for technical closure PR | The closure PR updates the four WP-CORE-008 §17 source rows with `REALIZED_BY`, `EXECUTED_AS`, and the real `EVIDENCED_BY` bundle; `traceability/` is regenerated from §17 in the same PR. Historical PR #207 is not rewritten. |
| DOD-WP-03 | PASS | The pre-closure exact-main CI run `40909586750`, projectctl regression `40909586938`, and release run `40909586582` succeeded without a retry/quarantine claim. After PR #210 merged, current-main CI `40921154635`, projectctl regression `40921154968`, and release run `40921154423` also succeeded on merge/current-main SHA `6299ab02491a9b7336b3637334ed461ce510ec21`. Its TL-13 field declares `FR-CORE-003`, `FR-CORE-006`, `FR-TWIN-010`, and `NFR-REL-010`. |
| DOD-WP-05 | PASS for exercised slice | Both focused drivers ran against the healthy current-main runtime with real PostgreSQL/NATS/JetStream/Twin and live Keycloak/UI surfaces; the authenticated browser result is bound from the prior real run. The scripts do not claim the unimplemented Vision/RCA/Scheduler/Automation path. |
| DOD-WP-06 | PASS for exercised slice | The machine-readable manifests and checker assert WorldID, CommandID, EventID, correlation/causation, revisions, outbox publication, JetStream consumer delivery, Twin freshness, Keycloak and UI results. |
| DOD-WP-12 | PASS | The final evidence is real runtime evidence; setup lots are explicitly identified as deterministic fixture setup and are not described as factory data. |

## Gate result

`WP-CORE-008 = ACCOUNTABLY_CERTIFIED / not DONE`.

The accountable owner certification is recorded in
`RUN-CORE-008-AV-20261029.json` and
`HUMAN-CERTIFICATION-CHECKLIST.md`, bound to the exact current-main,
technical-closure, historical-runtime and bundle identifiers above.
`projectctl check-done WP-CORE-008` remains `UNKNOWN` with
`execution_status: UNAVAILABLE (documentation only)`: the current
implementation has no post-merge evidence adapter and therefore cannot
mechanically consume the now-recorded owner certification. This is a tooling
fail-closed condition, not a missing runtime, trace, evidence or owner decision.

The owner action is complete. No broader AV portfolio, final EV-L5 evaluation,
production security acceptance or CORE-004 protected rework semantics is
claimed.

The same read-only gate was run for the materially affected
`WP-CORE-002`, `WP-CORE-003`, `WP-CORE-005`, `WP-EVT-003`, `WP-TWIN-001`, and
`WP-UI-002`; each returned `UNKNOWN` for the same unavailable accountable DoD
and trace assessment. This prevents the integration evidence from being
misreported as DONE for those packages.
