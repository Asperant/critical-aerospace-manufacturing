# CTRL-HOST-008 / CHG-023 — deferred acceptance scope projection

Scope: the canonical-scope comparison inside the CHG-022 deferred acceptance proof.
Product code, canonical preference, Plane state and the DONE evaluator are unchanged.

Cause: `deferred_proof()` compared whole `docs/03` and `docs/04` Git blobs at the
implementation merge against the pinned policy. Any later edit to those shared files
(for example WP-PLAT-002, #27) invalidated the WP-CORE-001 wait, giving
`MULTIPLE_ACTIVE_WORK`.

Fix: `scope_projection()` digests only the WP's own WBS rows and card plus the rows and
block of each referenced requirement. `build_policy.py` pins one digest per WP;
the proof recomputes it from the merge-time blobs (verified against their Git SHA).

Local verification, 23 October 2026:
- `python -m pytest tools/projectctl/tests/test_execution_queue.py -q`: 66 passed.
- `python -m unittest discover -s tools/host/plane-transition -p 'test_*.py' -q`: 127 passed.
- `python -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -q`: 17 passed.
- `projectctl validate`: PASS (existing canonical warnings retained).
- `uv run --project ci --locked python ci/scripts/static_ratchet.py check`: PASS,
  no new findings; existing baseline retained.
- `build_policy.py` dry run against this tree: 179 projections, none unavailable.

Coverage: unrelated shared-file edits preserve the proof; own WBS row/card/sub-card
and RTM row/block edits, and a changed requirement set, invalidate it; missing,
oversized, unhashable, unparsable or ambiguous projection input fails closed; other
pinned sources still require exact blobs; the existing valid proof still passes; every
canonical WP projects.

Deployment and real AUTO_NEXT behaviour
are verified after merge through the supported installer. The CORE-005 external
integration blocker policy is not changed here.
