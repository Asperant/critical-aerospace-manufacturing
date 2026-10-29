# WP-VIS-001 slice 3 — serving worker

Canonical requirements: FR-VIS-001, FR-VIS-009, TEST-VIS-PIPELINE,
TEST-EVT-SCHEMA.

The serving slice adds a fail-closed asynchronous worker. It accepts the
canonical `InspectionRequested`/`RunInspection` envelope only from the
configured Core/Simulator producer allowlist and exact world scope, parses the
existing Vision request boundary, reads `ArtifactReference` bytes through the
real `cap_artifacts.ArtifactStore` reader, validates the resulting
`vision.inspection-observation.v1` payload, publishes an enveloped observation
to the configured JetStream subject, and ACKs only after publication.

Malformed envelopes, unsupported event types, wrong producers/worlds, Oracle
artifacts, artifact integrity/read failures, inference failures, and publisher
failures NAK the delivery and publish no fabricated result. The worker does not
mutate Core state; Core remains the authority for normalized InspectionResult
and quality/manufacturing transitions.

The runtime binding verifies an existing stream and durable consumer but does
not provision broker topology. SeaweedFS, NATS, promoted model packages, and
real end-to-end scenario acceptance remain deployment/evidence gates.
