# DEP-002 START readiness at current main (CHG-076)

Accountable owner of both nodes: Yavuz Gümüş. Basis: canonical main
`b1da9845f32768640bb2131cfd2a14976e5b93a6` (2026-10-28).

DEP-002 is DN-PLAT-REPO to DN-PLAT-CD, HARD at START, required readiness INTEGRATION_READY.
CHG-076 clarifies its predicate: the immutable GHCR image build is DN-PLAT-CD's own
deliverable (WP-CICD-002) and is not a precondition of that package's START. This file
records only what DN-PLAT-REPO provides today.

## Facts verified at this revision

| Fact | Where it was observed |
|---|---|
| `main` is protected; the required status contexts are `ci-gate` and `projectctl`, enforcement level "everyone" | Live read of the branch through the GitHub API on 2026-10-28 (the branch-protection endpoint itself needs administrator rights and answers 404 to the reader, so the recorded readback below is cited for the remaining fields) |
| Required checks `ci-gate` and `projectctl`, strict up-to-date branches, protection enforced for administrators, zero required approvals (CHG-018), status APPLIED on 2026-10-21 | [ci/required_checks.json](../../ci/required_checks.json) and [branch-protection-readback.json](../WP-CICD-001/branch-protection-readback.json), recorded by the repository owner (WP-CICD-001) |
| Tiered CI pipeline: scope, static, unit, contract and integration jobs aggregated by the `ci-gate` job, which requires every applicable tier to have run and succeeded | [.github/workflows/ci.yml](../../.github/workflows/ci.yml); `ci/tests/test_required_gates.py` (WP-TEST-007) fails if a gate step could be skipped or `ci-gate` stopped waiting for its jobs |
| The required checks are green on main at this revision | `ci-gate` is success on `b1da984` (main CI run 40685800983) |

## What this does not claim

- No GHCR publication, image digest, provenance or DeploymentRecord exists or is claimed.
- DN-PLAT-CD is neither SKELETON_READY nor INTEGRATION_READY; DEP-005 (DN-PLAT-INTEG to
  DN-PLAT-CD, HARD at INTEGRATION) is untouched and stays open.
- WP-CICD-002 is F0 and WP-CICD-003 is F1; their DoD, integrated acceptance (TEST-PLAT-CD,
  INSP-DEP-HOST) and NFR-DEP-003/NFR-DEP-004 obligations are unchanged.
- Delegation: the change is applied by the node owner under authority delegated by the
  planning owner, as reported by Yavuz on 2026-10-28; CHG-076 is `UNDER_REVIEW` until the
  planning owner confirms it on the pull request.
