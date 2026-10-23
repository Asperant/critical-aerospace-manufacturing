# CTRL-HOST-012 / CHG-027 — developer queue deferred visibility

Scope: display and selection in `cap-plane-queue` only. Plane state, AUTO_NEXT policy, WIP rules,
candidate selection and DONE are unchanged; no WP ID is special-cased.

Cause: `select()` chose the first plain IN_PROGRESS row as `current_task` from Plane state alone and
only afterwards attached the resolver's `deferred_waits`, so a verified deferred IN_PROGRESS + BLOCKED
wait replaced and hid the owner's READY work.

Fix: health (including `deferred_waits`) is read first; `combine()` excludes those WP IDs from
selection and keeps them listed. READY work becomes `current_task` and remains in `next_task`.

Local verification, 23 October 2026:
- `python -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -q`: 25 passed (8 new).
- `python -m unittest discover -s tools/host/plane-transition -p 'test_*.py' -q`: 139 passed.
- `python -m pytest tools/projectctl/tests/test_execution_queue.py -q`: 90 passed.
- `projectctl validate`: PASS; static ratchet: PASS, no new findings; `build_policy.py` dry run OK.

Coverage: READY work is current_task with deferred IN_PROGRESS/VALIDATING waits excluded and listed;
only waits give null current/next with waits still listed; ordinary IN_PROGRESS and ordinary blocked
IN_PROGRESS still win; multiple actionable work stays AMBIGUOUS; unavailable or empty classification
excludes nothing; classification comes from resolver output, not IDs; other owners untouched.

Verification and deployment are recorded in the pull request.
