# CTRL-HOST-010 / CHG-025 — external wait re-assertion evidence

Scope: the evidence source of the CHG-024 proof. Re-asserting BLOCKED on an already
blocked WP records `UNCHANGED`, so a fresh owner assessment could never become a VERIFIED
audit without a false UNBLOCKED. The proof may now take the assessment comment from a later
UNCHANGED re-assertion of the same verified blocker. Product code, Plane state, candidate
ordering, DONE and the generic meaning of UNCHANGED are unchanged; no WP is special-cased.

Chain rules: see CHG-025. The VERIFIED audit remains the sole authority that the blocker is
active; the re-assertion links to it, repeats its reason, carries no blocker, and all rows
recompute their `audit_id`. Duplicate, edited, foreign, UNBLOCKED, INTENT or otherwise
unexpected later rows fail closed. The comment must satisfy every CHG-024 requirement.

Local verification, 23 October 2026:
- `python -m unittest discover -s tools/host/plane-transition -p 'test_*.py' -q`: 136 passed.
- `python -m pytest tools/projectctl/tests/test_execution_queue.py -q`: 83 passed.
- `python -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -q`: 17 passed.
- `projectctl validate`: PASS (existing canonical warnings retained).
- `uv run --project ci --locked python ci/scripts/static_ratchet.py check`: PASS,
  no new findings; existing baseline retained.
- `build_policy.py` dry run: CHG-025 in the manifest.

Coverage: valid VERIFIED -> UNCHANGED chain passes; the VERIFIED record alone and UNCHANGED
alone do not; direct VERIFIED proof still passes (also when a re-assertion comment is
unusable); changed reason or blocker, wrong WP, other state or operation, unknown,
non-VERIFIED or duplicated predecessor, INTENT or extra later rows, edited audit rows,
re-assertion carrying its own blocker, edited, foreign or incomplete comments, missing or
multiple comment refs, changed canonical scope, and generic blockers all fail closed.

Verification is recorded in the pull request; deployment and the real effect on the live
chain are recorded after merge.
