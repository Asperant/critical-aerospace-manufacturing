# CTRL-HOST-011 / CHG-026 — candidate-window starvation

Scope: the candidate window of health diagnostics and the preparation controller.
Eligibility, HARD dependency/DoR/readiness gates, UNKNOWN handling, AUTO_NEXT selection,
Plane state and canonical preference are unchanged. No WP or owner is special-cased.

Cause: both the resolver (`candidates[:3]`) and the controller (`health["candidates"][:3]`)
examined only the first three canonical candidates. When those were WAITING_DEP, later
candidates the preparation engine classifies AUTO_PREPARABLE were never assessed, so no
DoR preparation could start and AUTO_NEXT had nothing eligible.

Fix: `candidate_window()` returns the canonical-order prefix through the first actionable
candidate (never fewer than three); health supplies the engine's classification as the
`actionable` test, so the controller loop over that window and the resolver agree.
Non-actionable candidates stay reported; the scan is bounded by the finite BACKLOG.

Local verification, 23 October 2026:
- `python -m pytest tools/projectctl/tests -q`: 398 passed.
- `python -m unittest discover -s tools/host/plane-transition -p 'test_*.py' -q`: 139 passed.
- `python -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -q`: 17 passed.
- `projectctl validate`: PASS (existing canonical warnings retained).
- `uv run --project ci --locked python ci/scripts/static_ratchet.py check`: PASS,
  no new findings; existing baseline retained.
- `build_policy.py` dry run: CHG-026 in the manifest.
- Mutation check: restoring the old `[:3]` window in the resolver and the controller made
  5 resolver and 3 controller cases fail; both files were restored before the final run.

Coverage: first three blocked, fourth preparable is selected with the blocked head still
reported; the first eligible candidate still wins; an UNKNOWN candidate never becomes
eligible nor stops the scan; no eligible candidate keeps the three-candidate head and the
existing NO_TASK behavior; a custom classifier selects without making anything PREPARED;
determinism and bounds; the controller walks past WAITING_DEP / REAL_WORK_REQUIRED /
UNAVAILABLE candidates to the first AUTO_PREPARABLE one and acts once; with none it changes
nothing; the controller window and the resolver window share the same canonical order.

Verification is recorded in the pull request; deployment and the real first preparable
candidate are recorded after merge.
