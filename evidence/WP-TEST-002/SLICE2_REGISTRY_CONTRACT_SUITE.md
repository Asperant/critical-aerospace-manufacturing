# WP-TEST-002 slice 2 — registered contract suite

The WP-TEST-002 suite now exercises the current registry as a whole. Every
registered producer-owned fixture is validated at both producer and consumer
boundaries, producer-authority bindings are re-verified against repository
paths, and the DEP-021 request schema has explicit valid and negative cases.
The real declarations and hash-verified schemas are also passed through the
compatibility detector; generic breaking-change/version-policy tests remain in
the existing contract compatibility suite.

This is static contract evidence only. It does not claim broker, database,
outbox, or end-to-end runtime acceptance.
