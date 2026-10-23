-- WP-CORE-005: fact persistence only; no lifecycle/command or publisher behavior.
CREATE TABLE core.outbox (
    outbox_id text PRIMARY KEY CHECK (outbox_id ~ '\S'),
    event jsonb NOT NULL CHECK (jsonb_typeof(event) = 'object'),
    event_id text GENERATED ALWAYS AS (event ->> 'event_id') STORED
        NOT NULL UNIQUE CHECK (event_id ~ '\S'),
    event_type text GENERATED ALWAYS AS (event ->> 'event_type') STORED NOT NULL,
    schema_version text GENERATED ALWAYS AS (event ->> 'schema_version') STORED
        NOT NULL CHECK (schema_version = '1'),
    aggregate_id text GENERATED ALWAYS AS (event ->> 'aggregate_id') STORED
        NOT NULL CHECK (aggregate_id ~ '\S'),
    aggregate_version text GENERATED ALWAYS AS (event ->> 'aggregate_version') STORED
        NOT NULL CHECK (aggregate_version ~ '\S'),
    payload jsonb GENERATED ALWAYS AS (event -> 'payload') STORED
        NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    created_at timestamptz NOT NULL CHECK (isfinite(created_at)),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count = 0),
    last_error text CHECK (last_error IS NULL),
    publication_status text NOT NULL DEFAULT 'PENDING'
        CHECK (publication_status = 'PENDING'),
    CHECK ((event ->> 'producer' = 'manufacturing-core') IS TRUE),
    CHECK ((jsonb_typeof(event -> 'event_id') = 'string'
        AND jsonb_typeof(event -> 'aggregate_id') = 'string'
        AND jsonb_typeof(event -> 'aggregate_version') = 'string'
        AND jsonb_typeof(event -> 'schema_version') = 'string') IS TRUE),
    CHECK ((CASE event_type
        WHEN 'production.LotReleased' THEN
            event ->> 'aggregate_type' = 'Lot' AND payload ->> 'lot_id' = aggregate_id
        WHEN 'production.MaterialHoldApplied' THEN
            event ->> 'aggregate_type' = 'MaterialHold'
            AND payload ->> 'material_hold_id' = aggregate_id
        WHEN 'quality.QualityExcursionConfirmed' THEN
            event ->> 'aggregate_type' = 'QualityExcursion'
            AND payload ->> 'quality_excursion_id' = aggregate_id
        WHEN 'scheduling.ScheduleActivated' THEN
            event ->> 'aggregate_type' = 'ScheduleVersion'
            AND payload ->> 'schedule_id' = aggregate_id
        ELSE false
    END) IS TRUE)
);
