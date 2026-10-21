# Projectctl corrective maintenance — 2026-10-21

Authorized by Asrın’s explicit maintenance request for existing commit `cff5528`.
Control scope: CTRL-PM-005 unified tooling, CTRL-PM-004 RTM, CTRL-PM-006 read-only
Plane adapter, CTRL-PM-013 gates, and WP-GOV-001 catalog input boundary.
C1 / CR-1: restore approved controlled-error behavior; no canonical semantics change.
No product WP is started, reopened, or declared DONE.

Initial branch: `maintenance/projectctl-audit-fixes`; initial HEAD: `cff5528`.
Latest S1 base: `8a3fe0e`; merged without conflicts as `0d86b03`.
Recovery ref: `recovery/projectctl-audit-cff5528`. No rewritten history.
The original audit reports remain untracked and unchanged; hashes are in preflight.json.
Identity and live protection were verified through GitHub API as Asperant.
The live Plane queue returned NO_TASK; this explicitly authorized existing maintenance
was integrated without modifying Plane or beginning S2. projectctl context rejects
control IDs, so the canonical control specification and existing evidence were read.

A01: malformed RTM consumed metadata and short View A rows have controlled diagnostics.
A02: malformed/unsafe catalog YAML gives redacted input error and exit 2.
A03: missing gate repository gives input error and exit 2.
A04: gate evidence wording follows CHG-018; CI/owner evidence remains required,
reviewer approval is advisory, UNKNOWN never becomes PASS.
N01: required null Plane lists fail explicitly, including later pages; optional denial,
empty lists and pagination behavior retain regression coverage.

Environment: locked ci/uv.lock, Python 3.11.16, uv 0.12.13, Ruff 0.7.4,
Pyright 1.1.389; PYTHONPATH=ci:ci/scripts; PYTHONDONTWRITEBYTECODE=1.
Exact commands and exit codes are in results.json; outputs are in validation.log.txt
with trailing terminal-padding whitespace removed. Raw local logs remain in
/tmp/asrin-projectctl-maintenance; no diagnostic content was altered.
All 12 recorded checks exited 0:

- Targeted regressions: 111 passed.
- Full projectctl suite: 295 passed.
- CI tooling: 26 passed.
- Offline host queue: 13 passed; transitions: 67 passed.
- Canonical validation PASS (existing warnings preserved).
- Catalog lint PASS, 306 records, history checked against origin/main (8a3fe0e).
- Contracts: 1 schema and 1 instance validated.
- Flake policy: 0 active quarantines; none applied to pytest runs.
- Syntax and git diff --check passed.
- Static ratchet PASS: existing 311 Ruff, 189 Pyright, 56 unformatted files;
  no new findings, unchanged baseline. Raw static checks are not claimed clean.

Existing tests cover deterministic valid exports, schema/artifact equality,
no-network/no-write default commands and malformed-input negative paths.
Author review found only the intended four source/four test files before this evidence.
A bounded added-line credential-pattern scan passed (limitations in preflight.json).
No secrets, dependencies, policies, canonical docs or runtime state were added.

Required GitHub Actions (projectctl, four T1 tiers, ci-gate), real service integration,
merge confirmation and post-merge verification are PENDING at this evidence commit.
They must be inspected and recorded in the PR; local tests are not merge authority.
No local service containers were launched on the shared host.

Rollout: protected-main squash merge after actual required checks pass; no bypass.
Rollback: revert via normal compliant PR. Post-merge: fetch main, verify merge ancestry
and all changed source/test blobs, rerun projectctl suite/validation/catalog/static gate,
and inspect main Actions. Gate execution evidence remains unavailable/UNKNOWN;
canonical warnings/static debt remain; this report certifies no product acceptance.
