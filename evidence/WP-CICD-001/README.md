# WP-CICD-001 implementation evidence

Local development evidence, 2026-10-21, on `wp/WP-CICD-001-ci-pipeline`
(base `main` = `944fd567d7bfa98288c4c3ee2235f321dbde52da`). This is not a sealed EvidenceBundle, a remote CI
result or a final acceptance record.

## Authorization and scope

`projectctl context WP-CICD-001` was read before implementation.
`projectctl check-ready WP-CICD-001` returned UNKNOWN (planning prose never
yields PASS); UNKNOWN was not converted to PASS. The owner's manual DoR
assessment (DOR-WP-01…08) is recorded on the Plane item. Scope: F1, M0/S1,
DN-PLAT-REPO, ARCH-PLAT-CICD; source requirements FR-PLAT-004 (CI half) and
NFR-DX-006. Review risk class estimate CR-2; development approvals 0 (CHG-018).

## Deliverables

| Deliverable (04) | Realization |
|---|---|
| CI workflows (lint, type, unit, contract, integration tiers) | `.github/workflows/ci.yml`: t1-static, t1-unit, t1-contract, t1-integration and aggregate `ci-gate`; toolchain pinned in `ci/pyproject.toml` + `ci/uv.lock`; rules in `ruff.toml`, `pyrightconfig.json`; ratchet `ci/static_baseline.json` |
| required-check configuration | `ci/required_checks.json` (`ci-gate`, `projectctl`; 0 approvals; enforce_admins) and `ci/scripts/apply_branch_protection.sh`. **Status NOT_APPLIED**: HTTP 403 on private-repository protection (CTRL-PM-012) |
| flaky-test registry and quarantine policy | `ci/flaky_tests.yaml`, `ci/scripts/check_flake_policy.py` (expiry, ownership, no retry-until-green), `ci/pytest_quarantine.py` |

`.github/workflows/projectctl.yml` is unchanged on purpose: the Plane
transition helper binds to its `projectctl` job and step names.

## Readiness and completion obligations

| Criterion | Assessment and concrete references |
|---|---|
| DOD-WP-01 | Deliverables above exist; 04 repository reference updated |
| DOD-WP-02 | 03: NFR-DX-006 REALIZED_BY/VERIFIED_BY/EXECUTED_AS, planning EVIDENCE_PENDING; §19.2 assets; FR-PLAT-004 intentionally VERIFY_PLANNED (CD half is WP-CICD-002) |
| DOD-WP-03 | Local outputs recorded (RUN-CICD-001-LOCAL-001); remote CI on the PR head is pending |
| DOD-WP-04 | Negative paths tested: ratchet regression, new-file finding, new rule, newly unformatted file, tool-version drift, loosened baseline, update refusing regressions; registry missing fields, expired, overlong, duplicate, unknown owner; retry plugin/option/action/continue-on-error detection; plugin refuses an expired registry; invalid schema and invalid instance; integration tests fail (never skip) without services |
| DOD-WP-06 | Not a runtime service; CI job logs and the gate summary are the observable surface |
| DOD-WP-07 | `ci/README.md` documents tiers, local commands, ratchet, quarantine and protection procedure |
| DOD-WP-12 | No fixture is used as milestone/final evidence; integration boundary mode is REAL |

## Executions

`RUN-CICD-001-LOCAL-001.json` records every command, UTC start/end, exit code
and output tail; `RUN-CICD-001-LOCAL-001.log.txt` is the readable log. Result:
PASS for static, unit, contract, projectctl validate, catalog lint and
whitespace. **t1-integration was not executed locally** (no Docker in that
environment); no integration result is claimed until GitHub Actions runs it.

Static baseline at introduction (Ruff 0.7.4, Pyright 1.1.389, repository
rules): Ruff 311 findings, Pyright 189, 56 unformatted files — all in
pre-existing code (`tools/`, `project_control/`). New `ci/` code: 0 findings,
Pyright strict.

## Remaining gates and limitations

1. Remote CI on the PR head (all T1 jobs + `ci-gate` + `projectctl`).
2. Branch protection blocked by the GitHub plan; the repository owner must enable
   a supporting plan (GitHub Pro for a personal account), then run
   `ci/scripts/apply_branch_protection.sh --apply` and record the response.
3. Plane transition policy: `required_ci` currently lists only `projectctl`;
   adding `ci-gate` is a host-control (CTRL-HOST) change, not made here. The
   docs/03 and docs/04 edits change source hashes, so the host policy must be
   refreshed after merge, as after earlier documentation merges.
4. A Ruff configuration outside the repository exists on the shared host and
   should be removed so local runs use `ruff.toml`.
5. Pre-existing findings are owned by the code owners; the ratchet only keeps
   them from growing.
6. Post-merge validation on `main` is required before DONE (Merged != Done).

## Remote CI on PR #9

First remote execution on PR head `73a7ac42cc1f4fd186325284a4e6d93488590ac8` (2026-10-21): all 12 checks
successful on push and pull_request events: `projectctl`, `t1-static`,
`t1-unit`, `t1-contract`, `t1-integration` (first REAL PostgreSQL + NATS
JetStream execution) and `ci-gate`.

| Workflow | Event | Run |
|---|---|---|
| ci | pull_request | https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/39602871893 |
| projectctl | pull_request | https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/39602871790 |
| ci | push | https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/39602825691 |
| projectctl | push | https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/39602824964 |

Still pending: post-merge validation on main and branch protection (HTTP 403).

## Branch protection applied

The repository was made public by team decision so that branch protection is
available on the current plan. The owner (Asperant) created the classic rule on
`main` through the GitHub UI with the configuration in `ci/required_checks.json`:
required checks `ci-gate` and `projectctl`, up to date before merge, pull request
required with 0 approvals (CHG-018), no bypass for admins, no force push or
deletion. `apply_branch_protection.sh --apply` could not be used from the shared
host because every profile resolved to a non-admin GitHub identity (host-wide gh
keyring; see the owner's developer-environment audit of 2026-10-21).
Independent read-back by the WP owner: `branch-protection-readback.json`
(`enforcement_level: everyone` = admins included). Before publication the full
history was scanned with gitleaks 8.21.2 (46 commits, 0 findings). This pull
request is the first change merged under the protection.
