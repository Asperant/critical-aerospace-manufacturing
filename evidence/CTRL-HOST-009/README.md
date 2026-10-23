# CTRL-HOST-009 / CHG-024 — external integration binding wait

Scope: implementation-slot accounting for verified `IN_PROGRESS + BLOCKED` work whose
remaining work is gated solely by canonical external integration bindings. Product code,
canonical preference and candidate ordering, Plane state and the DONE evaluator are
unchanged. No work package is special-cased by ID.

Rule: see CHG-024. Proof mechanism: root verified BLOCKED audit -> exactly one unedited
owner-authored comment with exact single fields (`Canonical main revision`,
`External integration wait class`, `Owner-executable implementation work: NONE`) ->
audited blocker equals assessed blocker -> external dependency cites a canonical node of
the WP's own dependency edges at an explicit readiness level -> canonical inputs at the
assessed revision (including the WP WBS/RTM projection of CHG-023) equal the pinned
policy. Anything else leaves the slot occupied.

Local verification, 23 October 2026:
- `python -m pytest tools/projectctl/tests/test_execution_queue.py -q`: 83 passed.
- `python -m unittest discover -s tools/host/plane-transition -p 'test_*.py' -q`: 133 passed.
- `python -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -q`: 17 passed.
- `projectctl validate`: PASS (existing canonical warnings retained).
- `uv run --project ci --locked python ci/scripts/static_ratchet.py check`: PASS,
  no new findings; existing baseline retained.
- `build_policy.py` dry run: `external_wait_schema` pinned, CHG-024 in the manifest.

Coverage: verified external wait releases the slot and is previewed in `deferred_waits`;
owner-executable, UNKNOWN, duplicate or missing fields; generic or unknown blocker
classes; unverified, unblocked, other-state or other-profile audits; missing or multiple
comment refs; edited or foreign-authored comments; changed blocker; missing, unknown,
non-edge or level-less dependency nodes; changed or unavailable canonical scope;
ordinary IN_PROGRESS, unblocked and unsupported-schema paths; every other active state;
tampered or incomplete proofs; independence from the CHG-022 deferred proof; one READY,
unchanged candidate order and other owners.

Deployment, and whether any real WP currently satisfies the proof, are recorded after
merge; an existing prose-only assessment does not satisfy the exact-field requirement.
