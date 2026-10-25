# WP-EVT-001 resolved-definition compatibility slice

Date: 2026-10-25 (Europe/Istanbul).
Base: 889320682edc407d5b82f2583bea149b140e22af.
Branch: wp/WP-EVT-001-event-contracts.
Live queue: status OK, current WP-EVT-001 IN_PROGRESS, blocked false.
Read projectctl context for this WP, the architecture compatibility rules, and the
existing START/exemplar and reference-slice evidence. No lifecycle writes.

Implemented in the existing compatibility detector:

- Pure compare_schemas resolves internal references before comparing effective
  shape; compare_contracts inherits this and retains authority/semantic checks.
- compare_schema_files loads independently pinned old/new roots and approved
  dependencies through the existing loader. Missing, invalid, unapproved, cyclic,
  remote, escaped or drifted inputs become labelled unverifiable results.
- After successful resolution/validation, definition containers are removed.
  A single allOf branch is flattened only with nonconflicting annotation siblings;
  validation siblings remain unsupported because merging scopes can change meaning.
- Effective optional additions remain non-breaking; required removals, incompatible
  field/type/constraint/semantic changes remain breaking. Target names alone do not
  determine compatibility, and unresolved strings are never compared as proof.

Focused verification with pinned `uv run --project ci --locked` toolchain:

- `pytest -c ci/pyproject.toml ci/tests/test_contract_resolved_compatibility.py
  ci/tests/test_contract_compatibility.py ci/tests/test_contract_schema_references.py
  -q`: 108 passed in 1.09s (37 new, 71 existing compatibility/reference tests).
- `ruff check` and `ruff format --check` on the three changed Python files:
  compatibility.py, __init__.py, test_contract_resolved_compatibility.py: pass.
- `pyright` on those same files: zero errors/warnings/informations.
- `git diff --check`: pass.

Initial run: 105 focused tests passed; static checking found two errors from one
inferred nested test dictionary. Added its explicit annotation. Later checks passed.
Final coverage additionally exercises safe handling of validation siblings and a
changed approved file target with both equivalent and incompatible effective shapes.
No tests were removed or weakened. TEST-EVT-001-004 identifies the new focused tests.

Limits: the existing bounded supported schema subset remains. General composition,
validation siblings, conflicting annotations, formats, IDs and other unsupported
keywords stay unverifiable. File comparison performs read-only I/O; pure comparison
resolves internal pointers only, with no file approval context. Existing loader hash,
containment and expansion-limit protections are reused without modification.
This is structural policy evidence, not consumer/integration/scenario acceptance,
readiness, full WP DoD or DONE evidence. No broad/full suites or CI were run, and
no workflow, envelope, NATS, ACL, Plane or PR changes were made.

Next smallest slice: enforce breaking-change major-version rules against the
comparison result, with focused tests and no CI workflow change.
