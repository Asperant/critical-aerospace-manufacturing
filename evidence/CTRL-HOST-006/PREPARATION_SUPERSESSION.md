# CTRL-HOST-006 preparation supersession repair

The existing controller returned before discovering open preparation PRs when a
merged preparation artifact had a stale input digest. Its fixed two-file guard
also rejected an artifact-only refresh despite correct existing CODEOWNERS routing.

The controller now discovers an existing same-WP/current-digest preparation PR
when the merged artifact differs only in `source_sha` and `input_digest`. Every
other field and key must remain identical. Semantic changes still require review;
no supersession PR is created automatically when none exists.

The GET-only PR validator requires the authenticated preparation author, open
non-draft PR on the exact derived branch, current re-derived content, PASS/N/A
mechanical checks, canonical source blob equality and source ancestry. An older
source SHA with identical canonical inputs is valid; changed canonical blobs or
non-ancestor sources fail closed. Duplicate JSON keys and malformed records fail
closed. Existing multiple-PR, CI, fresh-head, clean mergeability, before-write
revalidation and bounded mutation guards remain in place.

The diff must contain the exact preparation artifact and no product files.
CODEOWNERS must remain byte-identical when its effective routing already matches;
otherwise only the exact canonical routing append is allowed and required.
Routing shadowing and arbitrary ownership changes fail closed.

Local verification (offline fixtures, no Plane writes):
- 44 focused preparation tests PASS, including mechanical supersession, existing
  routing, missing/wrong/shadowed routing, semantic changes, multiple PRs, stale
  input/branch/source, non-ancestor source, product files and malformed evidence.
- 154 Plane transition/controller tests and 25 queue tests PASS.
- Canonical validation and requirement catalog/history lint PASS; existing source
  metadata warnings remain uncertified.
- Static ratchet (Ruff lint/format and Pyright) PASS with no new findings.
- `git diff --check` PASS.

Required remote CI, merge, supported installation and read-only live validation
must be observed separately. This repair does not execute preparation, AUTO_NEXT,
Plane transitions or product implementation, and does not merge refresh PR #45.

## Live response-format correction

Initial GET-only validation after deployment of PR #46 failed closed with
`binascii.Error: Only base64 data is allowed`. GitHub Contents API wraps base64
content with newlines; the single-line fixtures had not represented that response.
The decoder now removes line breaks before strict base64 validation. Supersession
routing fixtures use the real wrapped encoding format. No PR #45 or Plane write
occurred during this failed validation. All 44 focused preparation, 154 controller
and 25 queue tests, canonical validation, catalog lint and static checks pass with
the corrected representation.
