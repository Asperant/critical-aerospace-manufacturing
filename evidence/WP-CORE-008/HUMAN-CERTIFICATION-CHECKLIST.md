# WP-CORE-008 accountable certification action

Status: `PENDING_ACCOUNTABLE_OWNER_CERTIFICATION`

This is an explicit human action, not an agent-generated approval.

The accountable owner must review these exact records:

- `docs/04_Work_Breakdown_Structure.md` — WP-CORE-008 deliverables, source requirements and selected DoD.
- `docs/03_Requirements_Traceability_Matrix.md` §17 — the four WP-CORE-008 source rows and their `EVIDENCED_BY`/`EXECUTED_AS` edges.
- `traceability/trace_edges.yaml` and `traceability/generated/` — regenerated trace projection.
- `evidence/WP-CORE-008/AV-SCEN-01-2026-10-29.json` and its consistency output.
- `evidence/WP-CORE-008/AV-SCEN-03-2026-10-29.json` and its consistency output.
- `evidence/WP-CORE-008/EVID-WP-CORE-008-TECH-20261029/` — hashed technical bundle.
- `evidence/WP-CORE-008/RUNTIME-E2E-2026-10-29.md` and `DEP-028-CURRENT-MAIN-2026-10-29.md` — prior real runtime and dispatch evidence.

The owner must record explicit answers to all of these assertions:

1. The real runtime evidence is sufficient for the WP-CORE-008 Core/outbox/JetStream/Twin/BFF/UI acceptance slice.
2. The scope boundary is accepted: this does not claim the full Vision/RCA/Scheduler/Automation AV-SCEN-01 portfolio, final EV-L5 evaluation, production security acceptance, or CORE-004 protected rework semantics.
3. The same-PR trace/evidence update is acceptable as the technical closure record for this package.
4. The selected DOD-WP-01, 02, 03, 05, 06 and 12 criteria are satisfied at the stated scope.

The owner must append the signed/attributable certification to the canonical
WP evidence record with the following provenance kept distinct:

- historical runtime execution/source-main SHA:
  `ee060997b611fae16d6c4f13c0d85cebafaf17e7` (preserve as recorded in the
  runtime manifests and technical bundle; it is not the current main SHA);
- PR #210 technical closure merge SHA:
  `6299ab02491a9b7336b3637334ed461ce510ec21`;
- current GitHub `main` SHA at this checklist refresh:
  `6299ab02491a9b7336b3637334ed461ce510ec21`;
- technical bundle ID: `EVID-WP-CORE-008-TECH-20261029`.

The agent must not fill the accountable certification record.

After that human record exists, run:

```bash
projectctl check-done WP-CORE-008
```

Expected result: the gate can advance past `UNKNOWN` only if the canonical
owner record and all other current DoD facts are accepted; otherwise the exact
remaining fail-closed reason must be retained.
