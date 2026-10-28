# Evidence — CTRL-HOST-031 (finish the CHG-054 start-transition decoupling)

Control item, not a product WP: scope authority is `09_change/CHG-054.yaml` and the approved plan
(SHA-256 `9d6b4bd5cb449f8c318334d295abd7d1408593a9235231add8200e50e40c0b83`). The change is in
`tools/host/plane-transition/` (`transition.py`, tests, README). These are **offline fixture runs**
(fake Plane and GitHub objects): no credential, network, Plane write or installation, and none is a
live deployment PASS.

## Run of record

`runs/run-3-uncommitted/` — one local run of `capture_run.py` on the **uncommitted** tree: base
`e1752d90febabc5db09ba61fd6380a2951462bf6` (`origin/main`), 11 changed or untracked input files hashed in
`identity.json` (`tree_clean` false: no commit is authorized in this pass), 2026-10-28T15:33:29Z to 15:34:00Z,
Python 3.11.16, locked CI toolchain, Intel i7-9700K, shared host. Not committed-source evidence.

| Command | Exit | Result |
|---|---|---|
| `focused-transition-artifact-chg054` (`test_transition`, `test_artifact_refs`, new `test_chg054_start_transitions`) | 0 | 102 passed |
| `collector-tests` (`evidence/CTRL-HOST-031/tests`, run by the existing CI host-transition step) | 0 | 6 passed |
| `focused-recovery-install` | 0 | 19 passed |
| `ci-style-unittest-discover` (the whole directory, as the CI step runs it) | 0 | 306 tests OK |
| `reproduce-on-original-source` | **1, expected** | **7 failed, 11 passed** (below) |
| `ruff-check`, `ruff-format --check` on new files and the collector | 0, 0 | clean |
| `static-ratchet` | 0 | no new findings; baseline tight after `update` |
| `check-test-strategy` | 0 | PASS (151 files, 27 suites) |
| `git-diff-check` | 0 | clean |

The run exits 1 only because of the reproduction, which is intended.

## Reproduction of the defect

`repro_original.py` runs the new regression module against `origin/main`'s `transition.py` in a temporary
tree. The 7 failing tests are exactly the removed or missing behaviors: BACKLOG to READY without READY.md, DoR
comment, preparation, schedule or free slot; an unresolved or status-less HARD + START edge stopping both start
transitions; real-object checks of READY evidence; and the typed GitHub failures (missing repository file,
403, 5xx, timeout, oversize and malformed responses). The 11 passing tests are protections that must hold both
before and after (owner and assignee, real BLOCKED, BACKLOG to IN_PROGRESS invalid, real work facts, later HARD
gates not blocking start, MERGE_READY and DONE staying fail-closed).

## Other checks (scratch, not committed)

12 injected defects in `transition.py` (drop the READY predicate, treat a missing status as ready, let an
INTEGRATION edge block start, relabel 404, 403, 5xx or a timeout, drop the missing-artifact family or the
oversize check, let READY ignore a BLOCKED label): all 12 caught. All 69 real HARD + START edges in the current
catalog carry a status (30 READY, 39 NOT_READY), so requiring a status loses nothing.

## What this does not show

No GitHub CI, no installation (the root helper and policy hashes are unchanged until a separate gate), no live
Plane write or SCH lifecycle synchronization, no governed Release, Environment or Hardware identity.

## Earlier runs kept as history

Both are byte for byte as captured; neither is committed-source evidence.

- `runs/run-1-uncommitted/`: `check-test-strategy` failed because the collector test file belonged to no declared suite.
  I first removed the test file; Codex review rejected that. The tests are restored, declared in `ci/test-strategy.json`
  and executed by the existing CI step "Host Plane transition tests (offline)", and run-3 records them passing.
- `runs/run-2-uncommitted/`: the tree Codex reviewed (no collector tests, 8 input hashes). Superseded by run-3.
