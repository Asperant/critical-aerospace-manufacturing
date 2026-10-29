# Demo technical cheat sheet

- **What does Core do?** Core owns canonical manufacturing state and accepts
  the typed `PlaceLotOnHold` command. The demo Core adapter calls the existing
  transition service.
- **Why transactional outbox?** The accepted PostgreSQL mutation and its domain
  event are committed together, so a committed hold cannot silently lose its
  event before relay publication.
- **Why NATS/JetStream?** JetStream provides the durable event stream and
  explicit-ack consumer boundary used by the Twin worker.
- **What is Twin?** A rebuildable, PostgreSQL-backed projection of source
  events. It is read-only from the BFF/UI perspective and is not canonical
  manufacturing truth.
- **Why BFF?** The browser talks to one server boundary. The BFF owns the
  Keycloak-backed session and reads the Twin contract without exposing tokens or
  private service/database details to the browser.
- **What does Keycloak provide?** Local demo OpenID Connect authentication and
  the `demo.operator` identity. The local realm uses HTTP and demo-only cookie
  settings; this is not production security acceptance.
- **Where is PostgreSQL used?** Core tables, command outcomes and outbox rows;
  Twin projection, revision and applied-event tables; and the shared runtime
  support databases defined by Compose.
- **How does idempotency work?** Core binds a command ID/idempotency key to its
  durable command outcome; Twin also records the EventID in its applied-event
  ledger and JetStream uses a durable consumer.
- **How do you know the event was processed?** `verify` binds one EventID to the
  Core outbox row, `twin-primary` ledger row, Twin projection source revision,
  fresh projection revision, BFF result, and authenticated UI result.
- **Source state vs Twin projection?** Core PostgreSQL is the authoritative
  source state. Twin is a rebuildable read model with source EventID and
  freshness metadata; a projection being fresh does not make it authoritative.
- **What happens if the consumer retries?** JetStream redelivers until the
  consumer acknowledges. The Twin ledger and projection logic preserve event
  identity and reject stale/gapped application rather than silently advancing.
- **What is real vs demo-only?** The command, PostgreSQL mutation, outbox,
  relay, NATS/JetStream, Twin consumer, BFF, Keycloak login and browser are real
  local runtime components. The world, lot, credentials, localhost HTTP and
  seeded fixture are demo-only.
- **What is intentionally not production-ready?** This is not certified
  aerospace manufacturing software, a MES/QMS/ERP replacement, CNC/PLC control,
  autonomous factory control, or production security acceptance. CORE-004
  protected rework remains parked.
