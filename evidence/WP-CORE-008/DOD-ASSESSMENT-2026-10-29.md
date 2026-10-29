# WP-CORE-008 DoD Assessment — 2026-10-29

Assessment is bound to merged PR #207 at
`6a7c17215223af56c981f6d8cbf9a560fb0d4911`, the real runtime evidence, and the
dispatch closure evidence in this directory. It is an evidence assessment,
not an owner self-certification and not a workflow transition.

| Criterion | Assessment | Exact basis / remaining condition |
| --- | --- | --- |
| DOD-WP-01 | PARTIAL | The runtime path and evidence exist, but the WBS-declared AV-SCEN-01/AV-SCEN-03 execution scripts and Core-vs-Twin consistency checker are not present as declared deliverables. No `TBD_BY_IMPLEMENTATION` is silently cleared. |
| DOD-WP-02 | NOT CLOSED | PR #207 did not update the relevant 03 trace edges in the same PR. Current trace rows still contain empty `EXECUTED_AS`/`EVIDENCED_BY` fields or pending evidence. The runtime evidence is real, but it cannot retroactively satisfy the same-PR timing rule. |
| DOD-WP-03 | PASS | Exact-main CI run `40909586750`, projectctl regression `40909586938`, and release run `40909586582` succeeded without a retry/quarantine claim. The closure PR must pass its own required CI. |
| DOD-WP-05 | PASS for exercised slice | Real PostgreSQL/NATS/JetStream/Twin/BFF/Keycloak/browser execution was observed after merge. The scenario is not a claim for unexecuted AV-SCEN-01/03 or the complete E2E-01. |
| DOD-WP-06 | PASS for exercised slice | Health surfaces, structured WorldID/correlation/causation identifiers, EventID propagation, and Twin source revision were observed. A separate package-wide metrics certification is not claimed. |
| DOD-WP-12 | PASS | The final evidence is real runtime evidence; setup lots are explicitly identified as deterministic fixture setup and are not described as factory data. |

## Gate result

`WP-CORE-008 = HUMAN_DECISION / not DONE`.

`projectctl check-done WP-CORE-008` remains `UNKNOWN` with the exact reason
`Required post-merge verification and accountable owner DoD evidence are
unavailable`; its missing list also names deliverable/requirement verification,
trace dispositions, identity-bound accepted evidence, and applicable DoD
confirmations. The accountable owner must decide how the declared missing
deliverables and same-PR trace requirement are to be closed or explicitly
accepted under canonical change control. No owner approval or acceptance is
invented here.

The same read-only gate was run for the materially affected
`WP-CORE-002`, `WP-CORE-003`, `WP-CORE-005`, `WP-EVT-003`, `WP-TWIN-001`, and
`WP-UI-002`; each returned `UNKNOWN` for the same unavailable accountable DoD
and trace assessment. This prevents the integration evidence from being
misreported as DONE for those packages.
