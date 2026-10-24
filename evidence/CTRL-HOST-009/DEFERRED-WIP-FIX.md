# CTRL-HOST-009: align transition WIP with verified deferred waits

Authorized scope: the 24 October 2026 user request to correct the heavy-Core WIP
counting bug only. Compatible correction under existing CHG-024/025, class C1,
review risk CR-3 (workflow gate); zero development approvals. No new policy,
threshold, authority, readiness or product semantics. No requirement/RTM change.

`transition.evaluate()` still selects other assigned IN_PROGRESS items and still
applies the same general threshold and size-L/any-Core heavy definition. Before
both checks, it obtains fresh `live_view()` through the existing root-owned
adapter and uses the shared `released_wait()` classifier. Only positively
verified waits are excluded. An incomplete view, missing item or exception
preserves the original active set; UNKNOWN or malformed proof keeps its item.
There are no production WP IDs in this implementation.

The production trust path is unchanged: installed policy/source verification,
root blocker audit, unedited owner assessment, exact owner/revision/dependency
binding and canonical-scope verification. The fix never accepts a health cache,
BLOCKED label or prose assertion as proof. Module loading and `live_view()` are
read-only; no AUTO_NEXT executor is called.

## Local verification

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tools/host/plane-transition -p 'test_*.py'`: 163 passed.
- `ci/.venv/bin/python ci/scripts/static_ratchet.py check`: PASS; unchanged tight baseline, Ruff 0.7.4 / Pyright 1.1.389.
- `projectctl validate --json`: PASS, existing canonical warnings retained.
- `projectctl catalog-lint --base origin/main`: PASS, 306 records; readiness NOT_CERTIFIED.
- `git diff --check`: PASS.

New regression cases exercise the actual transition evaluator, actual `live_view`
and actual shared classifier with offline root-proof-adapter fixtures: verified
deferred heavy Core; missing/UNKNOWN/invalid/foreign/owner-work/stale proof;
ordinary unblocked and BLOCKED Core; one/two nonheavy active WPs; a nonheavy
target alongside heavy work; only one of two items verifiably deferred; incomplete
view; missing item preventing partial active-set filtering. Existing adapter tests
exercise audit/comment/revision/scope proof validity. No tests call live Plane or
GitHub, and test evaluation performs no PATCH.

## Rollout and acceptance

Merge only after required current-head `projectctl` and `ci-gate` succeed. Deploy
only the clean merged reference source through the existing policy builder and
`install_auto_next.py` (root-only backup/rollback and hash verification). Do not
run AUTO_NEXT, transition any product WP, change product code or change unrelated
control rules. Verify installed source/helper and policy digests and make a fresh
read-only released-wait/WIP observation after deployment. A deployment attempt
without root privilege is a blocker, not a successful rollout. Deployment details
and CI/merge references belong in the PR; no deployment success is claimed here.
