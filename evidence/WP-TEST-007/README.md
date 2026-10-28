# WP-TEST-007 — Architecture rules and trace validation in CI: evidence

Owner: Yavuz Gümüş · supporting owner: Asrın (advisory, CHG-018) · F1 · M2/S3–S4 ·
readiness node DN-PLAT-REPO · requirements FR-EVT-007, FR-GOV-005.

DoR: owner assessment on issue #183 (started under CHG-054, `projectctl startability
WP-TEST-007` = STARTABLE).

## What was already there, and what this package adds

The rule checker `ci/scripts/check_architecture_boundaries.py` and its CI step belong to
WP-EVT-005 (Asrın, merged 27 October 2026); the trace linter and its CI steps belong to
WP-GOV-002. This package did not rewrite either. It added:

| Deliverable (04 card) | What was added |
|---|---|
| architecture rule checks | `ci/architecture/rules.json`: the identity (BR-01…BR-05) of each rule, the requirements it protects as worded in 01, their `ALLOCATED_TO` from 03 §17, the rule owner and whether an exception is allowed. The checker's violations carry their rule id (a `str` subclass, so existing tests and callers are unchanged) |
| trace linter integration | `ci/tests/test_required_gates.py`: the boundary check and the trace linter (`validate --base origin/main`, `drift --strict`, the PR Requirement-Impact step) cannot be skipped, made non-blocking or left out of `ci-gate`; `ci-gate` is a required status check |
| violation reporting | each violation prints its rule, the requirements it protects with their architecture components, the rule owner and what to do |
| exception process | `ci/architecture/exceptions.json` and its checks (rule BR-05), described in `ci/architecture/README.md` |

## Exception process: design decision

01 prohibits informal final waivers and says a known limitation never turns a failure into
a pass. The process is therefore a temporary **development allowance**, never a waiver: it
needs an owner, a reason, an approved CHG (decision `APPROVED` or `APPROVED_WITH_CONDITIONS`,
not `DRAFT`) and an expiry within 90 days, covers one rule in one file, is rejected for
rules that forbid exceptions (credentials, producer authority, the process itself), fails
when stale or expired, fails closed on an unreadable registry, and is listed on every run.
The 90-day limit is this package's choice, not a canonical value. The registry is empty and
a test asserts it, so adding an exception also edits that test.

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `ci/tests/test_architecture_rules.py` (TEST-TEST-007-001, 27 tests) | TEST-ARCH-BOUNDARY | FIXTURE_ALLOWED (temporary repositories) | CI t1-unit "CI tooling tests" |
| `ci/tests/test_required_gates.py` (TEST-TEST-007-002, 5 tests) | TEST-ARCH-BOUNDARY, TEST-GOV-TRACELINT | FIXTURE_ALLOWED by tier rule; it reads the real workflow and required-checks files | CI t1-unit "CI tooling tests" |
| `ci/tests/test_architecture_boundaries.py` (WP-EVT-005, 4 tests) | TEST-ARCH-BOUNDARY | unchanged, still passing | CI t1-unit |

Local run at the head of the branch: the three files 36 passed; all of `ci/tests` 768 passed;
static ratchet, test-strategy conformance, `projectctl validate` and `cap_trace validate/drift`
pass.

## Negative paths exercised

- Exception: unknown rule, a rule that forbids exceptions (BR-01, BR-04), missing or escaping
  path, empty owner, short reason, unapproved or missing CHG, a `DRAFT` CHG, non-date, past and
  today's expiry, beyond-limit expiry (and the exact 90/91-day boundary), duplicate id, stale
  exception, unreadable, wrong-schema and missing registry. In each case the covered violation
  stays reported.
- Gate wiring: the test was run against deliberately broken copies of `ci.yml` (static
  removed from the `ci-gate` needs, the boundary step made `continue-on-error`, the strict
  drift step deleted) and failed each time; the file was restored (`git checkout`) and passes.

## Findings

- **Fail-open found by the test (fixed before commit).** The first version of
  `check_exceptions` returned its "registry unreadable" violation in the list of *applied*
  exceptions, so `main()` would have printed it and still reported PASS. The negative test for
  an unreadable registry caught it; the violation now goes to the remaining list.
- **Catalog drift caught by the test (fixed).** BR-02 omitted `ARCH-CORE-CMD`, which one of its
  protected requirements is allocated to; the catalog-versus-03 test failed and the catalog was
  corrected.
- The static ratchet (zero findings allowed in this file) required explicit types around the
  untyped JSON; `cast` is used for the loaded entries.

## Known limitations

- TEST-SEC-SVCID (runtime service identity) is WP-SEC-002 and is not executed here; the runtime
  proof of FR-EVT-007 (database role separation) also stays with the integration work.
- Only the repository-level rules that WP-EVT-005 implemented are cataloged; further rules
  join as services land (rule owners per 03 TEST-ARCH-BOUNDARY, Asrın).
- `REALIZED_BY` of FR-EVT-007 is still `TBD_BY_IMPLEMENTATION` in its owner's 03 record; only a
  verification edge (TEST-TEST-007-001) was added there.
- EvidenceState stays EVIDENCE_PENDING: unit-level CI evidence, no EvidenceID invented.
