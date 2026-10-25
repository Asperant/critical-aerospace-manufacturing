# WP-EVT-001 versioned subject binding contract slice

Date: 2026-10-25 (Europe/Istanbul).
Base: 74bd5019051c29f8c1628887765be18ee10389d0.
Branch: wp/WP-EVT-001-event-contracts.
Read-only live queue: OK / CURRENT / WP-EVT-001 IN_PROGRESS, blocked false.
Retrieved projectctl context for this WP; no Plane/lifecycle fields changed.

Canonical inputs: 01, StreamDefinition minimum metadata / Canonical Producer
Ownership / Broker ACL Enforcement and Contract Naming section 76; 02, Integration
Contract Registry, workload semantics, retention/data classification and producer
rules. Naming details implement the approved contract catalog without changing
semantic ownership, dependencies, requirements or runtime architecture. No pinned
source or canonical specification changed; no change-control ID required.

Implemented in packages/contracts only: immutable validated StreamDefinition and
SubjectBinding records plus a deterministically serialized catalog. Strict fields,
version/family checks, exact registered producer/authority validation and global
subject/binding/stream uniqueness fail closed. No wildcard ownership is canonical
in this initial format, so all wildcards and inline overrides are rejected.
Allowed publishers equal bound producers; stream owner/family and known consumers
must agree with registered declarations. Complete declared policy metadata is
required, without interpreting those strings as runtime configuration.

The bounded initial subset handles async domain events and work/commands. Other
stream classes are unsupported and rejected. Stream-definition versions are
independent from payload versions, while binding identity matches its contract
family/major. Each active contract version has one binding and each concrete
subject has one owner across the entire supplied catalog.

Focused verification using the pinned uv CI toolchain:

- pytest -c ci/pyproject.toml ci/tests/test_contract_subject_bindings.py -q:
  42 passed in 0.47s. Valid/deterministic synthetic bindings, duplicate subjects
  within/across streams, conflicting/unknown producers, invalid/wildcard subjects,
  binding/stream version and family mismatches, missing/ambiguous metadata,
  undeclared consumers, duplicate identities and query-to-event rejection.
- ruff check and ruff format --check on streams.py, __init__.py and the new test:
  pass, 3 files already formatted.
- pyright on those same files: zero errors/warnings/informations.
- git diff --check: pass.

Initial focused tests passed; initial type check identified three missing container
annotations in the new test helper. Explicit fixture types fixed those errors;
the focused tests and changed-file static checks then passed. No existing test was
edited, removed or weakened.

All async examples are synthetic. The registered core.order-query.v1 remains an
unchanged synchronous query and is explicitly rejected as a publication binding.
Existing registry, authority, drift/hash and local-reference verification are
unchanged; this pure mapping validator does not replace artifact verification.
No production subject namespace, production binding, runtime stream, envelope,
ACL generation, broker configuration, CI edit, PR or lifecycle mutation was made.
No broad suites or full WP/consumer integration/freeze acceptance is claimed.

Next smallest slice: strict catalog file loading and existing-gate validation,
including duplicate JSON-field and committed-catalog failure tests. Production
bindings still require explicit canonical async declarations; they are not inferred
from the synchronous Core query. Final ACL derivation is not implemented.
