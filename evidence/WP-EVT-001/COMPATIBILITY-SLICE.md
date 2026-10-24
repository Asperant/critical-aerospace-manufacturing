# WP-EVT-001 pure compatibility detector slice

Date: 2026-10-25 (Europe/Istanbul). Base: 9ed376c95b57fa45416679e8dba433f78b2760d2.
Scope: pure schema/declaration comparison in packages/contracts; focused synthetic
unit tests in ci/tests/test_contract_compatibility.py (TEST-EVT-001-002).
The live queue reported WP-EVT-001 IN_PROGRESS, unblocked. START exemplar and
limitations remain those recorded in SLICE1.md. No lifecycle changes were made.

Delivered: immutable result with separate breaking/unverifiable reasons; compatible
only when neither exists. Optional property additions pass; required removals,
field/type/annotation semantics and declaration authority changes are breaking.
Ambiguous/invalid/unsupported comparisons fail closed. Input/output schemas are
both checked; comparison performs no I/O and does not mutate supplied inputs.

Verification executed with the pinned CI toolchain (`uv run --project ci --locked`):

- `pytest -c ci/pyproject.toml ci/tests/test_contract_compatibility.py -q`:
  34 passed in 0.53s on final run.
- `ruff check` and `ruff format --check` on compatibility.py, __init__.py,
  versioning.py and test_contract_compatibility.py: pass (4 files formatted).
- `pyright` on those four changed Python files: 0 errors/warnings/informations.
- `git diff --check`: pass.

Earlier verification: initial 30 tests passed; initial pyright found three typing
errors (object schema argument and inferred nested test dictionary). Corrected the
types and added four malformed/constant comparison tests; final results above.

Limitations: bounded inline JSON Schema subset, no reference/composition/format
resolution; even unchanged unsupported constructs fail closed. Core's reference-based
output exemplar therefore remains unverifiable here. Schema documents must be
loaded/hash-verified by callers. Undeclared semantic changes cannot be inferred.
Optional-addition policy does not replace known-consumer compatibility tests.

Not run/claimed: broad suites, CI, broker/integration/scenario acceptance, full WP
DoD, readiness or DONE. No envelope, ACL, CI workflow, Plane or PR changes.
Next smallest slice: support and test local schema references against the existing
Core exemplar, retaining fail-closed handling for unresolved/external references.
