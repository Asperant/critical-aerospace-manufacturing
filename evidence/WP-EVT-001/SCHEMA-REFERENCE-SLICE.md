# WP-EVT-001 local schema-reference slice

Date: 2026-10-25 (Europe/Istanbul).
Base: c5cec4558b776a3a1bdf0cd67d814152f9b781b8.
Branch: wp/WP-EVT-001-event-contracts.
Live queue: status OK, CURRENT WP-EVT-001, IN_PROGRESS, blocked false.
Context and the START exemplar scope in SLICE1.md were inspected. No lifecycle writes.

Implemented deterministic offline expansion in packages/contracts/references.py,
called by the existing load_schema boundary shared by BoundaryValidator and Registry.
Callers explicitly approve transitive package file dependencies with schema_refs,
a tuple of existing FileRef path/hash pins. Root and dependency hashes are checked;
expanded documents are schema-checked before boundary validation. No canonical
registry fields, schemas, producer ownership or infrastructure changed.

Focused tests: ci/tests/test_contract_schema_references.py, TEST-EVT-001-003.
Cases include pinned transitive files, fragments/escaped pointers/array indices,
producer and consumer request/output validation, registry fixtures, deterministic
output, immutability, missing targets, unapproved/remote/traversal references,
root/dependency drift, symlink escapes, internal and cross-file cycles, unused
bad definitions, ref siblings including unevaluatedProperties, invalid expanded
schemas, duplicate pins, expansion limits and the existing Core exemplar.

Final verification, pinned `uv run --project ci --locked` toolchain:

- `pytest -c ci/pyproject.toml ci/tests/test_contract_schema_references.py
  ci/tests/test_contract_registry.py ci/tests/test_contract_compatibility.py -q`:
  169 passed in 1.62s (37 reference tests, 132 existing contract regression tests).
- `ruff check` and `ruff format --check`: pass, four changed Python files
  (references.py, registry.py, boundary.py, test_contract_schema_references.py).
- `pyright` on those same four files: zero errors/warnings/informations.
- `git diff --check`: pass.

Earlier checks retained here: initial reference run had 31 passes and one failure
(malformed-pointer error classified missing before examining its later bad escape).
Initial static checks found two Ruff findings and two type-narrowing errors.
Corrected whole-pointer escape validation, Ruff findings and NoReturn typing;
subsequent focused runs passed. Final added containment, evaluation-scope and invalid
expanded-schema cases also passed; no failing tests were weakened or removed.

Limits: cycles, anchors, dynamic refs, nested ID rebasing, alternate dialects and
noncanonical file paths are rejected. File targets stay physically inside the
contracts package; internal pointers remain supported for producer-owned roots.
Expansion has a 10,000-node visit limit and recursion-depth guard. Root IDs are
identifiers; relative file resolution uses pinned package paths. The compatibility
subset remains conservative for raw refs and expanded $defs/allOf constructs.

Not run/claimed: broad/full suites, CI workflow, real broker/infrastructure/scenario
acceptance or WP DONE. No envelope, NATS, ACL, lifecycle or PR work.
Next smallest slice: compare resolved local definitions within the pure compatibility
detector, with focused tests preserving fail-closed behavior for unsupported constructs.
