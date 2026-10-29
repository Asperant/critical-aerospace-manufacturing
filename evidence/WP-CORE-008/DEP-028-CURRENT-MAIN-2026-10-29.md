# DEP-028 Current-Main Dispatch Evidence — 2026-10-29

This is the post-merge rerun of the missing dispatch-specific scenario. Source
and runtime verification are bound to `origin/main` at
`ec8955b9f9f41eb78e9d1384ef155387be5fe6a8`, the merge SHA of PR #208.

## Deterministic identity

- WorldID: `DEMO-WORLD`
- CorrelationID: `wp-core-008-dep028-current-main`
- HoldID: `DEMO-HOLD-DISPATCH-002`
- Held lot: `DEMO-LOT-DISPATCH-HOLD-002`
- Open lot: `DEMO-LOT-DISPATCH-OPEN-002`
- Hold command: `55555555-5555-4555-8555-555555555561`
- Illegal dispatch command: `55555555-5555-4555-8555-555555555562`
- Legal dispatch command: `55555555-5555-4555-8555-555555555563`

## Core persistence and guard behavior

Both lots were created only as deterministic setup rows with
`revision=dispatch-rev-2`, `lifecycle_state=CREATED`, and
`execution_state=QUEUED`. The actual hold/dispatch operations used the real
Core transition service with autocommit enabled so each command outcome was
durable.

| Command | OutcomeID | Status | Error / effect |
| --- | --- | --- | --- |
| Place hold | `5ef2bf7b-20fb-4540-919a-3cb03880a0d3` | `ACCEPTED` | active material hold persisted |
| Dispatch held lot | `36266fc3-0e28-4bf8-a74e-5494425e896a` | `REJECTED` | `ACTIVE_HOLD`; `active material hold blocks dispatch`; no outbox row |
| Dispatch open lot | `de0d0b2f-a59f-409a-87fd-bf0bbfc0b3c2` | `ACCEPTED` | execution changed `QUEUED → DISPATCHED` |

Final PostgreSQL state:

- held lot: `revision=dispatch-rev-2`, state revision `dispatch-rev-2`,
  lifecycle `CREATED`, execution `QUEUED`, active hold `true`
- open lot: revision and state revision
  `b43d21235ba44eb9bc4473ba0d36a178`, lifecycle `CREATED`, execution
  `DISPATCHED`, active hold `false`

All three outcomes retain `effect_verification=NOT_VERIFIED`; this evidence
does not confuse command acceptance with downstream effect verification.

## Transactional outbox and JetStream

| Transition | OutboxID | EventID | Event type | Publication | CausationID |
| --- | --- | --- | --- | --- | --- |
| hold | `f2cecf2e-dccb-4400-9c58-35f44dfd18bd` | `60a585c7-03a3-4226-82ad-1ad9837d997c` | `production.lot-held` | `PUBLISHED` | hold command |
| dispatch | `446961d8-ecad-4e33-98ec-4dacda8d9e98` | `e93172fd-41ba-441e-aeb1-ecde5d0a33cd` | `production.lot-dispatch-authorized` | `PUBLISHED` | legal dispatch command |

Both rows have `world_id=DEMO-WORLD` and the scenario correlation ID. The
rejected command has no outbox record.

JetStream observation after the rerun:

- stream `CAP_EVENTS`, subject `cap.core.events`, 5 messages
- durable consumer `twin-primary`, `deliver_policy=all`, `ack_policy=explicit`
- `consumer_seq=15`, `stream_seq=5`, `num_ack_pending=0`,
  `num_redelivered=1`

The single redelivery is the previously recorded recovery from the consumer
crash before PR #208; the current-main rerun completed with no pending
acknowledgement and a healthy Twin service.

## Twin result

Event `e93172fd-41ba-441e-aeb1-ecde5d0a33cd` is present in PostgreSQL under
`consumer_scope=twin-primary` and projected as:

- `Lot/DEMO-LOT-DISPATCH-OPEN-002`
- WorldID `DEMO-WORLD`, branch `PRIMARY`, aggregate version `1`
- `source_event_id` and `source_revision` equal to the EventID
- dispatch ID `55555555-5555-4555-8555-555555555563`
- `dispatchable=true`, `epistemic_class=OBSERVED`
- projection revision status `FRESH`

## Result

`DEP-028 = PASS` on merged current main for its precise hold/dispatch legal and
illegal transition predicate. CORE-004 remains parked. This is not a claim of
WP-CORE-008 DONE or production security acceptance.
