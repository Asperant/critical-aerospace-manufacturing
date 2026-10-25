# CTRL-HOST-015 — merged external binding wait slot accounting

Authorized scope: CHG-034, C3 / CR-3, explicit project-owner request dated
2026-10-25. Source baseline: main `9db6a1080b8604a36a4629d85c8f844b57879cd6`.
This evidence belongs to its containing commit; it makes no deployment or live
slot-release claim.

## Implemented behavior

A separate `cap-merged-external-wait-v1` proof can release an implementation slot
only for VALIDATING + BLOCKED + WAITING_EXTERNAL_INTEGRATION_BINDINGS.
The existing CHG-022 acceptance-only and CHG-024 IN_PROGRESS paths are unchanged.
The WP remains visible, VALIDATING and BLOCKED; no readiness, DONE, acceptance or
implementation-complete claim is generated, and transition predicates are unchanged.

Required proof: actual owner-authored merged WP PR, deleted branch and merge
ancestry; required successful CI and a successful main run at that exact merge
SHA; intact VERIFIED BLOCKED audit or valid UNCHANGED re-assertion; one unedited
owner comment at current main stating owner work NONE and local actionable work
NONE, exact audited/assessed blocker equality, and every approved binding ID.

The separately pinned `project_control/merged_external_bindings.yaml` requires
explicitly reviewed canonical producer/consumer WPs and owners, scope projection
digests, precise consumer requirements, canonical provenance hashes and concrete
producer binding output paths. Empty/missing/stale/ambiguous provenance retains
the slot. The real current-main tree must be complete and every mapped output
still absent; delivered output requires reassessment. Current-main movement also
requires fresh accountable evidence. No missing binding is inferred from a title,
owner-work declaration or transport name.

The initial registry has no entries. This is intentional: EVT-002 has no newly
invented producer mapping or live assessment. Actual mapping admission is a
separate reviewed canonical source change. This code change alone cannot release
EVT-002's slot or resolve CORE-004/005 ambiguity.

## Focused verification actually executed

All tests use local fixtures or a temporary policy output; no Plane/GitHub calls,
root installer, preparation controller or AUTO_NEXT writer were invoked.

| Command / check | Actual result |
|---|---|
| `python -m unittest discover -s tools/host/plane-transition -p test_merged_binding_wait.py -q` | 14 passed |
| `python -m unittest discover -s tools/host/plane-transition -p test_auto_next.py -q` | 44 passed |
| `python -m unittest discover -s tools/host/plane-transition -p test_transition.py -q` | 69 passed |
| Pinned CI Python / pytest on `tools/projectctl/tests/test_execution_queue.py` with this checkout on PYTHONPATH | 90 passed |
| Pinned CI Python `-m unittest test_recovery.PolicyPinningTests -q` | 1 passed; actual builder output in a temporary directory pins CHG-034 and binding registry in policy and source blobs |
| Pinned Ruff check/format on changed proof, resolver and regression modules | PASS |
| Pinned Pyright on new proof module, regression module and resolver | 0 errors, 0 warnings |
| Policy builder syntax and comparison against main | PASS; 0 added Ruff diagnostics; its 6 pre-existing Pyright diagnostics are identical to main |
| `projectctl validate --json` | PASS |
| `projectctl catalog-lint --base origin/main --json` | PASS |
| `git diff --check` | PASS |

Total: 218 focused tests, including 14 new regressions. Negative cases cover
unmerged/undeleted/unreachable PR, wrong or failed main CI, local/UNKNOWN/missing/
duplicate fields, forged/mismatched audits, edited/foreign/wrong-PR assessments,
missing/stale/foreign provenance, truncated trees, delivered bindings and invalid
re-assertion chains. Slot release does not bypass the blocker or DONE gate. No
broad repository suite ran. Fixtures mock canonical scope reads; the unchanged
scope algorithm is covered by the existing AUTO_NEXT suite.

## Delivery limitations

Not pushed, PR CI not observed, not merged, not deployed. Deploy only from merged
canonical reference through the existing policy/helper refresh and root
backup/rollback installer. Live blocker assessment or re-assertion requires separate
authorization and true reviewed binding provenance; historical evidence is not
rewritten and no artificial unblock/reblock cycle is introduced.
