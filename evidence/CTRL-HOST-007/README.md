# CTRL-HOST-007 / CHG-022 — deferred acceptance implementation slot

Scope: narrow slot accounting for verified downstream acceptance waits. Product
code, canonical preference and the transition/DONE evaluator are unchanged.

Local verification, 23 October 2026:
- `python -m pytest tools/projectctl/tests/test_execution_queue.py -q`: 49 passed.
- `python -m unittest discover -s tools/host/plane-transition -p 'test_*.py' -q`: 123 passed.
- `python -m unittest discover -s tools/host/plane-queue -p 'test_*.py' -q`: 17 passed.
- `projectctl validate`: PASS (existing canonical warnings retained).
- `uv run --project ci --locked python ci/scripts/static_ratchet.py check`: PASS,
  no new findings; existing baseline retained.

Coverage includes exact deferred classification, owner/revision/audit binding,
merge/branch/CI/artifact/canonical-scope failures, ambiguous assessment, remaining
owner work, every other active state, ordinary VALIDATING, duplicate READY,
canonical preference, other owners and unchanged final DoD rejection.
A historical health fixture was completed with its active item in the live snapshot.

Deployment and real AUTO_NEXT verification remain pending at this commit. Required
GitHub checks must pass before merge. Root-only installer backup/rollback is used;
no Plane state is restored by rollback. Real integrated acceptance for WP-CORE-001
is still missing and is not certified by these control-plane tests.
