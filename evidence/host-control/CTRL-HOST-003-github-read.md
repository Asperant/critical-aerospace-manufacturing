# CTRL-HOST-003 — deterministic GitHub evidence-reference read failure

Owner: Asrın Dündar (Asperant), authorized control-plane defect investigation.
Date: 2026-10-25. Change class: C1 compatible native-evidence parser repair;
no requirement, architecture, lifecycle predicate or authentication policy change.
Branch: control/CTRL-HOST-003-artifact-reference-read, based on merged main
`328052282fb3e5b660fb9be2009d24feb6a74dc5`. EVT-002's implementation branch,
product files, PR #76 and Plane lifecycle are unchanged by this control fix.

## Exact failure and one read-only reproduction

PR #76 head: `b46bf2e7a2acb40bf67b5f55ac2bb54053c6b560`.
The installed `GitHub._get` maps a failed gh GET (other than its specific HTTP
401 case) to `GITHUB_READ_UNAVAILABLE`. MERGE_READY's sequence is PR binding,
SHA-bound check/status and technical Actions job evidence, PR governance/artifact
reads, complete PR file inventory/fresh PR read, then comparison with main.

The first and only pre-fix read-path reproduction called the installed reader's
`pr_fact`, `ci` and `pr_governance` methods, without `evaluate`, `execute`, `main`,
any lifecycle launcher or any Plane client. Thirteen GETs were attempted. Login,
PR/head, checks/status, both required technical Actions runs/jobs and four evidence
files succeeded. The fifth evidence file failed:

```
GET repos/Asperant/critical-aerospace-manufacturing/contents/evidence/WP-EVT-002/WORLD-SCOPE-SLICE.md.?ref=b46bf2e7a2acb40bf67b5f55ac2bb54053c6b560
gh exit: 1
HTTP: 404
API status/message: 404 / Not Found
reader result: DENIED / GITHUB_READ_UNAVAILABLE
```

The PR's bare `repo:evidence/WP-EVT-002/WORLD-SCOPE-SLICE.md.` sentence includes
prose punctuation. `artifact_refs` included the final period in the filename,
so the reader queried a different, nonexistent path. The normal direct GET of
`WORLD-SCOPE-SLICE.md` at the same SHA returned the actual file (2336 bytes).
This explains why direct PR/CI/mergeability reads succeeded while governance did
not. Earlier descriptions of a transient provider outage were incorrect.

Sanitized per-read diagnostics, return codes, response sizes, failing status and
installed reader SHA-256 are in `CTRL-HOST-003-github-read.json` beside this file.
No credentials, token values, response bodies or full environment were recorded.

## Authentication, environment and other candidate causes

- The reproduction used `/usr/bin/gh`, the reader's explicit clean environment,
  `GH_CONFIG_DIR=/srv/ailab/user-profiles/asrin/gh`, cwd `/`, 30-second timeout,
  effective UID/GID 1001/1001 and the existing Asrin login. The installed reader's
  `/user` check confirmed Asperant. No credentials were copied or refreshed.
- Because reproduction ran unprivileged, it retained supplementary groups instead
  of invoking root's `extra_groups=()` drop. That limitation is explicit; the
  same authenticated context successfully accessed the other evidence, and the
  malformed filename is sufficient to reproduce the HTTP 404 deterministically.
- At direct comparison, core API quota was 4674/5000 remaining. The observed
  failure was 404, not 401, 403 or 429; auth/quota/network repairs are not indicated.
- `_get` caches successful responses by exact route for one client; failed reads
  are not cached and no API retry is performed. Parsed JSON/CI counts and required
  run/job binding checks succeeded before the bad artifact path was requested.
- The same expected PR/head SHA was returned. Pagination/stale-head mismatches
  were not observed. The reproduction acquired no shared Plane lock, establishing
  that lock contention does not cause this malformed-path failure.

## Smallest fail-closed fix and focused regression

`tools/host/plane-transition/transition.py:artifact_refs` now treats terminal full
stops before whitespace/end-of-text as prose delimiters for **bare** repo tokens.
Internal dots are preserved. Code spans, including multi-backtick spans, and
Markdown destinations retain literal filenames, including terminal dots. There
is no alternate-file lookup, filesystem fallback, auth change, generic retry or
changed `_get` error handling. The exact parsed artifact must still exist and be
a nonempty file at the assessed SHA; invalid paths/SHAs and UNKNOWN still fail.

`tools/host/plane-transition/test_artifact_refs.py` reproduces the actual PR #76
governance field and resulting contents API route, with a mocked 404 for the old
path. It also checks prose/quoted/Markdown behavior, internal dots, deduplication,
artifact IDs, genuinely absent files, no literal-path substitution, traversal,
invalid SHA and empty/non-file rejection. No live lifecycle operation is tested.

Executed from the isolated control worktree:

- `python -m unittest discover -s tools/host/plane-transition -p test_artifact_refs.py -v`:
  **8 tests PASS**.
- `python -m unittest discover -s tools/host/plane-transition -p test_transition.py -q`:
  **69 tests PASS** (existing control-plane regressions).
- Repository-pinned Ruff check/format for the new test module: **PASS** after
  combining two nested context managers; no assertions were weakened.
- `git diff --check`: **PASS**.

No full repository suite, product test, Plane mutation, MERGE_READY invocation,
PR #76 merge, Selman auth repair or broader GitHub cleanup was performed.

## Deployment blocker and truthful retry disposition

Normal procedure in `tools/host/plane-transition/README.md` requires clean merged
reference source and the supported root installer, including policy/helper hash
refresh and root-only backup/rollback. This repair is committed on its isolated
control branch; it is not merged or installed, and no raw helper overwrite is
attempted. No control PR or broad automatic CI run is launched by this bounded
commit-only repair.

Authorization preflight lists general sudo with authentication, while NOPASSWD
grants cover fixed queue/lifecycle/health operations, not the installer. A read-only
`sudo -n /usr/bin/test -r /etc/cap-plane-queue/transition-policy.json` failed with
`sudo: interactive authentication is required`. No secret was read and no
authentication or sudo configuration was changed. The safe deployment procedure
therefore cannot be executed in this session.

Post-deployment same-path verification: **NOT EXECUTED**, deployment blocked.
Installed reader is unchanged. MERGE_READY safe to retry: **NO**. After the control
fix is merged and normally installed by an authenticated operator, verify the same
GET-only path once before separately authorizing another lifecycle retry. This
record neither invents that result nor invokes a transition to test the repair.
