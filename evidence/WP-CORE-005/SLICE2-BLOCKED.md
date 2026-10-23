# WP-CORE-005 Slice 2 — blocked before implementation

Assessed by Asrın Dündar's developer agent on 2026-10-23.
Branch: `wp/WP-CORE-005-domain-events-outbox`.
Existing implementation: `3eb9a96fe874446fad60e8673e2b027524b700e2`.

Fresh `cap-plane-queue` returned OK / CURRENT, WP-CORE-005 IN_PROGRESS,
assigned to Asrın, without an active blocker. WP-CORE-001 remains a deferred
VALIDATING + BLOCKED downstream-acceptance wait. Queue health was UNAVAILABLE;
the live task itself was available. `projectctl context WP-CORE-005` was read.
No Plane state or blocker projection was changed.

## Candidate and missing consumer binding

The smallest candidate is `ReleaseLot`: Lot lifecycle CREATED -> RELEASED,
producing Slice 1's `production.LotReleased` / schema version "1".
Canonical sources: 01 Master Specification, Item 11 §2 (lines 6948–6966),
and 02 Architecture, lifecycle state machines / domain command discipline
(lines 1726–1730 and 1762–1766).

The actual current `Lot` model has only id, revision and order_id. Migration
`0001_domain.sql` stores those fields, and `CoreRepository` provides insert/read
only. The runtime role has SELECT/INSERT, not state UPDATE. No existing release
handler, persisted source lifecycle state, exact release-eligibility contract,
revision mutation contract or duplicate-command binding was found in this
implementation or the published v1 contracts.

The event schema describes a fact, not command acceptance. A unique event_id
alone would not prove canonical command idempotency: repeated commands could
carry different event IDs. Inventing release policy or treating all existing
lots as CREATED would manufacture missing semantics. An arbitrary revision
UPDATE, a parallel release-state store, or test-only canonical mutation would
not meet the requested domain-transition proof.

04 WBS WP-CORE-002 (lines 433–463) allocates authoritative transition guards and
handlers; WP-CORE-003 (lines 475–510) allocates versioned command contracts,
idempotency semantics, revision validation and durable outcomes. Their missing
implementation cannot silently be replaced by an outbox helper. DEP-022 is
still HARD at INTEGRATION, not START: this assessment does not turn it into a
blanket START gate or require the producer WP to be DONE. It identifies the
missing exact lifecycle/command artifact required for this particular proof.

## Verification environment and outcome

Direct local Docker access was denied at `/var/run/docker.sock`.
`sudo -n /usr/bin/docker version` also failed: interactive authentication is
required. No local PostgreSQL server binaries or supplied CI_PG_DSN were found.
The existing PostgreSQL 18 CI job is a possible future verification path;
it was not dispatched and its previous runs are not Slice 2 evidence.

No product code, migrations, grants or tests were changed. PostgreSQL tests,
lint/type checks and migration execution: NOT_EXECUTED for Slice 2. Slice 1's
100 passing tests are historical and are not claimed as Slice 2 verification.
Only evidence diff hygiene is checked for this change.

Resolution owner: Asrın (Core semantics), with canonical supporting routing to
Batuhan for transition/command consumer semantics. Required next input is an
exact current-revision lifecycle/ReleaseLot command binding, or an explicit
canonical scope decision resolving where that minimal transition is produced.
Then implement one real state mutation plus matching outbox insert in a single
transaction and execute the requested focused tests on disposable PostgreSQL 18.
No relay, retries, crash-consistency claim, instrumentation or WP DONE claim.
