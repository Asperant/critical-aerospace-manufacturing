# WP-EVT-001 producer-authority validation slice

Date: 2026-10-25 (Europe/Istanbul).
Base: edbf1ef2c4a969ef405171c691a5d5ae8c1134b6.
Branch: wp/WP-EVT-001-event-contracts.
Live queue: OK, current WP-EVT-001 IN_PROGRESS, blocked false.
Read projectctl context, architecture Data / Semantic Authority Map and Canonical
Producer Rule, and services/manufacturing-core/contracts/v1/README.md before coding.

Delivered an explicit producer-authorities.json model separate from declarations,
a ProducerAuthorities validator and Registry.verify_authorities. The initial binding
is narrowly derived from existing canonical/producer documentation: manufacturing-core,
Asrın Dündar, core.order-query, QUERY, the existing exact read-only authority, and
producer-owned services/manufacturing-core/contracts/ artifact paths. No authority
for other producers/families is inferred. Unknown/ambiguous or conflicting registrations
fail closed rather than gaining authority from their own declaration text.

Validation rejects unknown producers, mismatched semantic owner/type/authority/family,
consumer-as-producer claims, duplicate producers/families, overlapping source ownership,
placeholder/missing metadata and foreign root-schema/fixture paths. With repo_root,
physical containment prevents source symlinks from escaping registered ownership.
Declaration parsing still requires exactly one explicit producer. Existing root and
transitive reference approval/hash verification is unchanged.

CI now materializes the committed model and validates every declaration before any
unchanged comparison shortcut. A candidate model is mandatory. Historical snapshots
predating the model are checked against the candidate model, not exempted; existing
baseline models are loaded independently and malformed models fail closed.

Focused checks with pinned `uv run --project ci --locked` toolchain:

- `pytest -c ci/pyproject.toml ci/tests/test_contract_producer_authority.py
  ci/tests/test_contract_ci_gate.py -q`: 64 passed in 1.09s (35 new authority cases,
  29 gate regression cases). TEST-EVT-001-007 identifies the new focused tests.
- The real Core registry passes verify_authorities with physical containment and
  its existing Registry.verify hashes, schemas and fixtures. A pre-model baseline
  containing the same exact published artifacts also passes the current gate.
- `ruff check`, `ruff format --check` and `pyright` on the six changed Python files:
  authority.py, registry.py, __init__.py, ci_gate.py, test_contract_producer_authority.py,
  test_contract_ci_gate.py: pass; all 6 formatted, 0 type errors/warnings/informations.
- `git diff --check`: pass.

Initial focused run: 63 passed, one existing missing-registry test instead encountered
the newly required missing ownership model. Its fixture now supplies a valid model
so the original REGISTRY_MISSING assertion still checks the intended failure. The
new tests initially imported a private snapshot helper; strict typing rejected that.
They now use exact existing producer-owned artifacts through the public gate API.
The gate fixture helper registers its isolated synthetic artifact layout explicitly;
the production model remains limited to Core's actual producer-owned contract path.
The existing forged-producer test now expects the stronger earlier PRODUCER_UNKNOWN
rejection instead of reaching the compatibility/version stage. No rejection was weakened
and no failing test was removed.

Limits: this is static catalog/artifact ownership validation, not authenticated
publisher identity, runtime business authorization or broker enforcement. Callers
outside the CI gate explicitly invoke Registry.verify_authorities; declaration parsing
and schema-only validation remain separate primitives. Modifying the ownership model
itself needs canonical ownership evidence and applicable semantic change control;
it is not a self-registration API. No alternative project-management truth is added.

No workflow/policy-pinned source, Core declaration/schema/fixture, event envelope,
broker/NATS, subject ACL, Plane/lifecycle or PR was changed. No broad/full suites,
remote CI success, real integrated acceptance, dependency readiness or WP DONE is claimed.
Next smallest slice: pre-freeze contract naming reconciliation (GAP-RTM-009/010).
