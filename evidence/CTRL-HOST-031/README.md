# Evidence — CTRL-HOST-031 (finish the CHG-054 start-transition decoupling)

Control item, not a product WP: scope authority is `09_change/CHG-054.yaml` and the approved plan
(SHA-256 `9d6b4bd5cb449f8c318334d295abd7d1408593a9235231add8200e50e40c0b83`). The change is in
`tools/host/plane-transition/` (`transition.py`, tests, README). These are **offline fixture runs**
(fake Plane and GitHub objects): no credential, network, Plane write or installation, and none is a
live deployment PASS.

## Run of record

`runs/run-4-committed/` — one local run of `capture_run.py` on a **clean committed tree**: tested source commit
`e992a82a262d161c5fced8c530edea89bc51d8db` (tree `5dca8557cd8b5c0656757e1440e5b100febc7677`, `tree_clean` true, empty
changed-file manifest), rebased onto `origin/main` `1b06523ac681fb1689f5f0a8aed640c690bb31be`, started 2026-10-28T18:41:44Z,
finished 18:42:16Z, Python 3.11.16, uv 0.12.13, locked CI toolchain (`lock_sha256` in `identity.json`), Intel i7-9700K, shared host.
The commit that adds this run and this README changes only files under `evidence/CTRL-HOST-031/`, so every source, test, CI and
baseline file the run tested is unchanged (check with `git diff e992a82 <evidence commit> --stat`). The run records the tested
SHA, never its own commit. Offline fixture evidence, not CI and not an installed or live-runtime PASS.

| Command | Exit | Result |
|---|---|---|
| `focused-transition-artifact-chg054` (`test_transition`, `test_artifact_refs`, new `test_chg054_start_transitions`) | 0 | 102 passed |
| `collector-tests` (`evidence/CTRL-HOST-031/tests`, run by the existing CI host-transition step) | 0 | 6 passed |
| `focused-recovery-install` | 0 | 19 passed |
| `ci-style-unittest-discover` (the whole directory, as the CI step runs it) | 0 | 306 tests OK |
| `reproduce-on-original-source` | **1, expected** | **7 failed, 11 passed** (below) |
| `ruff-check`, `ruff-format --check` on new files and the collector | 0, 0 | clean |
| `static-ratchet` | 0 | no new findings; baseline tight after `update` |
| `check-test-strategy` | 0 | PASS (153 files, 29 suites, after integrating main) |
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

All three are byte for byte as captured; none is committed-source evidence.

- `runs/run-1-uncommitted/`: `check-test-strategy` failed because the collector test file belonged to no declared suite.
  I first removed the test file; Codex review rejected that. The tests are restored, declared in `ci/test-strategy.json`
  and executed by the existing CI step "Host Plane transition tests (offline)", and the later runs record them passing.
- `runs/run-2-uncommitted/`: the tree first reviewed (no collector tests, 8 input hashes).
- `runs/run-3-uncommitted/`: the tree Codex re-reviewed and approved (11 input hashes, base `e1752d9`), before the commits
  and the rebase onto main; its manifest hashes the pre-rebase `ci.yml` and `test-strategy.json`.
