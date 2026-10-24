# WP-DOC-002 closeout — ADR backfill and decision index

Owner: Asrın Dündar (Asperant). Date: 24 October 2026.
Branch: `wp/WP-DOC-002-adr-backfill`. Control record: `09_change/CHG-029.yaml` (C0).
This document reconciles engineering evidence. It does not certify requirement
verification, ADR validation or Plane state.

## Deliverables and where they are

| Deliverable (04) | Repository reference |
|---|---|
| ADR template and index | `docs/adr/TEMPLATE.md` (14 metadata fields, 16 body sections), `docs/adr/README.md` (lifecycle, levels, evidence levels, reversibility, triggers, exclusions, fixed map) |
| 13 backfill ADRs from 02 | `docs/adr/0001` … `docs/adr/0013`, minted by the fixed list position of the 02 backfill set |
| ADR linkage in the trace registry | `docs/03_Requirements_Traceability_Matrix.md`: the five existing `DECIDED_BY` edges (FR-CORE-012 → ADR-0012, FR-SIM-001 → ADR-0007, FR-SCH-009 → ADR-0008, FR-AUTO-002 → ADR-0004, FR-PLAT-001 → ADR-0011); GAP-RTM-023 resolved |
| When a new ADR is required | `docs/adr/README.md`, sections "When a new ADR is required" and "Exclusions" |

## Verification performed

- Focused structural test `ci/tests/test_adr_scaffold.py` (51 passed): the 13 IDs are unique and the position mapping is fixed; the template carries every field and section in order; every record is valid and matches the map; local links resolve; no `ADR:backfill-NN` placeholder remains in 03; each repointed edge targets a minted ACCEPTED ADR. Negative cases show malformed records (bad status, level, validation state, date, ADR-ID, missing or renamed section, missing or duplicated field, empty value) and a broken link are rejected.
- `projectctl validate` (exit 0, 634 existing warnings, zero errors), `projectctl catalog-lint` (exit 0), static ratchet (no new findings) and `git diff --check`.
- Required CI is recorded on the pull request.

## What is not claimed

- No ADR is `VALIDATED`; every record keeps `ValidationState: PENDING` and an honest evidence level (E0 or E1, documentation only).
- ADR reversibility classes and decision levels are record-author assignments where the specification states none; each record says so.
- Requirement, risk and debt links are `None linked yet` where the canonical sources record none. No `DECIDED_BY` edge was created for a requirement that had none. FR-AI-001, FR-SEC-001, FR-PLAT-006 and FR-RAG-005 were listed in the old GAP-RTM-023 text but never carried an edge.
- FR-GOV-004 is co-allocated to WP-GOV-002, which owns the trace registry and the trace linter (`TEST-GOV-TRACELINT`, TL-01…TL-13). That linter does not exist yet, so FR-GOV-004 coverage stays ALLOCATED and its evidence state stays `NOT_YET_EXECUTED`. This WP does not set `REALIZED_BY` or `VERIFIED_BY` for FR-GOV-004.
- The architecture-changing ADR update flow (02 updated after an accepted ADR) is not triggered: every record documents a decision already incorporated in 02.

## Pinned-source note

`docs/06A_Asrin_Engineering_Roadmap.md` is a whole-blob pinned source in every Asrın work package manifest. An edit to its WP-DOC-002 cut/fallback sentence invalidated the released-wait proofs of the other Asrın work packages, which are anchored to older revisions, so the edit was reverted to the exact earlier blob. That sentence ("DECIDED_BY edges in 03 currently point at placeholders") is therefore stale until a planned canonical refresh; 03 and the 04 card carry the current truth. `docs/03` and `docs/04` are compared by per-work-package projection and are unaffected.
