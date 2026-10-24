# WP-EVT-001 major-version rule slice

Date: 2026-10-25 (Europe/Istanbul).
Base: 1c8cad473bb98d7be0a6caaabe483d8a1179ea3b.
Branch: wp/WP-EVT-001-event-contracts.
Live queue eventually returned status OK, CURRENT WP-EVT-001 IN_PROGRESS,
blocked false. No code changes started while that read was pending.
Read projectctl context for this WP, existing START/exemplar scope and architecture
compatibility rules. No Plane/lifecycle writes.

Implemented/exported enforce_version_policy(old_id, new_id, compatibility):

- Breaking change at the same major raises BREAKING_CHANGE_REQUIRES_MAJOR.
- Verified breaking change at any higher major in the same family is allowed.
- Verified non-breaking same-major change is allowed (higher major is also allowed).
- Rollback raises VERSION_ROLLBACK; unrelated families raise CONTRACT_FAMILY_MISMATCH.
- Missing, foreign, malformed or unverifiable results raise COMPATIBILITY_UNVERIFIABLE;
  increasing the major never turns UNKNOWN into permission.

The check is explicit, pure and read-only. It consumes the existing comparison
result without changing that result, schemas, versions or deprecation status.
Registry continues to enforce replacement existence and a later major of the same
family using its unchanged implementation. File loading, approved references,
containment, cycle checks and hash/drift verification are unchanged.

Focused verification with the pinned `uv run --project ci --locked` toolchain:

- `pytest -c ci/pyproject.toml ci/tests/test_contract_version_policy.py
  ci/tests/test_contract_registry.py::test_deprecation_replacement_may_be_any_later_major_that_exists
  ci/tests/test_contract_registry.py::test_deprecation_replacement_must_exist
  ci/tests/test_contract_registry.py::test_deprecation_replacement_must_be_a_later_major_of_the_same_family
  -q`: 32 passed in 0.52s (29 new focused cases, 3 selected existing replacement tests).
- `ruff check` and `ruff format --check` on compatibility.py, __init__.py and
  test_contract_version_policy.py: pass; all 3 files formatted.
- `pyright` on those same changed Python files: zero errors/warnings/informations.
- `git diff --check`: pass.

The first focused run also passed (29 tests); no failed checks or weakened tests.
TEST-EVT-001-005 covers actual schema comparison outcomes, next/later majors,
rollback with both known and UNKNOWN results, invalid replacements and missing
replacement targets. Drifted/missing/cyclic schema results remain rejected even
with a major increase.

Limits: callers must explicitly invoke the gate with the relevant detector result;
CI wiring is not part of this slice. Schema compatibility stays bounded as documented
in earlier slices. No consumer/integration/scenario acceptance, readiness, full WP DoD
or DONE is claimed. No broad/full suites, CI workflow, envelope, broker/NATS, ACL,
Plane/lifecycle or PR work was performed.

Next smallest slice: wire the compatibility/version-policy gate into the canonical
CI contract check.
