# CTRL-HOST-014 / CHG-030 — deferred acceptance wait re-assertion

Scope: the evidence anchor of the CHG-022 deferred acceptance proof. The proof is bound to
the merged PR's merge commit and compared against the pinned canonical sources, so a later
change to a whole-blob pinned source (for example a roadmap) permanently invalidated an
unchanged wait, and a re-assertion of BLOCKED only records `UNCHANGED`. The proof may now be
bridged by a later UNCHANGED re-assertion of the same VERIFIED blocker, mirroring CHG-025 for
external waits. Product code, Plane state, candidate ordering, DONE, the meaning of UNCHANGED
and what qualifies as a deferred wait are unchanged; no work package is special-cased.

Rules: see CHG-030. The VERIFIED audit stays the sole authority that the blocker is active.
The re-assertion is only consulted when the original canonical-scope check fails on a changed
whole-blob source; the WP's own scope projection must be unchanged at the original merge
commit and at the assessed revision. The assessment comment must restate the identical
blocker, `Owner-executable implementation work: NONE`, claim no resolution and be unedited
and owner-authored. A fake UNBLOCKED to refresh the anchor is neither needed nor allowed.

Local verification, 24 October 2026:
- `python -m unittest test_auto_next` (tools/host/plane-transition): 44 passed.
- `python -m pytest tools/projectctl/tests/test_execution_queue.py`: 90 passed.
- Ruff lint and format on the changed files: clean.

Coverage: valid VERIFIED then UNCHANGED chain releases the slot while the original anchor
alone and UNCHANGED alone do not; an unchanged original anchor needs no re-assertion;
incomplete re-assertion proofs are rejected by the resolver; changed blocker code, reason,
dependency or blocking WP, changed scope now or at merge, invalid current sources,
owner-executable or UNKNOWN work, UNKNOWN revision, a claimed resolution, edited, foreign or
evidence-less comments, missing artifacts, missing or multiple comment refs, a carried
blocker, a wrong audit link, UNBLOCKED, other-state, other-WP and truncated-tree rows, and a
missing, INTENT, UNBLOCKED or wrong-state previous proof all fail closed.

Verification is recorded in the pull request; deployment and the real effect on the live
chain are recorded after merge.
