# WP-CORE-001 — query contract v1 slice

Owner: Asrın Dündar (Asperant). Scope: canonical WBS CORE-001 query contract v1,
fixtures and contract tests; architecture Query Contract/Integration Contract
Registry and DN-CORE-CONTRACTS. No requirement/authority change, new infrastructure,
HTTP transport, deployment, or lifecycle advancement.

Implemented `core.order-query.v1`: required typed request and response envelopes
reuse all existing domain entity models and their validation. Core's repository
supplies order/route/equipment plus order-scoped lots and components. Responses
preserve identities/revisions and route visit order; entity collections have
explicit deterministic ordering. Published generated JSON schemas and SYNTHETIC
TEST normal/reentrant fixtures include valid cross-entity references. Registry,
errors, ordering, revision and scope semantics are in `contracts/v1/README.md`.

The adapter performs only reads; database errors propagate. Invalid responses,
missing/unknown references and malformed requests fail validation. An unknown
order produces explicit ORDER_NOT_FOUND rather than an empty success. No
global snapshot revision, freshness guarantee, world binding, lifecycle state
or history interface is inferred from the current domain implementation.

## Verification

- Local focused unit run: 81 passed (47 domain + 34 contract), 29 database
  integration cases deselected; no failing or quarantined tests.
- Service Pyright: 0 errors, 0 warnings.
- Service Ruff lint/format and diff checks passed.
- Real PostgreSQL 18 round trips: pending pushed implementation's existing CI
  integration job; not claimed executed locally.

Contract tests compare published/generated schemas and exact nested wire shape,
validate both deterministic fixtures, round-trip every field, preserve repeated
class visit order/identity, reject missing/extra/version/identity/revision and
reference errors, duplicates and collection-order violations. Real database
tests load fixture entities in nonresponse order, query in a READ ONLY transaction,
compare the full serialized response, exclude unrelated order/material and test
missing-order behavior. Existing 26 persistence cases remain enabled.

Full-WP DoD and merge/post-merge evidence remain pending, including wider
architecture/auth/service-identity and scenario/benchmark verification. This
slice does not declare DN-CORE-CONTRACTS CONTRACT_READY: required merge,
consumer-specific acceptance and evidence obligations still apply. No Plane
state changes were made; WP remains IN_PROGRESS.
