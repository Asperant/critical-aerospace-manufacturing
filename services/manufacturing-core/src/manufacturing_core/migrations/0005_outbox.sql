-- WP-CORE-005: Core-owned immutable event intents and relay status.
CREATE TABLE core.lot_event_sequence (
    lot_id text PRIMARY KEY REFERENCES core.lot(id),
    next_version bigint NOT NULL DEFAULT 0 CHECK (next_version >= 0)
);

CREATE TABLE core.outbox (
    outbox_id text PRIMARY KEY CHECK (outbox_id ~ '\S'),
    event jsonb NOT NULL CHECK (jsonb_typeof(event) = 'object'),
    event_id text GENERATED ALWAYS AS (event ->> 'event_id') STORED
        NOT NULL UNIQUE CHECK (event_id ~ '\S'),
    event_type text GENERATED ALWAYS AS (event ->> 'event_type') STORED
        NOT NULL CHECK (event_type IN ('production.lot-held', 'production.lot-dispatch-authorized')),
    schema_version integer GENERATED ALWAYS AS ((event ->> 'schema_version')::integer) STORED
        NOT NULL CHECK (schema_version IN (1, 2)),
    aggregate_id text GENERATED ALWAYS AS (event -> 'payload' ->> 'aggregate_id') STORED
        NOT NULL CHECK (aggregate_id ~ '\S'),
    aggregate_version bigint GENERATED ALWAYS AS ((event -> 'payload' ->> 'aggregate_version')::bigint) STORED
        NOT NULL CHECK (aggregate_version > 0),
    payload jsonb GENERATED ALWAYS AS (event -> 'payload') STORED
        NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    world_id text GENERATED ALWAYS AS (event ->> 'world_id') STORED
        NOT NULL CHECK (world_id ~ '\S'),
    correlation_id text GENERATED ALWAYS AS (event ->> 'correlation_id') STORED
        NOT NULL CHECK (correlation_id ~ '\S'),
    causation_id text GENERATED ALWAYS AS (event ->> 'causation_id') STORED,
    trace_id text GENERATED ALWAYS AS (event ->> 'trace_id') STORED
        NOT NULL CHECK (trace_id ~ '\S'),
    occurred_at timestamptz NOT NULL CHECK (isfinite(occurred_at)),
    created_at timestamptz NOT NULL CHECK (isfinite(created_at)),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    last_error text,
    publication_status text NOT NULL DEFAULT 'PENDING'
        CHECK (publication_status IN ('PENDING', 'PUBLISHED')),
    CHECK ((event ->> 'producer') = 'manufacturing-core'),
    CHECK (jsonb_typeof(event -> 'occurred_at') = 'object'
        AND event -> 'occurred_at' ->> 'clock' = 'UTC'
        AND event -> 'occurred_at' ->> 'value' IS NOT NULL),
    CHECK (jsonb_typeof(event -> 'entity_refs') = 'array'),
    CHECK (
        (event_type = 'production.lot-held'
            AND payload ->> 'lot_id' = aggregate_id
            AND payload ->> 'event_type' = event_type
            AND payload ->> 'schema_version' = schema_version::text
            AND payload ->> 'aggregate_version' = aggregate_version::text)
        OR
        (event_type = 'production.lot-dispatch-authorized'
            AND payload ->> 'lot_id' = aggregate_id
            AND payload ->> 'event_type' = event_type
            AND schema_version = 1
            AND payload ->> 'schema_version' = '1'
            AND payload ->> 'aggregate_version' = aggregate_version::text)
    )
);

CREATE INDEX outbox_pending_created ON core.outbox(publication_status, created_at, outbox_id);
