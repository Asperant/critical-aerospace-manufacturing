Read-only analysis for the WP_IMPORT_POLICY human gate. No CTRL-PM-009 implementation or mutation is authorized by this proposal.

Exact canonical lists, source hashes, owners and unmodified sprint windows are in CTRL-PM-008-wp-mapping-analysis.json:

- 57 single-cycle WPs: exactly one source-supported native cycle mapping each.
- 117 multi-cycle WPs: two-cycle planning windows, with no approved native-cycle selection rule.
- 5 canonically unscheduled WPs: WP-R2-001, WP-R2-002, WP-R2-003, WP-S-001, WP-X-001.

Proposed policy:

1. Preserve one Plane issue per canonical WP ID, visible in the title and external_id; preserve the exact canonical sprint window and all source cycle IDs in auditable static metadata. No duplicate issues, copied sub-items or guessed first/last cycle.
2. Distinguish canonical planning_window from native coordination_cycle. The native cycle is an operational coordination choice and must not rewrite or imply the duration/completion of the canonical window.
3. Map the 57 single-cycle WPs directly. Require an explicit human-approved per-WP coordination-cycle selection for each of the 117 multi-cycle WPs, within its canonical window, before calling the full import executable. No selection is made in this report. Keep the exact five canonically unscheduled WPs without native cycle membership.
4. Until the 117 choices exist, either defer import entirely (recommended under the current CTRL-PM-009 acceptance contract), or separately approve a partial import with those 117 operationally unassigned but still explicitly marked canonically scheduled in metadata. Such a partial import would NOT satisfy the 174-assigned acceptance invariant and must not be reported as CTRL-PM-009 complete.
5. Create all new WPs in BACKLOG, never READY; do not reset existing execution state on rerun. Assign Asrın only to his own 73 WPs if exact active project membership is verified. Preserve the other owners' canonical names and leave their WPs unassigned until membership exists. Confirm no project default assignee would silently substitute another account.

Missing project members (no invitations or assignments performed):

| Canonical owner | Affected WPs |
|---|---:|
| Selman Özdemir | 17 |
| Batuhan Kaya | 32 |
| Yavuz Gümüş | 57 |

Exact proposed full-import mutation budget after policy and API-contract approval, using one association write per WP (no unverified bulk optimization):

| Request | Intended successful writes | Body / semantics |
|---|---:|---|
| POST issues/ | 179 | canonical external_id/source, visible ID/title, audited metadata, BACKLOG state ID, milestone labels and verified assignees in the creation body |
| POST modules/{module-id}/module-issues/ | 179 | {"issues":["<created-WP-issue-id>"]}, one canonical module per WP |
| POST cycles/{approved-cycle-id}/cycle-issues/ | 174 | {"issues":["<created-WP-issue-id>"]}, only after each intended native cycle is resolved |
| Total | 532 | no extra state, module, cycle, label, invitation, requirement, dependency or blocker creations |

The first 179 writes include milestone-label/owner fields; they do not imply separate label/owner mutation requests. Missing owners stay unassigned. Read requests and bounded HTTP retries are additional API requests, not additional intended entity mutations. Idempotent resume must recompute inventory and skip existing intended entities/relations. A complete second import should require zero successful writes.

If a partial import is separately approved, its budget is 415 intended writes (179 issues +179 module associations +57 single-cycle associations); the 117 deferred cycle associations remain an explicit incomplete acceptance condition. No such partial import is approved here.

API contracts inspected read-only in the installed Plane v1 source:

- IssueSerializer accepts state, labels and assignees; the endpoint checks external_source/external_id duplication and exposes filtered reads.
- Module/cycle association endpoints accept an issues ID list and return their relationship records; module/cycle association operations can move existing relationships, so desired-vs-observed checks are required.
- Issue descriptions are normalized and sanitized HTML, so byte-for-byte description equality in the current static planner is insufficient proof of a live no-drift rerun.
- Missing/empty assignees may trigger the project default assignee in the installed serializer; this must be checked before import rather than assuming omission means unassigned.

Still unverified for live CTRL-PM-009: issue-create/read round-trip of canonical metadata and HTML normalization; actual assignee/label persistence and project default behavior; external-ID duplicate handling and ambiguous-create reconciliation on real issues; module/cycle association postconditions and no-drift rerun behavior. No live issue or relation writes were used to verify these contracts. A source inspection is not a live mutation/effect-verification test.

Additional approval required: the projection policy and 117 explicit cycle choices (or a clearly bounded partial-import exception); then approval of a concrete WP import preview after contract checks. Neither policy approval nor CTRL-PM-009 execution is implied by approval of CTRL-PM-008.
