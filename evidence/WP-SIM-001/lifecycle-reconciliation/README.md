# WP-SIM-001 lifecycle reconciliation — evidence

Local, offline development evidence for the change record CHG-031 (DRAFT, UNDER_REVIEW), on a branch based on
`origin/main` 5269525. It is not a sealed EvidenceBundle, a remote CI result, an installation, a live Plane or GitHub run, or an
acceptance record, and it is separate from the kernel evidence in the parent directory.

## What this change is

`cap-plane-reconcile <WP-ID> <MERGED|VALIDATING>` repairs one case: a work package whose PR really merged while Plane still
shows a premerge state. Only cases allow-listed in `project_control/lifecycle_reconciliation.yaml` work (here: batuhan /
WP-SIM-001 / PR 52). It re-proves the PR, the complete file scope, the merge and the started main runs from fresh GitHub reads,
refuses over a second READY or IN_PROGRESS item of the same owner, writes a durable audit row, makes one state PATCH and
reads it back. It never writes DONE, clears BLOCKED, calls AUTO_NEXT or invents skipped history, and the ordinary
`cap-plane-transition` rules are unchanged. `GitHub.files` now reads every PR file page (ceiling 1000 files). Nothing is installed.
Authority: plan `bb3747e3…2061` (Codex), owner scope answer `fcacd0c9…`, task-local control-ID exception `288a928f…`.

## Files here

| File | Content |
|---|---|
| `results.json` | every command with exit code, timestamps and result line (`gate` run, then `post` run after these files existed) |
| `outputs/` | full output of commands whose output is short (<= 40 lines) or that failed |
| `run-manifest.json` | SHA-256 of each of the 21 changed/new source files and of their map, tool versions, plan hash |
| `mutation-check.txt`, `mutation_check.py` | 36 injected defects against a clean baseline; all must be caught |
| `lifecycle-offline-check.json`, `lifecycle_offline_check.py` | the real generated policy run through `reconcile()` against fixtures bound to PR 52 |

## Result

All 19 gate commands and the 5 post-evidence commands exit 0: 226 plane-transition tests (163 existing, 6 upstream, 57 new) and
25 plane-queue tests, static ratchet unchanged, flake policy, 96 ci tests, test-strategy gate, 398 projectctl tests,
contracts, validate, catalog-lint, Ruff and Pyright on the new Python files, policy-builder dry run, the offline fixture check
(one PATCH, audit INTENT then VERIFIED, helper hash pinned, upstream CHG-030 kept, CHG-031 present) and 36 of 36 injected
defects caught. These are offline fixtures: they do not show behaviour against real Plane or GitHub.

## Limits and open decisions

- Not run against real Plane or GitHub; the mutation and offline-check scripts live outside the repository tree and are copied here.
- The owner-queue rule is a conservative reading of "ambiguous membership/WIP" (AGENTS.md section 20): a live application is
  refused while the owner has a second READY or IN_PROGRESS item.
- Ordinary transitions now accept PRs of 100 to 1000 files. A refresh through `install_auto_next.py` also reinstalls the other
  AUTO_NEXT files and timers (existing installer behaviour).
- This change was first drafted locally as CHG-030, which upstream took (CTRL-HOST-014) before publication. Upstream's CHG-029 and
  CHG-030 are untouched; this change uses CHG-031. The CHG-031 owner field and registry row need governance-owner confirmation.
- Kernel DoR is UNKNOWN. FR-SIM-001 REAL, AV-SCEN-01, E2E-01, BENCH-SIMVAL-001 and DONE are open. Plane still shows READY; the update
  to VALIDATING happens only after merge, a merged-source installation and a separate live-application approval.
- History: earlier, larger revisions of this evidence (nine runs, about 15,800 lines) are kept outside the repository in the
  workflow folder and as the local backup ref `backup/WP-SIM-001-recon-c0eb47d`. They were reduced because most of that volume
  was repeated tool output.
