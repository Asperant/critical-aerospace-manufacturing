# CTRL-DOC-001 — Reconciliation inventory

Baseline: `644e380`; branch `reconcile/documentation-baseline`, isolated from setup partial files. Preflight: 144 tests passed in62.01s; offline validation PASS with947 warnings. No Plane/GitHub reads or writes.

All intended canonical edits are enumerated below before application. `inventory.json` carries impact/classification fields; `baseline-audit.json` contains every scanned occurrence, source hash, heading, numeric citation and diagnostic. Uncertain contexts remain untouched. Human policy approval is current, not historical approval; no owner peer-review or formal CHG closure is claimed.

| Finding | Control | Class/risk | Apply | Governing resolution |
|---|---|---|---|---|
| DOC-IDENTITY | CTRL-DOC-002 | C1/CR-2 | yes | Replace exactly two final branding occurrences; preserve governed automation and anti-patterns. |
| DOC-DATASET | CTRL-DOC-003 | C3/CR-4 | yes | Correct source identities and cross-domain-only roles; append Lane A/B/C policy and candidate-only portfolio; retain rights gates. |
| DOC-INSPECTION | CTRL-DOC-004 | C3/CR-3 | no — human decision | Preserve locations; request INSPECTION_CONTRACT_CANONICALIZATION; trace schemas/producers/consumers in audit. |
| DOC-COMMANDS | CTRL-DOC-004 | C3/CR-3 | no — human decision | Preserve unresolved aliases; record known ActivateSchedule/ActivateScheduleCommand reconciliation from R-003; request PROTECTED_COMMAND_NAMING. |
| DOC-DEPENDENCY | CTRL-DOC-005 | C3/CR-3 | no — human decision | Keep graph and statuses intact; enumerate exact diagnostics; require owner decisions instead of guessed fallback/readiness. |
| DOC-NFR-OD | CTRL-DOC-005 | C1/CR-1 | yes | Replace OD wording with normative RPO≤24h/16GiB host/p95≤12GiB 30min/shortpeak≤14GiB noOOM; remaining unspecified numbers stay open. |
| DOC-MC2 | CTRL-DOC-005 | C3/CR-4 | no — human decision | HUMAN_DECISION_REQUIRED: MC2_OWNER; preserve unspecified owner. |
| DOC-HARDWARE | CTRL-DOC-005 | C3/CR-4 | no — human decision | Require versioned release/environment/hardware/workload identity; no invented measured values or accepted host. |
| DOC-E2E | CTRL-DOC-005 | C1/CR-2 | no — human decision | HUMAN_DECISION_REQUIRED: E2E_COORDINATOR; preserve GS-01 and owner boundaries. |
| DOC-ARCH | CTRL-DOC-004 | C3/CR-3 | no — human decision | Record required owner-reviewed append-only allocation proposal; no new architecture IDs/services invented. |
| DOC-CITATIONS | CTRL-DOC-006 | C0/CR-0 | yes | Repair all306 YAML meta and306 View A anchors by exact ID; fix unique identified Item81/82/83 ranges; inventory all other numeric citations, leave ambiguous untouched. |
| DOC-FIELDS | CTRL-DOC-006 | C1/CR-1 | yes | Append null/unspecified interpretation to RTM; preserve missing fields/diagnostics; no fabricated values. |
| DOC-MIGRATION | CTRL-DOC-006 | C1/CR-1 | yes | Create docs/DOMAIN_MIGRATION_CHANGELOG.md as present-day source reconstruction; no historical approvals/dates invented; audit current tracked code identifiers; retain logical Item43 interpretation. |
| DOC-REGISTRY | CTRL-DOC-001 | C0/CR-0 | yes | Create sequential CSV+YAML records before canonical edits; append dated-state annotation without changing historical empty snapshot; leave formal peer review outstanding. |
| DOC-REDTEAM | CTRL-DOC-007 | C0/CR-0 | yes | Append additive delta table for all32 IDs; no erasure or blanket READY; final source-bound report. |
