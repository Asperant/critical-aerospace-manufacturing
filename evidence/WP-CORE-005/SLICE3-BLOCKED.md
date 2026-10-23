# WP-CORE-005 Slice 3 — publication binding unavailable

Assessed by Asrın Dündar's developer agent, 2026-10-23, from implementation
`c2a67aef020c82255c59b4857b5637c8a754f5d5` on the existing WP branch.
Fresh live queue confirmed Asrın's WP-CORE-005 IN_PROGRESS; context retrieved.
No Plane state/blocker projection was changed.

02 Architecture lines 1565–1571 select real NATS JetStream and require committed
outbox facts to remain pending until broker acknowledgement. Duplicate publication
after a crash between acknowledgement and local completion is explicitly possible.
The relay must not hold a database transaction across the remote publish call
(02 line 1561). No relay implementation or status migration is claimed here.

Missing exact input: the Core publication StreamDefinition / subject routing,
world separation and canonical publisher ACL binding. 01 Item 36 §§9–15
(lines 56545–56669) require bounded-context stream families and StreamDefinition
metadata. WP-EVT-001 explicitly owns the canonical producer registry and broker
subject ACLs (04 lines 749–780); WP-EVT-002 owns shared envelope/world scoping.
The Slice 1 schemas do not provide this publication binding.

The existing `ci/integration/test_runtime_services.py` uses a random isolated
`CI_SMOKE_*` stream and `ci.smoke.*` subject. It proves broker capability, not a
production Core routing/authority contract. No bound Core stream configuration
was found in the inspected source; no CI_NATS_URL was supplied. No real broker
was exercised for this slice, and runtime readiness is not inferred from static
planning NOT_READY values or the absence of a local environment variable.

Exact related readiness obligations (05 lines 1567–1600):
- DEP-023: DN-EVT-CONTRACTS@CONTRACT_READY -> DN-EVT-SPINE at INTEGRATION;
  contract merged, contract tests green, example fixture published.
- DEP-025: DN-RT-NATS@INTEGRATION_READY -> DN-EVT-SPINE at INTEGRATION;
  real JetStream in CI and INTEGRATION; no fake-bus fallback. Runtime owner Yavuz.
- DEP-024: DN-CORE-OUTBOX@INTEGRATION_READY -> DN-EVT-SPINE at INTEGRATION;
  real outbox -> NATS -> consumer evidence remains unproduced.
These are spine integration edges, not newly invented CORE-005 HARD START gates.
The immediate slice blocker is the unbound publication contract and unverified
real-broker path, not a requirement that all producer WPs be DONE.

Per the user's explicit stop condition, product code, schema, grants and tests
were left unchanged. Tests/type/lint/migration execution: NOT_EXECUTED for Slice 3;
only evidence diff hygiene checked. Earlier 49 PostgreSQL tests are not relay
evidence. No fake publisher/production contract or ad hoc stream was introduced.

Next action: obtain the attributable current-revision Core stream/subject/world/
publisher binding through WP-EVT-001/002 and an evidenced real JetStream test
path. Then implement one bounded pending -> publish/ack -> completion pass,
retaining pending state on failure, and verify redelivery against real JetStream.
The separate ReleaseLot / DN-CORE-LIFECYCLE blocker remains unchanged.
