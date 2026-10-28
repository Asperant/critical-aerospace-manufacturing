# Architecture rules: catalog and exception process (WP-TEST-007)

`ci/scripts/check_architecture_boundaries.py` (WP-EVT-005, Asrın) checks the
repository-level architecture boundaries without starting a service. It runs in the
`static` job and `ci-gate` requires it. WP-TEST-007 adds the identity of each rule, the
requirements it protects, and a defined exception process.

## Catalog: `rules.json`

| Rule | Checks | Protects | Exception |
|---|---|---|---|
| BR-01 | every contract declares one registered canonical producer; ids are unique | FR-EVT-008 | not allowed |
| BR-02 | a service other than manufacturing-core imports no database driver or ORM | FR-EVT-007, FR-CORE-013 | allowed |
| BR-03 | a service other than manufacturing-core does not import `manufacturing_core` | FR-EVT-001, FR-CORE-013 | allowed |
| BR-04 | service source assigns no literal credential | FR-SEC-002 | not allowed |
| BR-05 | exceptions are well-formed, approved, unexpired, within the limit and still needed | none of its own | not allowed |

A violation is printed with its rule, the requirements it protects (with their
allocated architecture components) and the rule owner:

```
VIOLATION [BR-02] services/x/src/a.py:3: private database import outside manufacturing-core
  rule: BR-02 - A service other than manufacturing-core does not import a database driver or ORM
  protects: FR-EVT-007, FR-CORE-013 (architecture ARCH-CTR-API, ARCH-CORE-DB, ARCH-CORE-CMD); rule owner Asrın
  fix the code, or record a temporary exception in ci/architecture/exceptions.json backed by an approved CHG
```

`ci/tests/test_architecture_rules.py` keeps the catalog true: every rule id the checker
emits is cataloged, each rule's `architecture` equals the union of its requirements'
`ALLOCATED_TO` in 03 §17, and its requirements are active in `requirements/catalog.json`.
A new rule needs its checker, a negative test and a catalog entry.

## Exception process: `exceptions.json`

An exception is a **temporary development allowance**, not a waiver. The canonical
rule is that informal final waivers are prohibited and a known limitation never turns
a failure into a pass (01, Requirement Waivers): an exception does not waive a
requirement, does not change acceptance, and DONE still needs the requirement's real
evidence. It follows the owner / reason / expiry shape of 01's suppression rule.

Each entry needs:

| Field | Rule |
|---|---|
| `id` | unique |
| `rule` | a cataloged rule with `exception_allowed: true` (BR-02, BR-03) |
| `path` | an existing repository file; an exception covers that rule in that file only |
| `owner` | who answers for removing it |
| `reason` | what is excepted and why (at least 20 characters) |
| `chg` | a change in `09_change/change_requests.csv` whose decision is `APPROVED` or `APPROVED_WITH_CONDITIONS` (`DRAFT` does not count) |
| `expires` | an ISO date in the future, at most 90 days from today |

Consequences, all enforced by the checker (`BR-05`):

- An invalid exception is rejected and the violation it was meant to cover stays reported.
- An expired exception stops covering its violation on its expiry date.
- An exception that no longer matches a violation is **stale** and fails the check: remove it.
- An unreadable or unknown-schema registry fails closed; it is never read as "no exceptions".
- Applied exceptions are listed on every run (`EXCEPTED ... until <date>`), so they stay visible.
- Credentials (BR-04), producer authority (BR-01) and the process itself (BR-05) accept no exception.

Empty is the normal state. A test asserts the committed registry is empty, so adding an
exception also means editing that test, which makes it visible in the diff.
