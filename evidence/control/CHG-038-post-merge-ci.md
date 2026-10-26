# CHG-038 / CTRL-HOST-019 — post-merge DONE CI evaluator

Status: PRE-MERGE
Control branch: `control/CHG-038-post-merge-ci`

## Implemented behavior

- `MERGE_READY` and other pre-merge paths continue to use the bounded
  `projectctl` fast gate.
- `DONE` uses aggregate main CI only, currently `ci-gate`.
- The aggregate check must resolve to a completed successful main workflow run
  at the exact merge SHA.
- Missing, failed, ambiguous, pull-request, or wrong-SHA CI evidence fails
  closed.
- `projectctl-full-regression` remains a main/nightly/manual regression lane;
  it is not a DONE hard gate.

## Local verification

- `python -m pytest -q tools/host/plane-transition/test_transition.py tools/host/plane-transition/test_reconcile_generic.py`
  — PASS: 79 passed, 101 subtests passed.
- `python -m pytest -q tools/host/plane-transition tools/host/plane-queue`
  — PASS: 316 passed, 505 subtests passed.
- `uv run --project ci --locked python ci/scripts/static_ratchet.py check`
  — PASS: no new static findings.
- `git diff --check` — PASS.

Post-merge CI and deployment evidence will be appended after the PR is merged;
no lifecycle transition is performed by this control change.
